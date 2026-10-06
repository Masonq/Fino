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


@router.get("/{slug}/intro")
def get_category_intro(slug: str, city: str | None = None, db: Session = Depends(get_db)):
    """Текст раздела на трёх языках — тот же, что видит поисковик на /c/<раздел>.

    Человеку и поисковику страница должна говорить одно и то же: текст,
    который есть только у робота, — подмена содержимого. Своего текста
    нет — берём ближайшего родителя, как и страница для поисковика.
    """
    from app.data.category_intros import intro

    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        return {}
    out, node = {}, cat
    while node is not None and not out:
        out = {lang: text for lang in ("sr", "ru", "en") if (text := intro(node.slug, lang))}
        node = node.parent
    return out


@router.get("/{slug}/schema")
def get_category_schema(slug: str, db: Session = Depends(get_db)):
    """Схема динамических атрибутов для формы публикации объявления."""
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        return {"error": "not_found"}

    # Подкатегория своих атрибутов не имеет и берёт схему родителя:
    # «Телефоны» и «Ноутбуки» описываются одними и теми же полями, а
    # отдельная схема под каждую ветку — полторы сотни схем на поддержке.
    #
    # Поднимаемся, пока не найдём: у третьего уровня («Телефоны» →
    # «Apple») родитель — подраздел, и если своей схемы нет и у него,
    # форма размещения оставалась вовсе без полей.
    from app.data.schemas import NO_FIELDS

    schema, node, hops = cat.attribute_schema, cat.parent, 0
    # Подразделы без полей вовсе (домашняя еда, бытовая химия) у раздела
    # ничего не берут: «материал» и «габариты» им чужие.
    if cat.slug in NO_FIELDS:
        node = None
    while not schema and node is not None and hops < 10:
        schema, node, hops = node.attribute_schema, node.parent, hops + 1

    # «Оплата» и «Как передать» записаны в схемах разделов, а у
    # большинства подразделов схема своя — и до «Телефонов», «Мебели»,
    # «Колясок» эти два вопроса не доходили вовсе. Дописываем их в конец,
    # если у раздела наверху они есть, а у подраздела нет.
    if schema and cat.parent is not None and cat.slug not in NO_FIELDS:
        from app.core.category_tree import root_of

        have = {f.get("key") for f in schema}
        tail = [f for f in (root_of(cat).attribute_schema or [])
                if f.get("key") in ("payment_way", "handover") and f.get("key") not in have]
        schema = list(schema) + tail

    return {
        "slug": cat.slug,
        "name": cat.name,
        "parent_slug": cat.parent.slug if cat.parent else None,
        "attribute_schema": schema or [],
    }
