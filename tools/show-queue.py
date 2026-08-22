"""
Показывает, что лежит в очереди модерации и почему туда попало.

Перенесённое объявление уходит на проверку, когда тема чата и разбор текста
разошлись. Если таких три четверти, дело не в объявлениях, а в правиле —
этот список даёт увидеть, что именно.

    python3 tools/show-queue.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.core.database import SessionLocal
from app.models import Category, Listing, ListingStatus, ListingTranslation


def main() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(Listing, ListingTranslation, Category)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .join(Category, Category.id == Listing.category_id)
            .filter(
                Listing.external_source == "telegram",
                Listing.status == ListingStatus.pending_moderation,
                ListingTranslation.language == "ru",
            )
            .order_by(Category.slug)
            .all()
        )
        print(f"в очереди: {len(rows)}\n")
        for listing, tr, category in rows:
            price = f"{int(listing.price)} {listing.currency.value}" if listing.price else "—"
            print(f"{category.slug:16} {price:>12}  {(tr.title or '(без заголовка)')[:46]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
