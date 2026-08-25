"""
Полнота объявления.

Первое впечатление важнее числа: человек, попавший на обрубки без цены и
фотографии, второй раз не придёт. Но и прятать их нельзя — вещь без
снимка тоже кому-то нужна.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeTranslation:
    def __init__(self, title, language="ru"):
        self.title = title
        self.language = language


class FakeListing:
    def __init__(self, title="Стол письменный IKEA", price=6000,
                 is_free=False, photos=1):
        self.translations = [FakeTranslation(title)]
        self.source_language = "ru"
        self.price = price
        self.is_free = is_free
        self.photos = [object()] * photos


def test_complete_needs_title_price_photo():
    """
    Название, цена и снимок — минимум, при котором вещь можно
    рассмотреть и купить.
    """
    from app.routers.listings import _looks_complete

    assert _looks_complete(FakeListing())
    assert not _looks_complete(FakeListing(price=None))
    assert not _looks_complete(FakeListing(photos=0))
    assert not _looks_complete(FakeListing(title="Стол"))   # слишком коротко


def test_free_counts_as_priced():
    """«Отдам даром» — это цена, а не её отсутствие."""
    from app.routers.listings import _looks_complete

    assert _looks_complete(FakeListing(price=None, is_free=True))


def test_incomplete_are_lowered_not_hidden():
    """
    Объявление без снимка тоже кому-то нужно: оно находится поиском,
    открывается по ссылке и живёт в своём разделе. В ленте — ниже.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    # в сортировке участвует, но не в отборе
    assert "Listing.is_complete.desc()" in source
    assert "filter(Listing.is_complete" not in source


def test_search_puts_the_word_first():
    """
    При поиске слово в названии важнее полноты: человек искал
    конкретную вещь, а не красивую карточку.
    """
    import inspect
    from app.routers.listings import search_listings

    source = inspect.getsource(search_listings)
    # при поиске слово идёт первым в списке сортировки
    assert "ordering = [title_hit, Listing.is_complete.desc()]" in source
    # а без поиска первой стоит полнота
    assert "ordering = [Listing.is_complete.desc()]" in source
