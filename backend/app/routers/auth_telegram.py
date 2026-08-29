"""
Вход на сайт по ссылке из бота.

Человек опубликовал объявление через бота и нигде не регистрировался.
Заставлять его придумывать пароль ради того, чтобы посмотреть своё же
объявление, — верный способ потерять его насовсем.

Поэтому вход одной кнопкой: бот выдаёт одноразовую ссылку, человек
открывает её и уже узнан. Ни пароля, ни кода, ни почты.

Ссылка живёт пять минут и срабатывает один раз: если она попадёт в чужие
руки — например, человек перешлёт переписку, — воспользоваться ею уже не
выйдет.
"""
import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.clock import utcnow
from app.core.database import get_db
from app.models import Language, User, UserRole

router = APIRouter(prefix="/api/auth/telegram", tags=["auth"])

# Сколько живёт ссылка. Пять минут — чтобы человек успел перейти, но
# ссылка не осталась рабочей в истории переписки навсегда.
TTL = timedelta(minutes=5)

# Ключи храним в базе, а не в памяти. Бот и сайт — разные процессы: то,
# что бот положил себе в память, сайт не увидит, и ссылка окажется
# «устаревшей» через две минуты после выдачи.
def issue(telegram_id: int, display_name: str | None = None) -> str:
    """Выдаёт одноразовый ключ для входа. Зовётся из бота."""
    from app.core.database import SessionLocal
    from app.models import LoginTicket

    key = secrets.token_urlsafe(24)
    with SessionLocal() as db:
        _forget_stale(db)
        db.add(LoginTicket(
            key=key,
            telegram_id=str(telegram_id),
            display_name=(display_name or "")[:120],
        ))
        db.commit()
    return key


def _forget_stale(db: Session) -> None:
    """Прибирает просроченные ключи, чтобы таблица не росла без конца."""
    from app.models import LoginTicket

    db.query(LoginTicket).filter(
        LoginTicket.created_at < utcnow() - TTL
    ).delete(synchronize_session=False)


class Ticket(BaseModel):
    key: str


@router.post("/enter")
def enter(payload: Ticket, request: Request, db: Session = Depends(get_db)):
    """
    Меняет ключ из бота на вход.

    Учётную запись заводим сами, если её ещё нет: человек и так уже
    подтвердил, кто он, — переписка с ботом идёт от его телеграма.
    """
    from app.models import LoginTicket

    ticket = db.query(LoginTicket).filter(LoginTicket.key == payload.key).first()
    if not ticket:
        raise HTTPException(400, "link_expired")

    telegram_id = ticket.telegram_id
    display_name = ticket.display_name
    issued_at = ticket.created_at

    # Ключ одноразовый: переписку могут переслать, и вечно рабочая
    # ссылка была бы дырой.
    db.delete(ticket)
    db.flush()

    if utcnow() - issued_at > TTL:
        raise HTTPException(400, "link_expired")

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            telegram_id=telegram_id,
            display_name=display_name or "Продавец",
            # Пароля нет и не будет: вход только через телеграм.
            hashed_password="!",
            role=UserRole.seller_private,
            default_language=Language.ru,
        )
        db.add(user)
        db.flush()

        _adopt_listings(db, user, telegram_id, display_name)

    db.commit()

    if user.is_blocked:
        raise HTTPException(403, "user_blocked")

    try:
        from app.core.login_events import record_login
        record_login(request, user.id, db)
    except Exception:
        pass

    return {
        "access_token": create_access_token(user.id, user.token_version),
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "role": user.role.value,
        },
    }


def _adopt_listings(db: Session, user: User, telegram_id: str,
                    display_name: str | None) -> None:
    """
    Передаёт человеку объявления, опубликованные им через бота.

    Они записаны на служебный аккаунт: когда человек публиковал, своей
    учётной записи у него ещё не было. Без этого он войдёт и увидит
    пустоту, хотя объявления его.
    """
    from app.models import Listing

    owned = (
        db.query(Listing)
        .filter(Listing.external_author.in_(
            [telegram_id, display_name] if display_name else [telegram_id]))
        .all()
    )
    for listing in owned:
        listing.owner_id = user.id


@router.get("/link")
def login_link():
    """
    Ссылка на бота для входа.

    Человек нажимает кнопку, попадает в бота, тот присылает одноразовую
    ссылку — и он уже на сайте. Ни имени пользователя, ни пароля вводить
    не нужно: телеграм и так знает, кто это.
    """
    from app.core.config import settings as cfg

    name = getattr(cfg, "telegram_bot_username", None) or "Baraholka_plonk_bot"
    return {"url": f"https://t.me/{name}?start=login"}
