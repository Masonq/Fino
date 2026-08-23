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

from fastapi import APIRouter, Depends, HTTPException
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

# Выданные ссылки: ключ → кто и когда. Держим в памяти, потому что они
# живут минуты, и заводить ради них таблицу незачем. Перезапуск сервера
# их теряет — человек просто нажмёт кнопку ещё раз.
_tickets: dict[str, tuple[str, object, str]] = {}


def issue(telegram_id: int, display_name: str | None = None) -> str:
    """Выдаёт одноразовый ключ для входа. Зовётся из бота."""
    _forget_stale()
    key = secrets.token_urlsafe(24)
    _tickets[key] = (str(telegram_id), utcnow(), display_name or "")
    return key


def _forget_stale() -> None:
    edge = utcnow() - TTL
    for key in [k for k, v in _tickets.items() if v[1] < edge]:
        _tickets.pop(key, None)


class Ticket(BaseModel):
    key: str


@router.post("/enter")
def enter(payload: Ticket, db: Session = Depends(get_db)):
    """
    Меняет ключ из бота на вход.

    Учётную запись заводим сами, если её ещё нет: человек и так уже
    подтвердил, кто он, — переписка с ботом идёт от его телеграма.
    """
    _forget_stale()
    ticket = _tickets.pop(payload.key, None)     # одноразовый
    if not ticket:
        raise HTTPException(400, "link_expired")

    telegram_id, issued_at, display_name = ticket
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
    return {
        "access_token": create_access_token(user.id),
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
