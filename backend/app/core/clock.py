"""
Текущее время в UTC.

datetime.utcnow() объявлен устаревшим и в будущих версиях Python исчезнет,
но простая замена на datetime.now(UTC) не годится: она возвращает время с
часовым поясом, а колонки в базе объявлены без него. Такое значение либо не
запишется, либо сравнение дат начнёт падать.

Поэтому берём время с поясом и снимаем его — получаем ровно то же, что
отдавал datetime.utcnow(), но без предупреждения.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Часовой пояс площадки. Белград: люди тут, объявления тут, и «сегодня»
# для них местное.
#
# Дни в статистике считались по UTC — а он отстаёт от Белграда на час
# летом и на два зимой. Оттого десятое число не появлялось в графике,
# хотя на часах уже десятое: по UTC ещё длилось девятое.
SITE_TZ = ZoneInfo("Europe/Belgrade")


def local_today() -> date:
    """Сегодняшний день по времени площадки, а не по UTC."""
    return datetime.now(SITE_TZ).date()


def local_date(moment: datetime) -> date:
    """День, к которому относится момент, по времени площадки."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(SITE_TZ).date()
