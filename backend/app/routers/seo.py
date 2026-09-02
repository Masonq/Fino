"""
Карта сайта: что поисковику стоит обойти.

Сайт собирается в браузере, и без карты поисковик видит пустую страницу
— обойти ссылки ему неоткуда. Карта отдаёт все объявления списком, и они
попадают в выдачу по названию вещи: человек ищет «сковорода Белград» и
находит наше объявление.

Собирается на лету, а не лежит готовым файлом: объявления появляются
каждый час, и суточной давности карта звала бы поисковика на снятые.
"""
from datetime import timedelta
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import get_db
from app.models import Category, Listing, ListingStatus

router = APIRouter(tags=["seo"])

# Сколько объявлений отдавать. Поисковики принимают до 50 тысяч в одном
# файле, но обходят они не всё сразу — свежие важнее.
MAX_LISTINGS = 5000


def _url(loc: str, changed=None, priority: str = "0.5",
         frequency: str = "daily") -> str:
    parts = [f"<loc>{escape(loc)}</loc>"]
    if changed:
        parts.append(f"<lastmod>{changed.date().isoformat()}</lastmod>")
    parts.append(f"<changefreq>{frequency}</changefreq>")
    parts.append(f"<priority>{priority}</priority>")
    return "<url>" + "".join(parts) + "</url>"


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    """Карта сайта: главная, разделы, объявления."""
    site = settings.public_base_url.rstrip("/")
    now = utcnow()
    urls = [_url(f"{site}/", now, "1.0", "hourly")]

    # Разделы — вторые по важности после главной: по ним ищут чаще, чем
    # по отдельной вещи («мебель Белград»).
    for category in db.query(Category).all():
        # Подразделы тоже: «сковороды» ищут чаще, чем «дом и сад».
        #
        # Раздел открывается поиском с отбором — отдельной страницы у
        # него нет, и звать поисковика на /category/ значит вести его
        # на пустой экран.
        top = category.parent_id is None
        # Ведём на страницу раздела, а не на поиск с параметром в
        # адресе: у /c/<slug> есть готовый текст со списком объявлений
        # (см. category_page ниже), а адреса с «?» поисковики
        # индексируют неохотно и часто считают одной и той же
        # страницей.
        urls.append(_url(f"{site}/c/{category.slug}", now,
                         "0.8" if top else "0.6"))

    listings = (
        db.query(Listing)
        .filter(Listing.status == ListingStatus.active)
        .order_by(Listing.created_at.desc())
        .limit(MAX_LISTINGS)
        .all()
    )
    for listing in listings:
        # Понятный адрес: человек видит его в выдаче и по нему решает,
        # нажимать ли. Набор цифр читается как случайная страница.
        # Свежие объявления поисковику стоит перечитывать чаще: цена
        # меняется, вещь продаётся.
        fresh = listing.created_at and listing.created_at > now - timedelta(days=7)
        urls.append(_url(
            site + _nice_path(db, listing),
            listing.updated_at or listing.created_at,
            "0.7" if fresh else "0.5",
            "daily" if fresh else "weekly",
        ))

    body = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(urls) + "</urlset>")
    return Response(content=body, media_type="application/xml")


# Страница объявления для поисковика.
#
# Сайт собирается в браузере: поисковик получает пустую страницу и ни
# названия вещи, ни цены не видит. Отдаём ему готовый разметанный
# документ — тот же, что человек увидит после загрузки, но сразу.
#
# Человека при этом сразу отправляем на обычную страницу: подменять
# людям вид — обман, за который поисковики наказывают.
LISTING_PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {price} · {city} | PLONK</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="product">
<meta property="og:site_name" content="PLONK">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
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
<h1>{title}</h1>
<p><strong>{price}</strong>{city_line}</p>
<p>{description}</p>
<p><a href="{url}">Открыть объявление на PLONK</a></p>
<script>location.replace("{url}")</script>
</body>
</html>"""


def _is_crawler(agent: str) -> bool:
    """
    Пришёл поисковик или человек.

    Человеку отдавать урезанную страницу нельзя — он ждёт живой сайт.
    """
    agent = (agent or "").lower()
    return any(bot in agent for bot in (
        "googlebot", "yandex", "bingbot", "duckduckbot", "baiduspider",
        "applebot", "facebookexternalhit", "twitterbot", "telegrambot",
        "whatsapp", "slackbot", "linkedinbot", "petalbot", "ahrefsbot",
    ))


@router.get("/go/{listing_id}", include_in_schema=False)
def short_listing_page(listing_id: str, request: Request,
                       db: Session = Depends(get_db)):
    """
    Короткий путь по ключу — из бота и админки.

    Поисковику показываем понятный адрес: иначе он сочтёт их двумя
    страницами и разделит между ними вес.
    """
    from fastapi.responses import RedirectResponse

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing:
        return RedirectResponse(_nice_path(db, listing), status_code=301)
    return listing_page(listing_id, request, db)


@router.get("/{city}/{category}/{slug}", include_in_schema=False)
def nice_listing_page(city: str, category: str, slug: str,
                      request: Request, db: Session = Depends(get_db)):
    """
    Понятный адрес объявления.

    Ключ ищем по хвосту: название могли поправить, и адрес разойдётся
    с нынешним — но хвост остаётся.
    """
    from app.core.urls import listing_id_from

    tail = listing_id_from(slug)
    if not tail:
        return listing_page(slug, request, db)

    from sqlalchemy import String, cast

    listing = db.query(Listing).filter(
        cast(Listing.id, String).like(f"{tail}-%")).first()
    return listing_page(str(listing.id) if listing else slug, request, db)


def listing_page(listing_id: str, request: Request,
                 db: Session = Depends(get_db)):
    """Страница объявления с текстом — для поисковиков и превью ссылок."""
    from html import escape as esc

    from app.models import ListingPhoto, ListingTranslation

    site = settings.public_base_url.rstrip("/")
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    # Адрес страницы — понятный: его увидит поисковик в разметке, и он
    # должен совпадать с тем, что в карте сайта. Иначе выйдут две
    # страницы вместо одной.
    url = site + _nice_path(db, listing) if listing else f"{site}/go/{listing_id}"

    if not listing:
        # Объявления нет — так и говорим. Перенаправлять на главную
        # нельзя: поисковик сочтёт это подменой, а человек не поймёт,
        # куда попал.
        return HTMLResponse(
            "<!DOCTYPE html><html lang=ru><head><meta charset=utf-8>"
            "<title>Объявление не найдено | PLONK</title>"
            "<meta name=robots content=noindex></head><body>"
            "<h1>Объявление не найдено</h1>"
            f'<p><a href="{site}">Другие объявления на PLONK</a></p>'
            "</body></html>",
            status_code=404,
        )

    lang = (listing.source_language.value
            if hasattr(listing.source_language, "value")
            else str(listing.source_language or "ru"))
    translation = (
        db.query(ListingTranslation)
        .filter(ListingTranslation.listing_id == listing.id,
                ListingTranslation.language == listing.source_language)
        .first()
    )
    title = (translation.title if translation else "") or "Объявление"
    body = (translation.description if translation else "") or ""

    price = _price_words(listing)
    city = _city_words(listing.city)
    photo = (db.query(ListingPhoto)
             .filter(ListingPhoto.listing_id == listing.id)
             .order_by(ListingPhoto.sort_order).first())

    schema = _listing_schema(listing, title, body, url,
                             photo.url if photo else None)

    # Цена первой строкой описания — в мессенджерах заголовок часто
    # обрезается по ширине, и цена из него пропадает; в самом описании
    # она видна всегда. Тот же порядок, что у Avito при вставке ссылки.
    body_text = _clean(body)
    description = f"{price} · {city}. {body_text}" if city else f"{price}. {body_text}"
    description = _cut(description, 300) or title

    # og:image:alt даём, а вот width/height — нет: фото приводятся к
    # 1600px по большей стороне с сохранением пропорций (MAX_DIM в
    # media.py), то есть вторая сторона у каждого своя, и указать
    # честные числа неоткуда. Соврать хуже, чем не указать: площадки,
    # увидев несовпадение с реальным файлом, обрежут превью по
    # заявленным пропорциям.
    image_tag = ""
    twitter_image = ""
    twitter_card = "summary"
    if photo:
        image_tag = (
            f'<meta property="og:image" content="{esc(photo.url)}">\n'
            f'<meta property="og:image:alt" content="{esc(title)}">'
        )
        twitter_image = f'<meta name="twitter:image" content="{esc(photo.url)}">'
        twitter_card = "summary_large_image"

    # og:type=product ожидает эти поля — без них разметка неполная и
    # часть площадок просто игнорирует тип, показывая ссылку как
    # обычную страницу.
    price_tags = ""
    if listing.price:
        currency = (listing.currency.value
                    if hasattr(listing.currency, "value")
                    else str(listing.currency or "RSD"))
        price_tags = (
            f'<meta property="product:price:amount" content="{float(listing.price):.0f}">\n'
            f'<meta property="product:price:currency" content="{esc(currency)}">'
        )

    return HTMLResponse(LISTING_PAGE.format(
        lang=lang,
        title=esc(title),
        price=esc(price),
        city=esc(city or "Сербия"),
        city_line=f" · {esc(city)}" if city else "",
        description=esc(description),
        url=url,
        og_locale={"ru": "ru_RS", "en": "en_RS", "sr": "sr_RS"}.get(lang, "ru_RS"),
        price_tags=price_tags,
        image_tag=image_tag,
        twitter_card=twitter_card,
        twitter_image=twitter_image,
        schema=schema,
    ))


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


def _price_words(listing) -> str:
    if listing.is_free:
        return "Бесплатно"
    if listing.price is None:
        return "Цена не указана"
    whole = f"{int(listing.price):,}".replace(",", " ")
    sign = "€" if str(listing.currency).endswith("eur") else "RSD"
    return f"{whole} {sign}"


def _city_words(city: str | None) -> str:
    if not city:
        return ""
    from app.bot.post_format import city_title

    return city_title(city)


def _listing_schema(listing, title: str, body: str, url: str,
                    image: str | None) -> str:
    """
    Разметка товара.

    По ней поисковик показывает цену и наличие прямо в выдаче — такое
    объявление открывают заметно чаще обычной строки.
    """
    import json

    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "description": body[:500] or title,
        "url": url,
        "offers": {
            "@type": "Offer",
            "url": url,
            "priceCurrency": ("EUR" if str(listing.currency).endswith("eur")
                              else "RSD"),
            "price": float(listing.price or 0),
            "availability": ("https://schema.org/InStock"
                             if listing.status == ListingStatus.active
                             else "https://schema.org/SoldOut"),
        },
    }
    if image:
        data["image"] = image
    if listing.city:
        data["areaServed"] = _city_words(listing.city)
    return json.dumps(data, ensure_ascii=False, indent=1)


def _nice_path(db: Session, listing) -> str:
    """Понятный адрес объявления для карты сайта."""
    from app.core.urls import listing_path
    from app.models import ListingTranslation

    translation = (
        db.query(ListingTranslation.title)
        .filter(ListingTranslation.listing_id == listing.id,
                ListingTranslation.language == listing.source_language)
        .first()
    )
    category = listing.category.slug if listing.category else None
    return listing_path(listing.id, translation[0] if translation else "",
                        listing.city, category)


# Страница раздела для поисковика.
#
# По разделу ищут чаще, чем по отдельной вещи: «мебель Белград»,
# «квартиры Нови Сад». Но раздел у нас — обычная страница приложения, и
# поисковик видел на ней пустоту: ни списка объявлений, ни текста, ни
# ссылок, по которым можно уйти вглубь сайта.
#
# Здесь отдаём роботу готовый документ: заголовок раздела, короткое
# описание, свежие объявления ссылками и разметку списка. Человека, как
# и на странице объявления, сразу отправляем в приложение.
CATEGORY_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PLONK">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<script type="application/ld+json">
{schema}
</script>
</head>
<body>
<h1>{heading}</h1>
<p>{description}</p>
<ul>
{items}
</ul>
<p><a href="{url}">Открыть раздел на PLONK</a></p>
</body>
</html>"""


@router.get("/c/{slug}", include_in_schema=False)
def category_page(slug: str, request: Request, db: Session = Depends(get_db)):
    """Раздел с объявлениями — для поисковиков."""
    import json
    from html import escape as esc

    from app.models import Category, ListingTranslation

    site = settings.public_base_url.rstrip("/")
    url = f"{site}/c/{slug}"

    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        return HTMLResponse(
            "<!doctype html><html><head>"
            "<meta name=robots content=noindex></head><body>"
            "<h1>Раздел не найден</h1></body></html>", status_code=404)

    name = (category.name or {}).get("ru") or slug
    # Дети раздела — чтобы поисковик знал и о подразделах тоже.
    children = db.query(Category).filter(Category.parent_id == category.id).all()

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(
            Listing.status == ListingStatus.active,
            ListingTranslation.language == "ru",
            Listing.category_id.in_(
                [category.id] + [c.id for c in children]),
        )
        .order_by(Listing.published_at.desc().nullslast())
        .limit(40)
        .all()
    )

    # Текст на странице: без него у раздела нет ни одного слова, по
    # которому его можно найти. Собираем из того, что знаем наверняка —
    # название раздела, число объявлений, города, — а не выдумываем
    # рекламные обещания.
    cities = {l.city for l, _ in rows if l.city}
    # Число объявлений называем, только если они есть: «0 свежих
    # объявлений» в описании раздела отпугивает и человека в выдаче, и
    # поисковика — раздел выглядит заброшенным, даже если завтра в нём
    # снова появятся вещи.
    if rows:
        head = f"{name} в Сербии на PLONK: {len(rows)} свежих объявлений"
        if cities:
            head += f" — {', '.join(sorted(cities)[:4])}"
    else:
        head = f"{name} в Сербии на PLONK"
    description = (
        head + ". Покупайте и продавайте рядом с домом, на русском, "
        "английском и сербском."
    )

    items, schema_items = [], []
    for i, (listing, tr) in enumerate(rows, start=1):
        path = _nice_path(db, listing)
        items.append(f'<li><a href="{esc(site + path)}">{esc(tr.title or "")}</a></li>')
        schema_items.append({
            "@type": "ListItem",
            "position": i,
            "url": site + path,
            "name": tr.title or "",
        })

    for child in children:
        child_name = (child.name or {}).get("ru") or child.slug
        items.append(
            f'<li><a href="{esc(site)}/c/{esc(child.slug)}">{esc(child_name)}</a></li>')

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name,
        "url": url,
        "numberOfItems": len(schema_items),
        "itemListElement": schema_items,
    }, ensure_ascii=False, indent=1)

    return HTMLResponse(CATEGORY_PAGE.format(
        title=f"{esc(name)} — объявления в Белграде и Сербии | PLONK",
        heading=esc(name),
        description=esc(description),
        url=url,
        schema=schema,
        items="\n".join(items),
    ))
