from fastapi import APIRouter, Depends, HTTPException
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

    def serialize(cat: Category, inherited=None):
        count = total(cat)
        # Картинку и цвет берём у родителя, если своих нет.
        #
        # Новые разделы заводятся без оформления, и на странице они
        # выглядели чужеродно: вместо объёмных значков — пустые
        # квадраты, а шапка меняла цвет с родительского на общий
        # зелёный при каждом заходе внутрь. Увидел на записи экрана.
        #
        # Наследование честнее подстановки случайной картинки: раздел
        # «Корма» показывает то же, что «Товары для животных», и это
        # ровно то, чем он и является — их частью.
        image = cat.image_url or (inherited or {}).get("image_url")
        color = cat.color or (inherited or {}).get("color")
        mine = {"image_url": image, "color": color}
        return {
            "id": str(cat.id),
            "slug": cat.slug,
            "name": cat.name,
            "icon": cat.icon or (inherited or {}).get("icon"),
            "image_url": image,
            "color": color,
            "count": count,
            "ready": True,
            "children": [serialize(c, {**mine, "icon": cat.icon})
                         for c in cat.children] if cat.children else [],
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


@router.get("/{slug}/price-hint")
def category_price_hint(slug: str, currency: str = "RSD",
                        db: Session = Depends(get_db)):
    """
    Сколько обычно просят за вещи из этого раздела.

    Нужно при подаче объявления: человек чаще всего не знает цену и
    ставит наугад — отсюда «Комод за 100 евро» рядом с «Комодом за 15».
    """
    from app.core.price_hint import price_hint

    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(404, "not_found")

    hint = price_hint(db, category, currency.upper())
    return hint or {"count": 0}
