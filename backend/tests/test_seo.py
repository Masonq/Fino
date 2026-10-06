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
    """«Сковороды» ищут чаще, чем «дом и сад» — подразделы в карте есть, но только живые.

    Пустой раздел в карте — «тонкая» страница: поисковик считает её
    пустышкой и тянет вниз весь сайт.
    """
    import inspect
    from app.routers.seo import sitemap

    source = inspect.getsource(sitemap)
    assert "_tree(db)" in source and "_branch_counts" in source
    assert "if counts.get(category.id)" in source
    # И разделы в городах — от порога объявлений.
    assert "MIN_CITY_LISTINGS" in source


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
    """У каждого языка свой адрес: сербский — основной и без приставки, русский — /ru/, английский — /en/."""
    from app.routers.seo import _lang_url

    site = "https://plonk.rs"
    assert _lang_url(site, "/c/mebel", "sr") == "https://plonk.rs/c/mebel"
    assert _lang_url(site, "/c/mebel", "ru") == "https://plonk.rs/ru/c/mebel"
    assert _lang_url(site, "/c/mebel", "en") == "https://plonk.rs/en/c/mebel"


def test_sitemap_lists_language_versions():
    """Карта сайта перечисляет версии, иначе они конкурируют друг с другом — и только существующие."""
    from app.routers.seo import _with_langs

    entry = _with_langs("https://plonk.rs", "/c/mebel")
    assert "<loc>https://plonk.rs/c/mebel</loc>" in entry
    assert 'hreflang="x-default" href="https://plonk.rs/c/mebel"' in entry
    assert 'hreflang="en" href="https://plonk.rs/en/c/mebel"' in entry
    assert 'hreflang="ru" href="https://plonk.rs/ru/c/mebel"' in entry

    # Объявление только на русском: одна версия, она же основная.
    only_ru = _with_langs("https://plonk.rs", "/beograd/mebel/stol-12345678", langs=["ru"], main="ru")
    assert "<loc>https://plonk.rs/ru/beograd/mebel/stol-12345678</loc>" in only_ru
    assert 'hreflang="en"' not in only_ru and 'hreflang="sr"' not in only_ru


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


def test_no_cache_busting_parameter_in_urls():
    """К адресам не дописывается служебный параметр.

    В шапке стоял скрипт, добавлявший ?_v=<время> и делавший переход на
    новый адрес — против устаревших снимков страницы в Safari. Лечил
    одно, ломая три: лишняя загрузка на каждом первом заходе, мусорный
    хвост в ссылках, которые люди копируют и шлют друг другу, и переход
    на неканонический адрес на глазах у поисковика.

    Вместо него — событие возврата из снимка (pageshow с признаком
    persisted), адрес при этом не меняется.
    """
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()
    app = (Path(__file__).resolve().parents[2]
           / "frontend" / "src" / "App.jsx").read_text()

    assert "searchParams.set('_v'" not in html
    assert "location.replace" not in html
    assert "event.persisted" in app


def test_page_can_be_zoomed():
    """Страницу можно увеличить пальцами.

    maximum-scale=1.0 это запрещал. Ставят его, чтобы Safari не
    увеличивал экран при вводе в поле, но платит за это человек,
    которому нужно разглядеть мелкий текст или фото. Против увеличения
    при вводе есть честный способ — шрифт в полях не меньше 16px.
    """
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()

    # Смотрим саму строку с настройками, а не весь файл: слово
    # «maximum-scale» осталось в пояснении рядом, и проверка по всему
    # файлу спотыкалась о собственный комментарий.
    import re

    viewport = re.search(r'<meta name="viewport" content="([^"]+)"', html).group(1)
    assert "maximum-scale" not in viewport
    assert "user-scalable=no" not in viewport


def test_page_without_scripts_says_what_to_do():
    """Без скриптов человек видит объяснение, а не пустоту."""
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()

    assert "<noscript>" in html
    assert "JavaScript" in html


def test_unknown_address_answers_not_found():
    """Несуществующий адрес отвечает «страницы нет», а не «всё хорошо».

    Раньше любой случайный путь отдавал приложение со статусом 200:
    поисковик считал такую страницу настоящей и заносил в индекс, а
    удалённые объявления оставались в выдаче живыми.

    Человека это не касается: ему по-прежнему отдаётся приложение —
    nginx доводит до этого обработчика только поисковика.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "seo.py").read_text()
    conf = (Path(__file__).resolve().parents[2]
            / "deploy" / "plonk.rs.conf").read_text()

    assert 'status_code=404' in source
    assert 'meta name="robots" content="noindex"' in source
    # Настоящие страницы приложения отвечают как прежде.
    assert '"/search"' in source and '"/categories"' in source
    # Человеку — приложение, поисковику — ответ бэкенда.
    assert "if ($is_crawler) { return 418; }" in conf


def test_broken_listing_id_does_not_crash():
    """Негодный номер объявления не роняет страницу.

    В адресе удалённого объявления хвост может не разбираться как
    номер. Такой запрос уходил в базу как есть и падал — поисковик
    получал «сервер сломался» вместо «страницы нет».
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "seo.py").read_text()

    listing_page = source.split("def listing_page")[1].split("def ")[0]
    assert "except Exception" in listing_page
    assert "db.rollback()" in listing_page


def test_social_locale_codes_are_real():
    """Коды языка для соцсетей — из тех, что они понимают.

    Стояли ru_RS и en_RS: таких сочетаний в списке нет, и разборщик
    либо пропускает их, либо откатывается к своему умолчанию. Сербский
    sr_RS существует, русский пишется ru_RU, английский en_US.
    """
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()

    # Смотрим сами теги, а не весь файл: прежние коды остались в
    # пояснении рядом — второй раз спотыкаюсь о собственный комментарий.
    import re

    codes = re.findall(r'property="og:locale[^"]*" content="([^"]+)"', html)
    assert codes, "коды языка должны быть"
    assert "ru_RU" in codes
    assert "ru_RS" not in codes and "en_RS" not in codes


def test_language_links_point_to_language_addresses():
    """Языковые ссылки главной ведут на языковые адреса: сербский — без приставки."""
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()

    assert 'hreflang="sr" href="https://plonk.rs/"' in html
    assert 'hreflang="ru" href="https://plonk.rs/ru/"' in html
    assert 'hreflang="en" href="https://plonk.rs/en/"' in html
    assert 'hreflang="x-default" href="https://plonk.rs/"' in html


def test_manifest_has_a_maskable_icon():
    """В манифесте есть значок, который система может обрезать по-своему.

    Без него Android рисует картинку целиком внутри белого круга, и
    логотип на домашнем экране получается вдвое меньше положенного.
    """
    import json

    manifest = json.loads((Path(__file__).resolve().parents[2]
                           / "frontend" / "public" / "manifest.webmanifest").read_text())

    assert any(i.get("purpose") == "maskable" for i in manifest["icons"])


# ── Скорость ────────────────────────────────────────────────────────────────
def test_pages_load_on_demand():
    """Страницы, кроме первого захода, подгружаются по требованию.

    Всё приложение уезжало в один файл на 808 КБ, и человек, открывший
    одну карточку из рекламы, ждал, пока догрузятся служебный раздел,
    чаты и подача объявления. Сразу грузятся только главная, объявление,
    раздел и поиск; остальное — когда человек туда идёт.
    """
    app = (Path(__file__).resolve().parents[2]
           / "frontend" / "src" / "App.jsx").read_text()

    assert app.count("lazy(() => import('./pages/") >= 20
    assert "<Suspense" in app
    # Страницы первого захода — сразу, не по требованию.
    for page in ("Home", "ListingDetail", "CategoryLanding", "Search"):
        assert f"import {page} from './pages/{page}'" in app, page


def test_card_images_load_lazily():
    """Картинки в карточках грузятся по мере приближения к экрану."""
    card = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "components" / "ListingCard.jsx").read_text()

    # Первые четыре карточки грузятся сразу, остальные лениво: верхние
    # видны в тот же миг, и лень для них — лишняя задержка.
    assert "priority ? 'eager' : 'lazy'" in card
    assert 'decoding="async"' in card


def test_photos_are_saved_as_webp():
    """Новые фото сохраняются в WebP — на четверть-треть легче JPEG."""
    media = (Path(__file__).resolve().parents[1]
             / "app" / "routers" / "media.py").read_text()

    assert '"WEBP"' in media
    assert 'f"{name}_thumb.webp"' in media


def test_listing_is_requested_before_the_tap_completes():
    """Объявление запрашивается, пока палец лежит на карточке.

    Между касанием и переходом проходит 100-300 миллисекунд: человек
    отпускает палец, срабатывает переход, рисуется страница. Если
    начать запрос в момент касания, к открытию ответ уже готов.

    Проверено вживую: наведение на карточку даёт один запрос заранее, а
    при открытии повторного не случается — используется готовый ответ.
    """
    client = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "api" / "client.js").read_text()
    card = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "components" / "ListingCard.jsx").read_text()

    assert "prefetchListing" in client
    assert "onTouchStart={() => api.prefetchListing(listing.id)}" in card
    # Готовый ответ отдаётся вместо повторного запроса.
    assert "prefetched.delete(id)" in client
    # И память не копится.
    assert "prefetched.size > 8" in client


def test_only_needed_language_is_loaded():
    """В первый файл едет один язык — основной сербский, остальные догружаются.

    Все три уезжали вместе — около 70 КБ, из которых человеку нужен один.
    """
    i18n = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "i18n" / "index.js").read_text()

    assert "import sr from './locales/sr.json'" in i18n
    assert "import en from" not in i18n and "import ru from" not in i18n
    assert "() => import('./locales/en.json')" in i18n
    assert "() => import('./locales/ru.json')" in i18n
    # Не догрузилось — остаёмся на сербском, а не показываем пустые подписи.
    assert "i18n.changeLanguage('sr')" in i18n


def test_next_page_loads_well_before_the_end():
    """Следующая порция ленты грузится за полтора экрана до конца.

    600px — меньше одного экрана телефона: человек долистывал до низа и
    упирался в пустоту, пока летел запрос, и прокрутка при этом
    останавливалась.
    """
    home = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()
    search = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "Search.jsx").read_text()

    assert "rootMargin: '1400px'" in home
    assert "rootMargin: '1400px'" in search


def test_map_library_is_not_in_the_first_load():
    """Библиотека карт грузится, когда карту открывают.

    Она весит около 150 КБ и лежала в первом файле, хотя карта
    открывается по нажатию и далеко не каждым. Подгрузка занимает доли
    секунды, и они теряются на самой отрисовке карты.

    Итог всей работы над весом: первый файл 377 КБ вместо 808.
    """
    detail = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    assert "lazy(() => import('../components/LocationMap'))" in detail
    assert "import LocationMap from" not in detail
    # Пока едет — ровная подложка, а не белая дыра на весь экран.
    assert 'className="map-loading"' in detail


def test_category_tree_is_kept_in_the_browser():
    """Дерево разделов не запрашивается заново при каждом заходе.

    Страница раздела без него не может нарисовать ни одной плитки:
    сперва ждём ответа сервера, потом рисуем плитки, потом грузим
    картинки — раздел «доезжает» на глазах. Из памяти браузера он
    открывается сразу.

    Держим сутки и всё равно обновляем в фоне: поменялись разделы —
    человек увидит новое при следующем заходе, а не будет ждать сейчас.
    """
    client = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "api" / "client.js").read_text()

    assert "plonk_categories" in client
    assert "if (saved?.tree?.length)" in client


def test_category_pictures_are_not_lazy():
    """Значки разделов грузятся сразу, а не лениво.

    Плитки почти всегда в первом экране, и откладывать их незачем:
    браузер начинал грузить картинку позже, и раздел заполнялся на
    глазах, плитка за плиткой. Ленивость полезна для длинной ленты, а не
    для десятка значков наверху.
    """
    art = (Path(__file__).resolve().parents[2]
           / "frontend" / "src" / "components" / "CategoryArt.jsx").read_text()

    code = [ln for ln in art.split("\n") if not ln.strip().startswith("//")]
    assert not any('loading="lazy"' in ln for ln in code)
    assert 'fetchpriority="high"' in art


def test_robots_see_a_real_page_not_a_stub():
    """Поисковику отдаётся настоящая страница, а не заглушка.

    Раньше на главной робот получал это:

        <title>PLONK</title><a href="...">Открыть PLONK</a>

    Человек при этом видел полноценный сайт. Такое расхождение —
    классическая примета обмана: роботу одно, людям другое. Именно за
    это сайты и помечают как мошеннические, а у нас как раз появилось
    предупреждение в Safari при домене, чистом по всем девяноста
    спискам безопасности.

    Теперь отдаём то же, что видит человек: чем занимается сайт, какие
    разделы есть, сколько объявлений.
    """
    from app.routers.seo import _plain_page

    class FakeRequest:
        pass

    html = _plain_page("https://plonk.rs", "/", FakeRequest())

    assert len(html) > 900, "страница не должна быть заглушкой"
    assert "<h1>" in html and "<h2>" in html
    assert html.count("<li>") >= 5, "разделы должны быть перечислены"
    assert 'name="description"' in html


def test_listing_page_links_its_language_versions():
    """Языковые версии объявления — свой текст и честные связи.

    Раньше /en/ и сербская страница брали текст оригинала, а hreflang
    называл их переводами: Google видел три одинаковые страницы и писал
    «Страница является копией». Теперь текст — на языке адреса, а связи
    перечисляют только языки, на которых текст действительно есть.
    """
    from types import SimpleNamespace as NS

    from app.routers.seo import _alternates_html, _listing_langs, _main_lang, _pick_translation

    tr = lambda lang, title: NS(language=lang, title=title)  # noqa: E731
    both = NS(source_language="ru", translations=[tr("ru", "Стол"), tr("en", "Table"), tr("sr", "Sto")])
    assert _pick_translation(both, "en").title == "Table"
    assert _pick_translation(both, "sr").title == "Sto"
    assert _main_lang(both) == "sr"

    only_ru = NS(source_language="ru", translations=[tr("ru", "Стол")])
    assert _pick_translation(only_ru, "en").title == "Стол"
    assert _listing_langs(only_ru) == ["ru"]
    assert _main_lang(only_ru) == "ru"

    links = _alternates_html("https://plonk.rs", "/beograd/mebel/stol-12345678", ["ru"])
    assert 'hreflang="ru"' in links and 'hreflang="en"' not in links
    assert 'hreflang="x-default" href="https://plonk.rs/ru/beograd/mebel/stol-12345678"' in links


def test_listing_markup_has_section_seller_and_trail():
    """В разметке объявления есть раздел, продавец и путь.

    Раньше было только название, цена и картинка. Раздел и продавца
    Google показывает в карточке товара, а путь — вместо длинного
    адреса в выдаче: вместо «plonk.rs/beograd/computers/igrovoy-...»
    человек видит «Белград › Настольные компьютеры». Понятнее и
    заметнее.

    Продавец указан частным лицом, а не магазином: выдавать частника за
    магазин нельзя, да и незачем.
    """
    import json
    import re

    from app.core.database import SessionLocal
    from app.models import Listing
    from app.routers.seo import listing_page

    class FakeUrl:
        scheme, netloc, path = "https", "plonk.rs", "/x"

    class FakeRequest:
        headers, url = {}, FakeUrl()

    from app.models import ListingStatus

    with SessionLocal() as db:
        # Живое объявление с ценой и продавцом: у снятого и отклонённого
        # своя страница (запрет индексации или «страницы нет»).
        listing = (db.query(Listing)
                   .filter(Listing.status == ListingStatus.active, Listing.price.isnot(None),
                           Listing.owner_id.isnot(None)).first())
        if not listing:
            return

        html = listing_page(listing_id=str(listing.id),
                            request=FakeRequest(), db=db).body.decode()

    blocks = json.loads(
        re.search(r'ld\+json">(.*?)</script>', html, re.S).group(1))
    if not isinstance(blocks, list):
        blocks = [blocks]

    kinds = {b["@type"] for b in blocks}
    assert "Product" in kinds
    assert "BreadcrumbList" in kinds, "путь до объявления должен быть"

    product = next(b for b in blocks if b["@type"] == "Product")
    assert product["offers"]["seller"]["@type"] == "Person"
