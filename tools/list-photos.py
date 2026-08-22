"""
Показывает перенесённые объявления вместе с именами файлов их фотографий.

Нужен, чтобы найти конкретное объявление и взять его снимки как образец —
например, чтобы отличить фото с водяным знаком от чистых.

    python3 tools/list-photos.py
"""
import os

from app.core.database import SessionLocal
from app.models import Listing, ListingPhoto, ListingTranslation


def main() -> None:
    db = SessionLocal()
    try:
        listings = (
            db.query(Listing)
            .filter(Listing.external_source == "telegram")
            .order_by(Listing.created_at.desc())
            .limit(40)
            .all()
        )
        for listing in listings:
            photos = db.query(ListingPhoto).filter(
                ListingPhoto.listing_id == listing.id
            ).order_by(ListingPhoto.sort_order).all()
            if not photos:
                continue
            tr = db.query(ListingTranslation).filter(
                ListingTranslation.listing_id == listing.id
            ).first()
            title = (tr.title if tr else "") or "(без заголовка)"
            names = [os.path.basename(p.url) for p in photos]
            print(f"{title[:46]:48} {len(names)} фото")
            for name in names:
                print(f"    {name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
