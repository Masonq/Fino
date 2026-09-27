import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token, generate_code, hash_code, verify_code,
    get_current_user,
)
from app.core.database import get_db
from app.core.notify import send_code
from app.models import User, VerificationCode, VerifyChannel
from app.core.clock import utcnow
from app.core.config import settings
from app.core.names import clean_display_name

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _normalize_phone(raw: str) -> str:
    """
    Приводит к единому виду перед сравнением/сохранением — только
    цифры и, если был, ведущий '+'. Пробелы, дефисы, скобки — из
    формы ввода, не часть самого номера.

    Не решает целиком: '631801643' и '+381631801643' — один и тот же
    реальный номер, но разные строки даже после этого, потому что
    сама функция не может надёжно угадать, что голому номеру не
    хватает кода страны +381, не спрашивая человека прямо — так уже
    случилось однажды (тестовый аккаунт 'YooKassa Test' занял номер
    в формате с кодом страны, настоящий владелец — без), и это не
    единственный возможный случай, раз нормализация не решает его
    целиком. Но одинаковый ввод в разных пробелах/дефисах/скобках —
    самый частый источник таких же на вид, но разных по строке
    номеров — теперь всегда даёт одну и ту же строку.
    """
    return re.sub(r"[^\d+]", "", raw)

CODE_TTL = timedelta(minutes=15)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)


# ---------- схемы ----------
class RequestCodeIn(BaseModel):
    destination: str          # email-адрес или telegram-идентификатор
    channel: VerifyChannel = VerifyChannel.email


class VerifyCodeIn(BaseModel):
    destination: str
    code: str
    display_name: str | None = None
    channel: VerifyChannel = VerifyChannel.email
    # Язык, на котором человек сейчас смотрит сайт — на нём и напишет
    # команда в первом сообщении.
    lang: str | None = None
    # Кто пригласил — id пользователя из ссылки ?ref=<id>. Только на
    # регистрации нового человека имеет значение; для уже
    # существующего аккаунта просто игнорируется.
    referred_by: str | None = None


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "email_verified": user.email_verified,
        # Привязан ли Telegram. Признак нужен странице «Мои данные», а
        # она читает именно этот эндпоинт — в /users/me его добавить
        # было мало: там его никто не спрашивает.
        "telegram_linked": bool(user.telegram_id),
        "role": user.role.value if user.role else None,
        "must_rename": bool(user.must_rename),
    }


# ---------- вход по коду ----------
@router.post("/request-code")
def request_code(payload: RequestCodeIn, db: Session = Depends(get_db)):
    destination = payload.destination.strip().lower()
    if not destination:
        raise HTTPException(400, "destination_required")

    # не даём засыпать человека кодами
    recent = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.destination == destination,
            VerificationCode.created_at > utcnow() - RESEND_COOLDOWN,
        )
        .first()
    )
    if recent:
        raise HTTPException(429, "too_many_requests")

    code = generate_code()
    # Проверяем адрес до того, как заводить код и слать письмо.
    #
    # Раньше принимали что угодно: «wwendjsjsj@icloud», «ivan@gmial.com».
    # Человек не получал код, пробовал ещё раз и уходил, а мы тратили
    # письмо и место в базе на адрес, которого нет.
    if payload.channel == VerifyChannel.email:
        from app.core.email_check import check as check_email

        ok, why, hint = check_email(destination)
        if not ok:
            raise HTTPException(400, why)
        if hint:
            # Домен существует, но похож на опечатку. Не отказываем —
            # вдруг человек и правда там, — но подсказываем: пусть
            # решает сам.
            return {"status": "typo_suspected", "suggestion": hint}

    db.add(VerificationCode(
        destination=destination,
        channel=payload.channel,
        code_hash=hash_code(code),
        expires_at=utcnow() + CODE_TTL,
    ))
    db.commit()

    # Проверочный адрес письмом не тревожим.
    #
    # tools/healthcheck.py запрашивает код на healthcheck@plonk.local,
    # чтобы убедиться, что вход работает. Такого домена не существует,
    # и каждый прогон давал отказ, который бил по репутации нашего
    # домена у почтовых служб — той самой, что мы восстанавливаем.
    #
    # Код при этом заводится как обычно: проверке важно, что он выдан и
    # принимается, а письмо ей ни к чему.
    if destination.endswith("@plonk.local"):
        return {"status": "sent", "channel": payload.channel.value}

    try:
        send_code(destination, code, payload.channel)
    except Exception as exc:                               # noqa: BLE001
        # Говорим прямо, что письмо не ушло, и куда идти дальше.
        #
        # Раньше сбой отправки поднимался как обычная ошибка, и человек
        # видел «что-то пошло не так»: он ждал код, не получал его и
        # уходил. Сколько людей так и не зарегистрировалось, мы уже не
        # узнаем, но повторять это нельзя.
        from app.core.notify import MailUndeliverable

        if isinstance(exc, MailUndeliverable):
            raise HTTPException(503, "apple_mail_unavailable") from exc
        raise HTTPException(503, "code_not_sent") from exc

    return {"status": "sent", "channel": payload.channel.value}


@router.post("/verify-code")
def verify_code_endpoint(payload: VerifyCodeIn, request: Request, db: Session = Depends(get_db)):
    destination = payload.destination.strip().lower()

    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.destination == destination,
            VerificationCode.used.is_(False),
            VerificationCode.expires_at > utcnow(),
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(400, "code_expired")

    if record.attempts >= MAX_ATTEMPTS:
        raise HTTPException(429, "too_many_attempts")

    if not verify_code(payload.code.strip(), record.code_hash):
        record.attempts += 1
        db.commit()
        raise HTTPException(400, "invalid_code")

    record.used = True

    # Проверяем и резолвим пригласившего один раз — до создания
    # пользователя, а не после: сам объект User() ещё не существует,
    # проще передать в конструктор сразу, чем потом отдельным UPDATE.
    # Код — первые 8 символов id (тот же приём, что уже используется
    # для коротких ссылок на объявления, см. seo.py:short_listing_page) —
    # не полный UUID, иначе ссылка получалась на километр длиной.
    # Строго 8 hex-символов: помимо формата, это ещё и защита от
    # спецсимволов LIKE (% _) — с ними можно было бы случайно
    # получить слишком широкое совпадение вместо одного человека.
    referrer_id = None
    if payload.referred_by and re.fullmatch(r"[0-9a-f]{8}", payload.referred_by):
        from sqlalchemy import String, cast
        match = (
            db.query(User.id)
            .filter(cast(User.id, String).like(f"{payload.referred_by}-%"))
            .first()
        )
        if match:
            referrer_id = match[0]

    # находим или создаём пользователя
    if payload.channel == VerifyChannel.email:
        user = db.query(User).filter(User.email == destination).first()
        if not user:
            user = User(
                email=destination,
                display_name=payload.display_name or destination.split("@")[0],
                email_verified=True,
                referred_by=referrer_id,
            )
            db.add(user)
        else:
            user.email_verified = True
    else:
        user = db.query(User).filter(User.telegram_id == destination).first()
        if not user:
            user = User(
                telegram_id=destination,
                display_name=payload.display_name or f"user{destination[-4:]}",
                referred_by=referrer_id,
            )
            db.add(user)

    db.commit()
    db.refresh(user)

    if user.is_blocked:
        raise HTTPException(403, "user_blocked")

    # Письмо от команды — только новичку; greet сам молчит, если уже писал.
    from app.core.team_chat import greet
    greet(db, user, payload.lang or "ru")

    try:
        from app.core.login_events import record_login
        record_login(request, user.id, db)
    except Exception:
        pass

    return {"token": create_access_token(user.id, user.token_version), "user": _user_payload(user)}


# Входа по паролю больше нет.
#
# Паролем пользовались трое из пяти, и у каждого была ещё почта, телефон
# или Telegram — то есть дверь была лишней, а не единственной. Лишняя
# дверь в систему входа это лишний способ её выбить: подбор пароля,
# утечка с другого сайта, где человек использовал тот же.
#
# Остаётся одноразовый код на почту или в Telegram и вход через внешние
# службы ниже. Колонку hashed_password в базе не трогаем: она никому не
# мешает, а менять устройство таблицы на живой базе ради этого незачем.

# ---------- внешние сервисы ----------
def _link_oauth(db: Session, provider: str, external_id: str,
                email: str | None, display_name: str | None,
                avatar_url: str | None) -> User:
    """
    Находит или заводит человека по внешнему аккаунту и связывает их.

    Вызывается только после того, как подлинность внешнего аккаунта уже
    проверена (см. google_login ниже). Прежде здесь был открытый
    эндпоинт, принимавший внешний идентификатор прямо из запроса — то
    есть войти под чужой учётной записью мог кто угодно, кто знал её
    google_id. Эндпоинт убран, осталась только эта внутренняя функция.
    """
    field_map = {
        "google": User.google_id,
        "apple": User.apple_id,
        "telegram": User.telegram_id,
        "viber": User.viber_id,
    }
    column = field_map[provider]
    user = db.query(User).filter(column == external_id).first()

    # Аккаунта нет — связываем с существующим по почте. Почта от Google
    # приходит уже подтверждённой им самим, так что это не дыра: подтвердить
    # чужую почту в Google, не владея ею, нельзя.
    if not user and email:
        user = db.query(User).filter(User.email == email.lower()).first()

    if not user:
        user = User(
            display_name=clean_display_name(display_name) or provider.capitalize(),
            email=email.lower() if email else None,
            email_verified=bool(email),
            avatar_url=avatar_url,
        )
        db.add(user)

    setattr(user, column.key, external_id)
    if avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url

    db.commit()
    db.refresh(user)
    if user.is_blocked:
        raise HTTPException(403, "user_blocked")
    from app.core.team_chat import greet
    greet(db, user)
    return user


class GoogleIn(BaseModel):
    credential: str


@router.post("/google")
def google_login(payload: GoogleIn, db: Session = Depends(get_db)):
    """
    Вход через Google — по ID-токену из Google Identity Services.

    Браузер получает от Google подписанный токен и присылает его сюда;
    мы проверяем подпись открытыми ключами Google, издателя, срок и то,
    что токен выписан именно нашему приложению. Без последней проверки
    подошёл бы токен, выданный любому другому сайту, — обычная ошибка в
    таких обработчиках.
    """
    if not settings.google_client_id:
        raise HTTPException(503, "google_disabled")

    from app.core.google_auth import verify_google_token

    try:
        claims = verify_google_token(payload.credential, settings.google_client_id)
    except ValueError:
        raise HTTPException(401, "bad_token")

    user = _link_oauth(
        db, "google",
        external_id=claims["sub"],
        email=claims.get("email") if claims.get("email_verified") else None,
        display_name=claims.get("name"),
        avatar_url=claims.get("picture"),
    )
    return {"token": create_access_token(user.id, user.token_version), "user": _user_payload(user)}


# ---------- профиль ----------
@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_payload(user)


class UpdateMeIn(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    default_language: str | None = None


@router.patch("/me")
def update_me(
    payload: UpdateMeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.display_name:
        user.display_name = payload.display_name.strip()[:120]
    if payload.phone is not None:
        user.phone = _normalize_phone(payload.phone.strip()) or None
    if payload.default_language:
        user.default_language = payload.default_language
    try:
        db.commit()
    except IntegrityError:
        # Телефон уникален в базе — если кто-то другой уже указал тот
        # же номер, коммит падает целиком без этой обработки: 500
        # вместо понятной ошибки. Стало заметно после того, как форму
        # публикации подключили сохранять сюда телефон.
        db.rollback()
        raise HTTPException(400, "phone_taken")
    db.refresh(user)
    return _user_payload(user)


class ChangeEmailRequestIn(BaseModel):
    new_email: EmailStr


@router.post("/change-email/request")
def change_email_request(
    payload: ChangeEmailRequestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Смена почты — раньше просто не было такой возможности вовсе: если
    человек пытался «войти» с новой почтой, обычный вход заводил ему
    ВТОРОЙ, отдельный аккаунт, а не переносил старый на новый адрес.

    Код шлём на НОВУЮ почту (не на старую) — подтверждаем, что человек
    реально владеет тем адресом, на который переезжает, тем же самым
    способом, что уже проверен для обычной регистрации.
    """
    new_email = payload.new_email.strip().lower()

    if new_email == (user.email or "").lower():
        raise HTTPException(400, "same_email")

    taken = db.query(User).filter(User.email == new_email, User.id != user.id).first()
    if taken:
        raise HTTPException(400, "email_taken")

    recent = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.destination == new_email,
            VerificationCode.created_at > utcnow() - RESEND_COOLDOWN,
        )
        .first()
    )
    if recent:
        raise HTTPException(429, "too_many_requests")

    code = generate_code()
    db.add(VerificationCode(
        destination=new_email,
        channel=VerifyChannel.email,
        code_hash=hash_code(code),
        expires_at=utcnow() + CODE_TTL,
    ))
    db.commit()

    send_code(new_email, code, VerifyChannel.email)
    return {"status": "sent"}


class ChangeEmailVerifyIn(BaseModel):
    new_email: EmailStr
    code: str


@router.post("/change-email/verify")
def change_email_verify(
    payload: ChangeEmailVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_email = payload.new_email.strip().lower()

    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.destination == new_email,
            VerificationCode.used.is_(False),
            VerificationCode.expires_at > utcnow(),
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(400, "code_expired")

    record.attempts += 1
    if record.attempts > MAX_ATTEMPTS:
        record.used = True
        db.commit()
        raise HTTPException(400, "too_many_attempts")

    if not verify_code(payload.code, record.code_hash):
        db.commit()
        raise HTTPException(400, "wrong_code")

    record.used = True

    # Второй раз проверяем занятость прямо перед записью — окно между
    # запросом кода и его вводом может занять минуты, и почту мог
    # успеть занять кто-то другой за это время.
    taken = db.query(User).filter(User.email == new_email, User.id != user.id).first()
    if taken:
        db.commit()
        raise HTTPException(400, "email_taken")

    user.email = new_email
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return _user_payload(user)


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Отзывает ВСЕ токены этого человека разом, не только тот, что
    предъявлен сейчас — увеличивает token_version, и любой ранее
    выпущенный токен (этот телефон, другой телефон, чужой компьютер,
    если он там сохранился) перестаёт проходить проверку в
    get_current_user немедленно, а не через 30 дней естественного
    истечения. Раньше signOut() на фронтенде только чистил
    localStorage на самом устройстве — сам токен на сервере
    продолжал молча работать весь оставшийся срок."""
    user.token_version += 1
    db.commit()
    return {"ok": True}
