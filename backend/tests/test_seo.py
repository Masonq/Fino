"""
Что видит поисковик.

Сайт собирается в браузере: без карты поисковик видит пустую страницу и
обойти ссылки ему неоткуда. Объявления в выдачу не попадут вовсе.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_sitemap_is_built_live():
    """
    Объявления появляются каждый час. Карта суточной давности звала бы
    поисковика на снятые.
    """
    import inspect
    from app.routers.seo import sitemap

    source = inspect.getsource(sitemap)
    assert "ListingStatus.active" in source
    assert "order_by" in source


def test_service_pages_are_closed():
    """
    Личные страницы и админка в поиске не нужны никому — а вот
    объявления наоборот.
    """
    robots = (Path(__file__).resolve().parents[2]
              / "frontend" / "public" / "robots.txt").read_text()

    for page in ("/profile", "/admin", "/chats", "/enter"):
        assert f"Disallow: {page}" in robots, page
    assert "Allow: /" in robots
    assert "sitemap.xml" in robots


def test_page_tells_who_it_is():
    """
    Без описания поисковик покажет нас только по названию, а люди ищут
    «объявления Белград».
    """
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()

    assert 'rel="canonical"' in html
    # Раньше здесь требовалось три hreflang — по одному на язык сайта.
    # Требование снято намеренно: все три вели на один и тот же адрес,
    # потому что языковых адресов у сайта нет вовсе — язык переключается
    # внутри приложения, страница остаётся та же. Для поисковика три
    # ссылки на один адрес означают «других версий нет», то есть пользы
    # от них не было никакой. Остаётся x-default: он честно говорит, что
    # страница одна и подходит любому языку.
    #
    # Если когда-нибудь заведём настоящие адреса вида /en/... — сюда
    # вернётся проверка на три языка, но уже с разными адресами.
    assert 'hreflang="x-default"' in html
    assert "application/ld+json" in html
    # старый адрес с портом нигде не остался
    assert "89.208" not in html


def test_crawlers_get_text_people_get_the_site():
    """
    Сайт собирается в браузере: поисковик получает пустую страницу и ни
    названия вещи, ни цены не видит. Человеку урезанную страницу
    отдавать нельзя — он ждёт живой сайт.
    """
    from app.routers.seo import _is_crawler

    for agent in ("Mozilla/5.0 (compatible; Googlebot/2.1)",
                  "Mozilla/5.0 (compatible; YandexBot/3.0)",
                  "TelegramBot (like TwitterBot)"):
        assert _is_crawler(agent), agent

    for agent in ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
                  "Mozilla/5.0 (Windows NT 10.0; Win64) Chrome/120"):
        assert not _is_crawler(agent), agent


def test_listing_page_shows_price_in_search():
    """
    Разметка товара показывает цену прямо в выдаче — такое объявление
    открывают заметно чаще обычной строки.
    """
    import inspect
    from app.routers.seo import _listing_schema

    source = inspect.getsource(_listing_schema)
    assert '"@type": "Product"' in source
    assert "priceCurrency" in source
    assert "availability" in source


def test_subcategories_are_in_the_map():
    """«Сковороды» ищут чаще, чем «дом и сад»."""
    import inspect
    from app.routers.seo import sitemap

    source = inspect.getsource(sitemap)
    assert "Category).all()" in source


def test_description_is_clean_for_search():
    """
    В выдаче показывают около полутора сотен знаков. Тратить их на
    смайлики и переносы строк жалко.
    """
    from app.routers.seo import _clean

    out = _clean("Продам шлема, лежат без дела 🙈\nРазмеры M и L")
    assert "🙈" not in out
    assert "\n" not in out
    assert "Размеры M и L" in out


# ── Языковые адреса ─────────────────────────────────────────────────────────
def test_each_language_has_its_own_address():
    """У каждого языка свой адрес, а не один на троих.

    Раньше три hreflang вели на одну страницу: язык переключался внутри
    приложения, адрес не менялся. Для поисковика это значило «версий
    нет», и серб с англичанином находили в выдаче русскую страницу — а
    это половина людей в Белграде.
    """
    from app.routers.seo import _lang_url

    site = "https://plonk.rs"
    # Русский — основной и живёт без приставки: на него ведут все
    # существующие ссылки, ломать их ради единообразия нельзя.
    assert _lang_url(site, "/c/mebel", "ru") == "https://plonk.rs/c/mebel"
    assert _lang_url(site, "/c/mebel", "en") == "https://plonk.rs/en/c/mebel"
    assert _lang_url(site, "/c/mebel", "sr") == "https://plonk.rs/sr/c/mebel"


def test_sitemap_lists_language_versions():
    """Карта сайта перечисляет версии, иначе они конкурируют друг с другом."""
    from app.routers.seo import _with_langs

    entry = _with_langs("https://plonk.rs", "/c/mebel")
    assert 'hreflang="x-default"' in entry
    assert 'hreflang="en" href="https://plonk.rs/en/c/mebel"' in entry
    assert 'hreflang="sr" href="https://plonk.rs/sr/c/mebel"' in entry


def test_section_page_is_translated_whole():
    """Страница раздела переведена целиком, а не только название.

    Иначе у английской версии выходит половина заголовка по-русски —
    «Real Estate — объявления в Белграде и Сербии», — и в англоязычной
    выдаче она выглядит страницей на чужом языке.
    """
    from app.routers.seo import CATEGORY_TEXTS

    for lang in ("ru", "en", "sr"):
        assert set(CATEGORY_TEXTS[lang]) == set(CATEGORY_TEXTS["ru"])
    assert "classifieds" in CATEGORY_TEXTS["en"]["title"]
    assert "oglasi" in CATEGORY_TEXTS["sr"]["title"]
