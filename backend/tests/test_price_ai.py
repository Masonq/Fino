"""
Цена нейросетью.

В описании чего только нет: размер «EUR 36», объём памяти, год выпуска,
старая цена. Правила берут первое подходящее число и промахиваются —
куртка становится за семьдесят динар, а веб-камера за тысячу евро.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.price_ai import _in_text, looks_wrong  # noqa: E402


def test_suspicious_prices_go_to_the_model():
    """
    Вещь дешевле сотни динар — это почти всегда размер или объём, а не
    деньги.
    """
    assert looks_wrong(70, "RSD", "Лёгкая куртка Zara", "размер S")
    assert looks_wrong(2, "EUR", "Кроссовки", "")
    assert looks_wrong(None, None, "Электроника", "")


def test_traps_in_the_text_go_to_the_model():
    """
    «Размер», «GB», «батарея 99%», «покупал за» — из-за них правила и
    промахиваются.
    """
    assert looks_wrong(2000, "RSD", "Кеды Converse", "р.37 -2000 rsd")
    assert looks_wrong(2200, "EUR", "MacBook", "батарея 99%")
    assert looks_wrong(6000, "RSD", "Телевизор", "покупал за 12000")


def test_ordinary_prices_are_left_alone():
    """
    Обычное объявление модели не показываем: правила на нём не
    ошибаются, а обращения к модели не бесплатны.
    """
    assert not looks_wrong(6000, "RSD", "Стол письменный IKEA",
                           "отличное состояние, самовывоз")
    assert not looks_wrong(25000, "RSD", "Диван раскладной", "Земун")


def test_invented_price_is_refused():
    """
    Модель может придумать число. Записать выдумку вместо пустоты хуже,
    чем оставить пустоту.
    """
    assert _in_text(2000, "продам за 2000 динар")
    assert _in_text(2000, "цена 2 000 динар")     # с пробелом
    assert not _in_text(5000, "продам за 2000 динар")
