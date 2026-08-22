import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import User, UserRole, Language

router = APIRouter(prefix="/api/users", tags=["users"])


class QuickIdentifyIn(BaseModel):
    phone: str
    display_name: str




@router.get("/{user_id}/public")
def public_profile(user_id: uuid.UUID, lang: str = "ru", db: Session = Depends(get_db)):
    """
    Открытая карточка продавца: то, по чему покупатель решает, иметь ли дело.

    Ни телефона, ни почты — контакты появляются только через чат, иначе
    страница продавца превращается в базу для сбора номеров.
    """
    from app.models import Listing, ListingStatus

    user = db.query(User).get(user_id)
    if not user or user.is_blocked:
        raise HTTPException(404, "not_found")

    active = (
        db.query(Listing)
        .filter(Listing.owner_id == user.id, Listing.status == ListingStatus.active)
        .count()
    )

    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "is_company": user.role == UserRole.seller_business,
        "company_name": user.company_name if user.role == UserRole.seller_business else None,
        "phone_verified": user.phone_verified,
        "document_verified": user.document_verified,
        "company_verified": user.company_verified,
        "rating_avg": float(user.rating_avg or 0),
        "rating_count": int(user.rating_count or 0),
        "active_listings": active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
    }
