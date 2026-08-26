"""
Проверка цены по соседям.

«Стол за 500 000 динар» проходит все прежние проверки: число в тексте
есть, нижней границы у столов нет. Но соседи знают, сколько обычно
стоит стол.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.price_sanity import ENOUGH_NEIGHBOURS, is_outlier  # noqa: E402


def test_extra_zero_is_caught():
    """Приписанный ноль — самая частая ошибка в цене."""
    assert is_outlier(500_000, 6_000) == "выше"
    assert is_outlier(60_000_000, 500_000) == "выше"


def test_too_cheap_is_caught():
    """
    Взято не то число: размер вместо цены, объём вместо цены.
    """
    assert is_outlier(300, 6_000) == "ниже"
    assert is_outlier(37, 2_000) == "ниже"


def test_ordinary_spread_is_left_alone():
    """
    Вещи в одном разделе бывают очень разными. Придирчивость выбросит
    верные цены: дизайнерский стол дороже обычного вдесятеро.
    """
    assert is_outlier(6_000, 6_000) is None
    assert is_outlier(25_000, 6_000) is None
    assert is_outlier(70_000, 6_000) is None
    assert is_outlier(1_000, 6_000) is None


def test_no_neighbours_no_judgement():
    """Судить не по чему, если соседей мало."""
    assert is_outlier(500_000, None) is None
    assert ENOUGH_NEIGHBOURS >= 5
