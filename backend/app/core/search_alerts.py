"""
Оповещение подписчиков о подходящих объявлениях.

Работает при публикации: проверяем сохранённые поиски и уведомляем тех,
чьим фильтрам объявление отвечает. Уведомление отправляем не чаще раза
в сутки на подписку — иначе при активной категории оно превращается в поток.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import SavedSearch, Listing, ListingTranslation

log = logging.getLogger(__name__)

# Не чаще одного уведомления в сутки по одной подписке
COOLDOWN = timedelta(hours=24)


def matches(listing: Listing, filters: dict, translations: list) -> bool:
    """Подходит ли объявление под фильтры подписки."""
    if not filters:
        return False

    if filters.get("category_slug"):
        if not listing.category or listing.category.slug != filters["category_slug"]:
            return False

    if filters.get("city") and listing.city != filters["city"]:
        return False

    price = float(listing.price) if listing.price else None
    if filters.get("price_min") is not None:
        if price is None or price < float(filters["price_min"]):
            return False
    if filters.get("price_max") is not None:
        if price is None or price > float(filters["price_max"]):
            return False

    if filters.get("with_photo") and not listing.photos:
        return False

    # текстовый запрос — ищем по всем языкам объявления
    q = (filters.get("q") or "").strip().lower()
    if q:
        haystack = " ".join(
            f"{t.title or ''} {t.description or ''}" for t in translations
        ).lower()
        if q not in haystack:
            return False

    return True


def notify_subscribers(db: Session, listing: Listing) -> int:
    """
    Вызывается, когда объявление становится активным. Возвращает,
    скольким людям ушло уведомление.
    """
    translations = list(listing.translations or [])
    title = translations[0].title if translations else ""

    searches = db.query(SavedSearch).filter(SavedSearch.notify_enabled.is_(True)).all()

    sent = 0
    now = datetime.utcnow()

    for s in searches:
        # себе не уведомляем
        if s.user_id == listing.owner_id:
            continue
        if not matches(listing, s.filters or {}, translations):
            continue

        # не частим: одно уведомление в сутки на подписку
        last = (s.filters or {}).get("_last_notified")
        if last:
            try:
                if now - datetime.fromisoformat(last) < COOLDOWN:
                    continue
            except ValueError:
                pass

        try:
            from app.core.notifications import notify
            price = f"{listing.price:.0f} {listing.currency}" if listing.price else ""
            text = (
                f"По вашему поиску «{s.name}» новое объявление:\n\n"
                f"<b>{title}</b>\n{price}"
            )
            # Человек сам включил уведомления по этой подписке — если
            # Telegram не привязан, уходит на почту.
            if notify(db, s.user_id, text, allow_email=True,
                      subject=f"PLONK — новое по поиску «{s.name}»"):
                sent += 1
        except Exception:
            continue

        # запоминаем время прямо в фильтрах — отдельное поле заводить
        # ради этого не стоит
        filters = dict(s.filters or {})
        filters["_last_notified"] = now.isoformat()
        s.filters = filters

    if sent:
        db.commit()
        log.info("Объявление %s: уведомлено подписчиков %s", listing.id, sent)

    return sent
