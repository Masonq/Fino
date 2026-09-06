"""
Сколько обычно просят за такие вещи.

Человек, подающий объявление, чаще всего не знает цену. Отсюда и
«Комод за 100 евро» рядом с «Комодом за 15»: один поставил наугад
много, другой — наугад мало, и оба потом не понимают, почему не
пишут.

Считаем по своим же объявлениям: у нас их несколько тысяч, и этого
довольно, чтобы показать вилку. Никаких внешних источников — цены на
рынке Белграда лучше всего описывают объявления самого Белграда.

Что показываем: середину и вилку, а не одно число. Одно число человек
воспримет как указание («сайт сказал 30»), а вилка оставляет решение
за ним — он лучше знает состояние своей вещи.
"""
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import utcnow

# За какой срок берём цены. Полгода: рынок за это время не успевает
# уйти, а данных набирается достаточно даже в редких разделах.
WINDOW_DAYS = 180

# Меньше этого — не показываем ничего. По трём объявлениям вилку не
# построишь, а неверная подсказка хуже её отсутствия: человек ей
# поверит.
MIN_SAMPLE = 8

QUERY = """
    select
        percentile_cont(0.25) within group (order by l.price) as low,
        percentile_cont(0.50) within group (order by l.price) as mid,
        percentile_cont(0.75) within group (order by l.price) as high,
        count(*) as n
    from listings l
    where l.category_id = :category_id
      and l.currency = cast(:currency as currency)
      and l.price is not null
      and l.price > 0
      and l.is_free is not true
      and l.created_at >= :since
      and l.status in ('active', 'sold')
"""


def price_hint(db: Session, category, currency: str) -> dict | None:
    """
    Вилка цен для раздела. Если в самом разделе объявлений мало,
    поднимаемся к родительскому: лучше показать вилку по «Мебели», чем
    промолчать из-за того, что «Комодов» всего пять.
    """
    since = utcnow() - timedelta(days=WINDOW_DAYS)
    # В базе валюта хранится строчными («rsd», «eur») и как отдельный
    # тип: строку в верхнем регистре она не принимает. Поймал сразу на
    # запросе.
    currency = (currency or "").lower()
    node = category

    while node is not None:
        row = db.execute(text(QUERY), {
            "category_id": node.id, "currency": currency, "since": since,
        }).first()

        if row and row.n >= MIN_SAMPLE:
            return {
                "low": int(row.low),
                "mid": int(row.mid),
                "high": int(row.high),
                "count": int(row.n),
                # По какому разделу считали: если поднялись к родителю,
                # человек должен это видеть, иначе решит, что вилка
                # ровно про его комоды.
                "category": (node.name or {}),
                "exact": node.id == category.id,
            }

        node = node.parent

    return None
