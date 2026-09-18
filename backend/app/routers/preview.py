"""
Превью объявления для мессенджеров и поисковиков.

Приложение собирается в браузере, поэтому у ссылки нет ни заголовка, ни
картинки — в Telegram или WhatsApp она выглядит голым адресом, а поисковики
видят пустую страницу. Здесь отдаём ту же страницу, но с заполненными
мета-тегами: их читают только роботы, живой человек сразу попадает
в приложение.
"""
import html
import uuid

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session, joinedload

from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import get_db
from app.core.urls import listing_path
from app.models import Listing, ListingStatus

router = APIRouter(tags=["preview"])

SITE = "PLONK"

TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>{title}</title>
<meta name="description" content="{description}" />

<meta property="og:type" content="product" />
<meta property="og:site_name" content="{site}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{description}" />
<meta property="og:url" content="{url}" />
{image_tags}

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{description}" />

<link rel="canonical" href="{url}" />
</head>
<body>
<h1>{title}</h1>
<p>{description}</p>
<p><a href="{app_url}">{site}</a></p>
</body>
</html>"""

# Боты соцсетей и поисковиков — только им отдаём страницу-превью
BOTS = (
    "telegrambot", "whatsapp", "viber", "facebookexternalhit", "twitterbot",
    "slackbot", "discordbot", "googlebot", "yandexbot", "bingbot",
    "linkedinbot", "skypeuripreview", "vkshare",
)


def is_bot(request: Request) -> bool:
    ua = (request.headers.get("user-agent") or "").lower()
    return any(b in ua for b in BOTS)


@router.get("/preview/listing/{listing_id}", response_class=HTMLResponse)
def listing_preview(
    listing_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    base = f"{request.base_url}".rstrip("/")
    # Короткая ссылка /go/:id — она уже умеет находить объявление по
    # UUID целиком (см. фронт, ListingDetail.jsx). Раньше тут был
    # /#/listing/{id}: приложение работает на BrowserRouter, а не
    # HashRouter, и такой адрес не подходил ни под один маршрут —
    # обычный человек, перешедший по ссылке, попадал на пустую
    # главную вместо объявления.
    go_url = f"{base}/go/{listing_id}"

    # Человеку — обычное перенаправление, а не пустая страница с одним
    # скриптом. Страница, в которой нет ничего, кроме
    # location.replace(...), — ровно то, как выглядят прокладки
    # фишинговых сайтов, и классификаторы Safe Browsing на неё смотрят
    # в первую очередь.
    if not is_bot(request):
        return RedirectResponse(go_url, status_code=302)

    listing = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos),
                 joinedload(Listing.category))
        .filter(Listing.id == listing_id, Listing.status == ListingStatus.active)
        .first()
    )
    if not listing:
        return HTMLResponse(f"<!doctype html><title>{SITE}</title>", status_code=404)

    tr = next((t for t in listing.translations), None)
    title = tr.title if tr else SITE
    if listing.price:
        title = f"{title} — {listing.price:.0f} {listing.currency}"

    # Красивый постоянный адрес, а не короткий — под него и canonical
    # выдают лучше, и это тот же адрес, что человек видит в приложении.
    app_url = base + listing_path(
        str(listing.id), tr.title if tr else "", listing.city,
        listing.category.slug if listing.category else None,
    )

    description = (tr.description if tr else "") or ""
    description = " ".join(description.split())[:200]
    if listing.city:
        description = f"{listing.city}. {description}".strip()

    # Собранная карточка вместо голой фотографии: с ценой, городом и
    # домом. Размер указываем явно — иначе Telegram показывает её
    # маленькой иконкой сбоку, а не картинкой во всю ширину.
    card = f"{base}/api/og/listing/{listing.id}.png"
    image_tags = (
        f'<meta property="og:image" content="{html.escape(card)}" />\n'
        f'<meta property="og:image:width" content="1200" />\n'
        f'<meta property="og:image:height" content="630" />\n'
        f'<meta name="twitter:card" content="summary_large_image" />\n'
        f'<meta name="twitter:image" content="{html.escape(card)}" />'
    )

    return HTMLResponse(TEMPLATE.format(
        lang=listing.source_language or "ru",
        title=html.escape(title),
        description=html.escape(description or title),
        site=SITE,
        url=html.escape(str(request.url)),
        app_url=html.escape(app_url),
        image_tags=image_tags,
    ))

@router.get("/api/og/listing/{listing_id}.png")
def og_card(listing_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Картинка объявления для ссылок в мессенджерах.

    Раньше в og:image шла сама фотография товара: без цены, без города,
    без признака, что это объявление — в ленте чата такая ссылка похожа
    на случайную картинку. Теперь отдаём собранную карточку.
    """
    from app.core.og_image import cached

    listing = (
        db.query(Listing)
        .options(joinedload(Listing.photos), joinedload(Listing.translations),
                 joinedload(Listing.category))
        .filter(Listing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(404, "not_found")

    by_lang = {t.language: t for t in listing.translations}
    tr = next((by_lang[l] for l in ("ru", "en", "sr") if l in by_lang), None)
    title = (tr.title if tr else "") or SITE

    if listing.is_free:
        price_text = "Бесплатно"
    elif listing.price:
        amount = f"{float(listing.price):,.0f}".replace(",", "\u2009")
        price_text = f"{amount} {'€' if (listing.currency or '').upper() == 'EUR' else (listing.currency or '')}".strip()
    else:
        price_text = "Цена не указана"

    # Название города по-русски: слаг «beograd» в картинке выглядел бы
    # техническим. Берём первое написание из списка и делаем заглавной
    # первую букву — там русское идёт первым.
    city = ""
    if listing.city:
        from app.data.cities_data import _CITIES

        variants = _CITIES.get(listing.city) or []
        city = (variants[0].title() if variants else listing.city.title())
    section = ""
    if listing.category:
        names = listing.category.name or {}
        section = names.get("ru") or names.get("en") or listing.category.slug
    meta = " · ".join(p for p in (city, section) if p)

    cover = next((p for p in listing.photos if p.is_cover and not p.is_video),
                 next((p for p in listing.photos if not p.is_video), None))
    photo_url = None
    if cover:
        photo_url = cover.url
        if photo_url.startswith("/"):
            photo_url = settings.public_base_url.rstrip("/") + photo_url

    fresh = bool(listing.published_at and
                 (utcnow() - listing.published_at) < timedelta(hours=24))
    key = "|".join([
        str(listing.id), title, price_text, meta, photo_url or "", str(fresh),
    ])
    data = cached(key, title=title, price_text=price_text, meta=meta,
                  photo_url=photo_url, is_free=bool(listing.is_free), is_fresh=fresh)
    # Кэш на сутки: карточка меняется только вместе с объявлением, а
    # мессенджеры дёргают её при каждой пересылке ссылки.
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})

