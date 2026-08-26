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


def test_advertising_phrases_are_rejected():
    """
    «Наш капитан поможет», «уже более 4 лет помогаем» — рекламная
    фраза, а не название. Настоящее название глагола не содержит:
    «Комод антикварный», «Монитор Philips».
    """
    from app.routers.listings import title_is_clear

    assert not title_is_clear("Наш капитан поможет сделать много фотографий")
    assert not title_is_clear("Уже более 4 лет помогаем клиентам с трансферами")
    assert not title_is_clear("Приглашаю в нейл студию на маникюр")


def test_service_names_survive():
    """
    «Уборка», «хранение», «стрижка» — отглагольные существительные, но
    это названия услуг, и в ленте им место.
    """
    from app.routers.listings import title_is_clear

    assert title_is_clear("Хранение ваших вещей в Белграде")
    assert title_is_clear("Мужская классическая стрижка в центре Белграда")
    assert title_is_clear("Клининг в Белграде от опытного клинера")
    assert title_is_clear("Мелкогабаритный переезд (без мебели)")


def test_count_before_the_thing_is_fine():
    """
    «2 велосипедных шлема» — после числа вещь стоит в родительном, и
    это верная форма, а не обрывок фразы.
    """
    from app.routers.listings import title_is_clear

    assert title_is_clear("2 велосипедных шлема")
    assert title_is_clear("3 стула из массива")


def test_unknown_words_do_not_break_it():
    """
    Незнакомое слово словарь принимает за глагол («юникло»). Судить по
    неуверенному разбору нельзя — хорошие названия попадут под нож.
    """
    from app.routers.listings import title_is_clear

    assert title_is_clear("рубашка юникло, размер xs")


def test_latin_names_are_fine():
    """
    Название техники целиком на латинице — обычное дело: «Honor Magic
    V3», «Canon RF 28mm». Требовать от них русского слова значит
    выбросить половину электроники.
    """
    from app.routers.listings import title_is_clear

    for title in ("Legion Go S", "Honor Magic V3 - 512 GB",
                  "Synology DS420j", "Canon RF 28mm f/2.8 STM",
                  "Nespresso VERTUO POP", "Canyon Grizl"):
        assert title_is_clear(title), title


def test_new_words_are_known():
    """
    Словарь не знает «худи», «свитшот», «лонгслив» — слова новые, а
    объявления с ними живые.
    """
    from app.routers.listings import title_is_clear

    assert title_is_clear("Худи оверсайз с огромным капюшоном")
    assert title_is_clear("Свитшот H&M размер M")


def test_case_is_not_required():
    """
    «Три мяча», «Два матраса» — верные названия, а словарь видит в них
    родительный падеж. Строгость тут выбрасывает больше хорошего, чем
    ловит плохого.
    """
    from app.routers.listings import title_is_clear

    assert title_is_clear("Три мяча для тенниса")
    assert title_is_clear("Два матраса 180х90 примерно")


def test_single_word_is_not_enough():
    """
    «Обувь», «Стол», «Hutschenreuther» — одно слово без уточнений.
    Вещь названа, но что именно продают, непонятно: ни размера, ни
    марки, ни состояния. Такое объявление откроют вслепую.
    """
    from app.routers.listings import title_is_clear

    for title in ("Обувь", "Стол", "Скейт", "Компьютер",
                  "Hutschenreuther", "Privileg"):
        assert not title_is_clear(title), title


def test_short_names_with_details_survive():
    """А с уточнением — годится, даже если само название короткое."""
    from app.routers.listings import title_is_clear

    assert title_is_clear("AirPods 4")
    assert title_is_clear("Зимние Skechers")
    assert title_is_clear("Стол письменный IKEA")
    assert title_is_clear("Скейт для начинающих")


def test_direct_visitor_can_leave():
    """
    navigate(-1) возвращает в историю браузера, а у пришедшего по
    прямой ссылке — из поиска, из телеграма — её нет: кнопка не делает
    ничего, и человек застревает.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    assert "window.history.state?.idx" in page
    # без истории ведём в раздел объявления
    assert "/category/${listing.category_slug}" in page
    # и прямых navigate(-1) не осталось
    assert "onClick={() => navigate(-1)}" not in page


def test_long_description_is_folded():
    """
    В объявлениях из чата описания пишут на пол-экрана, и до продавца
    человек не доскроллит.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    assert "descOpen" in page
    assert "detail.read_more" in page


def test_empty_categories_are_marked():
    """
    Раздел с тремя объявлениями хуже, чем его отсутствие: он обещает
    выбор и не даёт его. OpenTable выяснил числом — около полусотни
    предложений, и тогда поиск даёт достаточно, чтобы решить задачу.
    """
    import inspect
    from app.routers.categories import ENOUGH_FOR_CHOICE, list_categories

    assert 20 <= ENOUGH_FOR_CHOICE <= 100

    source = inspect.getsource(list_categories)
    assert '"ready"' in source
    assert '"count"' in source
    # считаем разом, а не запросом на каждый раздел
    assert "group_by(Listing.category_id)" in source


def test_subcategories_count_towards_the_parent():
    """
    Объявления лежат в подразделах, и без них верхний раздел выглядит
    пустым, хотя выбор в нём есть.
    """
    import inspect
    from app.routers.categories import list_categories

    source = inspect.getsource(list_categories)
    assert "sum(total(c) for c in cat.children)" in source
