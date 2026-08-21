import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Listing, ListingStatus, ListingTranslation, Category

router = APIRouter(prefix="/api/listings", tags=["listings"])


class TranslationIn(BaseModel):
    language: str
    title: str
    description: str


class ListingCreate(BaseModel):
    category_id: uuid.UUID
    source_language: str = "ru"
    price: float | None = None
    currency: str = "EUR"
    price_negotiable: bool = False
    attributes: dict = {}
    city: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    hide_exact_address: bool = False
    translations: list[TranslationIn]


LISTING_TTL_DAYS = 45


@router.post("")
def create_listing(payload: ListingCreate, owner_id: uuid.UUID, db: Session = Depends(get_db)):
    """Создаёт объявление в статусе pending_moderation.
    owner_id временно передаётся параметром — заменить на auth-зависимость после подключения JWT.
    """
    category = db.query(Category).get(payload.category_id)
    if not category:
        raise HTTPException(404, "category_not_found")

    listing = Listing(
        owner_id=owner_id,
        category_id=payload.category_id,
        source_language=payload.source_language,
        price=payload.price,
        currency=payload.currency,
        price_negotiable=payload.price_negotiable,
        attributes=payload.attributes,
        city=payload.city,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
        hide_exact_address=payload.hide_exact_address,
        status=ListingStatus.pending_moderation,
        expires_at=datetime.utcnow() + timedelta(days=LISTING_TTL_DAYS),
    )
    db.add(listing)
    db.flush()

    for t in payload.translations:
        db.add(ListingTranslation(
            listing_id=listing.id,
            language=t.language,
            title=t.title,
            description=t.description,
            is_auto_translated=False,
        ))

    db.commit()
    db.refresh(listing)
    return {"id": str(listing.id), "status": listing.status}


@router.get("")
def search_listings(
    category_slug: str | None = None,
    city: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    lang: str = Query("ru"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Listing).options(
        joinedload(Listing.translations), joinedload(Listing.photos)
    ).filter(Listing.status == ListingStatus.active)

    if category_slug:
        q = q.join(Category).filter(Category.slug == category_slug)
    if city:
        q = q.filter(Listing.city == city)
    if price_min is not None:
        q = q.filter(Listing.price >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price <= price_max)

    total = q.count()
    items = q.order_by(Listing.published_at.desc()).offset(offset).limit(limit).all()

    def serialize(listing: Listing):
        translation = next((t for t in listing.translations if t.language == lang), None)
        if not translation and listing.translations:
            translation = listing.translations[0]
        cover = next((p for p in listing.photos if p.is_cover), listing.photos[0] if listing.photos else None)
        return {
            "id": str(listing.id),
            "title": translation.title if translation else None,
            "price": float(listing.price) if listing.price else None,
            "currency": listing.currency,
            "city": listing.city,
            "cover_photo": cover.thumbnail_url if cover else None,
            "delivery_available": listing.delivery_available,
            "is_urgent": listing.is_urgent,
        }

    return {"total": total, "items": [serialize(l) for l in items]}


@router.get("/{listing_id}")
def get_listing(listing_id: uuid.UUID, db: Session = Depends(get_db)):
    listing = db.query(Listing).options(
        joinedload(Listing.translations), joinedload(Listing.photos), joinedload(Listing.owner)
    ).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")

    listing.views_count += 1
    db.commit()

    return {
        "id": str(listing.id),
        "category_slug": listing.category.slug,
        "translations": {t.language: {"title": t.title, "description": t.description, "is_auto_translated": t.is_auto_translated} for t in listing.translations},
        "price": float(listing.price) if listing.price else None,
        "currency": listing.currency,
        "price_negotiable": listing.price_negotiable,
        "attributes": listing.attributes,
        "city": listing.city,
        "photos": [{"url": p.url, "is_cover": p.is_cover} for p in listing.photos],
        "views_count": listing.views_count,
        "owner": {
            "id": str(listing.owner.id),
            "display_name": listing.owner.display_name,
            "rating_avg": listing.owner.rating_avg,
            "phone_verified": listing.owner.phone_verified,
        },
        "delivery_available": listing.delivery_available,
        "safe_deal_available": listing.safe_deal_available,
    }
