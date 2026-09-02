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
        urls.append(_url(f"{site}/search?category={category.slug}", now,
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
