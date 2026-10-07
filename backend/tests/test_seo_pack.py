"""
SEO-пакет 7 окт. 2026: языковые версии, статусы, пустые разделы, страницы
по городам, пагинация, файлы для роботов, IndexNow.

Часть проверок — на живой базе: если её нет или она пуста, такие тесты
молча пропускаются, как и прочие тесты страниц для поисковика.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]


class _Url:
    def __init__(self, path):
        self.scheme, self.netloc, self.path, self.query = "https", "plonk.rs", path, ""


class _Request:
    def __init__(self, path="/", page=None):
        self.headers, self.url = {}, _Url(path)
        self.query_params = {"page": str(page)} if page else {}


def _db():
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("select 1"))
        return db
    except Exception:  # noqa: BLE001 — базы нет: проверки на ней пропускаем
        return None


# ── Города ──────────────────────────────────────────────────────────────────
def test_every_city_of_the_site_has_proper_grammar():
    """Каждый город сайта — с готовым «в городе» на трёх языках: склонять на лету нельзя."""
    from app.routers.seo import CITY_IN

    cities = re.findall(r"slug:\s*'([^']+)'", (ROOT / "frontend/src/data/cities.js").read_text())
    assert cities
    for slug in cities:
        assert set(CITY_IN[slug]) == {"sr", "ru", "en"}, slug
    assert CITY_IN["novi-sad"]["sr"] == "u Novom Sadu"
    assert CITY_IN["beograd"]["ru"] == "в Белграде"


def test_one_city_has_one_address():
    """«Белград», «Belgrade» и «beograd» в объявлении дают один и тот же город в адресе."""
    from app.core.urls import city_code, listing_path

    for name in ("Белград", "Belgrade", "beograd", "Beograd"):
        assert city_code(name) == "beograd", name
    assert city_code("Нови-Сад") == "novi-sad"
    assert city_code("Šabac") == "sabac"  # незнакомый город — как раньше, латиницей
    assert listing_path("45e17e58-0000", "Стол", "Белград", "mebel").startswith("/beograd/mebel/")


# ── Тексты разделов ─────────────────────────────────────────────────────────
def test_every_second_level_section_has_its_own_text():
    """У каждого подраздела второго уровня — свой текст на трёх языках, а не родительский."""
    from app.data.category_intros import INTROS
    from app.data.category_intros_more import MORE

    for slug, texts in MORE.items():
        assert len(texts) == 3 and all(t.strip() for t in texts), slug
        assert set(INTROS[slug]) == {"sr", "ru", "en"}, slug


def test_people_see_the_section_text_too():
    """Текст раздела видит и человек, а не только поисковик: иначе это подмена содержимого."""
    landing = (ROOT / "frontend/src/pages/CategoryLanding.jsx").read_text()
    client = (ROOT / "frontend/src/api/client.js").read_text()
    router = (ROOT / "backend/app/routers/categories.py").read_text()

    assert "getCategoryIntro" in client and "api.getCategoryIntro(slug)" in landing
    assert 'className="landing-about"' in landing
    assert '@router.get("/{slug}/intro")' in router


def test_city_section_route_exists_for_people():
    """По адресу /novi-sad/c/namestaj человек видит тот же раздел с этим городом, что и поисковик."""
    app = (ROOT / "frontend/src/App.jsx").read_text()

    assert '<Route path="/:city/c/:slug" element={<CityCategoryPage />} />' in app
    assert "localStorage.setItem('plonk_city', city)" in app
    assert "return <NotFound />" in app


# ── Файлы для роботов ───────────────────────────────────────────────────────
def test_robots_get_real_files_not_the_app():
    """robots.txt и картинки роботы получают файлами с диска, развилка робот/человек — только для страниц.

    Раньше робот за robots.txt уходил в приложение и получал «страницы нет»:
    Google не видел ни правил, ни ссылки на карту сайта.
    """
    conf = (ROOT / "deploy/plonk.rs.conf").read_text()
    main = conf[conf.index("    location / {"):]
    assert "try_files $uri @page;" in main
    page = conf[conf.index("    location @page {"):]
    assert page.index("if ($is_crawler) { return 418; }") < page.index("rewrite ^ /index.html break;")
    assert 'add_header Cache-Control "no-store";' in page


def test_private_pages_closed_in_every_language():
    robots = (ROOT / "frontend/public/robots.txt").read_text()
    for lang in ("", "/ru", "/en"):
        for page in ("/profile", "/admin", "/chats", "/my"):
            assert f"Disallow: {lang}{page}" in robots, (lang, page)


# ── IndexNow ────────────────────────────────────────────────────────────────
def test_indexnow_key_file_matches_and_timer_is_installed():
    """Ключ IndexNow лежит файлом в корне сайта и совпадает с кодом; таймер ставится деплоем."""
    from app.core.indexnow import KEY

    key_file = ROOT / "frontend/public" / f"{KEY}.txt"
    assert key_file.read_text().strip() == KEY
    timer = (ROOT / "deploy/plonk-indexnow.timer").read_text()
    assert "OnUnitActiveSec=15min" in timer
    assert "app.core.indexnow" in (ROOT / "deploy/plonk-indexnow.service").read_text()


def test_indexnow_sends_nothing_when_nothing_changed():
    from app.core.indexnow import submit

    assert submit([]) == 0


# ── Живые страницы ──────────────────────────────────────────────────────────
def test_listing_page_speaks_the_language_of_its_address():
    """/en/ — английский текст, если перевод есть; нет — canonical на основную версию."""
    db = _db()
    if db is None:
        return
    from app.models import Listing, ListingStatus, ListingTranslation
    from app.routers.seo import _nice_path, listing_page

    with db:
        row = (db.query(Listing).join(ListingTranslation)
               .filter(Listing.status == ListingStatus.active, ListingTranslation.language == "en")
               .first())
        if not row:
            return
        en = next(t for t in row.translations if t.language == "en")
        html = listing_page(str(row.id), _Request("/en" + _nice_path(db, row)), db).body.decode()
    assert f"<h1>{en.title}" in html.replace("&amp;", "&") or en.title[:10] in html
    assert '<html lang="en">' in html
    assert "Открыть объявление" not in html  # ни одной русской надписи на английской странице


def test_rejected_listing_is_not_found_and_sold_is_not_indexed():
    db = _db()
    if db is None:
        return
    from app.models import Listing, ListingStatus
    from app.routers.seo import listing_page

    with db:
        rejected = db.query(Listing).filter(Listing.status == ListingStatus.rejected).first()
        if rejected:
            assert listing_page(str(rejected.id), _Request("/x"), db).status_code == 404
        sold = db.query(Listing).filter(Listing.status == ListingStatus.sold).first()
        if sold:
            resp = listing_page(str(sold.id), _Request("/x"), db)
            assert resp.status_code == 200
            assert 'name="robots" content="noindex"' in resp.body.decode()


def test_empty_section_is_not_indexed_and_pages_go_on():
    db = _db()
    if db is None:
        return
    from sqlalchemy import func

    from app.models import Category, Listing, ListingStatus
    from app.routers.seo import PER_PAGE, _section_page

    with db:
        used = {c for (c,) in db.query(Listing.category_id).filter(Listing.status == ListingStatus.active)}
        empty = (db.query(Category).filter(~Category.id.in_(used), ~Category.children.any()).first()
                 if used else None)
        if empty:
            html = _section_page(db, _Request(), empty.slug, "sr", None).body.decode()
            assert 'name="robots" content="noindex"' in html

        busy = (db.query(Listing.category_id, func.count()).filter(Listing.status == ListingStatus.active)
                .group_by(Listing.category_id).order_by(func.count().desc()).first())
        if busy and busy[1] > PER_PAGE:
            cat = db.get(Category, busy[0])
            first = _section_page(db, _Request(), cat.slug, "sr", None).body.decode()
            assert f'rel="next" href="https://plonk.rs/c/{cat.slug}?page=2"' in first
            second = _section_page(db, _Request(page=2), cat.slug, "sr", None).body.decode()
            assert f'rel="canonical" href="https://plonk.rs/c/{cat.slug}?page=2"' in second
            assert _section_page(db, _Request(page=999), cat.slug, "sr", None).status_code == 404


def test_city_section_page_is_in_the_city():
    db = _db()
    if db is None:
        return
    from app.models import Category
    from app.routers.seo import city_category_page

    with db:
        cat = db.query(Category).filter(Category.parent_id.is_(None)).first()
        if not cat:
            return
        html = city_category_page("novi-sad", cat.slug, _Request(), db, lang="sr").body.decode()
        assert "u Novom Sadu" in html
        assert city_category_page("zagreb", cat.slug, _Request(), db).status_code == 404


# ── Полезное ────────────────────────────────────────────────────────────────
def test_every_guide_is_complete_in_three_languages():
    """Каждая статья — на трёх языках, с обложкой, датой проверки и кнопкой в живой раздел."""
    from app.data.guides import GUIDES
    from app.routers.seo import CITY_IN

    from app.data.category_intros import INTROS

    sections = set(INTROS)  # все разделы с текстами: верхний и второй уровень
    sections |= {"flats", "cars", "jobs", "electronics", "pets-supplies"}
    assert len({g["slug"] for g in GUIDES}) == len(GUIDES)
    for g in GUIDES:
        assert (ROOT / "frontend/public" / g["cover"].split("?")[0].lstrip("/")).exists(), g["cover"]
        for lang in ("sr", "ru", "en"):
            loc = g[lang]
            assert loc["title"] and loc["lead"], (g["slug"], lang)
            kind, (label, href) = loc["blocks"][-1]
            assert kind == "cta" and label
            m = re.fullmatch(r"(?:/([a-z-]+))?/c/([a-z0-9-]+)", href)
            if m:
                city, section = m.groups()
                assert city is None or city in CITY_IN, href
                assert section in sections, href
