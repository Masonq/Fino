"""
Проверка цены по соседям.

До сих пор мы проверяли цену саму по себе: есть ли она в тексте, не
слишком ли мала для такой вещи. Но «стол за 500 000 динар» проходит обе
проверки — число в тексте есть, а нижней границы у столов нет.

Соседи об этом знают: если два десятка столов стоят от трёх до
пятнадцати тысяч, а этот пятьсот, где-то ошибка — приписан лишний ноль
или взято не то число.

Отклонение считаем по медиане, а не по среднему: одно объявление за
миллион утянет среднее так, что после него всё покажется нормальным.
"""
import logging
import statistics

log = logging.getLogger(__name__)

# Во сколько раз цена должна отличаться от медианы, чтобы счесть её
# ошибкой. Три — намеренно широко: вещи в одном разделе бывают очень
# разными, и придирчивость выбросит верные цены.
TIMES_ABOVE = 12
TIMES_BELOW = 12

# Меньше этого числа соседей — судить не по чему.
ENOUGH_NEIGHBOURS = 8


def median_price(db, category_id, currency) -> float | None:
    """
    Обычная цена в разделе.

    Берём медиану: одно объявление за миллион утянет среднее так, что
    после него всё покажется нормальным.
    """
    from app.models import Listing, ListingStatus

    prices = [
        float(p) for (p,) in
        db.query(Listing.price)
        .filter(Listing.category_id == category_id,
                Listing.currency == currency,
                Listing.price.isnot(None),
                Listing.status == ListingStatus.active)
        .all()
        if p
    ]
    if len(prices) < ENOUGH_NEIGHBOURS:
        return None
    return statistics.median(prices)


def is_outlier(price: float, median: float | None) -> str | None:
    """
    Цена выбивается из ряда.

    Возвращает «выше» или «ниже» — или None, если всё в порядке.
    """
    if not median or median <= 0 or price <= 0:
        return None

    if price > median * TIMES_ABOVE:
        return "выше"
    if price < median / TIMES_BELOW:
        return "ниже"
    return None
