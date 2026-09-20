"""
Подарок новичку за первое объявление.

Не за регистрацию: пустые аккаунты ничего не стоят и накручиваются
одним скриптом. Платим за то, что человек довёл дело до конца —
написал объявление, и оно прошло проверку.

Сумма выбрана по прайсу продвижения, а не круглым числом: 300 динаров —
это ровно неделя выделенной карточки или два поднятия в поиске. Человек
пробует платную возможность целиком, а не откусывает от неё кусок.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import User, Listing, ListingStatus

log = logging.getLogger(__name__)

WELCOME_BONUS = Decimal("300")


def reward_first_listing(db: Session, listing: Listing) -> bool:
    """Начислить подарок, если это первое одобренное объявление человека."""
    owner = db.query(User).get(listing.owner_id)
    if not owner or owner.welcome_bonus_given:
        return False

    # «Первое» — то же понимание, что и в реферальной программе: у
    # человека нет другого объявления, которое когда-либо было живым.
    # Нынешнее не считаем — оно одобряется прямо сейчас.
    has_earlier = (
        db.query(Listing)
        .filter(
            Listing.owner_id == owner.id,
            Listing.id != listing.id,
            Listing.status.in_((ListingStatus.active, ListingStatus.sold, ListingStatus.archived)),
        )
        .first()
        is not None
    )
    if has_earlier:
        return False

    owner.balance = owner.balance + WELCOME_BONUS
    owner.welcome_bonus_given = True
    db.commit()

    try:
        from app.core.notifications import notify
        notify(
            db, owner.id,
            f"Первое объявление опубликовано — дарим {WELCOME_BONUS:.0f} RSD "
            f"на продвижение. Хватит на неделю выделенной карточки.",
            force=True,
        )
    except Exception as exc:                          # noqa: BLE001
        log.warning("Уведомление о подарке новичку не отправлено: %s", exc)

    log.info("Подарок новичку: %s -> %s", listing.id, owner.id)
    return True
