import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.routers.listings import pick_translation
from app.models import User, Favorite, Listing, ListingStatus

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("")
def list_favorites(
    lang: str = Query("ru"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.id
    rows = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .limit(200)
        .all()
    )
    listing_ids = [r.listing_id for r in rows]
    if not listing_ids:
        return {"total": 0, "items": []}

    listings = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos))
        .filter(Listing.id.in_(listing_ids), Listing.status == ListingStatus.active)
        .all()
    )
    by_id = {l.id: l for l in listings}

    def serialize(listing: Listing):
        translation = pick_translation(listing, lang)
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

    # сохраняем порядок добавления в избранное
    items = [serialize(by_id[lid]) for lid in listing_ids if lid in by_id]
    return {"total": len(items), "items": items}


@router.get("/ids")
def favorite_ids(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = user.id
    rows = db.query(Favorite.listing_id).filter(Favorite.user_id == user_id).all()
    return {"ids": [str(r[0]) for r in rows]}


@router.post("/{listing_id}")
def add_favorite(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.id
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "listing_not_found")

    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
        .first()
    )
    if existing:
        return {"status": "already_added"}

    db.add(Favorite(user_id=user_id, listing_id=listing_id))
    db.commit()
    return {"status": "added"}


@router.delete("/{listing_id}")
def remove_favorite(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.id
    db.query(Favorite).filter(
        Favorite.user_id == user_id, Favorite.listing_id == listing_id
    ).delete()
    db.commit()
    return {"status": "removed"}
