"""
Истечение объявлений.

Объявление живёт LISTING_TTL_DAYS (сейчас 45) — срок ставится при
публикации, но раньше нигде не проверялся: expires_at существовал
только в базе, ничего не читало его обратно. Объявление оставалось
«активным» бессрочно, сколько бы лет ни прошло. Это особенно заметно
для объявлений, перенесённых из телеграм-чатов, — автор давно продал
вещь и не заходит поменять статус вручную.

Тем же способом, что уже отправляет просроченные отзывы и сводки по
почте: отдельная функция + systemd-таймер, раз в сутки.

    python3 -m app.core.listing_expiry     разовый запуск
"""
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Listing, ListingStatus, User

log = logging.getLogger(__name__)

# За сколько дней до истечения предупреждать — время успеть отреагировать,
# но не настолько рано, чтобы уведомление забылось к делу.
WARN_DAYS_BEFORE = 3


def warn_expiring_soon(db: Session) -> int:
    """
    Предупреждает тех, у кого объявление истекает через WARN_DAYS_BEFORE
    дней. Раз на объявление — метим отправленные, чтобы не звать по
    два раза за один и тот же срок.
    """
    from app.core.notifications import notify_expiring_soon

    window_start = utcnow() + timedelta(days=WARN_DAYS_BEFORE)
    window_end = window_start + timedelta(days=1)

    listings = (
        db.query(Listing)
        .filter(
            Listing.status == ListingStatus.active,
            Listing.expires_at >= window_start,
            Listing.expires_at < window_end,
            Listing.expiry_warned.is_(False),
        )
        .all()
    )

    sent = 0
    for listing in listings:
        from app.routers.listings import pick_translation
        owner = db.query(User).get(listing.owner_id)
        owner_lang = owner.default_language.value if owner else "ru"
        tr = pick_translation(listing, owner_lang)
        title = tr.title if tr else ""
        try:
            notify_expiring_soon(db, listing.owner_id, title, WARN_DAYS_BEFORE)
        except Exception:
            log.warning("не удалось предупредить об истечении %s", listing.id)
        # Метим независимо от того, дошло ли уведомление: иначе при
        # недоступном канале связи будем пытаться каждый день до
        # самого истечения.
        listing.expiry_warned = True
        sent += 1

    if sent:
        db.commit()
        log.info("предупреждено об истечении: %s", sent)
    return sent


def archive_expired(db: Session) -> int:
    """Архивирует объявления с истёкшим сроком, уведомляет владельцев."""
    from app.core.notifications import notify_expired

    expired = (
        db.query(Listing)
        .filter(
            Listing.status == ListingStatus.active,
            Listing.expires_at < utcnow(),
        )
        .all()
    )

    for listing in expired:
        from app.routers.listings import pick_translation
        owner = db.query(User).get(listing.owner_id)
        owner_lang = owner.default_language.value if owner else "ru"
        tr = pick_translation(listing, owner_lang)
        title = tr.title if tr else ""
        listing.status = ListingStatus.archived
        try:
            notify_expired(db, listing.owner_id, title)
        except Exception:
            log.warning("не удалось уведомить о снятии %s", listing.id)

    if expired:
        db.commit()
        log.info("архивировано по истечении срока: %s", len(expired))
    return len(expired)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        warned = warn_expiring_soon(session)
        archived = archive_expired(session)
        print(f"Предупреждено: {warned}. Архивировано: {archived}.")
    finally:
        session.close()
