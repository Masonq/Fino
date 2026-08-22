"""
Текущее время в UTC.

datetime.utcnow() объявлен устаревшим и в будущих версиях Python исчезнет,
но простая замена на datetime.now(UTC) не годится: она возвращает время с
часовым поясом, а колонки в базе объявлены без него. Такое значение либо не
запишется, либо сравнение дат начнёт падать.

Поэтому берём время с поясом и снимаем его — получаем ровно то же, что
отдавал datetime.utcnow(), но без предупреждения.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
