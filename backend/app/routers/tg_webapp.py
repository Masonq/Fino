"""
Вход в приложение внутри Telegram.

Telegram открывает WebApp и передаёт ему строку initData — кто открыл,
когда и подпись. Подпись считается ключом бота, поэтому её невозможно
подделать, не зная этого ключа: человека можно впустить сразу, без
кода на почту и без пароля.

Это и есть главный смысл публикатора в боте: продавец нажал кнопку в
чате, выложил вещь и вернулся к переписке. Ни регистрации, ни перехода
в браузер, ни ожидания письма.

Проверка по документации Telegram: из строки берётся hash, остальные
поля сортируются и склеиваются, от них считается HMAC на ключе,
выведенном из токена бота. Совпало — данные настоящие.
"""
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.config import settings
from app.core.database import get_db
from app.models import User

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tg", tags=["telegram-webapp"])

# Сколько живёт подпись. Сутки — с запасом на то, что человек открыл
# окно, отвлёкся и вернулся; дольше держать незачем: Telegram выдаёт
# свежую строку при каждом открытии.
MAX_AGE = 24 * 60 * 60


class WebAppIn(BaseModel):
    init_data: str
    ref: str | None = None


def check_init_data(init_data: str) -> dict | None:
    """
    Разбирает и проверяет строку от Telegram. Вернёт данные или None.
    """
    token = settings.telegram_bot_token
    if not token or not init_data:
        return None

    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:                                   # noqa: BLE001
        return None

    given = pairs.pop("hash", None)
    if not given:
        return None

    # Поля по алфавиту, каждое строкой «ключ=значение», склеены
    # переводом строки — так это описано у Telegram.
    checked = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, checked.encode(), hashlib.sha256).hexdigest()

    # Сравнение с защитой от подбора по времени ответа.
    if not hmac.compare_digest(expected, given):
        return None

    issued = int(pairs.get("auth_date") or 0)
    if not issued or time.time() - issued > MAX_AGE:
        return None

    try:
        user = json.loads(pairs.get("user") or "{}")
    except Exception:                                   # noqa: BLE001
        return None
    if not user.get("id"):
        return None
    return user


@router.post("/webapp/auth")
def webapp_auth(payload: WebAppIn, request: Request, db: Session = Depends(get_db)):
    """
    Впускает человека, открывшего публикатор из бота.

    Находим по телеграм-идентификатору или заводим нового. Имя берём из
    профиля Telegram — спрашивать его отдельно значит поставить лишний
    шаг там, где мы обещали быстро.
    """
    data = check_init_data(payload.init_data)
    if not data:
        raise HTTPException(401, "bad_init_data")

    telegram_id = str(data["id"])
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        name = " ".join(x for x in (data.get("first_name"), data.get("last_name")) if x)
        user = User(
            telegram_id=telegram_id,
            display_name=(name or data.get("username") or f"user{telegram_id[-4:]}")[:60],
        )
        # Кто пригласил — то же, что и при обычном входе: ссылка с
        # меткой приходит параметром запуска бота.
        if payload.ref:
            inviter = db.query(User).filter(User.id == payload.ref).first()
            if inviter and inviter.id != user.id:
                user.referred_by = inviter.id
        db.add(user)
        db.commit()
        db.refresh(user)

    if user.is_blocked:
        raise HTTPException(403, "user_blocked")

    try:
        from app.core.login_events import record_login
        record_login(request, user.id, db)
    except Exception:                                   # noqa: BLE001
        pass

    return {
        "token": create_access_token(user.id, user.token_version),
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "must_rename": bool(user.must_rename),
        },
    }


class SiteLinkIn(BaseModel):
    init_data: str
    next: str = "/post"


@router.post("/site-link")
def site_link(payload: SiteLinkIn):
    """
    Ссылка на сайт, по которой человек попадает уже вошедшим.

    Он только что работал в публикаторе, где вход не нужен вовсе, — и
    упереться на сайте в «Войдите» значит потерять его на ровном месте.
    Выдаём тот же одноразовый ключ, что бот выдаёт по кнопке «Войти на
    сайт»: действует пять минут и только для него.
    """
    data = check_init_data(payload.init_data)
    if not data:
        raise HTTPException(401, "bad_init_data")

    from app.routers.auth_telegram import issue

    name = " ".join(x for x in (data.get("first_name"), data.get("last_name")) if x)
    key = issue(int(data["id"]), name or None, data.get("username"))

    # Адрес внутри сайта и только: «next» приходит со страницы, и без
    # проверки им можно было бы увести человека куда угодно.
    where = payload.next if payload.next.startswith("/") else "/post"
    site = settings.public_base_url.rstrip("/")
    return {"url": f"{site}/enter?key={key}&next={where}"}
