"""
Проверяет базу на несостыковки, которые не видны в коде.

Ищет то, что ломает страницы уже после публикации: объявление без
переводов, ссылки на несуществующие файлы, цену без валюты, объявления в
категории, которой нет, — то есть последствия, а не причины.

    python3 tools/check-data.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import (
    Category, Chat, Favorite, Listing, ListingPhoto, ListingStatus,
    ListingTranslation, Review, User,
)

MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", settings.media_dir)


def main() -> None:
    db = SessionLocal()
    found = 0
    try:
        def report(name, rows):
            nonlocal found
            rows = list(rows)
            if rows:
                found += len(rows)
                print(f"\n{name}: {len(rows)}")
                for r in rows[:5]:
                    print(f"    {r}")

        # объявление без единого перевода — на странице пустой заголовок
        no_tr = (
            db.query(Listing.id)
            .outerjoin(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(ListingTranslation.id.is_(None))
            .all()
        )
        report("объявления без переводов", [str(r[0]) for r in no_tr])

        # активные без фото — в ленте показывается серый прямоугольник
        no_photo = (
            db.query(Listing.id)
            .outerjoin(ListingPhoto, ListingPhoto.listing_id == Listing.id)
            .filter(Listing.status == ListingStatus.active, ListingPhoto.id.is_(None))
            .all()
        )
        report("активные объявления без фотографий", [str(r[0]) for r in no_photo])

        # ссылки на файлы, которых нет на диске
        broken = []
        for ph in db.query(ListingPhoto).all():
            name = os.path.basename(ph.url)
            if not os.path.exists(os.path.join(MEDIA, name)):
                broken.append(name)
        report("фотографии без файла на диске", broken)

        # осиротевшее: ссылается на удалённое
        orphan_fav = (
            db.query(Favorite.id).outerjoin(Listing, Listing.id == Favorite.listing_id)
            .filter(Listing.id.is_(None)).all()
        )
        report("избранное без объявления", [str(r[0]) for r in orphan_fav])

        orphan_chat = (
            db.query(Chat.id).outerjoin(Listing, Listing.id == Chat.listing_id)
            .filter(Listing.id.is_(None)).all()
        )
        report("переписки без объявления", [str(r[0]) for r in orphan_chat])

        orphan_rev = (
            db.query(Review.id).outerjoin(User, User.id == Review.target_id)
            .filter(User.id.is_(None)).all()
        )
        report("отзывы без адресата", [str(r[0]) for r in orphan_rev])

        # объявление в категории, которой больше нет
        bad_cat = (
            db.query(Listing.id).outerjoin(Category, Category.id == Listing.category_id)
            .filter(Category.id.is_(None)).all()
        )
        report("объявления в несуществующей категории", [str(r[0]) for r in bad_cat])

        # цена есть, валюты нет — на карточке будет голое число
        no_cur = db.query(Listing.id).filter(
            Listing.price.isnot(None), Listing.currency.is_(None)).all()
        report("цена без валюты", [str(r[0]) for r in no_cur])

        # объявления из телеграма без ника автора: кнопка ведёт в никуда
        no_author = db.query(Listing.id).filter(
            Listing.external_source == "telegram", Listing.external_author.is_(None)).all()
        report("перенесённые без ника автора", [str(r[0]) for r in no_author])

        print(f"\nвсего замечаний: {found}" if found else "\nнесостыковок не найдено")
    finally:
        db.close()


if __name__ == "__main__":
    main()
