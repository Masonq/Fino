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


def test_sub_schemas_do_not_ask_a_boat_for_mileage():
    """
    Подраздел без своей схемы брал схему раздела: у «Лодок» форма
    спрашивала пробег, коробку и VIN, у «Мониторов» — память и
    аккумулятор, и по этому же предлагал искать фильтр подраздела.
    """
    from app.data.schemas import NO_FIELDS, SUB_SCHEMAS

    def keys(slug):
        return {f["key"] for f in SUB_SCHEMAS[slug]}

    for slug in ("water", "agri", "trailers", "e-transport"):
        assert not keys(slug) & {"mileage_km", "transmission", "vin", "body_type"}, slug
    for slug in ("monitors", "tv-projectors", "components", "network-gear"):
        assert not keys(slug) & {"storage_gb", "ram_gb", "battery_health"}, slug
    assert "size" not in keys("tickets") and "size" not in keys("jewelry")
    assert not NO_FIELDS & set(SUB_SCHEMAS)


def test_every_schema_field_is_well_formed():
    from app.data.schemas import SUB_SCHEMAS

    for slug, schema in SUB_SCHEMAS.items():
        seen = [f["key"] for f in schema]
        assert len(seen) == len(set(seen)), slug
        for field in schema:
            assert set(field["label"]) == {"ru", "en", "sr"}, (slug, field["key"])
            if field["type"] == "select":
                assert field.get("options"), (slug, field["key"])
