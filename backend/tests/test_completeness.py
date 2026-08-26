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


def test_sold_listing_stays_visible():
    """
    Снятое объявление не исчезает: по нему смотрят, за сколько ушла
    похожая вещь, и на него уже стоят ссылки. Но человек должен видеть,
    что вещи больше нет, а не писать продавцу впустую.
    """
    import inspect
    from app.routers.listings import get_listing

    # состояние отдаётся сайту
    assert '"status": listing.status.value' in inspect.getsource(get_listing)

    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()
    assert "listing?.status === 'sold'" in page
    assert "detail.sold" in page
    # внизу — возврат в раздел, а не обещание похожих: подбор пока
    # слабый, и пустая надежда хуже честного «смотрите раздел»
    assert "detail.gone_to_category" in page


def test_brand_alone_is_not_a_title():
    """
    «Hutschenreuther» — марка без вещи, «Чем занимался» — обрывок
    фразы. Человек не поймёт, что продают, пока не откроет: в ленте
    таким не место.
    """
    from app.routers.listings import title_is_clear

    assert not title_is_clear("Hutschenreuther")
    assert not title_is_clear("Privileg")
    assert not title_is_clear("Чем занимался")
    assert not title_is_clear("Studio")

    # а с названием вещи — годится
    assert title_is_clear("Ваза фарфоровая Hutschenreuther")
    assert title_is_clear("Комод антикварный, массив дерева")


def test_known_brands_are_an_exception():
    """
    «iPhone 13 Pro» понятен без слова «телефон»: такие марки знают все,
    и требовать пояснения было бы придиркой.
    """
    from app.routers.listings import title_is_clear

    assert title_is_clear("iPhone 13 Pro 256gb")
    assert title_is_clear("MacBook m3 max 16")


def test_mid_sentence_titles_are_rejected():
    """
    «И я могу взять на себя уборку» — фраза из середины: существительное
    в ней есть, но названием вещи это не является.
    """
    from app.routers.listings import title_is_clear

    assert not title_is_clear("И я могу взять на себя уборку вашего дома")
    assert not title_is_clear("Вроде бы размер XS, носили в 5 лет")
    assert not title_is_clear("Это отличный стол")
    assert not title_is_clear("Как новый диван")

    # а нормальное название начинается с вещи
    assert title_is_clear("Уборка домов и квартир в Белграде")
    assert title_is_clear("Комод антикварный, массив дерева")
