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


def things(title: str) -> set[str]:
    """Сама вещь: «шлем», «коляска», «стол»."""
    return _title_words(FakeListing(title), "ru")[0]


def traits(title: str) -> set[str]:
    """Признаки: «велосипедный», «детский», «письменный»."""
    return _title_words(FakeListing(title), "ru")[1]


def test_empty_words_are_dropped():
    """
    «Продам», «срочно», «в отличном состоянии» есть в половине
    объявлений и роднят стол с диваном.
    """
    assert things("Продам срочно диван в отличном состоянии, недорого") \
        == {"диван"}


def test_forms_are_normalised():
    """«Коляска» и «коляски» — одно слово: человек пишет как придётся."""
    assert "коляска" in things("Коляски Peg Perego")
    assert "коляска" in things("Коляску Chicco продам")


def test_similar_things_share_words():
    """Коляска ближе к коляске, чем к столу за те же деньги."""
    base = things("Коляска Chicco 2в1")

    assert base & things("Коляска трость Chicco")
    assert not (base & things("Стол письменный IKEA"))


def test_brand_matters():
    """
    «Коляска Chicco» ближе к другой Chicco, чем к коляске иной марки:
    марку в названии пишут не просто так.
    """
    base = things("Коляска Chicco 2в1")

    same_brand = len(base & things("Коляска трость Chicco"))
    other_brand = len(base & things("Коляска Peg Perego прогулочная"))

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


def test_shared_adjective_is_not_enough():
    """
    «Велосипедный шлем» и «велосипедное кресло» делят определение, но
    вещи разные. Ставить их рядом нельзя — подборка теряет смысл.
    """
    helmet = things("2 велосипедных шлема")

    assert helmet & things("Шлем велосипедный со съемной защитой")
    assert not (helmet & things("Детское велосипедное кресло"))

    # определение при этом общее — значит решает именно предмет
    assert traits("2 велосипедных шлема") & traits("Детское велосипедное кресло")


def test_brands_count_as_the_thing():
    """
    «Chicco» отличает коляску от коляски вернее любого прилагательного,
    поэтому марка идёт к предмету, а не к признакам.
    """
    assert "chicco" in things("Коляска Chicco 2в1")
    assert "ikea" in things("Стол письменный IKEA MICKE")
