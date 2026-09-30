"""
Карта сайта: что поисковику стоит обойти.

Сайт собирается в браузере, и без карты поисковик видит пустую страницу
— обойти ссылки ему неоткуда. Карта отдаёт все объявления списком, и они
попадают в выдачу по названию вещи: человек ищет «сковорода Белград» и
находит наше объявление.

Собирается на лету, а не лежит готовым файлом: объявления появляются
каждый час, и суточной давности карта звала бы поисковика на снятые.
"""
from app.core.plural import count as _cnt
from app.core.category_tree import branch_ids as _branch_ids
from datetime import timedelta
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request
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


# Языки сайта и их приставки в адресе. Русский — основной и живёт без
# приставки: он был первым, на него ведут все существующие ссылки, и
# ломать их ради единообразия нельзя.
LANGS = ("ru", "en", "sr")

# Обрамление страницы раздела на каждом языке. Без него у английской
# версии по-русски выходила половина заголовка — «Real Estate —
# объявления в Белграде и Сербии», — и в англоязычной выдаче она
# выглядела бы страницей на чужом языке.
CATEGORY_TEXTS = {
    "ru": {
        "title": "{name} — объявления в Белграде и Сербии | PLONK",
        "with_count": "{name} в Сербии на PLONK — свежих объявлений: {count}",
        "plain": "{name} в Сербии на PLONK",
        "tail": ". Покупайте и продавайте рядом с домом, на русском, "
                "английском и сербском.",
        "open": "Открыть раздел на PLONK",
        "missing": "Раздел не найден",
    },
    "en": {
        "title": "{name} — classifieds in Belgrade and Serbia | PLONK",
        "with_count": "{name} in Serbia on PLONK — fresh listings: {count}",
        "plain": "{name} in Serbia on PLONK",
        "tail": ". Buy and sell close to home, in Russian, English "
                "and Serbian.",
        "open": "Open this section on PLONK",
        "missing": "Section not found",
    },
    "sr": {
        "title": "{name} — oglasi u Beogradu i Srbiji | PLONK",
        "with_count": "{name} u Srbiji na PLONK — novih oglasa: {count}",
        "plain": "{name} u Srbiji na PLONK",
        "tail": ". Kupujte i prodajte blizu kuće, na ruskom, engleskom "
                "i srpskom.",
        "open": "Otvorite sekciju na PLONK",
        "missing": "Sekcija nije pronađena",
    },
}


def _lang_url(site: str, path: str, lang: str) -> str:
    """Адрес страницы на нужном языке."""
    prefix = "" if lang == "ru" else f"/{lang}"
    return f"{site}{prefix}{path}"


def _url(loc: str, changed=None, priority: str = "0.5",
         frequency: str = "daily", alternates: dict | None = None) -> str:
    parts = [f"<loc>{escape(loc)}</loc>"]
    if changed:
        parts.append(f"<lastmod>{changed.date().isoformat()}</lastmod>")
    parts.append(f"<changefreq>{frequency}</changefreq>")
    parts.append(f"<priority>{priority}</priority>")
    # Языковые версии перечисляем прямо в карте сайта. Так поисковик
    # узнаёт, что /en/c/mebel и /c/mebel — одна и та же страница на
    # разных языках, а не две конкурирующие: иначе он выберет одну и
    # покажет её всем, включая тех, кто ищет по-сербски.
    for lang, href in (alternates or {}).items():
        code = "x-default" if lang == "ru" else lang
        parts.append(
            f'<xhtml:link rel="alternate" hreflang="{code}" '
            f'href="{escape(href)}"/>'
        )
        if lang == "ru":
            parts.append(
                f'<xhtml:link rel="alternate" hreflang="ru" '
                f'href="{escape(href)}"/>'
            )
    return "<url>" + "".join(parts) + "</url>"


def _with_langs(site: str, path: str, changed=None, priority: str = "0.5",
                frequency: str = "daily") -> str:
    """Одна запись карты сайта — со ссылками на все языковые версии."""
    alternates = {lang: _lang_url(site, path, lang) for lang in LANGS}
    return _url(_lang_url(site, path, "ru"), changed, priority, frequency,
                alternates)


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    """Карта сайта: главная, разделы, объявления."""
    site = settings.public_base_url.rstrip("/")
    now = utcnow()
    urls = [_with_langs(site, "/", now, "1.0", "hourly")]

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
        urls.append(_with_langs(site, f"/c/{category.slug}", now,
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
        urls.append(_with_langs(
            site, _nice_path(db, listing),
            listing.updated_at or listing.created_at,
            "0.7" if fresh else "0.5",
            "daily" if fresh else "weekly",
        ))

    body = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
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
{alternates}
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
</body>
</html>"""


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


@router.get("/{lang}/{city}/{category}/{slug}", include_in_schema=False)
def nice_listing_page_localised(lang: str, city: str, category: str, slug: str,
                                request: Request,
                                db: Session = Depends(get_db)):
    """Объявление на другом языке: /en/beograd/mebel/stol-45e17e58."""
    if lang not in ("en", "sr"):
        return HTMLResponse(
            "<!doctype html><html><head><meta name=robots content=noindex>"
            "</head><body><h1>404</h1></body></html>", status_code=404)
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
    # /en/c/mebel те же три части, что у /beograd/mebel/stol. Разбираем
    # здесь, потому что этот маршрут объявлен раньше и перехватывает их
    # первым — поймал на живом запросе, английская страница отвечала
    # ошибкой про негодный ключ.
    if city in ("en", "sr") and category == "c":
        return category_page(slug, request, db, lang=city)

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

    # Номер может оказаться не номером: адрес удалённого объявления или
    # просто набранный от руки. Раньше такой запрос уходил в базу как
    # есть и падал с ошибкой — поисковик получал «сервер сломался»
    # вместо «страницы нет».
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
    except Exception:                                      # noqa: BLE001
        db.rollback()
        listing = None

    # Адрес страницы — понятный и на том же языке, что открыт.
    #
    # Раньше здесь всегда указывался русский адрес, даже когда страница
    # отдавалась на английском. Google заходил на /en/..., читал «основная
    # версия — русская» и записывал страницу в копии: «канонические
    # версии, выбранные Google и пользователем, не совпадают». Из-за
    # этого объявления выпадали из поиска.
    #
    # Языковые версии связаны отдельно, через hreflang ниже, — там и
    # сказано, что это одна страница на трёх языках.
    url = f"{site}/go/{listing_id}"   # ниже заменим на понятный адрес

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

    # Язык берём из адреса, а не из объявления.
    #
    # Раньше смотрели на источник объявления: приехало из русского чата
    # — значит и основная версия русская, даже когда открыт /en/...
    # Google на это и жаловался: «канонические версии не совпадают».
    #
    # Языка в адресе нет — берём язык объявления, как раньше: значит
    # открыта версия по умолчанию.
    path = request.url.path if hasattr(request, "url") else "/"
    if path.startswith("/en/"):
        lang = "en"
    elif path.startswith("/sr/"):
        lang = "sr"
    else:
        lang = (listing.source_language.value
                if hasattr(listing.source_language, "value")
                else str(listing.source_language or "ru"))

    # Адрес на том же языке, что открыт.
    #
    # Раньше здесь всегда стоял русский, даже когда страница отдавалась
    # на английском: Google заходил на /en/..., читал «основная версия —
    # русская» и записывал страницу в копии. Оттого объявления и
    # выпадали из поиска.
    if listing:
        url = _lang_url(site, _nice_path(db, listing), lang)

    # Языковые версии одного объявления.
    #
    # У разделов такие связи были, у объявлений — нет вовсе. Google
    # видел три страницы с одним товаром и не знал, что это одна вещь на
    # трёх языках: выбирал одну сам, остальные записывал в копии.
    path_for_langs = _nice_path(db, listing) if listing else f"/go/{listing_id}"
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{code}" '
        f'href="{_lang_url(site, path_for_langs, code_lang)}">'
        for code, code_lang in (("x-default", "ru"), ("ru", "ru"),
                                ("en", "en"), ("sr", "sr"))
    )
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
    # У перенесённых объявлений описание часто слово в слово повторяет
    # заголовок — его из описания и собирали. В превью это выглядело
    # так, будто одно и то же написано дважды подряд.
    def _words(text: str) -> set:
        return {w.strip(".,!?()»«\"'").lower() for w in text.split() if len(w) > 3}

    if body_text and not (_words(body_text) - _words(title)):
        body_text = ""

    head = f"{price} · {city}" if city else price
    description = f"{head}. {body_text}".strip(" .") if body_text else head
    description = _cut(description, 300) or title

    # Собранная карточка: фотография слева, цена, город и раздел справа,
    # снизу домен. Размер у неё всегда 1200×630, поэтому width/height
    # указываем честно — раньше их не было вовсе, потому что размер
    # присланной продавцом фотографии заранее неизвестен.
    card = f"{site}/api/og/listing/{listing.id}.png"
    image_tag = (
        f'<meta property="og:image" content="{esc(card)}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">\n'
        f'<meta property="og:image:alt" content="{esc(title)}">'
    )
    twitter_image = f'<meta name="twitter:image" content="{esc(card)}">'
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
        alternates=alternates,
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

    # Раздел объявления. Google показывает его в карточке товара и
    # понимает, к чему вещь относится, — а у нас это знание есть и
    # пропадало зря.
    if listing.category and listing.category.name:
        section = (listing.category.name or {}).get("ru")
        if section:
            data["category"] = section

    # Продавец. Для доски объявлений это частное лицо, и так и пишем:
    # выдавать частника за магазин нельзя, да и незачем.
    if listing.owner and getattr(listing.owner, "display_name", None):
        data["offers"]["seller"] = {
            "@type": "Person",
            "name": listing.owner.display_name,
        }

    # Цена действует, пока висит объявление. Без этого поля Google
    # считает цену просроченной через полгода и перестаёт её показывать.
    if listing.expires_at:
        data["offers"]["priceValidUntil"] = listing.expires_at.date().isoformat()

    # Путь до объявления: город → раздел → вещь.
    #
    # Google показывает его в выдаче вместо длинного адреса: вместо
    # «plonk.rs/beograd/computers/igrovoy-...» человек видит
    # «Белград › Настольные компьютеры». Понятнее и заметнее.
    crumbs = []
    if listing.city:
        crumbs.append(_city_words(listing.city))
    if listing.category and listing.category.name:
        section = (listing.category.name or {}).get("ru")
        if section:
            crumbs.append(section)

    if crumbs:
        site_root = url.split("/", 3)[:3]
        site_root = "/".join(site_root)
        trail = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name}
                for i, name in enumerate(crumbs)
            ],
        }
        trail["itemListElement"].append(
            {"@type": "ListItem", "position": len(crumbs) + 1,
             "name": title, "item": url})
        return json.dumps([data, trail], ensure_ascii=False, indent=1)

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
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
{alternates}
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
<p><a href="{url}">{open_text}</a></p>
</body>
</html>"""


@router.get("/{lang}/c/{slug}", include_in_schema=False)
def category_page_localised(lang: str, slug: str, request: Request,
                            db: Session = Depends(get_db)):
    """Тот же раздел на другом языке: /en/c/mebel, /sr/c/mebel."""
    if lang not in ("en", "sr"):
        return HTMLResponse(
            "<!doctype html><html><head><meta name=robots content=noindex>"
            "</head><body><h1>404</h1></body></html>", status_code=404)
    return category_page(slug, request, db, lang=lang)


@router.get("/c/{slug}", include_in_schema=False)
def category_page(slug: str, request: Request, db: Session = Depends(get_db),
                  lang: str = "ru"):
    """Раздел с объявлениями — для поисковиков."""
    import json
    from html import escape as esc

    from app.models import Category, ListingTranslation

    site = settings.public_base_url.rstrip("/")
    url = _lang_url(site, f"/c/{slug}", lang)

    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        return HTMLResponse(
            "<!doctype html><html><head>"
            "<meta name=robots content=noindex></head><body>"
            f"<h1>{CATEGORY_TEXTS.get(lang, CATEGORY_TEXTS['ru'])['missing']}"
            "</h1></body></html>", status_code=404)

    name = (category.name or {}).get(lang) or (category.name or {}).get("ru") or slug
    # Дети раздела — чтобы поисковик знал и о подразделах тоже.
    children = db.query(Category).filter(Category.parent_id == category.id).all()

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(
            Listing.status == ListingStatus.active,
            ListingTranslation.language == lang,
            # Вся ветка: с третьим уровнем прямых детей мало — у
            # «Услуг» объявления лежат в «Мастера» → «Сантехник», и
            # поисковик видел раздел почти пустым.
            Listing.category_id.in_(_branch_ids(category)),
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
    words = CATEGORY_TEXTS.get(lang, CATEGORY_TEXTS["ru"])
    if rows:
        head = words["with_count"].format(name=name, count=len(rows))
        if cities:
            head += f" — {', '.join(sorted(cities)[:4])}"
    else:
        head = words["plain"].format(name=name)
    description = head + words["tail"]

    # Свой текст раздела, если он написан.
    #
    # Шаблонное «Недвижимость — 98 объявлений» одинаково у всех разделов
    # и ничего не говорит ни поисковику, ни человеку. Живой текст
    # объясняет, что тут можно найти, теми же словами, которыми люди
    # спрашивают вслух.
    from app.data.category_intros import intro as category_intro

    # Родителя передаём, чтобы подраздел без своего текста показал
    # описание раздела, а не пустоту.
    # Поднимаемся, пока не найдём текст: у третьего уровня родитель —
    # подраздел, и своего текста у него чаще всего тоже нет.
    own_text, node = category_intro(slug, lang), category.parent
    while not own_text and node is not None:
        own_text, node = category_intro(node.slug, lang), node.parent
    if own_text:
        # В описание для выдачи — первое предложение: там всего полторы
        # сотни знаков, длинное всё равно обрежут на полуслове.
        description = own_text.split(". ")[0] + "."

    items, schema_items = [], []
    for i, (listing, tr) in enumerate(rows, start=1):
        path = _nice_path(db, listing)
        href = _lang_url(site, path, lang)
        items.append(f'<li><a href="{esc(href)}">{esc(tr.title or "")}</a></li>')
        schema_items.append({
            "@type": "ListItem",
            "position": i,
            "url": href,
            "name": tr.title or "",
        })

    for child in children:
        child_name = ((child.name or {}).get(lang)
                      or (child.name or {}).get("ru") or child.slug)
        items.append(
            f'<li><a href="{esc(_lang_url(site, f"/c/{child.slug}", lang))}">'
            f'{esc(child_name)}</a></li>')

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name,
        "url": url,
        "numberOfItems": len(schema_items),
        "itemListElement": schema_items,
    }, ensure_ascii=False, indent=1)

    # Языковые версии — на каждой странице: поисковик должен знать, что
    # /en/c/mebel и /c/mebel одно и то же на разных языках, иначе
    # выберет одну и покажет её всем.
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{code}" '
        f'href="{_lang_url(site, f"/c/{slug}", code_lang)}">'
        for code, code_lang in (("x-default", "ru"), ("ru", "ru"),
                                ("en", "en"), ("sr", "sr"))
    )

    return HTMLResponse(CATEGORY_PAGE.format(
        lang=lang,
        alternates=alternates,
        title=esc(words["title"].format(name=name)),
        heading=esc(name),
        description=esc(description),
        url=url,
        schema=schema,
        items="\n".join(items),
        open_text=esc(words["open"]),
    ))


# Ответ на несуществующий адрес.
#
# Раньше любой случайный путь отдавал приложение со статусом «всё
# хорошо»: поисковик считал такую страницу настоящей и заносил в
# индекс, а удалённые объявления оставались в выдаче живыми. Со стороны
# человека это тоже неприятно — вместо честного «страницы нет» он видит
# пустоту или бесконечное ожидание.
#
# Отвечаем честно, но только поисковику: человеку по-прежнему отдаётся
# приложение (nginx до этого обработчика его просто не доводит), и
# внутренние переходы в нём работают как раньше.
NOT_FOUND_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<title>Страница не найдена — PLONK</title>
</head>
<body>
<h1>Страница не найдена</h1>
<p>Возможно, объявление уже продано или снято с публикации.</p>
<p><a href="{site}">Открыть PLONK</a></p>
</body>
</html>"""

# Адреса, которые существуют в приложении и должны отвечать «всё
# хорошо», даже когда собственной страницы для поисковика у них нет.
# Всё прочее — несуществующий адрес.
KNOWN_PATHS = ("/", "/search", "/categories", "/login", "/rules", "/terms",
               "/privacy", "/support")


@router.get("/{full_path:path}", include_in_schema=False)
def not_found(full_path: str, request: Request):
    """Последний обработчик: сюда попадает всё, что не разобрали выше.

    Служебные адреса пропускаем дальше. Этот обработчик ловит любой
    путь, а часть служебных объявлена в main.py уже после подключения
    роутеров — их он перехватывал и отвечал «страницы нет». Поймал
    сразу: проверка браузером перестала достукиваться до сервера.
    """
    site = settings.site_base_url.rstrip("/")
    path = "/" + full_path.strip("/")

    if path.startswith(("/api", "/media", "/docs", "/openapi", "/redoc")):
        raise HTTPException(404, "not_found")

    # Языковую приставку отбрасываем: /en/search — тот же поиск.
    for lang in ("/en", "/sr"):
        if path == lang or path.startswith(lang + "/"):
            path = path[len(lang):] or "/"
            break

    if path in KNOWN_PATHS:
        # Настоящая страница, а не заглушка с одной ссылкой.
        #
        # Раньше поисковику и проверяющим отдавалось это:
        #   <title>PLONK</title><a href="...">Открыть PLONK</a>
        # Человек при этом видел полноценный сайт. Такое расхождение —
        # классическая примета обмана: роботу одно, людям другое. Именно
        # за это сайты и помечают как мошеннические, а у нас как раз
        # появилось предупреждение в Safari при чистом домене по всем
        # спискам безопасности.
        #
        # Теперь отдаём то же, что видит человек: чем занимается сайт,
        # какие разделы есть, сколько объявлений.
        return HTMLResponse(_plain_page(site, path, request))

    return HTMLResponse(NOT_FOUND_PAGE.format(site=site), status_code=404)


def _plain_page(site: str, path: str, request: Request) -> str:
    """Простая, но настоящая страница для поисковиков и проверяющих."""
    from xml.sax.saxutils import escape as esc

    from sqlalchemy import text

    from app.core.database import SessionLocal

    titles = {
        "/": "PLONK — объявления в Белграде и по всей Сербии",
        "/search": "Поиск объявлений — PLONK",
        "/categories": "Все разделы — PLONK",
        "/login": "Вход на PLONK",
        "/rules": "Правила размещения объявлений — PLONK",
        "/terms": "Условия использования — PLONK",
        "/privacy": "Политика конфиденциальности — PLONK",
        "/support": "Поддержка — PLONK",
    }
    title = titles.get(path, "PLONK — объявления в Белграде и Сербии")

    rows, total = [], 0
    try:
        with SessionLocal() as db:
            total = db.execute(text(
                "select count(*) from listings where status = 'active'"
            )).scalar() or 0
            rows = db.execute(text("""
                select c.slug, c.name->>'ru'
                from categories c
                where c.parent_id is null
                order by c.sort_order nulls last, c.slug
                limit 14
            """)).fetchall()
    except Exception:                                      # noqa: BLE001
        pass

    links = "\n".join(
        f'<li><a href="{site}/c/{esc(slug)}">{esc(name or slug)}</a></li>'
        for slug, name in rows
    )


    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<meta name="description" content="Объявления в Белграде и по всей Сербии: недвижимость, авто, электроника, работа, услуги. Сейчас на сайте {_cnt(total, 'объявление', 'объявления', 'объявлений')}.">
<link rel="canonical" href="{site}{path}">
</head>
<body>
<h1>{esc(title)}</h1>
<p>Бесплатная доска объявлений для Белграда и всей Сербии. Аренда и
продажа жилья, автомобили, электроника, мебель, работа, услуги —
на русском, английском и сербском.</p>
<p>Сейчас опубликовано объявлений: {total}.</p>
<h2>Разделы</h2>
<ul>
{links}
</ul>
<p><a href="{site}">Все объявления</a></p>
</body>
</html>"""
