"""Заполняет базовые категории MVP (Этап 1): недвижимость, авто, услуги, работа.
Остальные категории из ТЗ добавляются на Этапе 2 — сейчас только структура,
чтобы не размазывать модерацию/наполнение на старте.

Запуск: python seed_categories.py
"""
from app.core.database import SessionLocal
from app.models import Category

CATEGORIES = [
    {
        "slug": "real-estate",
        "name": {"ru": "Недвижимость", "en": "Real Estate", "sr": "Nekretnine"},
        "icon": "home",
        "attribute_schema": [
            {"key": "deal_type", "type": "select", "required": True,
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
        "attribute_schema": [
            {"key": "service_type", "type": "text", "required": True,
             "label": {"ru": "Вид услуги", "en": "Service type", "sr": "Vrsta usluge"}},
            {"key": "service_area", "type": "text", "required": False,
             "label": {"ru": "Район обслуживания", "en": "Service area", "sr": "Područje usluge"}},
            {"key": "experience_years", "type": "number", "required": False,
             "label": {"ru": "Опыт, лет", "en": "Experience, years", "sr": "Iskustvo, godine"}},
        ],
    },
    {
        "slug": "jobs",
        "name": {"ru": "Работа", "en": "Jobs", "sr": "Poslovi"},
        "icon": "briefcase",
        "attribute_schema": [
            {"key": "listing_kind", "type": "select", "required": True,
             "options": [{"value": "vacancy", "label": {"ru": "Вакансия", "en": "Vacancy", "sr": "Slobodno radno mesto"}},
                         {"value": "resume", "label": {"ru": "Резюме", "en": "Resume", "sr": "Radna biografija"}}]},
            {"key": "employment_type", "type": "select", "required": False,
             "options": [{"value": "full_time", "label": {"ru": "Полная занятость", "en": "Full-time", "sr": "Puno radno vreme"}},
                         {"value": "part_time", "label": {"ru": "Частичная занятость", "en": "Part-time", "sr": "Skraćeno radno vreme"}}]},
            {"key": "salary_min", "type": "number", "required": False,
             "label": {"ru": "Зарплата от", "en": "Salary from", "sr": "Plata od"}},
            {"key": "salary_max", "type": "number", "required": False,
             "label": {"ru": "Зарплата до", "en": "Salary to", "sr": "Plata do"}},
        ],
    },
]


def run():
    db = SessionLocal()
    try:
        for idx, cat_data in enumerate(CATEGORIES):
            existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
            if existing:
                print(f"skip (exists): {cat_data['slug']}")
                continue
            db.add(Category(sort_order=idx, **cat_data))
            print(f"added: {cat_data['slug']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
