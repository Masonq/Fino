import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import SavedSearch, User, Category

router = APIRouter(prefix="/api/saved-searches", tags=["saved-searches"])

MAX_PER_USER = 20   # больше человек всё равно не отслеживает, а рассылка растёт


class SavedSearchIn(BaseModel):
    name: str | None = None
    filters: dict
    notify_enabled: bool = True


def describe(filters: dict, db: Session, lang: str, fallback: str = "Поиск") -> str:
    """
    Человеческое название из фильтров, если пользователь не задал своё.

    Раньше category_slug клался как есть («furniture») — сырой
    английский идентификатор, не то, что видит человек нигде больше в
    интерфейсе. Ищем категорию по slug и берём её человеческое
    название на нужном языке, с откатом на русский и сам slug, если
    вдруг категория пропала.
    """
    parts = []
    if filters.get("q"):
        parts.append(f'«{filters["q"]}»')
    slug = filters.get("category_slug")
    if slug:
        category = db.query(Category).filter(Category.slug == slug).first()
        if category and category.name:
            parts.append(category.name.get(lang) or category.name.get("ru") or slug)
        else:
            parts.append(slug)
    if filters.get("price_min") or filters.get("price_max"):
        lo = filters.get("price_min") or ""
        hi = filters.get("price_max") or ""
        parts.append(f"{lo}–{hi}")
    if filters.get("city"):
        parts.append(filters["city"])
    return " · ".join(str(p) for p in parts) or fallback


@router.get("")
def list_saved(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SavedSearch)
        .filter(SavedSearch.user_id == user.id)
        .order_by(SavedSearch.created_at.desc())
        .all()
    )
    return {
        "total": len(rows),
        "items": [
            {
                "id": str(s.id),
                "name": s.name,
                "filters": s.filters,
                "notify_enabled": s.notify_enabled,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in rows
        ],
    }


@router.post("")
def create_saved(
    payload: SavedSearchIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.filters:
        raise HTTPException(400, "empty_filters")

    count = db.query(SavedSearch).filter(SavedSearch.user_id == user.id).count()
    if count >= MAX_PER_USER:
        raise HTTPException(400, "too_many")

    # тот же поиск второй раз не сохраняем
    existing = db.query(SavedSearch).filter(SavedSearch.user_id == user.id).all()
    for s in existing:
        if s.filters == payload.filters:
            return {"status": "exists", "id": str(s.id)}

    item = SavedSearch(
        user_id=user.id,
        name=(payload.name or describe(payload.filters, db, user.default_language.value))[:120],
        filters=payload.filters,
        notify_enabled=payload.notify_enabled,
    )
    db.add(item)
    db.commit()
    return {"status": "ok", "id": str(item.id)}


@router.delete("/{search_id}")
def delete_saved(
    search_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(SavedSearch).filter(
        SavedSearch.id == search_id, SavedSearch.user_id == user.id
    ).delete()
    db.commit()
    return {"status": "ok"}


class ToggleIn(BaseModel):
    notify_enabled: bool


@router.patch("/{search_id}")
def toggle_notify(
    search_id: uuid.UUID,
    payload: ToggleIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(SavedSearch).filter(
        SavedSearch.id == search_id, SavedSearch.user_id == user.id
    ).first()
    if not item:
        raise HTTPException(404, "not_found")
    item.notify_enabled = payload.notify_enabled
    db.commit()
    return {"status": "ok"}
