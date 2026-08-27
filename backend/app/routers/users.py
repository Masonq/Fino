import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_current_user
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


class ProfileEdit(BaseModel):
    """Что человек может поменять о себе сам."""
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    default_language: Language | None = None
    # Компания — для тех, кто продаёт как бизнес. Проверку по реестру
    # это не отменяет: название человек пишет сам, а галочку ставим мы.
    company_name: str | None = Field(default=None, max_length=255)

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, v):
        # min_length в Field проверяет строку ДО обрезки пробелов —
        # «  a  » (4 символа) проходил бы, хотя после strip() внизу
        # это один символ. Обрезаем здесь же, до самой проверки длины.
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("too_short")
        return v


@router.get("/me")
def my_profile(user: User = Depends(get_current_user)):
    """Свои данные — для страницы профиля."""
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "role": user.role.value,
        "default_language": user.default_language.value,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "company_name": user.company_name,
        "company_verified": user.company_verified,
        "rating_avg": round(user.rating_avg or 0, 2),
        "rating_count": user.rating_count,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.patch("/me")
def edit_profile(
    payload: ProfileEdit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Правка своих данных.

    Меняем только то, что прислали: пустое поле означает «не трогать», а
    не «стереть» — иначе правка имени обнулила бы всё остальное.
    """
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url or None
    if payload.default_language is not None:
        user.default_language = payload.default_language
    if payload.company_name is not None:
        name = payload.company_name.strip()
        # Название поменяли — прежняя проверка к нему не относится.
        if name != (user.company_name or ""):
            user.company_verified = False
        user.company_name = name or None

    db.commit()
    return my_profile(user)
