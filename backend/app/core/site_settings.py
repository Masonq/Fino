"""
Настройки сайта из админки (см. models/site_setting.py).

Оплата картой по умолчанию ВЫКЛЮЧЕНА: пока у владельца нет зарегистрированного предпринимателя или фирмы, брать
деньги за услуги от потребителей как частное лицо рискованно (налоги, права потребителей, обязанность назвать
поставщика услуги). Включает её владелец сам, одним нажатием, когда будет готов.

Кэша нет — сознательно. Первая версия держала значение в памяти процесса на 5 секунд, а боевой сервер работает
в два процесса (uvicorn --workers 2, deploy/fino.service): владелец нажимал переключатель в одном, а другой ещё
до пяти секунд отвечал по-старому. Замер: второй процесс показывал прежнее значение на 10 из 14 проверок подряд.
Со стороны это выглядело так, будто тумблер «срабатывает только после обновления страницы». Значение читается
из базы каждый раз: это выборка одной строки по первичному ключу, она стоит меньше, чем весь остальной запрос,
а выключатель, который иногда не выключает, хуже любой экономии.
"""
from sqlalchemy.orm import Session

from app.models import SiteSetting, User

CARD_PAYMENTS = "card_payments_enabled"
DEFAULTS = {CARD_PAYMENTS: False}


def get(db: Session, key: str):
    row = db.get(SiteSetting, key)
    return row.value if row is not None else DEFAULTS[key]


def set_value(db: Session, key: str, value, actor: User | None) -> None:
    """Записывает значение; commit — на вызывающем (вместе с записью в журнал)."""
    from app.core.clock import utcnow

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
