"""
Сообщаем, когда подешевело то, что человек отложил.

Часть лучших сделок — не свежие объявления, а те, что повисели без
покупателя и подешевели: продавец устал ждать и сбросил цену. Заметить
это самому нельзя, разве что заходить в избранное каждый день.

Кому пишем: тем, у кого объявление в избранном. Это прямой знак
интереса — человек сам его отложил, а значит ждёт удобного момента.
Просмотревшим не пишем: посмотреть можно и случайно.

О чём молчим:
  • о повышении цены — это не новость, а огорчение;
  • о копеечных изменениях: сбросили сто динаров из десяти тысяч —
    человека это не касается;
  • о том, о чём уже сообщали: цена меняется несколько раз, а
    сообщение об одном и том же приходит один.

Запуск по расписанию:
    python3 -m app.core.price_drop_alerts
"""
from decimal import Decimal

from sqlalchemy import text

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.notifications import notify

# Насколько должна упасть цена, чтобы об этом стоило писать.
#
# Десятая часть — заметная скидка: с 10 000 до 9 000 динар человек
# правда захочет вернуться, а из-за 200 динар его беспокоить не за что.
MIN_DROP = Decimal("0.10")

# И не меньше этого в деньгах — иначе на дешёвых вещах десятая часть
# оказывается парой сотен динар.
MIN_ABS = {"rsd": Decimal("300"), "eur": Decimal("3")}


def run() -> int:
    """Рассылает уведомления о подешевевшем. Возвращает, сколько отправлено."""
    from app.models import Favorite, Listing, ListingStatus

    sent = 0
    with SessionLocal() as db:
        # Берём только то, что кто-то отложил: остальное никому не
        # обещали, и рассылать по всей базе незачем.
        rows = (
            db.query(Listing, Favorite)
            .join(Favorite, Favorite.listing_id == Listing.id)
            .filter(Listing.status == ListingStatus.active,
                    Listing.price.isnot(None))
            .all()
        )

        for listing, fav in rows:
            drop = _drop_size(listing)
            if not drop:
                continue

            # Об этой цене уже писали — молчим. Иначе продавец,
            # поправивший цену трижды, разошлёт три сообщения об одном
            # и том же.
            told = (listing.notified_price_drop or {})
            if str(told.get(str(fav.user_id))) == str(listing.price):
                continue

            was, now, percent = drop
            text_lines = [
                "Подешевело то, что вы отложили:",
                "",
                listing.translations[0].title if listing.translations else "",
                f"{was} → {now} ({percent}% дешевле)",
            ]

            if notify(db, fav.user_id, "\n".join(text_lines),
                      allow_email=True,
                      subject="Подешевело объявление из избранного",
                      link=None):
                sent += 1

            told[str(fav.user_id)] = str(listing.price)
            listing.notified_price_drop = told
            db.commit()

    return sent


def _drop_size(listing):
    """
    (было, стало, процент) — или None, если писать не о чем.
    """
    if not listing.price_history:
        return None

    last = listing.price_history[-1]
    if last.get("currency") != (
        listing.currency.value if hasattr(listing.currency, "value")
        else listing.currency
    ):
        # Сменили валюту — сравнивать нечего: 100 евро против 12 000
        # динар это не «подорожало», а другая единица.
        return None

    was = Decimal(str(last["price"]))
    now = Decimal(str(listing.price))
    if now >= was or was <= 0:
        return None

    diff = was - now
    if diff / was < MIN_DROP:
        return None

    currency = (listing.currency.value if hasattr(listing.currency, "value")
                else str(listing.currency)).lower()
    if diff < MIN_ABS.get(currency, Decimal("0")):
        return None

    return int(was), int(now), int(diff / was * 100)


if __name__ == "__main__":
    print(f"отправлено уведомлений: {run()}")
