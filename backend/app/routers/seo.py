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

from fastapi import APIRouter, Depends
from fastapi.responses import Response
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
    for category in db.query(Category).filter(Category.parent_id.is_(None)):
        urls.append(_url(f"{site}/category/{category.slug}", now, "0.8"))

    listings = (
        db.query(Listing)
        .filter(Listing.status == ListingStatus.active)
        .order_by(Listing.created_at.desc())
        .limit(MAX_LISTINGS)
        .all()
    )
    for listing in listings:
        # Свежие объявления поисковику стоит перечитывать чаще: цена
        # меняется, вещь продаётся.
        fresh = listing.created_at and listing.created_at > now - timedelta(days=7)
        urls.append(_url(
            f"{site}/listing/{listing.id}",
            listing.updated_at or listing.created_at,
            "0.7" if fresh else "0.5",
            "daily" if fresh else "weekly",
        ))

    body = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(urls) + "</urlset>")
    return Response(content=body, media_type="application/xml")
