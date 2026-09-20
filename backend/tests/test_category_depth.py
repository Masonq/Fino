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
from app.core.category_tree import branch_ids as _branch_ids, root_of  # noqa: E402


class Cat:
    def __init__(self, id, children=()):
        self.id, self.children, self.parent = id, list(children), None
        for child in self.children:
            child.parent = self


def test_root_is_found_from_third_level():
    """
    «Родитель или сам» на третьем уровне давал подраздел вместо раздела:
    сантехник из «Услуги» → «Мастера» попадал во вкладку «Даром», а
    интересы человека писались на «Мастеров», а не на «Услуги».
    """
    leaf = Cat("plumber")
    root = Cat("services", [Cat("masters", [leaf])])
    assert root_of(leaf) is root
    assert root_of(root) is root


def test_no_more_parent_or_self_shortcuts():
    """Привычка считать корнем родителя не должна вернуться в код."""
    import re
    app = Path(__file__).resolve().parents[1] / "app"
    bad = re.compile(r"coalesce\(\s*\w+\.(parent_id|slug)\s*,|\.parent_id or \w+\.id")
    hits = [f"{f.relative_to(app)}:{n}" for f in app.rglob("*.py")
            for n, line in enumerate(f.read_text().splitlines(), 1)
            if bad.search(line) and not line.lstrip().startswith("#")
            and f.name != "category_tree.py"]
    assert not hits, hits


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
