"""
Подбор похожих объявлений.

Раздел и цена слишком грубы: в «Мебели» тысяча вещей, и рядом со столом
оказывался шкаф за те же деньги. Человек, открывший коляску, хочет
посмотреть другие коляски.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.listings import _title_words  # noqa: E402


class FakeTranslation:
    def __init__(self, title):
        self.title = title
        self.language = "ru"


class FakeListing:
    def __init__(self, title):
        self.translations = [FakeTranslation(title)]
        self.source_language = "ru"


def words(title: str) -> set[str]:
    return _title_words(FakeListing(title), "ru")


def test_empty_words_are_dropped():
    """
    «Продам», «срочно», «в отличном состоянии» есть в половине
    объявлений и роднят стол с диваном.
    """
    got = words("Продам срочно диван в отличном состоянии, недорого")
    assert got == {"диван"}


def test_forms_are_normalised():
    """«Коляска» и «коляски» — одно слово: человек пишет как придётся."""
    assert "коляска" in words("Коляски Peg Perego")
    assert "коляска" in words("Коляску Chicco продам")


def test_similar_things_share_words():
    """Коляска ближе к коляске, чем к столу за те же деньги."""
    base = words("Коляска Chicco 2в1")

    close = words("Коляска трость Chicco")
    far = words("Стол письменный IKEA")

    assert base & close
    assert not (base & far)


def test_brand_matters():
    """
    «Коляска Chicco» ближе к другой Chicco, чем к коляске иной марки:
    марку в названии пишут не просто так.
    """
    base = words("Коляска Chicco 2в1")

    same_brand = len(base & words("Коляска трость Chicco"))
    other_brand = len(base & words("Коляска Peg Perego прогулочная"))

    assert same_brand > other_brand


def test_ranking_puts_title_first():
    """
    Сходство названий решает, раздел и цена уточняют. Иначе подборка
    наполняется случайными вещами в том же бюджете.
    """
    import inspect
    from app.routers.listings import similar_listings

    source = inspect.getsource(similar_listings)
    order = source[source.index("return (own,"):source.index("candidates.sort")]
    assert order.index("overlap") < order.index("diff")
    assert order.index("overlap") < order.index("same_city")
