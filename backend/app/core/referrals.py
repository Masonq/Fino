"""
Реферальная программа — простой крючок для роста.

Ссылка вида plonk.rs/?ref=<id> запоминается на телефоне при первом
заходе (см. фронтенд), передаётся при регистрации нового человека —
кто именно его привёл (User.referred_by, пишется один раз в auth.py).

Награда — не за саму регистрацию (пустые аккаунты ничего не стоят
и легко накручиваются), а за первое ОДОБРЕННОЕ объявление
приглашённого: реальное намерение продавать, не просто клик по ссылке.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import User, Listing, ListingStatus

log = logging.getLogger(__name__)

# Столько же, сколько стоит «поднятие» — бонус ощутимый (можно сразу
# попробовать платное продвижение бесплатно), не символический.
# В динарах. Двести — это поднятие объявления с запасом, а не мелочь,
# ради которой не стоит и писать другу.
REFERRAL_BONUS = Decimal("200")


def reward_referral_if_first_listing(db: Session, listing: Listing) -> bool:
    owner = db.query(User).get(listing.owner_id)
    if not owner or not owner.referred_by or owner.referral_reward_given:
        return False

    # «Первое» — уже одобренное когда-либо хоть раз, включая нынешнее:
    # если это не первое, у человека есть другое объявление, которое
    # УЖЕ было активным раньше (не считая отклонённых и текущего —
    # оно ещё не подтверждено как одобренное на момент этой проверки,
    # но одобряется прямо сейчас вызывающим кодом).
    has_earlier_active = (
        db.query(Listing)
        .filter(
            Listing.owner_id == owner.id,
            Listing.id != listing.id,
            Listing.status.in_((ListingStatus.active, ListingStatus.sold, ListingStatus.archived)),
        )
        .first()
        is not None
    )
    if has_earlier_active:
        return False

    referrer = db.query(User).get(owner.referred_by)
    if not referrer:
        return False   # пригласивший сам удалил аккаунт — бонусу некому идти

    from app.core import wallet

    wallet.grant_bonus(referrer, REFERRAL_BONUS)      # награда — на бонусный счёт обоим
    wallet.grant_bonus(owner, REFERRAL_BONUS)
    owner.referral_reward_given = True
    # Коммитим сразу, до уведомлений — не полагаемся на то, что notify()
    # ниже коммитит всю сессию целиком как побочный эффект (сейчас так
    # и есть, но это не то, на что эта функция должна молча рассчитывать).
    db.commit()

    try:
        from app.core.notifications import notify
        notify(
            db, referrer.id,
            f"Ваш друг опубликовал первое объявление — вам начислено {REFERRAL_BONUS:.0f} RSD на баланс",
            force=True,
        )
        notify(
            db, owner.id,
            f"Спасибо за первое объявление — вам начислено {REFERRAL_BONUS:.0f} RSD на баланс",
            force=True,
        )
    except Exception as exc:                          # noqa: BLE001
        log.warning("Уведомление о реферальном бонусе не отправлено: %s", exc)

    log.info("Реферальный бонус: %s -> пригласивший %s, приглашённый %s", listing.id, referrer.id, owner.id)
    return True
