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

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

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

    cover = next((p for p in listing.photos if p.is_cover), listing.photos[0] if listing.photos else None)
    image_tags = ""
    if cover:
        img = cover.url
        if img.startswith("/"):
            img = base + img
        image_tags = (
            f'<meta property="og:image" content="{html.escape(img)}" />\n'
            f'<meta name="twitter:image" content="{html.escape(img)}" />'
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
