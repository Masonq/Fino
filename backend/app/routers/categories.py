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
            "children": [serialize(c) for c in cat.children] if cat.children else [],
        }

    return [serialize(c) for c in top_level]


@router.get("/{slug}/schema")
def get_category_schema(slug: str, db: Session = Depends(get_db)):
    """Схема динамических атрибутов для формы публикации объявления."""
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        return {"error": "not_found"}
    return {"slug": cat.slug, "name": cat.name, "attribute_schema": cat.attribute_schema}
