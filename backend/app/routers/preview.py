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

    # Русский перевод, а не первый попавшийся: порядок в базе
    # произвольный, и в превью уходил сербский текст.
    by_lang = {t.language: t for t in listing.translations}
    tr = next((by_lang[l] for l in ("ru", "en", "sr") if l in by_lang),
              listing.translations[0] if listing.translations else None)
    title = tr.title if tr else SITE

    # Красивый постоянный адрес, а не короткий — под него и canonical
    # выдают лучше, и это тот же адрес, что человек видит в приложении.
    app_url = base + listing_path(
        str(listing.id), tr.title if tr else "", listing.city,
        listing.category.slug if listing.category else None,
    )

    # Описание под заголовком: цена, город и — если оно правда добавляет
    # что-то новое — текст продавца.
    #
    # У перенесённых объявлений описание часто слово в слово повторяет
    # заголовок: заголовок из него и собирали. В превью это выглядело
    # так, будто одно и то же написано дважды подряд.
    code = getattr(listing.currency, "value", listing.currency) or ""
    if listing.is_free:
        price_line = "Бесплатно"
    elif listing.price:
        amount = f"{float(listing.price):,.0f}".replace(",", "\u2009")
        price_line = f"{amount} {'€' if code.upper() == 'EUR' else code}".strip()
    else:
        price_line = ""

    body = " ".join(((tr.description if tr else "") or "").split())

    def _words(text: str) -> set:
        return {w.strip(".,!?()»«\"'").lower() for w in text.split() if len(w) > 3}

    if body and not (_words(body) - _words(title)):
        body = ""

    city_name = ""
    if listing.city:
        from app.data.cities_data import _CITIES

        variants = _CITIES.get(listing.city) or []
        city_name = variants[0].title() if variants else listing.city.title()

    head = " · ".join(p for p in (price_line, city_name) if p)
    description = f"{head}. {body}".strip(" .") if body else head
    description = description[:200]

    # Собранная карточка вместо голой фотографии: с ценой, городом и
    # домом. Размер указываем явно — иначе Telegram показывает её
    # маленькой иконкой сбоку, а не картинкой во всю ширину.
    card = f"{base}/api/og/listing/{listing.id}.png?v=3"   # ?v — новый адрес после смены оформления: мессенджеры хранят картинку по адресу
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
def og_card(listing_id: uuid.UUID, lang: str = "ru", db: Session = Depends(get_db)):
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
    # язык карточки = язык страницы, где стоит ссылка (раньше всегда русский — при сербском тексте превью)
    lang = lang if lang in ("ru", "en", "sr") else "ru"
    order = [lang] + [l for l in ("ru", "en", "sr") if l != lang]
    tr = next((by_lang[l] for l in order if l in by_lang), None)
    title = (tr.title if tr else "") or SITE
    L = {"ru": ("Бесплатно", "Цена не указана"), "en": ("Free", "Price on request"), "sr": ("Besplatno", "Cena nije navedena")}[lang]

    if listing.is_free:
        price_text = L[0]
    elif listing.price:
        amount = f"{float(listing.price):,.0f}".replace(",", "\u2009")
        # Валюта — перечисление, а не строка: в подпись уезжало
        # «Currency.rsd» вместо «RSD». Берём значение, а не сам элемент.
        code = getattr(listing.currency, "value", listing.currency) or ""
        price_text = f"{amount} {'€' if code.upper() == 'EUR' else code}".strip()
    else:
        price_text = L[1]

    # Название города по-русски: слаг «beograd» в картинке выглядел бы
    # техническим. Берём первое написание из списка и делаем заглавной
    # первую букву — там русское идёт первым.
    city = ""
    if listing.city:
        from app.data.cities_data import _CITIES, city_label

        try:
            city = city_label(listing.city, lang) or ""
        except Exception:                                # noqa: BLE001
            city = ""
        if not city or city == listing.city:
            variants = _CITIES.get(listing.city) or []
            city = (variants[0].title() if variants else listing.city.title())
    section = ""
    if listing.category:
        names = listing.category.name or {}
        section = names.get(lang) or names.get("ru") or names.get("en") or listing.category.slug
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
        str(listing.id), lang, title, price_text, meta, photo_url or "", str(fresh),
    ])
    data = cached(key, title=title, price_text=price_text, meta=meta,
                  photo_url=photo_url, is_free=bool(listing.is_free), is_fresh=fresh, lang=lang)
    # Кэш на сутки: карточка меняется только вместе с объявлением, а
    # мессенджеры дёргают её при каждой пересылке ссылки.
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})

