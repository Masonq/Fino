from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    """Возвращает дерево категорий верхнего уровня с дочерними."""
    top_level = db.query(Category).filter(Category.parent_id.is_(None)).order_by(Category.sort_order).all()

    def serialize(cat: Category):
        return {
            "id": str(cat.id),
            "slug": cat.slug,
            "name": cat.name,
            "icon": cat.icon,
            "image_url": cat.image_url,
            "color": cat.color,
            "children": [serialize(c) for c in cat.children] if cat.children else [],
        }

    return [serialize(c) for c in top_level]


@router.get("/{slug}/schema")
def get_category_schema(slug: str, db: Session = Depends(get_db)):
    """Схема динамических атрибутов для формы публикации объявления."""
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        return {"error": "not_found"}

    # Подкатегория своих атрибутов не имеет и берёт схему родителя:
    # «Телефоны» и «Ноутбуки» описываются одними и теми же полями, а
    # отдельная схема под каждую ветку — полторы сотни схем на поддержке.
    schema = cat.attribute_schema
    if not schema and cat.parent_id:
        parent = db.query(Category).get(cat.parent_id)
        schema = parent.attribute_schema if parent else []

    return {
        "slug": cat.slug,
        "name": cat.name,
        "parent_slug": cat.parent.slug if cat.parent else None,
        "attribute_schema": schema or [],
    }
