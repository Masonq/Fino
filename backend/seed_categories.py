"""Заполняет базовые категории MVP (Этап 1): недвижимость, авто, услуги, работа.
Остальные категории из ТЗ добавляются на Этапе 2 — сейчас только структура,
чтобы не размазывать модерацию/наполнение на старте.

Запуск: python seed_categories.py
"""
from app.core.database import SessionLocal
from app.models import Category
from app.data.subcategories import SUBCATEGORIES

CATEGORIES = [
    {
        "slug": "real-estate",
        "name": {"ru": "Недвижимость", "en": "Real Estate", "sr": "Nekretnine"},
        "icon": "home",
        "image_url": "https://picsum.photos/seed/cat-realestate/220/220",
        "color": "#0E9F6E",
        "attribute_schema": [
            {"key": "deal_type", "type": "select", "required": True,
             "label": {"ru": "Тип сделки", "en": "Deal type", "sr": "Vrsta ponude"},
             "options": [{"value": "rent", "label": {"ru": "Аренда", "en": "Rent", "sr": "Izdavanje"}},
                         {"value": "sale", "label": {"ru": "Продажа", "en": "Sale", "sr": "Prodaja"}}]},
            {"key": "area_m2", "type": "number", "required": True,
             "label": {"ru": "Площадь, м²", "en": "Area, m²", "sr": "Površina, m²"}},
            {"key": "rooms", "type": "number", "required": False,
             "label": {"ru": "Комнат", "en": "Rooms", "sr": "Sobe"}},
            {"key": "floor", "type": "number", "required": False,
             "label": {"ru": "Этаж", "en": "Floor", "sr": "Sprat"}},
            {"key": "no_commission", "type": "boolean", "required": False,
             "label": {"ru": "Без комиссии", "en": "No commission", "sr": "Bez provizije"}},
        ],
    },
    {
        "slug": "auto",
        "name": {"ru": "Авто", "en": "Cars", "sr": "Automobili"},
        "icon": "car",
        "image_url": "https://picsum.photos/seed/cat-auto/220/220",
        "color": "#3B7BF6",
        "attribute_schema": [
            {"key": "brand", "type": "text", "required": True,
             "label": {"ru": "Марка", "en": "Brand", "sr": "Marka"}},
            {"key": "model", "type": "text", "required": True,
             "label": {"ru": "Модель", "en": "Model", "sr": "Model"}},
            {"key": "year", "type": "number", "required": True,
             "label": {"ru": "Год", "en": "Year", "sr": "Godina"}},
            {"key": "mileage_km", "type": "number", "required": False,
             "label": {"ru": "Пробег, км", "en": "Mileage, km", "sr": "Kilometraža"}},
            {"key": "transmission", "type": "select", "required": False,
             "label": {"ru": "Коробка передач", "en": "Transmission", "sr": "Menjač"},
             "options": [{"value": "manual", "label": {"ru": "Механика", "en": "Manual", "sr": "Manuelni"}},
                         {"value": "automatic", "label": {"ru": "Автомат", "en": "Automatic", "sr": "Automatik"}}]},
            {"key": "vin", "type": "text", "required": False,
             "label": {"ru": "VIN (необязательно)", "en": "VIN (optional)", "sr": "VIN (opciono)"}},
        ],
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
        "attribute_schema": [
            {"key": "listing_kind", "type": "select", "required": True,
             "label": {"ru": "Тип объявления", "en": "Listing type", "sr": "Vrsta oglasa"},
             "options": [{"value": "vacancy", "label": {"ru": "Вакансия", "en": "Vacancy", "sr": "Slobodno radno mesto"}},
                         {"value": "resume", "label": {"ru": "Резюме", "en": "Resume", "sr": "Radna biografija"}}]},
            {"key": "employment_type", "type": "select", "required": False,
             "label": {"ru": "Тип занятости", "en": "Employment type", "sr": "Vrsta zaposlenja"},
             "options": [{"value": "full_time", "label": {"ru": "Полная занятость", "en": "Full-time", "sr": "Puno radno vreme"}},
                         {"value": "part_time", "label": {"ru": "Частичная занятость", "en": "Part-time", "sr": "Skraćeno radno vreme"}}]},
            {"key": "salary_min", "type": "number", "unit": "currency", "required": False,
             "label": {"ru": "Зарплата от", "en": "Salary from", "sr": "Plata od"}},
            {"key": "salary_max", "type": "number", "unit": "currency", "required": False,
             "label": {"ru": "Зарплата до", "en": "Salary to", "sr": "Plata do"}},
        ],
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
        for idx, cat_data in enumerate(CATEGORIES):
            existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
            if existing:
                existing.image_url = cat_data.get("image_url")
                existing.color = cat_data.get("color")
                if cat_data.get("attribute_schema"):
                    existing.attribute_schema = cat_data["attribute_schema"]
                print(f"updated: {cat_data['slug']}")
                continue
            db.add(Category(sort_order=idx, **cat_data))
            print(f"added: {cat_data['slug']}")
        db.commit()

        # Подкатегории. Схему атрибутов не задаём — она наследуется от
        # родителя: «Телефоны» и «Ноутбуки» описываются одними полями.
        for parent_slug, children in SUBCATEGORIES.items():
            parent = db.query(Category).filter(Category.slug == parent_slug).first()
            if not parent:
                print(f"пропуск: нет родителя {parent_slug}")
                continue
            for order, child in enumerate(children):
                exists = db.query(Category).filter(Category.slug == child["slug"]).first()
                if exists:
                    exists.name = child["name"]
                    exists.parent_id = parent.id
                    exists.sort_order = order
                    continue
                db.add(Category(
                    slug=child["slug"], name=child["name"],
                    parent_id=parent.id, sort_order=order,
                ))
            print(f"{parent_slug}: подкатегорий {len(children)}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
