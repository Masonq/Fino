"""Наполняет БД демо-объявлениями для проверки ленты вживую.
Не для продакшена — тестовый продавец + несколько карточек.
Запуск: python seed_demo_listings.py
"""
import uuid
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models import (
    User, UserRole, Language, Category, Listing, ListingStatus,
    ListingTranslation, ListingPhoto, Currency,
)

DEMO_PHONE = "+381600000000"

DEMO_LISTINGS = [
    {
        "category_slug": "real-estate",
        "price": 450, "currency": Currency.eur, "city": "Београд, Врачар",
        "attributes": {"deal_type": "rent", "area_m2": 62, "rooms": 2, "floor": 4},
        "title_ru": "2-комнатная квартира с балконом, Врачар",
        "desc_ru": "Светлая квартира в центре Врачара, 5 минут пешком до Каленич пиjаце. Свежий ремонт, вся техника новая.",
        "photo": "https://picsum.photos/seed/fino-a1/700/500",
    },
    {
        "category_slug": "auto",
        "price": 9800, "currency": Currency.eur, "city": "Нови Сад", "price_negotiable": True,
        "attributes": {"brand": "Volkswagen", "model": "Golf 7", "year": 2016, "mileage_km": 142000, "transmission": "automatic"},
        "title_ru": "Volkswagen Golf 7, 2016, автомат",
        "desc_ru": "Один владелец, полная сервисная история, зимняя резина в комплекте.",
        "photo": "https://picsum.photos/seed/fino-a2/700/500",
    },
    {
        "category_slug": "real-estate",
        "price": 185000, "currency": Currency.eur, "city": "Београд, Земун",
        "attributes": {"deal_type": "sale", "area_m2": 145, "no_commission": True},
        "title_ru": "Дом 145 м² с участком 4 сотки, Земун",
        "desc_ru": "Отдельный дом с участком, продажа напрямую от собственника без комиссии.",
        "photo": "https://picsum.photos/seed/fino-a3/700/500",
    },
    {
        "category_slug": "services",
        "price": 15, "currency": Currency.eur, "city": "Београд",
        "attributes": {"service_type": "Репетитор английского", "experience_years": 6},
        "title_ru": "Репетитор английского, все уровни",
        "desc_ru": "Подготовка к IELTS, разговорный английский, онлайн и очно.",
        "photo": "https://picsum.photos/seed/fino-a4/700/500",
    },
    {
        "category_slug": "jobs",
        "price": 1800, "currency": Currency.eur, "city": "Београд",
        "attributes": {"listing_kind": "vacancy", "employment_type": "full_time", "salary_min": 1800},
        "title_ru": "Frontend-разработчик, remote",
        "desc_ru": "React/TypeScript, удалённо, гибкий график.",
        "photo": "https://picsum.photos/seed/fino-a6/700/500",
    },
]


def run():
    db = SessionLocal()
    try:
        seller = db.query(User).filter(User.phone == DEMO_PHONE).first()
        if not seller:
            seller = User(
                id=uuid.uuid4(),
                phone=DEMO_PHONE,
                hashed_password="demo",
                display_name="Ана М. (демо)",
                role=UserRole.seller_private,
                default_language=Language.ru,
                phone_verified=True,
                rating_avg=4.8,
                rating_count=23,
            )
            db.add(seller)
            db.flush()
            print("created demo seller")

        for item in DEMO_LISTINGS:
            category = db.query(Category).filter(Category.slug == item["category_slug"]).first()
            if not category:
                print(f"skip — category not found: {item['category_slug']}")
                continue

            exists = db.query(Listing).join(ListingTranslation).filter(
                ListingTranslation.title == item["title_ru"]
            ).first()
            if exists:
                print(f"skip (exists): {item['title_ru']}")
                continue

            listing = Listing(
                id=uuid.uuid4(),
                owner_id=seller.id,
                category_id=category.id,
                source_language="ru",
                price=item["price"],
                currency=item["currency"],
                price_negotiable=item.get("price_negotiable", False),
                attributes=item["attributes"],
                city=item["city"],
                status=ListingStatus.active,
                published_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=45),
            )
            db.add(listing)
            db.flush()

            db.add(ListingTranslation(
                listing_id=listing.id, language="ru",
                title=item["title_ru"], description=item["desc_ru"],
            ))
            db.add(ListingPhoto(
                listing_id=listing.id, url=item["photo"], thumbnail_url=item["photo"],
                sort_order=0, is_cover=True,
            ))
            print(f"added: {item['title_ru']}")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
