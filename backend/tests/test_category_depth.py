"""
Раздел показывает объявления всех уровней ниже себя.

Страница «Бизнес и оборудование» писала «3 объявления», а по кнопке
открывалось одно: счётчик шёл по дереву до конца, а поиск брал только
прямых детей. Два объявления лежали на третьем уровне.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.plural import count  # noqa: E402
from app.routers.listings import _branch_ids  # noqa: E402


class Cat:
    def __init__(self, id, children=()):
        self.id, self.children = id, list(children)


def test_third_level_is_included():
    tree = Cat("business", [Cat("equipment", [Cat("food-equipment")]), Cat("ready")])
    assert set(_branch_ids(tree)) == {"business", "equipment", "food-equipment", "ready"}


def test_leaf_is_itself():
    assert _branch_ids(Cat("leaf")) == ["leaf"]


def test_plural_forms():
    words = ("объявление", "объявления", "объявлений")
    assert count(1, *words) == "1 объявление"
    assert count(3, *words) == "3 объявления"
    assert count(11, *words) == "11 объявлений"
    assert count(21, *words) == "21 объявление"
    assert count(112, *words) == "112 объявлений"
