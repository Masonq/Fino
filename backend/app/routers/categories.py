from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from sqlalchemy import func

from app.models import Category, Listing, ListingStatus

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    """
    Дерево разделов с числом объявлений в каждом.

    Число нужно, чтобы честно показать пустые: раздел с тремя
    объявлениями хуже, чем его отсутствие — он обещает выбор и не даёт
    его. Лучше сказать «скоро появится» и позвать опубликовать первым.
    """
    top_level = (
        db.query(Category)
        .filter(Category.parent_id.is_(None))
        .order_by(Category.sort_order)
        .all()
    )

    # Считаем разом, а не для каждого раздела: иначе дюжина запросов
    # вместо одного на странице, которую открывают чаще прочих.
    # Считаем все живые, а не только полные: в разделе с двадцатью
    # объявлениями, из которых полных пятнадцать, выбор всё равно есть.
    counts = dict(
        db.query(Listing.category_id, func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active)
        .group_by(Listing.category_id)
        .all()
    )

    def total(cat: Category) -> int:
        """Объявления раздела вместе с подразделами."""
        return counts.get(cat.id, 0) + sum(total(c) for c in cat.children)

    def serialize(cat: Category):
        count = total(cat)
        return {
            "id": str(cat.id),
            "slug": cat.slug,
            "name": cat.name,
            "icon": cat.icon,
            "image_url": cat.image_url,
            "color": cat.color,
            "count": count,
            "ready": True,
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
