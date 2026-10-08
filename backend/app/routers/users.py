import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_current_user, get_current_user_optional
from app.core.clock import utcnow
from app.core.database import get_db
from app.core.names import clean_display_name, is_unusable_name
from app.models import User, UserRole, Language, BlockedUser, SellerSubscription, Listing, ListingStatus, Favorite

router = APIRouter(prefix="/api/users", tags=["users"])


class QuickIdentifyIn(BaseModel):
    phone: str
    display_name: str




@router.get("/{user_id}/public")
def public_profile(user_id: uuid.UUID, lang: str = "ru", db: Session = Depends(get_db),
                    viewer: User | None = Depends(get_current_user_optional)):
    """
    Открытая карточка продавца: то, по чему покупатель решает, иметь ли дело.

    Ни телефона, ни почты — контакты появляются только через чат, иначе
    страница продавца превращается в базу для сбора номеров.
    """
    from app.models import Listing, ListingStatus

    user = db.query(User).get(user_id)
    if not user or user.is_blocked:
        raise HTTPException(404, "not_found")

    active = (
        db.query(Listing)
        .filter(Listing.owner_id == user.id, Listing.status == ListingStatus.active)
        .count()
    )

    is_subscribed = False
    if viewer and viewer.id != user.id:
        is_subscribed = (
            db.query(SellerSubscription)
            .filter(SellerSubscription.subscriber_id == viewer.id,
                    SellerSubscription.seller_id == user.id)
            .first() is not None
        )

    from app.core.reply_speed import reply_speed, speed_label

    from app.core.active_seller import is_active_seller

    active = is_active_seller(db, user.id)
    speed = reply_speed(db, user.id)
    reply = {"label": speed_label(speed["median_minutes"]),
             "answered": speed["answered"]} if speed else None

    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "is_company": user.role == UserRole.seller_business,
        "company_name": user.company_name if user.role == UserRole.seller_business else None,
        "company_description": user.company_description if user.role == UserRole.seller_business else None,
        "document_verified": user.document_verified,
        "company_verified": user.company_verified,
        "official": user.role in (UserRole.admin, UserRole.moderator),  # команда PLONK
        "rating_avg": float(user.rating_avg or 0),
        "rating_count": int(user.rating_count or 0),
        "active_listings": active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        "is_subscribed": is_subscribed,
        # Как быстро отвечает — по своим же перепискам.
        #
        # Люди ждут ответа быстро, и там, где он приходит скоро, чаще
        # доходит до сделки. Показываем не точные минуты, а порядок:
        # «обычно отвечает в течение часа». Точная цифра звучала бы как
        # обещание, которого продавец не давал.
        #
        # Пока ответов меньше трёх — не показываем ничего: два быстрых
        # ответа это случайность, а не отзывчивость.
        "reply_speed": reply,
        # Значок активного продавца — за поведение, а не за деньги.
        #
        # У площадок такой значок работает как множитель: не заменяет
        # качество объявления, но при прочих равных решает выбор.
        # Ключевое — его нельзя купить, иначе он перестаёт что-либо
        # значить, а вместе с ним обесцениваются и остальные знаки.
        "active_seller": active,
    }


@router.post("/{user_id}/subscribe")
def subscribe_to_seller(user_id: uuid.UUID, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user_id == user.id:
        raise HTTPException(400, "cannot_subscribe_self")
    seller = db.query(User).get(user_id)
    if not seller or seller.is_blocked:
        raise HTTPException(404, "not_found")

    existing = (
        db.query(SellerSubscription)
        .filter(SellerSubscription.subscriber_id == user.id,
                SellerSubscription.seller_id == user_id)
        .first()
    )
    if not existing:
        db.add(SellerSubscription(subscriber_id=user.id, seller_id=user_id))
        db.commit()
    return {"status": "subscribed"}


@router.delete("/{user_id}/subscribe")
def unsubscribe_from_seller(user_id: uuid.UUID, user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    (
        db.query(SellerSubscription)
        .filter(SellerSubscription.subscriber_id == user.id,
                SellerSubscription.seller_id == user_id)
        .delete()
    )
    db.commit()
    return {"status": "unsubscribed"}


class ProfileEdit(BaseModel):
    """Что человек может поменять о себе сам."""
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    default_language: Language | None = None
    # Компания — для тех, кто продаёт как бизнес. Проверку по реестру
    # это не отменяет: название человек пишет сам, а галочку ставим мы.
    company_name: str | None = Field(default=None, max_length=255)
    # Описание на витрине — под названием, покупатель видит его первым.
    company_description: str | None = Field(default=None, max_length=2000)
    # Для звонка через чат (см. chats.py) — без него вся функция
    # скрыта целиком, нечего раскрывать покупателю. Формат — как
    # прислал фронтенд (код страны уже вписан туда же, не отдельным
    # полем): +381 плюс цифры, но заставлять именно этот формат тут
    # незачем — просто нормализуем и проверяем, что не занят.
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, v):
        # min_length в Field проверяет строку ДО обрезки пробелов —
        # «  a  » (4 символа) проходил бы, хотя после strip() внизу
        # это один символ. Обрезаем здесь же, до самой проверки длины.
        if v is None:
            return v
        v = clean_display_name(v)
        if len(v) < 2:
            raise ValueError("too_short")
        # Имя без букв или состоящее почти из одних значков не годится:
        # оно не читается, ломает вёрстку и прячет продавца от узнавания.
        if is_unusable_name(v):
            raise ValueError("bad_name")
        return v


@router.get("/me")
def my_profile(user: User = Depends(get_current_user)):
    """Свои данные — для страницы профиля."""
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "role": user.role.value,
        "default_language": user.default_language.value,
        "email_verified": user.email_verified,
        # Привязан ли Telegram: по этому странице решать, предлагать
        # привязку или нет. Сам идентификатор не отдаём, он ни к чему.
        "telegram_linked": bool(user.telegram_id),
        "company_name": user.company_name,
        "company_description": user.company_description,
        "company_verified": user.company_verified,
        "rating_avg": round(user.rating_avg or 0, 2),
        "rating_count": user.rating_count,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "must_rename": bool(user.must_rename),
    }


@router.patch("/me")
def edit_profile(
    payload: ProfileEdit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Правка своих данных.

    Меняем только то, что прислали: пустое поле означает «не трогать», а
    не «стереть» — иначе правка имени обнулила бы всё остальное.
    """
    if payload.display_name is not None:
        user.display_name = payload.display_name
        # Имя сменили — запрет снят.
        user.must_rename = False
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url or None
    if payload.default_language is not None:
        user.default_language = payload.default_language
    if payload.company_name is not None:
        name = payload.company_name.strip()
        # Впервые становится бизнес-аккаунтом именно сейчас — не был
        # им раньше и не персонал. На уже действующий бизнес-аккаунт
        # (правит своё же название) эта проверка второй раз не действует.
        becoming_business = bool(
            name and user.role not in (UserRole.moderator, UserRole.admin, UserRole.seller_business)
        )
        if becoming_business and not user.document_verified:
            # Витрина, значок компании, доверие покупателя — всё это
            # не выдаём просто по факту того, что кто-то напечатал
            # название в поле. Сначала подтвердить, что за аккаунтом
            # стоит реальный, проверенный человек.
            raise HTTPException(400, "verify_identity_first")
        # Название поменяли — прежняя проверка к нему не относится.
        if name != (user.company_name or ""):
            user.company_verified = False
        user.company_name = name or None
        if becoming_business:
            user.role = UserRole.seller_business
    if payload.company_description is not None:
        user.company_description = payload.company_description.strip() or None
    if payload.phone is not None:
        phone = payload.phone.strip()
        if phone:
            taken = (
                db.query(User)
                .filter(User.phone == phone, User.id != user.id)
                .first()
            )
            if taken:
                raise HTTPException(400, "phone_already_used")
            user.phone = phone
        else:
            user.phone = None

    db.commit()
    return my_profile(user)


@router.get("/me/referrals")
def my_referrals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Что вышло из приглашений: сколько позвал, сколько из них дошли до
    объявления, сколько получено.

    Три цифры, а не одна, потому что они отвечают на разные вопросы.
    «Позвал» говорит, сколько ссылок разошлось. «Разместили» — сколько
    из них оказались живыми людьми, а не просто переходами. «Получено»
    — ради чего всё и затевалось.

    Ниже — сами приглашённые: имя, когда пришёл, что с ним. Без этого
    цифры висят в воздухе: человек не понимает, кто из позванных
    дошёл, а кто застрял, и не знает, кому напомнить.

    Отдельным эндпоинтом, а не в /auth/me: тот дёргается при каждом
    запуске приложения, и вешать на него четыре запроса ради страницы,
    куда заходят раз в месяц, незачем.
    """
    from app.core.referrals import REFERRAL_BONUS

    invited = (db.query(User)
               .filter(User.referred_by == user.id)
               .order_by(User.created_at.desc())
               .all())

    rewarded = [u for u in invited if u.referral_reward_given]

    # Кто дошёл до объявления. Считаем всех, у кого есть хоть одно
    # объявление в любом состоянии, кроме черновика: человек своё дело
    # сделал, а что оно на проверке — уже наша забота.
    ids = [u.id for u in invited]
    with_listing = set()
    if ids:
        rows = (db.query(Listing.owner_id)
                .filter(Listing.owner_id.in_(ids),
                        Listing.status != ListingStatus.draft)
                .distinct().all())
        with_listing = {row[0] for row in rows}

    def state(person: User) -> str:
        if person.referral_reward_given:
            return "rewarded"
        if person.id in with_listing:
            return "posted"
        return "joined"

    return {
        "invited": len(invited),
        "posted": len(with_listing),
        "rewarded": len(rewarded),
        "earned": int(REFERRAL_BONUS) * len(rewarded),
        "bonus": int(REFERRAL_BONUS),
        # Десяти хватает: страница не список контактов, а напоминание,
        # что приглашения работают.
        "people": [{
            "name": person.display_name or "—",
            "avatar_url": person.avatar_url,
            "joined_at": person.created_at.isoformat() if person.created_at else None,
            "state": state(person),
        } for person in invited[:10]],
    }


@router.get("/me/stats")
def my_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Три цифры для шапки профиля: активных объявлений, просмотров по
    всем активным и сколько раз их добавили в избранное. Отдельным
    эндпоинтом — по той же причине, что и /me/referrals: не грузить
    /auth/me лишними COUNT при каждом запуске приложения.
    """
    active = db.query(Listing.id, Listing.views_count).filter(
        Listing.owner_id == user.id, Listing.status == ListingStatus.active).all()
    ids = [row[0] for row in active]
    favorites = db.query(func.count(Favorite.id)).filter(Favorite.listing_id.in_(ids)).scalar() if ids else 0
    # Сколько людей ждут отзыва от вас.
    #
    # Приглашение появляется после переписки, похожей на сделку, но
    # живёт только в самой переписке: не открыл её — не узнал. В
    # профиле это строка, на которую можно нажать, и главный повод
    # вернуться, когда покупать сейчас нечего. Отзывов у площадки почти
    # нет, а доверие держится на них.
    from app.models import ReviewInvite

    waiting = (db.query(func.count(ReviewInvite.id))
               .filter(ReviewInvite.user_id == user.id,
                       ReviewInvite.responded.is_(False),
                       ReviewInvite.dismissed.is_(False))
               .scalar() or 0)

    # Поводы вернуться — то, что человек иначе не заметит.
    #
    # Объявление на проверке (не понимает, почему его не видно),
    # отклонённое (не знает, что надо поправить), скоро снимут (ещё
    # можно продлить) и неотвеченное обращение в поддержку. Каждое из
    # них уже есть в базе, но нигде не показывается, пока человек сам
    # не откроет нужный экран.
    from app.models import Ticket, TicketStatus

    pending = (db.query(func.count(Listing.id))
               .filter(Listing.owner_id == user.id,
                       Listing.status == ListingStatus.pending_moderation)
               .scalar() or 0)
    rejected = (db.query(func.count(Listing.id))
                .filter(Listing.owner_id == user.id,
                        Listing.status == ListingStatus.rejected)
                .scalar() or 0)
    expiring = (db.query(func.count(Listing.id))
                .filter(Listing.owner_id == user.id,
                        Listing.status == ListingStatus.active,
                        Listing.expires_at.isnot(None),
                        Listing.expires_at <= utcnow() + timedelta(days=7))
                .scalar() or 0)
    support_answered = (db.query(func.count(Ticket.id))
                        .filter(Ticket.user_id == user.id,
                                Ticket.status == TicketStatus.answered)
                        .scalar() or 0)

    return {
        "listings": len(ids),
        "listings_pending": int(pending),
        "listings_rejected": int(rejected),
        "listings_expiring": int(expiring),
        "support_answered": int(support_answered),
        "views": int(sum((row[1] or 0) for row in active)),
        "favorites": int(favorites or 0),
        "reviews_waiting": int(waiting),
    }


@router.get("/blocked")
def list_blocked(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Кого сам заблокировал — раньше это можно было увидеть и снять
    только изнутри конкретного чата (кнопка «Разблокировать» в
    шапке переписки), отдельной страницы со списком не было вовсе.
    """
    rows = (
        db.query(BlockedUser, User)
        .join(User, User.id == BlockedUser.blocked_id)
        .filter(BlockedUser.blocker_id == user.id)
        .order_by(BlockedUser.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": str(blocked.id),
                "display_name": blocked.display_name,
                "avatar_url": blocked.avatar_url,
                "blocked_at": bu.created_at.isoformat(),
            }
            for bu, blocked in rows
        ]
    }


@router.post("/blocked/{blocked_id}/unblock")
def unblock_user(
    blocked_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Та же операция, что и кнопка внутри чата (chats.py:unblock_participant),
    только не требует открывать конкретную переписку, чтобы её найти."""
    db.query(BlockedUser).filter(
        BlockedUser.blocker_id == user.id,
        BlockedUser.blocked_id == blocked_id,
    ).delete()
    db.commit()
    return {"status": "unblocked"}


@router.post("/me/link-telegram")
def link_telegram_start(user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """
    Ссылка, по которой человек привяжет свой Telegram.

    На сайте подписи Telegram нет и взяться ей неоткуда, поэтому
    доказательство приходит с другой стороны: мы выдаём одноразовый
    ключ, человек открывает по нему бота, и бот говорит нам, кто он в
    Telegram. Пять минут и один раз — чтобы ключ, попавший не туда, был
    бесполезен.
    """
    import secrets
    from datetime import timedelta

    from app.core.config import settings
    from app.models import LinkTicket

    if user.telegram_id:
        return {"status": "already_linked"}

    # Прежние ключи этого человека гасим: две живые ссылки на одно и то
    # же — лишний способ ошибиться.
    (db.query(LinkTicket)
     .filter(LinkTicket.user_id == user.id, LinkTicket.used.is_(False))
     .update({LinkTicket.used: True}))

    key = secrets.token_urlsafe(18)
    db.add(LinkTicket(key=key, user_id=user.id,
                      expires_at=utcnow() + timedelta(minutes=5)))
    db.commit()

    bot = (settings.telegram_bot_username or "Baraholka_plonk_bot").lstrip("@")
    return {"status": "ok", "url": f"https://t.me/{bot}?start=link_{key}"}


@router.delete("/me/link-telegram")
def unlink_telegram(user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """
    Отвязать Telegram.

    Отказываем, если другого способа войти нет: человек нажмёт кнопку,
    выйдет — и обратно уже не попадёт. Пусть сперва добавит почту.
    """
    if not user.telegram_id:
        return {"status": "not_linked"}

    if not (user.email and user.email_verified):
        raise HTTPException(409, "no_other_login")

    user.telegram_id = None
    db.commit()
    return {"status": "unlinked"}


# ---------- какие уведомления присылать (Профиль → Уведомления) ----------
NOTIFY_KINDS = ("messages", "price_drop", "searches", "following", "digest")


class NotifyPrefsIn(BaseModel):
    prefs: dict


@router.get("/me/notify-prefs")
def get_notify_prefs(user: User = Depends(get_current_user)):
    """Что присылать в Telegram / на почту / пушем. Не указано — включено."""
    p = user.notify_prefs or {}
    return {k: p.get(k, True) is not False for k in NOTIFY_KINDS}


@router.put("/me/notify-prefs")
def set_notify_prefs(body: NotifyPrefsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = dict(user.notify_prefs or {})
    for k, v in (body.prefs or {}).items():
        if k in NOTIFY_KINDS:
            p[k] = bool(v)
    user.notify_prefs = p
    db.commit()
    return {k: p.get(k, True) is not False for k in NOTIFY_KINDS}
