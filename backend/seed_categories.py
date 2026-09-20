"""Заполняет базовые категории MVP (Этап 1): недвижимость, авто, услуги, работа.
Остальные категории из ТЗ добавляются на Этапе 2 — сейчас только структура,
чтобы не размазывать модерацию/наполнение на старте.

Запуск: python seed_categories.py
"""
from app.core.database import SessionLocal
from app.models import Category
from app.data.subcategories import SUBCATEGORIES, SUB_SUBCATEGORIES
from app.data.schemas import SCHEMAS, SUB_SCHEMAS

CATEGORIES = [
    {
        "slug": "real-estate",
        "name": {"ru": "Недвижимость", "en": "Real Estate", "sr": "Nekretnine"},
        "icon": "home",
        "image_url": "https://picsum.photos/seed/cat-realestate/220/220",
        "color": "#0E9F6E",
        # схема — в app/data/schemas.py (SCHEMAS["real-estate"]), чтобы не
        # держать её тут второй копией и не расходиться при правках
        "attribute_schema": [],
    },
    {
        "slug": "auto",
        "name": {"ru": "Авто", "en": "Cars", "sr": "Automobili"},
        "icon": "car",
        "image_url": "https://picsum.photos/seed/cat-auto/220/220",
        "color": "#3B7BF6",
        "attribute_schema": [],
    },
    {
        "slug": "services",
        "name": {"ru": "Услуги", "en": "Services", "sr": "Usluge"},
        "icon": "wrench",
        "image_url": "https://picsum.photos/seed/cat-services/220/220",
        "color": "#F2A11D",
        "attribute_schema": [
            {"key": "service_type", "type": "text", "translatable": True, "required": True,
             "label": {"ru": "Вид услуги", "en": "Service type", "sr": "Vrsta usluge"}},
            {"key": "service_area", "type": "text", "translatable": True, "required": False,
             "label": {"ru": "Район обслуживания", "en": "Service area", "sr": "Područje usluge"}},
            {"key": "experience_years", "type": "number", "required": False,
             "label": {"ru": "Опыт, лет", "en": "Experience, years", "sr": "Iskustvo, godine"}},
        ],
    },
    {
        "slug": "jobs",
        "name": {"ru": "Работа", "en": "Jobs", "sr": "Poslovi"},
        "icon": "briefcase",
        "image_url": "https://picsum.photos/seed/cat-jobs/220/220",
        "color": "#6D5DFC",
        # схема — в app/data/schemas.py (SCHEMAS["jobs"]), один источник
        "attribute_schema": [],
    },
    # Этап 2 — остальные категории из ТЗ, без модерации/наполнения пока, но уже видны в каталоге
    {
        "slug": "electronics",
        "name": {"ru": "Электроника", "en": "Electronics", "sr": "Elektronika"},
        "icon": "device",
        "image_url": "https://picsum.photos/seed/cat-electronics/220/220",
        "color": "#FF6152",
        "attribute_schema": [],
    },
    {
        "slug": "fashion",
        "name": {"ru": "Одежда и обувь", "en": "Fashion", "sr": "Odeća i obuća"},
        "icon": "shirt",
        "image_url": "https://picsum.photos/seed/cat-fashion/220/220",
        "color": "#E85D9C",
        "attribute_schema": [],
    },
    {
        "slug": "home-garden",
        "name": {"ru": "Дом и сад", "en": "Home & Garden", "sr": "Dom i bašta"},
        "icon": "sofa",
        "image_url": "https://picsum.photos/seed/cat-home/220/220",
        "color": "#8B6F47",
        "attribute_schema": [],
    },
    {
        "slug": "hobby-sport",
        "name": {"ru": "Хобби, спорт, отдых", "en": "Hobby & Sport", "sr": "Hobi i sport"},
        "icon": "ball",
        "image_url": "https://picsum.photos/seed/cat-hobby/220/220",
        "color": "#3FB6A8",
        "attribute_schema": [],
    },
    {
        "slug": "kids",
        "name": {"ru": "Детские товары", "en": "Kids", "sr": "Za decu"},
        "icon": "kids",
        "image_url": "https://picsum.photos/seed/cat-kids/220/220",
        "color": "#F2A11D",
        "attribute_schema": [],
    },
    {
        "slug": "pets",
        "name": {"ru": "Животные", "en": "Pets", "sr": "Životinje"},
        "icon": "paw",
        "image_url": "https://picsum.photos/seed/cat-pets/220/220",
        "color": "#6D5DFC",
        "attribute_schema": [],
    },
    {
        "slug": "beauty",
        "name": {"ru": "Личные вещи, красота", "en": "Beauty", "sr": "Lepota"},
        "icon": "beauty",
        "image_url": "https://picsum.photos/seed/cat-beauty/220/220",
        "color": "#FF6152",
        "attribute_schema": [],
    },
    {
        "slug": "business",
        "name": {"ru": "Бизнес и оборудование", "en": "Business", "sr": "Biznis"},
        "icon": "business",
        "image_url": "https://picsum.photos/seed/cat-business/220/220",
        "color": "#0B7A54",
        "attribute_schema": [],
    },
]


def run():
    db = SessionLocal()
    try:
        # Схемы для категорий, у которых их не было: без полей блок
        # характеристик пуст, и вещь не с чем сравнить
        for cat_data in CATEGORIES:
            extra = SCHEMAS.get(cat_data["slug"])
            if extra and not cat_data.get("attribute_schema"):
                cat_data["attribute_schema"] = extra

        for idx, cat_data in enumerate(CATEGORIES):
            existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
            if existing:
                existing.image_url = cat_data.get("image_url")
                existing.color = cat_data.get("color")
                if cat_data.get("attribute_schema"):
                    existing.attribute_schema = cat_data["attribute_schema"]
                existing.name = cat_data["name"]
                print(f"updated: {cat_data['slug']}")
                continue
            db.add(Category(sort_order=idx, **cat_data))
            print(f"added: {cat_data['slug']}")
        db.commit()

        # Подкатегории. Схема — из SUB_SCHEMAS, где для подраздела она
        # задана (у него свои поля, отличные от соседей); иначе пусто —
        # тогда форма публикации сама возьмёт схему родителя.
        for parent_slug, children in SUBCATEGORIES.items():
            parent = db.query(Category).filter(Category.slug == parent_slug).first()
            if not parent:
                print(f"пропуск: нет родителя {parent_slug}")
                continue
            for order, child in enumerate(children):
                sub_schema = SUB_SCHEMAS.get(child["slug"], [])
                exists = db.query(Category).filter(Category.slug == child["slug"]).first()
                if exists:
                    exists.name = child["name"]
                    exists.parent_id = parent.id
                    exists.sort_order = order
                    exists.attribute_schema = sub_schema
                    continue
                db.add(Category(
                    slug=child["slug"], name=child["name"],
                    parent_id=parent.id, sort_order=order,
                    attribute_schema=sub_schema,
                ))
            print(f"{parent_slug}: подкатегорий {len(children)}")
        db.commit()

        # Третий уровень — тот же цикл, но родителя теперь ищем среди
        # уже созданных ПОДКАТЕГОРИЙ (SUBCATEGORIES выше), не корневых
        # категорий. Отдельным проходом, после commit() над вторым
        # уровнем — иначе к моменту поиска родителя-подкатегории она
        # могла ещё не существовать в базе.
        for parent_slug, children in SUB_SUBCATEGORIES.items():
            parent = db.query(Category).filter(Category.slug == parent_slug).first()
            if not parent:
                print(f"пропуск: нет родителя-подкатегории {parent_slug}")
                continue
            for order, child in enumerate(children):
                sub_schema = SUB_SCHEMAS.get(child["slug"], [])
                exists = db.query(Category).filter(Category.slug == child["slug"]).first()
                if exists:
                    exists.name = child["name"]
                    exists.parent_id = parent.id
                    exists.sort_order = order
                    exists.attribute_schema = sub_schema
                    continue
                db.add(Category(
                    slug=child["slug"], name=child["name"],
                    parent_id=parent.id, sort_order=order,
                    attribute_schema=sub_schema,
                ))
            print(f"{parent_slug}: под-подкатегорий {len(children)}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
