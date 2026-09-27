"""
Автопубликация объявления сразу после размещения.

До этого каждое объявление ждало ручной проверки. На живом сайте это
значило: разместил вечером — висит до утра, человек решает, что сайт
не работает. Одно настоящее объявление так пролежало 6,5 часов.

Пропускаем сразу только то, где сходится и текст, и продавец:
проверка не нашла ничего подозрительного, а человек уже показал себя —
подтвердил личность или у него есть одобренные объявления. Всё
остальное, включая первое объявление новичка, идёт модератору, как и
раньше.
"""
import logging

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Listing, ListingStatus, User

log = logging.getLogger(__name__)

# Сколько одобренных объявлений делают продавца знакомым. Одного мало:
# мошенники сперва размещают безобидное, чтобы пройти проверку.
TRUSTED_APPROVED = 2


def _seller_is_known(db: Session, user: User) -> bool:
    if user.document_verified:
        return True
    approved = (db.query(Listing)
                .filter(Listing.owner_id == user.id,
                        Listing.published_at.isnot(None))
                .count())
    return approved >= TRUSTED_APPROVED


def decide(db: Session, listing: Listing, user: User) -> tuple[bool, str]:
    """
    Публиковать ли сразу. Возвращает (решение, причина для журнала).

    Причина пишется всегда — и когда пропустили, и когда нет: иначе по
    очереди модерации не понять, почему объявление в ней оказалось.
    """
    from app.core.moderation_ai import check

    translation = next((t for t in listing.translations), None)
    title = translation.title if translation else ""
    body = translation.description if translation else ""

    try:
        verdict, why = check(title, body)
    except Exception:                                   # noqa: BLE001
        # Проверка не сработала — это не повод публиковать вслепую.
        log.warning("проверка объявления не отработала", exc_info=True)
        return False, "проверка не отработала"

    if verdict != "ok":
        return False, f"проверка: {why}"[:255]
    if not _seller_is_known(db, user):
        return False, "первые объявления продавца смотрим сами"
    return True, "проверка чистая, продавец знакомый"


def apply(db: Session, listing: Listing, user: User) -> bool:
    ok, why = decide(db, listing, user)
    if ok:
        listing.status = ListingStatus.active
        listing.published_at = utcnow()
    listing.rejection_reason = None if ok else listing.rejection_reason
    log.info("автопубликация %s: %s (%s)", listing.id, "да" if ok else "нет", why)
    return ok
