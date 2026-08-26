import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.audit import record
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Category, Listing, ListingStatus, User, UserRole
from app.core.clock import utcnow

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_moderator")
    return user


@router.get("/queue")
def queue(
    lang: str = Query("ru"),
    limit: int = Query(50, le=200),
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Объявления, ожидающие проверки — самые старые первыми."""
    items = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos),
                 joinedload(Listing.owner),
                 joinedload(Listing.category).joinedload(Category.parent))
        .filter(Listing.status == ListingStatus.pending_moderation)
        .order_by(Listing.created_at.asc())
        .limit(limit)
        .all()
    )

    from app.core.urls import listing_path

    def serialize(l: Listing):
        tr = next((t for t in l.translations if t.language == lang), None) or (l.translations[0] if l.translations else None)
        # «Раздел → Подраздел» — модератору важно видеть, куда объявление
        # реально попадёт, до того как решать, пропускать его или нет.
        category_name = None
        if l.category:
            cat_label = l.category.name.get(lang) or l.category.name.get("ru")
            if l.category.parent:
                parent_label = l.category.parent.name.get(lang) or l.category.parent.name.get("ru")
                category_name = f"{parent_label} → {cat_label}"
            else:
                category_name = cat_label
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "description": tr.description if tr else None,
            "price": float(l.price) if l.price else None,
            "currency": l.currency,
            "city": l.city,
            "photos": [p.url for p in l.photos],
            "owner_name": l.owner.display_name if l.owner else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "category_name": category_name,
            # Модератор должен видеть объявление так же, как его увидит
            # покупатель — фото и текст в карточке очереди этого не
            # заменяют (кадрирование, порядок фото, вёрстка страницы).
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    total = db.query(Listing).filter(Listing.status == ListingStatus.pending_moderation).count()
    return {"total": total, "items": [serialize(l) for l in items]}


class DecisionIn(BaseModel):
    reason: str | None = None


@router.post("/{listing_id}/approve")
def approve(
    listing_id: uuid.UUID,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    listing.status = ListingStatus.active
    # Момент публикации — по нему сортируется лента и собирается сводка.
    # Раньше поле оставалось пустым, из-за чего сортировка «сначала новые»
    # работала непредсказуемо.
    if not listing.published_at:
        listing.published_at = utcnow()
    record(db, moderator, "listing.approve", target_type="listing",
           target_id=listing.id, owner=str(listing.owner_id))
    db.commit()

    try:
        from app.core.notifications import notify_moderation
        tr = listing.translations[0] if listing.translations else None
        notify_moderation(db, listing.owner_id, tr.title if tr else "", True)
    except Exception:
        pass

    # Достраиваем недостающие языки: продавец пишет на одном, а искать
    # объявление будут на трёх. Делаем до рассылки, чтобы подписчики
    # получили его уже на своём языке.
    try:
        from app.core.translate import translate_listing
        translate_listing(db, listing)
    except Exception:
        pass   # перевод не должен мешать публикации

    # оповещаем тех, кто подписан на подходящий поиск
    try:
        from app.core.search_alerts import notify_subscribers
        notify_subscribers(db, listing)
    except Exception:
        pass

    return {"status": "active"}


@router.post("/{listing_id}/reject")
def reject(
    listing_id: uuid.UUID,
    payload: DecisionIn,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    listing.status = ListingStatus.rejected
    listing.rejection_reason = payload.reason
    record(db, moderator, "listing.reject", target_type="listing",
           target_id=listing.id, reason=payload.reason,
           owner=str(listing.owner_id))
    db.commit()

    try:
        from app.core.notifications import notify_moderation
        tr = listing.translations[0] if listing.translations else None
        notify_moderation(db, listing.owner_id, tr.title if tr else "", False, payload.reason)
    except Exception:
        pass

    return {"status": "rejected"}
