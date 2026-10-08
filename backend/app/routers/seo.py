"""
Что видит поисковик.

Сайт собирается в браузере, и без готовых страниц поисковик видит пустоту.
nginx отправляет сюда только роботов (см. deploy/plonk.rs.conf), человек
получает обычное приложение — по тем же адресам и с тем же содержимым.

Страницы:
  /                              главная — разделы, города, свежие объявления
  /c/<раздел>                    раздел по всей Сербии (?page=N — дальше)
  /<город>/c/<раздел>            раздел в городе: «nameštaj Novi Sad»
  /<город>/<раздел>/<вещь>-<ключ> объявление
  /seller/<ключ>                 продавец
  /sitemap.xml                   карта сайта
Всё то же на /ru/… и /en/…; сербский — основной, без приставки.
"""
import re
import uuid
from collections import defaultdict
from datetime import timedelta
from html import escape as esc
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session, selectinload

from app.core.category_tree import branch_ids as _branch_ids
from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import get_db

from app.models import Category, Listing, ListingStatus

router = APIRouter(tags=["seo"])

# Сколько объявлений отдавать в карте. Поисковики принимают до 50 тысяч в
# одном файле, но обходят не всё сразу — свежие важнее.
MAX_LISTINGS = 5000

# Объявлений на страницу раздела. Дальше — ?page=2: раньше раздел
# показывал 40 штук и всё, остальные поисковик находил только по карте и
# считал второстепенными.
PER_PAGE = 40

# С какого числа объявлений страница «раздел в городе» идёт в индекс.
# Страница с одним-двумя объявлениями — «тонкая»: поисковик считает её
# пустышкой и тянет вниз весь сайт. Ниже порога она открывается, но с
# запретом индексации и в карту сайта не попадает.
MIN_CITY_LISTINGS = 3

# Языки сайта. Сербский — основной и живёт без приставки, русский — /ru/…,
# английский — /en/…
LANGS = ("sr", "ru", "en")

# Обрамление страницы раздела на каждом языке.
CATEGORY_TEXTS = {
    "ru": {
        "title": "{name} — объявления в Белграде и Сербии | PLONK",
        "with_count": "{name} в Сербии на PLONK — объявлений: {count}",
        "plain": "{name} в Сербии на PLONK",
        "tail": ". Покупайте и продавайте рядом с домом, на русском, "
                "английском и сербском.",
        "open": "Открыть раздел на PLONK",
        "missing": "Раздел не найден",
        "city_title": "{name} {city_in} — объявления | PLONK",
        "city_head": "{name} {city_in} на PLONK — объявлений: {count}",
    },
    "en": {
        "title": "{name} — classifieds in Belgrade and Serbia | PLONK",
        "with_count": "{name} in Serbia on PLONK — listings: {count}",
        "plain": "{name} in Serbia on PLONK",
        "tail": ". Buy and sell close to home, in Russian, English "
                "and Serbian.",
        "open": "Open this section on PLONK",
        "missing": "Section not found",
        "city_title": "{name} {city_in} — classifieds | PLONK",
        "city_head": "{name} {city_in} on PLONK — listings: {count}",
    },
    "sr": {
        "title": "{name} — oglasi u Beogradu i Srbiji | PLONK",
        "with_count": "{name} u Srbiji na PLONK — oglasa: {count}",
        "plain": "{name} u Srbiji na PLONK",
        "tail": ". Kupujte i prodajte blizu kuće, na srpskom, ruskom "
                "i engleskom.",
        "open": "Otvorite sekciju na PLONK",
        "missing": "Sekcija nije pronađena",
        "city_title": "{name} {city_in} — oglasi | PLONK",
        "city_head": "{name} {city_in} na PLONK — oglasa: {count}",
    },
}

# Остальные надписи страниц для поисковика. Раньше часть их была
# по-русски на всех языках («Открыть объявление на PLONK» на сербской
# странице) — для поисковика это страница на смеси языков.
UI = {
    "sr": {
        "open_listing": "Otvorite oglas na PLONK", "listing": "Oglas", "serbia": "Srbija",
        "pending": "Oglas čeka proveru i uskoro će biti objavljen.",
        "inactive": "Oglas više nije aktivan — prodat je ili skinut.",
        "similar": "Slični oglasi", "more_in": "Svi oglasi: {name}", "more_in_city": "{name} {city_in}",
        "nf_title": "Stranica nije pronađena", "nf_text": "Možda je oglas već prodat ili skinut.",
        "nf_link": "Otvorite PLONK", "fresh": "Novi oglasi", "cities": "Po gradovima",
        "sections": "Kategorije", "subsections": "Podkategorije", "page": "strana {n}",
        "next": "Sledeća strana", "prev": "Prethodna strana", "all_serbia": "{name} u celoj Srbiji",
        "seller_title": "{name} — prodavac na PLONK", "seller_desc": "Oglasi prodavca {name} na PLONK: {n}.",
        "seller_intro": "Prodavac na PLONK — oglasi u Beogradu i Srbiji.", "seller_list": "Oglasi",
        "seller_none": "Trenutno nema aktivnih oglasa", "seller": "Prodavac", "all": "Svi oglasi na PLONK",
        "home_city": "Oglasi {city_in}",
    },
    "ru": {
        "open_listing": "Открыть объявление на PLONK", "listing": "Объявление", "serbia": "Сербия",
        "pending": "Объявление ждёт проверки и скоро появится.",
        "inactive": "Объявление больше не активно — продано или снято.",
        "similar": "Похожие объявления", "more_in": "Все объявления: {name}", "more_in_city": "{name} {city_in}",
        "nf_title": "Страница не найдена", "nf_text": "Возможно, объявление уже продано или снято.",
        "nf_link": "Открыть PLONK", "fresh": "Новые объявления", "cities": "По городам",
        "sections": "Разделы", "subsections": "Подразделы", "page": "страница {n}",
        "next": "Следующая страница", "prev": "Предыдущая страница", "all_serbia": "{name} по всей Сербии",
        "seller_title": "{name} — продавец на PLONK", "seller_desc": "Объявления продавца {name} на PLONK: {n}.",
        "seller_intro": "Продавец на PLONK — доске объявлений Белграда и Сербии.", "seller_list": "Объявления",
        "seller_none": "Сейчас нет активных объявлений", "seller": "Продавец", "all": "Все объявления на PLONK",
        "home_city": "Объявления {city_in}",
    },
    "en": {
        "open_listing": "Open this listing on PLONK", "listing": "Listing", "serbia": "Serbia",
        "pending": "This listing is awaiting review and will appear soon.",
        "inactive": "This listing is no longer active — sold or removed.",
        "similar": "Similar listings", "more_in": "All listings: {name}", "more_in_city": "{name} {city_in}",
        "nf_title": "Page not found", "nf_text": "The listing may have been sold or removed.",
        "nf_link": "Open PLONK", "fresh": "New listings", "cities": "By city",
        "sections": "Categories", "subsections": "Subcategories", "page": "page {n}",
        "next": "Next page", "prev": "Previous page", "all_serbia": "{name} across Serbia",
        "seller_title": "{name} — seller on PLONK", "seller_desc": "Listings by {name} on PLONK: {n}.",
        "seller_intro": "Seller on PLONK — classifieds in Belgrade and Serbia.", "seller_list": "Listings",
        "seller_none": "No active listings right now", "seller": "Seller", "all": "All listings on PLONK",
        "home_city": "Classifieds {city_in}",
    },
}

# «В городе» на каждом языке. Склонять на лету нельзя: «u Beograd» и
# «в Нови-Сад» в заголовке выдачи читаются как машинный перевод.
CITY_IN = {
    "beograd":    {"sr": "u Beogradu",     "ru": "в Белграде",     "en": "in Belgrade"},
    "novi-sad":   {"sr": "u Novom Sadu",   "ru": "в Нови-Саде",    "en": "in Novi Sad"},
    "nis":        {"sr": "u Nišu",         "ru": "в Нише",         "en": "in Niš"},
    "kragujevac": {"sr": "u Kragujevcu",   "ru": "в Крагуеваце",   "en": "in Kragujevac"},
    "subotica":   {"sr": "u Subotici",     "ru": "в Суботице",     "en": "in Subotica"},
    "zrenjanin":  {"sr": "u Zrenjaninu",   "ru": "в Зренянине",    "en": "in Zrenjanin"},
    "pancevo":    {"sr": "u Pančevu",      "ru": "в Панчеве",      "en": "in Pančevo"},
    "cacak":      {"sr": "u Čačku",        "ru": "в Чачаке",       "en": "in Čačak"},
    "novi-pazar": {"sr": "u Novom Pazaru", "ru": "в Нови-Пазаре",  "en": "in Novi Pazar"},
    "kraljevo":   {"sr": "u Kraljevu",     "ru": "в Кралеве",      "en": "in Kraljevo"},
}

OG_LOCALE = {"sr": "sr_RS", "ru": "ru_RU", "en": "en_US"}


def _ui(lang: str) -> dict:
    return UI.get(lang, UI["sr"])


def _lang_url(site: str, path: str, lang: str) -> str:
    """Адрес страницы на нужном языке: сербский — основной, без приставки; русский — /ru/…, английский — /en/…"""
    prefix = "" if lang == "sr" else f"/{lang}"
    return f"{site}{prefix}{path}"


def _site() -> str:
    return settings.site_base_url.rstrip("/")  # адрес сайта (plonk.rs), а не сервера приложения


def _cat_name(category, lang: str) -> str:
    names = category.name or {}
    return names.get(lang) or names.get("sr") or names.get("ru") or category.slug


def _pick_translation(listing, lang: str):
    """Текст объявления на нужном языке; нет перевода — на языке оригинала, потом любой.

    Раньше страница на любом языке брала текст оригинала: /en/ и сербская
    версия показывали русский текст, а hreflang при этом называл их
    переводами. Google видел три одинаковые страницы и склеивал их в копии.
    """
    rows = list(listing.translations or [])
    for want in (lang, listing.source_language, "sr", "ru", "en"):
        for tr in rows:
            if tr.language == want and (tr.title or "").strip():
                return tr
    return rows[0] if rows else None


def _listing_langs(listing) -> list[str]:
    """Языки, на которых у объявления есть свой текст, — только они получают свою страницу."""
    have = {tr.language for tr in (listing.translations or []) if (tr.title or "").strip()}
    return [lang for lang in LANGS if lang in have]


def _main_lang(listing) -> str:
    """Язык основной версии объявления: сербский, если есть, иначе язык оригинала."""
    langs = _listing_langs(listing)
    if "sr" in langs:
        return "sr"
    if listing.source_language in langs:
        return listing.source_language
    return langs[0] if langs else "sr"


def _alternates_html(site: str, path: str, langs, query: str = "") -> str:
    """hreflang-связи страницы: только языки, на которых она действительно есть."""
    langs = [lang for lang in LANGS if lang in langs]
    links = [f'<link rel="alternate" hreflang="{lang}" href="{esc(_lang_url(site, path, lang) + query)}">'
             for lang in langs]
    default = "sr" if "sr" in langs else (langs[0] if langs else None)
    if default:
        links.append(f'<link rel="alternate" hreflang="x-default" '
                     f'href="{esc(_lang_url(site, path, default) + query)}">')
    return "\n".join(links)


# ── Города ───────────────────────────────────────────────────────────────────
def _city_slug_of(value: str | None) -> str | None:
    """Код города по тому, что записано в объявлении: «beograd», «Белград», «Belgrade» — всё это Белград."""
    if not value:
        return None
    v = value.strip().lower()
    for slug, row in _city_rows().items():
        if v == slug or v in row:
            return slug
    return None


_CITY_ROWS: dict | None = None


def _city_rows() -> dict:
    """{код: множество написаний в нижнем регистре} — по тому же списку, что у сайта."""
    global _CITY_ROWS
    if _CITY_ROWS is None:
        rows = {}
        names = _city_names()
        for slug in CITY_IN:
            row = names.get(slug) or {}
            rows[slug] = {slug} | {str(v).lower() for v in row.values()}
        _CITY_ROWS = rows
    return _CITY_ROWS


def _city_filter(slug: str):
    """Условие «объявление из этого города» — по любому из написаний."""
    return func.lower(Listing.city).in_(sorted(_city_rows()[slug]))


# ── Счёт объявлений по веткам разделов ───────────────────────────────────────
def _tree(db: Session):
    cats = db.query(Category).all()
    parent = {c.id: c.parent_id for c in cats}
    return cats, parent


def _branch_counts(db: Session, parent: dict, city: str | None = None) -> dict:
    """{раздел: активных объявлений во всей его ветке} одним запросом."""
    q = db.query(Listing.category_id, func.count()).filter(Listing.status == ListingStatus.active)
    if city:
        q = q.filter(_city_filter(city))
    counts = defaultdict(int)
    for cat_id, n in q.group_by(Listing.category_id).all():
        node, guard = cat_id, 0
        while node is not None and guard < 10:
            counts[node] += n
            node, guard = parent.get(node), guard + 1
    return counts


def _city_branch_counts(db: Session, parent: dict) -> dict:
    """{(код города, раздел): объявлений в ветке} — для страниц «раздел в городе» и карты сайта."""
    rows = (db.query(Listing.category_id, func.lower(Listing.city), func.count())
            .filter(Listing.status == ListingStatus.active, Listing.city.isnot(None))
            .group_by(Listing.category_id, func.lower(Listing.city)).all())
    counts = defaultdict(int)
    for cat_id, city_value, n in rows:
        slug = _city_slug_of(city_value)
        if not slug:
            continue
        node, guard = cat_id, 0
        while node is not None and guard < 10:
            counts[(slug, node)] += n
            node, guard = parent.get(node), guard + 1
    return counts


def _not_found_page(site: str, lang: str = "sr") -> HTMLResponse:
    t = _ui(lang)
    prefix = "" if lang == "sr" else f"/{lang}"
    return HTMLResponse(
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="robots" content="noindex">\n<title>{esc(t["nf_title"])} — PLONK</title>\n</head>\n'
        f'<body>\n<h1>{esc(t["nf_title"])}</h1>\n<p>{esc(t["nf_text"])}</p>\n'
        f'<p><a href="{site}{prefix}/">{esc(t["nf_link"])}</a></p>\n</body>\n</html>',
        status_code=404)


def _lang_of_path(path: str) -> str:
    """Язык по приставке адреса: /en/ — английский, /ru/ — русский, без приставки — сербский (основной)."""
    if path.startswith("/en/") or path == "/en":
        return "en"
    if path.startswith("/ru/") or path == "/ru":
        return "ru"
    return "sr"


def _page_number(request: Request) -> int:
    try:
        return max(1, int(request.query_params.get("page", "1")))
    except (ValueError, AttributeError, TypeError):
        return 1


def _is_crawler(agent: str) -> bool:
    """
    Пришёл поисковик или человек.

    Человеку отдавать урезанную страницу нельзя — он ждёт живой сайт.
    """
    # Applebot здесь нарочно нет. Он собран на WebKit и исполняет
    # JavaScript, то есть видит обычный сайт таким же, каким его видит
    # Safari. Отдавать ему отдельную страницу — значит показывать
    # роботу Apple одно, а людям в Safari другое: это и есть
    # «подмена содержимого», один из главных признаков мошеннического
    # сайта в классификаторе Safari. Google-боту отдельная страница
    # нужна (он не всегда дожидается сборки приложения), Apple — нет.
    agent = (agent or "").lower()
    return any(bot in agent for bot in (
        "googlebot", "yandex", "bingbot", "duckduckbot", "baiduspider",
        "facebookexternalhit", "twitterbot", "telegrambot",
        "whatsapp", "slackbot", "linkedinbot", "petalbot", "ahrefsbot",
    ))


def _as_uuid(value: str):
    """Ключ объявления из строки или None — чтобы не отдавать в базу то, что она не примет."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None



def _cut(text: str, limit: int) -> str:
    """
    Обрезает по границе слова, а не посреди него: раньше был простой
    срез [:300], и описание могло оборваться на «прямостоя…».
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return f"{cut}…"


def _clean(text: str) -> str:
    """
    Описание для выдачи.

    Смайлики и переносы строк в поисковой строке выглядят мусором, а
    места занимают: в выдаче показывают полторы сотни знаков, и тратить
    их на «🙈» жалко.
    """
    import re

    body = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", text or "")
    return " ".join(body.split())


def _price_words(listing, lang: str = "ru") -> str:
    if listing.is_free:
        return {"sr": "Besplatno", "en": "Free"}.get(lang, "Бесплатно")
    if listing.price is None:
        return {"sr": "Cena nije navedena", "en": "Price not specified"}.get(lang, "Цена не указана")
    whole = f"{int(listing.price):,}".replace(",", " ")
    sign = "€" if str(listing.currency).endswith("eur") else "RSD"
    return f"{whole} {sign}"


_CITY_NAMES: dict | None = None


def _city_names() -> dict:
    """Названия городов на трёх языках — из того же списка, что у сайта (frontend/src/data/cities.js):
    ключи — и код города, и его русское название (в объявлениях встречаются оба)."""
    global _CITY_NAMES
    if _CITY_NAMES is None:
        import re as _re
        from pathlib import Path
        names = {}
        try:
            src = (Path(__file__).resolve().parents[3] / "frontend" / "src" / "data" / "cities.js").read_text("utf8")
            for m in _re.finditer(r"slug:\s*'([^']+)',\s*ru:\s*'([^']+)',\s*en:\s*'([^']+)',\s*sr:\s*'([^']+)'", src):
                row = {"ru": m.group(2), "en": m.group(3), "sr": m.group(4)}
                names[m.group(1)] = row
                names[m.group(2).lower()] = row
        except OSError:
            pass
        _CITY_NAMES = names
    return _CITY_NAMES


def _city_words(city: str | None, lang: str = "ru") -> str:
    if not city:
        return ""
    row = _city_names().get(city) or _city_names().get(city.lower())
    if row:
        return row.get(lang) or row["ru"]
    from app.bot.post_format import city_title

    return city_title(city)




def _url(loc: str, changed=None, priority: str = "0.5",
         frequency: str = "daily", alternates: dict | None = None) -> str:
    parts = [f"<loc>{escape(loc)}</loc>"]
    if changed:
        parts.append(f"<lastmod>{changed.date().isoformat()}</lastmod>")
    parts.append(f"<changefreq>{frequency}</changefreq>")
    parts.append(f"<priority>{priority}</priority>")
    # Языковые версии прямо в карте: поисковик узнаёт, что /en/c/mebel и
    # /c/mebel — одна страница на разных языках, а не две конкурирующие.
    alternates = alternates or {}
    for lang, href in alternates.items():
        parts.append(f'<xhtml:link rel="alternate" hreflang="{lang}" href="{escape(href)}"/>')
    if alternates:
        default = alternates.get("sr") or next(iter(alternates.values()))
        parts.append(f'<xhtml:link rel="alternate" hreflang="x-default" href="{escape(default)}"/>')
    return "<url>" + "".join(parts) + "</url>"


def _with_langs(site: str, path: str, changed=None, priority: str = "0.5",
                frequency: str = "daily", langs=LANGS, main: str = "sr") -> str:
    """Одна запись карты сайта — со ссылками на все языковые версии, которые у страницы есть."""
    alternates = {lang: _lang_url(site, path, lang) for lang in LANGS if lang in langs}
    return _url(_lang_url(site, path, main if main in langs else next(iter(alternates), "sr")),
                changed, priority, frequency, alternates)


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    """Карта сайта: главная, разделы, разделы в городах, объявления, витрины.

    Пустые разделы в карту не идут: из ~250 разделов многие без единого
    объявления, и такие «тонкие» страницы поисковик считает пустышками —
    это тянет вниз весь сайт. Раздел появится в карте с первым объявлением.
    """
    site = _site()
    now = utcnow()
    urls = [_with_langs(site, "/", now, "1.0", "hourly")]

    cats, parent = _tree(db)
    counts = _branch_counts(db, parent)
    for category in cats:
        if counts.get(category.id):
            top = category.parent_id is None
            urls.append(_with_langs(site, f"/c/{category.slug}", now, "0.8" if top else "0.6"))

    # Разделы в городах: «nameštaj Novi Sad» ищут чаще, чем просто «nameštaj».
    by_id = {c.id: c for c in cats}
    for (city, cat_id), n in _city_branch_counts(db, parent).items():
        if n >= MIN_CITY_LISTINGS and cat_id in by_id:
            urls.append(_with_langs(site, f"/{city}/c/{by_id[cat_id].slug}", now, "0.7"))

    listings = (
        db.query(Listing)
        .options(selectinload(Listing.translations), selectinload(Listing.category))
        .filter(Listing.status == ListingStatus.active)
        .order_by(Listing.created_at.desc())
        .limit(MAX_LISTINGS)
        .all()
    )
    for listing in listings:
        langs = _listing_langs(listing)
        if not langs:
            continue
        # Свежие объявления поисковику стоит перечитывать чаще: цена
        # меняется, вещь продаётся.
        fresh = listing.created_at and listing.created_at > now - timedelta(days=7)
        urls.append(_with_langs(
            site, _nice_path(db, listing),
            listing.updated_at or listing.created_at,
            "0.7" if fresh else "0.5",
            "daily" if fresh else "weekly",
            langs=langs, main=_main_lang(listing),
        ))

    # Статьи-путеводители — на трёх языках (сербский без приставки, /ru/, /en/)
    from app.data.guides import GUIDES
    urls.append(_with_langs(site, "/vodic", now, "0.6", "weekly"))
    for g in GUIDES:
        urls.append(_with_langs(site, f"/vodic/{g['slug']}", now, "0.7", "monthly"))

    # Витрины продавцов — отдельные страницы с собственным адресом (/s/<адрес>)
    try:
        from app.models.storefront import Storefront
        urls.append(_url(f"{site}/vitriny", now, "0.6", "daily"))
        for sf in db.query(Storefront).filter(Storefront.status == "published").all():
            urls.append(_url(f"{site}/s/{sf.slug}", sf.updated_at or now, "0.6", "daily"))
    except Exception:  # noqa: BLE001 — карта сайта не должна падать из-за витрин
        db.rollback()

    body = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            + "".join(urls) + "</urlset>")
    return Response(content=body, media_type="application/xml")


# Страница объявления для поисковика — то же, что человек видит после
# загрузки приложения, но сразу и текстом.
LISTING_PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {price} · {city} | PLONK</title>
<meta name="description" content="{description}">
{robots}<link rel="canonical" href="{canonical}">
{alternates}
<meta property="og:type" content="product">
<meta property="og:site_name" content="PLONK">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="{og_locale}">
{price_tags}
{image_tag}
<meta name="twitter:card" content="{twitter_card}">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
{twitter_image}
<script type="application/ld+json">
{schema}
</script>
</head>
<body>
<nav>{crumbs}</nav>
<h1>{title}</h1>
{inactive}<p><strong>{price}</strong>{city_line}</p>
<p>{body}</p>
<p><a href="{url}">{open_text}</a></p>
{seller}{similar}{more}
</body>
</html>"""

# Объявления, которых человек по ссылке не увидит: черновик и отклонённое.
# Для поисковика их нет — «страницы нет», а не живая карточка в выдаче.
HIDDEN = (ListingStatus.draft, ListingStatus.rejected)
# Ждёт проверки, продано, снято: страница открывается (ссылку могли
# переслать, превью в мессенджере должно собраться), но в индекс не идёт.
NOINDEX = (ListingStatus.pending_moderation, ListingStatus.sold, ListingStatus.archived)


@router.get("/go/{listing_id}", include_in_schema=False)
def short_listing_page(listing_id: str, request: Request,
                       db: Session = Depends(get_db)):
    """
    Короткий путь по ключу — из бота и админки.

    Поисковику показываем понятный адрес: иначе он сочтёт их двумя
    страницами и разделит между ними вес.
    """
    # Пришёл не ключ, а «слаг» или мусор — в базу его не отдаём: Postgres падал на приведении к UUID.
    lid = _as_uuid(listing_id)
    if lid is not None:
        listing = db.query(Listing).filter(Listing.id == lid).first()
    else:
        tail = listing_id.rsplit("-", 1)[-1].lower()
        listing = (db.query(Listing).filter(cast(Listing.id, String).like(f"{tail}-%")).first()
                   if re.fullmatch(r"[0-9a-f]{8}", tail) else None)
    if listing:
        return RedirectResponse(_nice_path(db, listing), status_code=301)
    return listing_page(listing_id, request, db)


@router.get("/{lang}/{city}/{category}/{slug}", include_in_schema=False)
def nice_listing_page_localised(lang: str, city: str, category: str, slug: str,
                                request: Request,
                                db: Session = Depends(get_db)):
    """Объявление (или раздел в городе) на другом языке: /en/beograd/mebel/stol-45e17e58, /ru/novi-sad/c/mebel."""
    if lang == "sr":  # сербский без приставки — старые адреса /sr/… ведём на основные
        return RedirectResponse(f"/{city}/{category}/{slug}", status_code=301)
    if lang not in ("en", "ru"):
        return _not_found_page(_site())
    if category == "c":
        return city_category_page(city, slug, request, db, lang=lang)
    return nice_listing_page(city, category, slug, request, db)


@router.get("/{city}/{category}/{slug}", include_in_schema=False)
def nice_listing_page(city: str, category: str, slug: str,
                      request: Request, db: Session = Depends(get_db)):
    """
    Понятный адрес объявления.

    Ключ ищем по хвосту: название могли поправить, и адрес разойдётся
    с нынешним — но хвост остаётся.
    """
    from app.core.urls import listing_id_from

    # Языковые адреса совпадают по форме с адресом объявления: у
    # /en/c/mebel те же три части, что у /beograd/mebel/stol.
    if category == "vodic" and city in ("en", "ru", "sr"):
        if city == "sr":
            return RedirectResponse(f"/vodic/{slug}", status_code=301)
        page = _guide_page(_site(), f"/vodic/{slug}", city)
        return HTMLResponse(page) if page else _not_found_page(_site(), city)
    if city == "sr" and category == "c":
        return RedirectResponse(f"/c/{slug}", status_code=301)
    if city in ("en", "ru") and category == "c":
        return category_page(slug, request, db, lang=city)
    # И раздел в городе: /novi-sad/c/namestaj.
    if category == "c":
        lang = _lang_of_path(request.url.path if hasattr(request, "url") else "/")
        return city_category_page(city, slug, request, db, lang=lang)

    # Языковая приставка перед служебной страницей (/ru/seller/…, /en/jobs/my)
    # и любой адрес из трёх частей без ключа объявления в хвосте — не
    # объявление: разбираем общим обработчиком. Раньше /ru/seller/… отвечал
    # «страницы нет», хотя у человека она открывается.
    tail = listing_id_from(slug)
    if city in ("en", "ru", "sr") or not tail:
        return not_found(f"{city}/{category}/{slug}", request)

    listing = db.query(Listing).filter(
        cast(Listing.id, String).like(f"{tail}-%")).first()
    return listing_page(str(listing.id) if listing else slug, request, db)


def listing_page(listing_id: str, request: Request,
                 db: Session = Depends(get_db)):
    """Страница объявления с текстом — для поисковиков и превью ссылок."""
    from app.models import ListingPhoto

    site = _site()
    path = request.url.path if hasattr(request, "url") else "/"
    lang = _lang_of_path(path)

    # Номер может оказаться не номером: адрес удалённого объявления или
    # просто набранный от руки. Такой запрос в базу не отдаём — поисковик
    # должен получить «страницы нет», а не «сервер сломался».
    try:
        lid = _as_uuid(listing_id)
        listing = (db.query(Listing).options(selectinload(Listing.translations))
                   .filter(Listing.id == lid).first()) if lid is not None else None
    except Exception:                                      # noqa: BLE001
        db.rollback()
        listing = None

    if not listing or listing.status in HIDDEN:
        return _not_found_page(site, lang)

    t = _ui(lang)
    nice = _nice_path(db, listing)
    langs = _listing_langs(listing) or [lang]
    url = _lang_url(site, nice, lang)
    # Перевода на этот язык нет — страница показывает текст на другом
    # языке, и своей она не считается: основная версия — та, где текст есть.
    content_lang = lang if lang in langs else _main_lang(listing)
    canonical = _lang_url(site, nice, content_lang)
    alternates = _alternates_html(site, nice, langs)

    tr = _pick_translation(listing, lang)
    title = (tr.title if tr else "") or t["listing"]
    body = (tr.description if tr else "") or ""

    price = _price_words(listing, lang)
    city = _city_words(listing.city, lang)
    photo = (db.query(ListingPhoto)
             .filter(ListingPhoto.listing_id == listing.id)
             .order_by(ListingPhoto.sort_order).first())

    chain = _category_chain(db, listing.category)
    schema = _listing_schema(listing, title, body, canonical,
                             photo.url if photo else None, lang=content_lang, chain=chain)

    # Цена первой строкой описания — в мессенджерах заголовок часто
    # обрезается по ширине, и цена из него пропадает.
    body_text = _clean(body)

    # У перенесённых объявлений описание часто слово в слово повторяет заголовок.
    def _words(text: str) -> set:
        return {w.strip(".,!?()»«\"'").lower() for w in text.split() if len(w) > 3}

    short_body = "" if body_text and not (_words(body_text) - _words(title)) else body_text
    head = f"{price} · {city}" if city else price
    description = f"{head}. {short_body}".strip(" .") if short_body else head
    description = _cut(description, 300) or title

    # Собранная карточка 1200×630: фото, цена, город, домен.
    card = f"{site}/api/og/listing/{listing.id}.png"
    image_tag = (
        f'<meta property="og:image" content="{esc(card)}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">\n'
        f'<meta property="og:image:alt" content="{esc(title)}">'
    )
    twitter_image = f'<meta name="twitter:image" content="{esc(card)}">'

    price_tags = ""
    if listing.price:
        currency = (listing.currency.value if hasattr(listing.currency, "value")
                    else str(listing.currency or "RSD"))
        price_tags = (
            f'<meta property="product:price:amount" content="{float(listing.price):.0f}">\n'
            f'<meta property="product:price:currency" content="{esc(currency)}">'
        )

    # Путь сверху и ссылки снизу — по ним поисковик уходит вглубь сайта:
    # раздел, раздел в городе, похожие вещи. Раньше со страницы объявления
    # вела одна ссылка — на неё же саму.
    crumbs = " › ".join(
        [f'<a href="{_lang_url(site, "/", lang)}">PLONK</a>']
        + [f'<a href="{_lang_url(site, f"/c/{c.slug}", lang)}">{esc(_cat_name(c, lang))}</a>'
           for c in chain])

    similar = ""
    more = ""
    if listing.category_id:
        others = (db.query(Listing).options(selectinload(Listing.translations))
                  .filter(Listing.status == ListingStatus.active,
                          Listing.category_id == listing.category_id,
                          Listing.id != listing.id)
                  .order_by(Listing.published_at.desc().nullslast()).limit(8).all())
        if others:
            similar = (f"<h2>{esc(t['similar'])}</h2>\n<ul>\n"
                       + "\n".join(_listing_li(db, site, o, lang) for o in others) + "\n</ul>\n")
        if chain:
            leaf = chain[-1]
            links = [f'<a href="{_lang_url(site, f"/c/{leaf.slug}", lang)}">'
                     f'{esc(t["more_in"].format(name=_cat_name(leaf, lang)))}</a>']
            city_slug = _city_slug_of(listing.city)
            if city_slug:
                links.append(
                    f'<a href="{_lang_url(site, f"/{city_slug}/c/{leaf.slug}", lang)}">'
                    f'{esc(t["more_in_city"].format(name=_cat_name(leaf, lang), city_in=CITY_IN[city_slug][lang]))}</a>')
            more = "<p>" + " · ".join(links) + "</p>\n"

    seller = ""
    if listing.owner_id:
        seller = (f'<p>{esc(t["seller"])}: <a href="{_lang_url(site, f"/seller/{listing.owner_id}", lang)}">'
                  f'{esc(getattr(listing.owner, "display_name", None) or t["seller"])}</a></p>\n')

    active = listing.status == ListingStatus.active
    return HTMLResponse(LISTING_PAGE.format(
        lang=content_lang,
        title=esc(title),
        price=esc(price),
        city=esc(city or t["serbia"]),
        city_line=f" · {esc(city)}" if city else "",
        description=esc(description),
        body=esc(_cut(body_text, 1500)),
        url=url,
        canonical=canonical,
        robots="" if active else '<meta name="robots" content="noindex">\n',
        inactive="" if active else "<p><strong>{}</strong></p>\n".format(esc(
            t["pending"] if listing.status == ListingStatus.pending_moderation else t["inactive"])),
        alternates=alternates,
        og_locale=OG_LOCALE.get(content_lang, "sr_RS"),
        price_tags=price_tags,
        image_tag=image_tag,
        twitter_card="summary_large_image",
        twitter_image=twitter_image,
        schema=schema,
        crumbs=crumbs,
        open_text=esc(t["open_listing"]),
        similar=similar,
        more=more,
        seller=seller,
    ))


def _listing_li(db: Session, site: str, listing, lang: str) -> str:
    """Строка списка: название, цена, город — со ссылкой на объявление."""
    tr = _pick_translation(listing, lang)
    title = (tr.title if tr else "") or _ui(lang)["listing"]
    city = _city_words(listing.city, lang)
    tail = f" — {esc(_price_words(listing, lang))}" + (f" · {esc(city)}" if city else "")
    # Ссылка — на ту языковую версию, где текст действительно есть: у
    # непереведённого объявления /en/-страница указывает основной другую.
    href_lang = lang if lang in _listing_langs(listing) else _main_lang(listing)
    href = _lang_url(site, _nice_path(db, listing), href_lang)
    return f'<li><a href="{esc(href)}">{esc(title)}</a>{tail}</li>'


def _category_chain(db: Session, category) -> list:
    """Раздел объявления и его родители — от корня к самому разделу."""
    chain, cat = [], category
    while cat is not None and len(chain) < 4:
        chain.append(cat)
        cat = db.get(Category, cat.parent_id) if cat.parent_id else None
    return list(reversed(chain))


def _listing_schema(listing, title: str, body: str, url: str,
                    image: str | None, lang: str = "sr", chain: list | None = None) -> str:
    """
    Разметка товара и пути до него.

    По ней поисковик показывает цену и наличие прямо в выдаче — такое
    объявление открывают заметно чаще обычной строки. Названия разделов —
    на языке страницы: раньше на сербской странице путь был по-русски.
    """
    import json

    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "description": _clean(body)[:500] or title,
        "url": url,
    }
    # Цену указываем, только когда она есть: «0 динаров» у вещи без цены
    # Google показал бы в выдаче как «бесплатно» — это обман покупателя.
    if listing.price is not None or listing.is_free:
        data["offers"] = {
            "@type": "Offer",
            "url": url,
            "priceCurrency": ("EUR" if str(listing.currency).lower().endswith("eur") else "RSD"),
            "price": 0 if listing.is_free else float(listing.price or 0),
            "availability": ("https://schema.org/InStock"
                             if listing.status == ListingStatus.active
                             else "https://schema.org/SoldOut"),
            "itemCondition": "https://schema.org/UsedCondition",
        }
        # Цена действует, пока висит объявление. Без этого поля Google
        # считает цену просроченной через полгода и перестаёт её показывать.
        if listing.expires_at:
            data["offers"]["priceValidUntil"] = listing.expires_at.date().isoformat()
        # Продавец — частное лицо: выдавать частника за магазин нельзя.
        if listing.owner and getattr(listing.owner, "display_name", None):
            data["offers"]["seller"] = {"@type": "Person", "name": listing.owner.display_name}
    if image:
        data["image"] = image
    if listing.city:
        data["areaServed"] = _city_words(listing.city, lang)

    chain = chain or []
    if chain:
        data["category"] = " > ".join(_cat_name(c, lang) for c in chain)

    # Путь: PLONK → раздел (→ подраздел) → вещь. У каждой ступени, кроме
    # последней, Google требует адрес (поле item) — иначе Search Console
    # помечает «Строки навигации» как недопустимые.
    site_root = "/".join(url.split("/", 3)[:3])
    crumbs = [("PLONK", _lang_url(site_root, "/", lang))]
    for c in chain:
        crumbs.append((_cat_name(c, lang), _lang_url(site_root, f"/c/{c.slug}", lang)))
    crumbs.append((title, url))
    trail = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": item}
            for i, (name, item) in enumerate(crumbs)
        ],
    }
    return json.dumps([data, trail], ensure_ascii=False, indent=1)


def _nice_path(db: Session, listing) -> str:
    """Понятный адрес объявления. Название — на языке оригинала: адрес один на все языки."""
    from app.core.urls import listing_path

    title = ""
    for tr in (listing.translations or []):
        if tr.language == listing.source_language:
            title = tr.title or ""
            break
    else:
        tr = _pick_translation(listing, listing.source_language)
        title = tr.title if tr else ""
    category = listing.category.slug if listing.category else None
    return listing_path(listing.id, title, listing.city, category)


# Страница раздела для поисковика: заголовок, текст раздела, путь,
# подразделы, города, объявления по страницам и разметка списка.
CATEGORY_PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{robots}<link rel="canonical" href="{url}">
{alternates}
{pager_links}<meta property="og:type" content="website">
<meta property="og:site_name" content="PLONK">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{og_locale}">
<meta property="og:image" content="{site}/og-cover.png?v=2">
<script type="application/ld+json">
{schema}
</script>
</head>
<body>
<nav>{crumbs}</nav>
<h1>{heading}</h1>
<p>{intro}</p>
{subsections}{cities}<ul>
{items}
</ul>
{pager}<p><a href="{url}">{open_text}</a></p>
</body>
</html>"""


@router.get("/{lang}/c/{slug}", include_in_schema=False)
def category_page_localised(lang: str, slug: str, request: Request,
                            db: Session = Depends(get_db)):
    """Тот же раздел на другом языке: /en/c/mebel, /ru/c/mebel."""
    if lang == "sr":
        return RedirectResponse(f"/c/{slug}", status_code=301)
    if lang not in ("en", "ru"):
        return _not_found_page(_site())
    return category_page(slug, request, db, lang=lang)


@router.get("/c/{slug}", include_in_schema=False)
def category_page(slug: str, request: Request, db: Session = Depends(get_db),
                  lang: str = "sr"):
    """Раздел с объявлениями по всей Сербии — для поисковиков."""
    return _section_page(db, request, slug, lang, city=None)


def city_category_page(city: str, slug: str, request: Request,
                       db: Session = Depends(get_db), lang: str = "sr"):
    """Раздел в одном городе: /novi-sad/c/namestaj — «nameštaj Novi Sad».

    По таким запросам люди и ищут, а на русском и английском у них почти
    нет конкурентов: KupujemProdajem отвечает только по-сербски.
    """
    if city not in CITY_IN:
        return _not_found_page(_site(), lang)
    return _section_page(db, request, slug, lang, city=city)


def _section_page(db: Session, request: Request, slug: str, lang: str, city: str | None):
    import json

    from app.data.category_intros import intro as category_intro

    site = _site()
    words = CATEGORY_TEXTS.get(lang, CATEGORY_TEXTS["sr"])
    t = _ui(lang)
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        return _not_found_page(site, lang)

    path = f"/{city}/c/{slug}" if city else f"/c/{slug}"
    page = _page_number(request)
    query = f"?page={page}" if page > 1 else ""
    url = _lang_url(site, path, lang) + query
    name = _cat_name(category, lang)

    base = (db.query(Listing)
            .filter(Listing.status == ListingStatus.active,
                    Listing.category_id.in_(_branch_ids(category))))
    if city:
        base = base.filter(_city_filter(city))
    total = base.count()
    pages = max(1, -(-total // PER_PAGE))
    if page > pages:
        return _not_found_page(site, lang)
    rows = (base.options(selectinload(Listing.translations), selectinload(Listing.category))
            .order_by(Listing.published_at.desc().nullslast(), Listing.id)
            .offset((page - 1) * PER_PAGE).limit(PER_PAGE).all())

    # Текст раздела: свой или ближайшего родителя.
    own_text, node = category_intro(slug, lang), category.parent
    while not own_text and node is not None:
        own_text, node = category_intro(node.slug, lang), node.parent

    city_in = CITY_IN[city][lang] if city else ""
    if city:
        title = words["city_title"].format(name=name, city_in=city_in)
        head = words["city_head"].format(name=name, city_in=city_in, count=total)
    else:
        title = words["title"].format(name=name)
        head = (words["with_count"].format(name=name, count=total) if total
                else words["plain"].format(name=name))
    if page > 1:
        title = title.replace(" | PLONK", f" — {t['page'].format(n=page)} | PLONK")
    intro_text = own_text or (head + words["tail"])
    # В описание для выдачи — главное: сколько и где, потом первая фраза
    # текста. Длинное всё равно обрежут на полуслове.
    description = _cut(f"{head}. {own_text.split('. ')[0]}." if own_text else head + words["tail"], 300)

    # Подразделы — только непустые, со счётом: ссылка на пустую страницу
    # тратит обход поисковика впустую.
    _, parent = _tree(db)
    counts = _branch_counts(db, parent, city=city)
    children = sorted(category.children or [], key=lambda c: (c.sort_order or 0, c.slug))
    sub_links = [
        f'<li><a href="{esc(_lang_url(site, (f"/{city}/c/" if city else "/c/") + c.slug, lang))}">'
        f'{esc(_cat_name(c, lang))}</a> ({counts[c.id]})</li>'
        for c in children if counts.get(c.id)]
    subsections = (f"<h2>{esc(t['subsections'])}</h2>\n<ul>\n" + "\n".join(sub_links) + "\n</ul>\n"
                   if sub_links else "")

    # Города: со страницы по всей Сербии — в города, где раздел живой;
    # со страницы города — обратно на всю Сербию и в соседние города.
    city_counts = _city_branch_counts(db, parent)
    city_links = []
    if city:
        city_links.append(f'<li><a href="{esc(_lang_url(site, f"/c/{slug}", lang))}">'
                          f'{esc(t["all_serbia"].format(name=name))}</a></li>')
    for other in CITY_IN:
        n = city_counts.get((other, category.id), 0)
        if other != city and n >= MIN_CITY_LISTINGS:
            city_links.append(
                f'<li><a href="{esc(_lang_url(site, f"/{other}/c/{slug}", lang))}">'
                f'{esc(name)} {esc(CITY_IN[other][lang])}</a> ({n})</li>')
    cities = (f"<h2>{esc(t['cities'])}</h2>\n<ul>\n" + "\n".join(city_links) + "\n</ul>\n"
              if city_links else "")

    items, schema_items = [], []
    for i, listing in enumerate(rows, start=(page - 1) * PER_PAGE + 1):
        items.append(_listing_li(db, site, listing, lang))
        tr = _pick_translation(listing, lang)
        item_lang = lang if lang in _listing_langs(listing) else _main_lang(listing)
        schema_items.append({"@type": "ListItem", "position": i,
                             "url": _lang_url(site, _nice_path(db, listing), item_lang),
                             "name": (tr.title if tr else "") or t["listing"]})

    # Страницы списка: ссылками в тексте — по ним поисковик доходит до
    # объявлений старше первых сорока.
    pager, pager_links = [], []
    if page > 1:
        prev_url = _lang_url(site, path, lang) + (f"?page={page - 1}" if page > 2 else "")
        pager.append(f'<a href="{esc(prev_url)}">{esc(t["prev"])}</a>')
        pager_links.append(f'<link rel="prev" href="{esc(prev_url)}">')
    if page < pages:
        next_url = _lang_url(site, path, lang) + f"?page={page + 1}"
        pager.append(f'<a href="{esc(next_url)}">{esc(t["next"])}</a>')
        pager_links.append(f'<link rel="next" href="{esc(next_url)}">')

    chain = _category_chain(db, category)
    crumb_pairs = [("PLONK", _lang_url(site, "/", lang))]
    crumb_pairs += [(_cat_name(c, lang), _lang_url(site, f"/c/{c.slug}", lang)) for c in chain]
    if city:
        crumb_pairs.append((f"{name} {city_in}", _lang_url(site, path, lang)))
    crumbs = " › ".join(f'<a href="{esc(href)}">{esc(label)}</a>' for label, href in crumb_pairs)

    schema = json.dumps([
        {"@context": "https://schema.org", "@type": "ItemList", "name": f"{name} {city_in}".strip(),
         "url": url, "numberOfItems": total, "itemListElement": schema_items},
        {"@context": "https://schema.org", "@type": "BreadcrumbList",
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": label, "item": href}
                             for i, (label, href) in enumerate(crumb_pairs)]},
    ], ensure_ascii=False, indent=1)

    # Пустой раздел и «город» с парой объявлений — открываются, но в
    # индекс не идут: это «тонкие» страницы.
    thin = total == 0 or (city is not None and total < MIN_CITY_LISTINGS)

    return HTMLResponse(CATEGORY_PAGE.format(
        lang=lang,
        site=site,
        alternates=_alternates_html(site, path, LANGS, query),
        robots='<meta name="robots" content="noindex">\n' if thin else "",
        pager_links="".join(f"{link}\n" for link in pager_links),
        title=esc(title),
        heading=esc(f"{name} {city_in}".strip()),
        description=esc(description),
        intro=esc(intro_text),
        url=url,
        og_locale=OG_LOCALE.get(lang, "sr_RS"),
        schema=schema,
        crumbs=crumbs,
        subsections=subsections,
        cities=cities,
        items="\n".join(items),
        pager=("<p>" + " · ".join(pager) + "</p>\n") if pager else "",
        open_text=esc(words["open"]),
    ))


# Адреса, которые существуют в приложении и должны отвечать «всё
# хорошо», даже когда собственной страницы для поисковика у них нет.
# Всё прочее — несуществующий адрес.
KNOWN_PATHS = ("/", "/search", "/categories", "/login", "/rules", "/terms",
               "/privacy", "/support", "/vitriny", "/volunteer", "/enter")

# Страницы, которые у человека открываются (после входа): робот получает простую страницу с запретом
# индексации — расхождение «человеку страница есть, роботу — нет» проверки безопасности считают приметой обмана.
PRIVATE_PATHS = ("/post", "/vitrina", "/shops/new", "/shops/mine", "/jobs/responses", "/jobs/my", "/favorites",
                 "/notifications", "/reviews/waiting", "/chats", "/profile", "/my", "/saved", "/history",
                 "/profile/edit", "/profile/blocked", "/profile/invite", "/tg/post", "/tg/my", "/moderation")
PRIVATE_PREFIXES = ("/chat/", "/edit/", "/my/", "/jobs/responses/", "/shops/", "/admin")


@router.get("/{full_path:path}", include_in_schema=False)
def not_found(full_path: str, request: Request):
    """Последний обработчик: сюда попадает всё, что не разобрали выше.

    Служебные адреса пропускаем дальше: часть их объявлена в main.py уже
    после подключения роутеров, и этот обработчик их перехватывал бы.
    """
    site = _site()
    path = "/" + full_path.strip("/")

    if path.startswith(("/api", "/media", "/docs", "/openapi", "/redoc")):
        raise HTTPException(404, "not_found")

    # Сербский — без приставки: старые адреса /sr/… ведём на основные
    if path == "/sr" or path.startswith("/sr/"):
        q = request.url.query
        return RedirectResponse((path[3:] or "/") + (f"?{q}" if q else ""), status_code=301)
    # Языковую приставку отбрасываем: /en/search — тот же поиск.
    plang = "sr"
    for lang in ("/en", "/ru"):
        if path == lang or path.startswith(lang + "/"):
            path = path[len(lang):] or "/"
            plang = lang[1:]
            break

    if path == "/vodic" or path.startswith("/vodic/"):
        page = _guide_page(site, path, plang)
        if page:
            return HTMLResponse(page)
        return _not_found_page(site, plang)

    if path.startswith("/seller/"):
        page = _seller_page(site, path.rsplit("/", 1)[-1], plang)
        if page:
            return HTMLResponse(page)
        return _not_found_page(site, plang)

    if path in PRIVATE_PATHS or path.startswith(PRIVATE_PREFIXES):
        return HTMLResponse(_plain_page(site, path, request, plang).replace(
            "<head>\n", '<head>\n<meta name="robots" content="noindex">\n', 1))

    if path in KNOWN_PATHS:
        # Настоящая страница, а не заглушка с одной ссылкой: то же, что
        # видит человек — чем занимается сайт, разделы, города, свежие
        # объявления. Расхождение «роботу одно, людям другое» — примета
        # обмана, за неё сайты и помечают мошенническими.
        return HTMLResponse(_plain_page(site, path, request, plang))

    return _not_found_page(site, plang)


def _plain_page(site: str, path: str, request: Request, lang: str = "sr") -> str:
    """Простая, но настоящая страница для поисковиков и проверяющих — на языке адреса.

    На главной — ещё города и свежие объявления: раньше с главной не вело
    ни одной ссылки на объявление, и до них поисковик добирался только по
    карте сайта, считая их второстепенными.
    """
    from app.core.database import SessionLocal

    T = {
        "sr": {"/": "PLONK — oglasi u Beogradu i celoj Srbiji", "/search": "Pretraga oglasa — PLONK",
               "/categories": "Sve kategorije — PLONK", "/login": "Prijava na PLONK",
               "/rules": "Pravila objavljivanja oglasa — PLONK", "/terms": "Uslovi korišćenja — PLONK",
               "/privacy": "Politika privatnosti — PLONK", "/support": "Podrška — PLONK",
               "/vitriny": "Izlozi prodavaca — PLONK", "/volunteer": "Za volontere — PLONK",
               "_": "PLONK — oglasi u Beogradu i Srbiji",
               "desc": "Besplatni oglasi u Beogradu i širom Srbije: nekretnine, automobili, elektronika, nameštaj, posao, usluge. Trenutno oglasa na sajtu: {n}.",
               "intro": "Besplatni oglasi za Beograd i celu Srbiju. Izdavanje i prodaja stanova, automobili, elektronika, nameštaj, posao, usluge — na srpskom, ruskom i engleskom.",
               "count": "Trenutno objavljeno oglasa: {n}."},
        "ru": {"/": "PLONK — объявления в Белграде и по всей Сербии", "/search": "Поиск объявлений — PLONK",
               "/categories": "Все разделы — PLONK", "/login": "Вход на PLONK",
               "/rules": "Правила размещения объявлений — PLONK", "/terms": "Условия использования — PLONK",
               "/privacy": "Политика конфиденциальности — PLONK", "/support": "Поддержка — PLONK",
               "/vitriny": "Витрины продавцов — PLONK", "/volunteer": "Волонтёрам — PLONK",
               "_": "PLONK — объявления в Белграде и Сербии",
               "desc": "Бесплатные объявления в Белграде и по всей Сербии: недвижимость, авто, электроника, мебель, работа, услуги. Сейчас на сайте объявлений: {n}.",
               "intro": "Бесплатная доска объявлений для Белграда и всей Сербии. Аренда и продажа жилья, автомобили, электроника, мебель, работа, услуги — на сербском, русском и английском.",
               "count": "Сейчас опубликовано объявлений: {n}."},
        "en": {"/": "PLONK — classifieds in Belgrade and all of Serbia", "/search": "Search listings — PLONK",
               "/categories": "All categories — PLONK", "/login": "Sign in to PLONK",
               "/rules": "Posting rules — PLONK", "/terms": "Terms of use — PLONK",
               "/privacy": "Privacy policy — PLONK", "/support": "Support — PLONK",
               "/vitriny": "Seller storefronts — PLONK", "/volunteer": "For volunteers — PLONK",
               "_": "PLONK — classifieds in Belgrade and Serbia",
               "desc": "Free classifieds in Belgrade and across Serbia: property, cars, electronics, furniture, jobs, services. Listings on the site now: {n}.",
               "intro": "Free classifieds for Belgrade and all of Serbia. Flats to rent and buy, cars, electronics, furniture, jobs, services — in Serbian, Russian and English.",
               "count": "Listings published now: {n}."},
    }
    t = T.get(lang, T["sr"])
    ui = _ui(lang)
    title = t.get(path, t["_"])
    prefix = "" if lang == "sr" else f"/{lang}"

    sections, total, fresh, city_links = [], 0, [], []
    try:
        with SessionLocal() as db:
            total = db.query(Listing).filter(Listing.status == ListingStatus.active).count()
            cats, parent = _tree(db)
            counts = _branch_counts(db, parent)
            tops = sorted((c for c in cats if c.parent_id is None), key=lambda c: (c.sort_order or 0, c.slug))
            sections = [(c.slug, _cat_name(c, lang), counts.get(c.id, 0)) for c in tops]
            if path in ("/", "/categories"):
                # Города с живыми разделами: «Nameštaj u Novom Sadu (12)».
                city_counts = _city_branch_counts(db, parent)
                for city in CITY_IN:
                    for c in tops:
                        n = city_counts.get((city, c.id), 0)
                        if n >= MIN_CITY_LISTINGS:
                            city_links.append((f"/{city}/c/{c.slug}",
                                               f"{_cat_name(c, lang)} {CITY_IN[city][lang]}", n))
            if path == "/":
                rows = (db.query(Listing).options(selectinload(Listing.translations),
                                                  selectinload(Listing.category))
                        .filter(Listing.status == ListingStatus.active)
                        .order_by(Listing.published_at.desc().nullslast()).limit(30).all())
                fresh = [_listing_li(db, site, row, lang) for row in rows]
    except Exception:                                      # noqa: BLE001 — страница без списков лучше, чем ошибка
        pass

    links = "\n".join(
        f'<li><a href="{site}{prefix}/c/{esc(slug)}">{esc(name)}</a>' + (f" ({n})" if n else "") + "</li>"
        for slug, name, n in sections)
    cities = ""
    if city_links:
        cities = (f"<h2>{esc(ui['cities'])}</h2>\n<ul>\n"
                  + "\n".join(f'<li><a href="{site}{prefix}{esc(href)}">{esc(label)}</a> ({n})</li>'
                              for href, label, n in city_links) + "\n</ul>\n")
    fresh_html = (f"<h2>{esc(ui['fresh'])}</h2>\n<ul>\n" + "\n".join(fresh) + "\n</ul>\n") if fresh else ""
    alts = _alternates_html(site, path, LANGS)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<meta name="description" content="{esc(t['desc'].format(n=total))}">
<link rel="canonical" href="{site}{prefix}{path}">
{alts}
<meta property="og:type" content="website">
<meta property="og:site_name" content="PLONK">
<meta property="og:title" content="{esc(title)}">
<meta property="og:url" content="{site}{prefix}{path}">
<meta property="og:locale" content="{OG_LOCALE.get(lang, 'sr_RS')}">
<meta property="og:image" content="{site}/og-cover.png?v=2">
</head>
<body>
<h1>{esc(title)}</h1>
<p>{esc(t['intro'])}</p>
<p>{esc(t['count'].format(n=total))}</p>
<h2>{esc(ui['sections'])}</h2>
<ul>
{links}
</ul>
{cities}{fresh_html}<p><a href="{site}{prefix or '/'}">{esc(ui['all'])}</a></p>
</body>
</html>"""


def _seller_page(site: str, user_id: str, lang: str = "sr") -> str | None:
    """Страница продавца для поисковика: имя и его объявления — на языке адреса, с понятными ссылками."""
    from app.core.database import SessionLocal
    from app.models import User

    t = _ui(lang)
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    with SessionLocal() as db:
        u = db.get(User, uid)
        if not u or getattr(u, "is_blocked", False):
            return None
        rows = (db.query(Listing).options(selectinload(Listing.translations), selectinload(Listing.category))
                .filter(Listing.owner_id == uid, Listing.status == ListingStatus.active)
                .order_by(Listing.published_at.desc().nullslast()).limit(40).all())
        name = u.company_name or u.display_name or t["seller"]
        items = [_listing_li(db, site, row, lang) for row in rows]
    path = f"/seller/{uid}"
    # Продавец без объявлений — пустая страница: открывается, но не в индекс.
    robots = "" if items else '<meta name="robots" content="noindex">\n'
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{esc(t['seller_title'].format(name=name))}</title>
<meta name="description" content="{esc(t['seller_desc'].format(name=name, n=len(items)))}">
{robots}<link rel="canonical" href="{_lang_url(site, path, lang)}">
{_alternates_html(site, path, LANGS)}
</head>
<body>
<h1>{esc(name)}</h1>
<p>{esc(t['seller_intro'])}</p>
<h2>{esc(t['seller_list'])}</h2>
<ul>
{chr(10).join(items) or '<li>' + esc(t['seller_none']) + '</li>'}
</ul>
<p><a href="{_lang_url(site, '/', lang)}">{esc(t['all'])}</a></p>
</body>
</html>"""


def _guide_page(site: str, path: str, lang: str) -> str | None:
    """Статья или список статей для поисковика — полный текст на языке адреса, со связями языковых версий."""
    import json as _json
    from xml.sax.saxutils import escape as esc

    from app.data.guides import BY_SLUG, GUIDES, HEADINGS, TITLES, localized
    prefix = "" if lang == "sr" else f"/{lang}"
    alts = "\n".join(
        f'<link rel="alternate" hreflang="{code}" href="{site}{"" if code_l == "sr" else "/" + code_l}{path}">'
        for code, code_l in (("x-default", "sr"), ("sr", "sr"), ("ru", "ru"), ("en", "en")))
    if path == "/vodic":
        items = "\n".join(f'<li><a href="{site}{prefix}/vodic/{g["slug"]}">{esc(localized(g, lang)["title"])}</a> — '
                          f'{esc(localized(g, lang)["lead"])}</li>' for g in GUIDES)
        return (f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n<title>{esc(TITLES[lang])}</title>\n'
                f'<link rel="canonical" href="{site}{prefix}/vodic">\n{alts}\n</head>\n<body>\n<h1>{esc(HEADINGS[lang])}</h1>\n'
                f'<ul>\n{items}\n</ul>\n</body>\n</html>')
    g = BY_SLUG.get(path.rsplit("/", 1)[-1])
    if not g:
        return None
    loc = localized(g, lang)
    body = []
    for t, v in loc["blocks"]:
        if t == "h2":
            body.append(f"<h2>{esc(v)}</h2>")
        elif t == "p":
            body.append(f"<p>{esc(v)}</p>")
        elif t == "ul":
            body.append("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in v) + "</ul>")
        elif t == "cta":
            body.append(f'<p><a href="{site}{prefix}{v[1] if v[1] != "/" else "/"}">{esc(v[0])}</a></p>')
    schema = _json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": loc["title"],
                          "description": loc["lead"], "datePublished": g["date"], "dateModified": g["date"],
                          "image": f"{site}{g['cover']}", "inLanguage": lang,
                          "publisher": {"@type": "Organization", "name": "PLONK", "url": site},
                          "mainEntityOfPage": f"{site}{prefix}{path}"}, ensure_ascii=False)
    return (f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n<title>{esc(loc["title"])} | PLONK</title>\n'
            f'<meta name="description" content="{esc(loc["lead"])}">\n<link rel="canonical" href="{site}{prefix}{path}">\n{alts}\n'
            f'<meta property="og:type" content="article">\n<meta property="og:title" content="{esc(loc["title"])}">\n'
            f'<meta property="og:description" content="{esc(loc["lead"])}">\n<meta property="og:image" content="{site}{g["cover"]}">\n'
            f'<script type="application/ld+json">{schema}</script>\n</head>\n<body>\n<article>\n<h1>{esc(loc["title"])}</h1>\n'
            f'<p>{esc(loc["lead"])}</p>\n' + "\n".join(body) + f'\n</article>\n<p><a href="{site}{prefix}/vodic">{esc(HEADINGS[lang])}</a></p>\n</body>\n</html>')
