"""
Оповещение подписчиков о подходящих объявлениях.

Работает при публикации: проверяем сохранённые поиски и уведомляем тех,
чьим фильтрам объявление отвечает. Уведомление отправляем не чаще раза
в сутки на подписку — иначе при активной категории оно превращается в поток.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import SavedSearch, Listing, User, SellerSubscription, Favorite
from app.core.clock import utcnow

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

    # Цена в фильтре — всегда в евро (фронт не даёт выбрать валюту),
    # а в базе — в исходной валюте объявления. Тот же курс, что и в
    # самом поиске (listings.py) и в tg_import.py.
    price = float(listing.price) if listing.price else None
    price_eur = price if (price is None or listing.currency == "EUR") else price / 117
    if filters.get("price_min") is not None:
        if price_eur is None or price_eur < float(filters["price_min"]):
            return False
    if filters.get("price_max") is not None:
        if price_eur is None or price_eur > float(filters["price_max"]):
            return False

    if filters.get("with_photo") and not listing.photos:
        return False

    # «Купить/Снять/Посуточно» и подобное — structural атрибут объявления
    # (недвижимость хранит под deal_type, работа — под listing_kind), а
    # не отдельное текстовое слово. Без этой проверки подписка на
    # «Снять» присылала бы и объявления о продаже.
    deal_type = filters.get("deal_type")
    if deal_type:
        attrs = listing.attributes or {}
        if attrs.get("deal_type") != deal_type and attrs.get("listing_kind") != deal_type:
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

    searches = db.query(SavedSearch).filter(SavedSearch.notify_enabled.is_(True)).all()
    if not searches:
        return 0

    # Язык каждого подписчика — чтобы уведомление пришло на понятном
    # ему языке, а не на том, что случайно оказался первым в списке
    # переводов объявления (обычно это язык оригинала).
    users_by_id = {
        u.id: u for u in db.query(User)
        .filter(User.id.in_({s.user_id for s in searches})).all()
    }
    from app.routers.listings import pick_translation

    sent = 0
    now = utcnow()

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
            subscriber = users_by_id.get(s.user_id)
            lang = "ru"
            if subscriber:
                lang = getattr(subscriber.default_language, "value", None) or "ru"
            tr = pick_translation(listing, lang)
            title = tr.title if tr else (translations[0].title if translations else "")
            price = f"{listing.price:.0f} {listing.currency}" if listing.price else ""
            text = (
                f"По вашему поиску «{s.name}» новое объявление:\n\n"
                f"<b>{title}</b>\n{price}"
            )
            # Человек сам включил уведомления по этой подписке — если
            # Telegram не привязан, уходит на почту.
            if notify(db, s.user_id, text, kind="searches", allow_email=True,
                      subject=f"PLONK — новое по поиску «{s.name}»",
                      link=f"/go/{listing.id}"):
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


def notify_seller_subscribers(db: Session, listing: Listing) -> int:
    """
    Подписка на продавца — не на фильтр, а на конкретного человека:
    любое его новое объявление интересно подписчику по определению,
    без ограничения на раз в сутки (в отличие от notify_subscribers
    выше) — тут подписчик сам решил следить именно за этим продавцом,
    а не попал под широкий фильтр категории.
    """
    subs = (
        db.query(SellerSubscription)
        .filter(SellerSubscription.seller_id == listing.owner_id)
        .all()
    )
    if not subs:
        return 0

    users_by_id = {
        u.id: u for u in db.query(User)
        .filter(User.id.in_({s.subscriber_id for s in subs})).all()
    }
    from app.routers.listings import pick_translation
    from app.core.notifications import notify

    translations = list(listing.translations or [])
    seller = db.query(User).get(listing.owner_id)
    seller_name = seller.display_name if seller else ""

    sent = 0
    for s in subs:
        subscriber = users_by_id.get(s.subscriber_id)
        if not subscriber:
            continue
        lang = getattr(subscriber.default_language, "value", None) or "ru"
        tr = pick_translation(listing, lang)
        title = tr.title if tr else (translations[0].title if translations else "")
        price = f"{listing.price:.0f} {listing.currency}" if listing.price else ""
        text = (
            f"{seller_name} опубликовал(а) новое объявление:\n\n"
            f"<b>{title}</b>\n{price}"
        )
        try:
            if notify(db, s.subscriber_id, text, kind="following", allow_email=True,
                      subject=f"PLONK — новое объявление от {seller_name}",
                      link=f"/go/{listing.id}"):
                sent += 1
        except Exception:
            continue

    if sent:
        log.info("Объявление %s: уведомлено подписчиков продавца %s", listing.id, sent)

    return sent


def notify_price_drop(db: Session, listing: Listing) -> int:
    """
    Тем, у кого объявление в избранном — цена упала с прошлого раза,
    когда оно было опубликовано. Вызывается там же, где и остальные
    'объявление стало активным' уведомления — не сразу при самой правке
    цены: правка сначала уводит объявление на повторную модерацию
    (см. content_changed в update_listing), в это время оно не
    показывается вовсе, и уведомлять о нём рано.

    Только в приложение/Telegram — специально без почты (allow_email
    не передаём, по умолчанию False): для избранного это не то, ради
    чего стоит открывать почтовый ящик, в отличие от решения по
    объявлению или запроса на вход.
    """
    history = listing.price_history or []
    if not history or listing.price is None:
        return 0
    prev_price = history[-1].get("price")
    prev_currency = history[-1].get("currency")
    if prev_price is None or prev_currency != listing.currency:
        return 0
    if float(listing.price) >= float(prev_price):
        return 0   # не упала — выросла или не изменилась с той записи

    favorites = (
        db.query(Favorite)
        .filter(Favorite.listing_id == listing.id)
        .all()
    )
    if not favorites:
        return 0

    from app.routers.listings import pick_translation
    from app.core.notifications import notify

    translations = list(listing.translations or [])
    sent = 0
    for fav in favorites:
        if fav.user_id == listing.owner_id:
            continue
        user = db.query(User).get(fav.user_id)
        if not user:
            continue
        lang = getattr(user.default_language, "value", None) or "ru"
        tr = pick_translation(listing, lang)
        title = tr.title if tr else (translations[0].title if translations else "")
        text = (
            f"Цена снизилась на объявление из избранного:\n\n"
            f"<b>{title}</b>\n"
            f"{prev_price:.0f} → {listing.price:.0f} {listing.currency}"
        )
        try:
            if notify(db, fav.user_id, text, kind="price_drop", subject="PLONK — цена снизилась",
                      link=f"/go/{listing.id}"):
                sent += 1
        except Exception:
            continue

    if sent:
        log.info("Объявление %s: уведомлено о снижении цены %s", listing.id, sent)

    return sent
