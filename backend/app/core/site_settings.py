"""
Настройки сайта из админки (см. models/site_setting.py).

Оплата картой по умолчанию ВЫКЛЮЧЕНА: пока у владельца нет зарегистрированного предпринимателя или фирмы, брать
деньги за услуги от потребителей как частное лицо рискованно (налоги, права потребителей, обязанность назвать
поставщика услуги). Включает её владелец сам, одним нажатием, когда будет готов.

Значение кэшируется на несколько секунд: проверка стоит в каждом запросе про оплату, и ходить за ней в базу каждый
раз незачем. Другой процесс увидит перемену не позже чем через TTL.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import SiteSetting, User

CARD_PAYMENTS = "card_payments_enabled"
DEFAULTS = {CARD_PAYMENTS: False}
TTL_SECONDS = 5

_cache: dict[str, tuple[object, datetime]] = {}


def reset_cache() -> None:
    _cache.clear()


def get(db: Session, key: str):
    hit = _cache.get(key)
    if hit and (utcnow() - hit[1]).total_seconds() < TTL_SECONDS:
        return hit[0]
    row = db.get(SiteSetting, key)
    value = row.value if row is not None else DEFAULTS[key]
    _cache[key] = (value, utcnow())
    return value


def set_value(db: Session, key: str, value, actor: User | None) -> None:
    """Записывает значение; commit — на вызывающем (вместе с записью в журнал)."""
    if key not in DEFAULTS:
        raise KeyError(key)
    row = db.get(SiteSetting, key)
    if row is None:
        row = SiteSetting(key=key)
        db.add(row)
    row.value = value
    row.updated_at = utcnow()
    row.updated_by = actor.id if actor else None
    db.flush()
    reset_cache()


def card_payments_enabled(db: Session) -> bool:
    return bool(get(db, CARD_PAYMENTS))


def describe(db: Session) -> dict:
    row = db.get(SiteSetting, CARD_PAYMENTS)
    who = None
    if row is not None and row.updated_by:
        user = db.get(User, row.updated_by)
        who = user.display_name if user else None
    return {
        CARD_PAYMENTS: card_payments_enabled(db),
        "updated_at": row.updated_at.isoformat() if row is not None and row.updated_at else None,
        "updated_by": who,
    }
