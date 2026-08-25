#!/usr/bin/env python3
"""
Смотрит, сколько объявлений годятся для ленты.

Первое впечатление важнее числа: человек, попавший на обрубки без цены и
с невнятным названием, второй раз не придёт. Лучше показать четыреста
хороших, чем полторы тысячи вперемешку.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Listing, ListingPhoto, ListingStatus, ListingTranslation,
)


def flaws(listing, title: str, body: str, photos: int) -> list[str]:
    """Чего не хватает объявлению."""
    bad = []
    if not title or len(title) < 8:
        bad.append("нет внятного названия")
    elif len(title) > 90:
        bad.append("название слишком длинное")
    if listing.price is None and not listing.is_free:
        bad.append("нет цены")
    if not photos:
        bad.append("нет фотографии")
    if len(body or "") < 20:
        bad.append("нет описания")
    if not listing.city:
        bad.append("нет города")
    return bad


def main() -> None:
    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation.title,
                     ListingTranslation.description)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status == ListingStatus.active)
            .all()
        )

        photo_counts = dict(
            db.query(ListingPhoto.listing_id,
                     __import__("sqlalchemy").func.count(ListingPhoto.id))
            .group_by(ListingPhoto.listing_id).all()
        )

        found = Counter()
        perfect = 0
        for listing, title, body in rows:
            bad = flaws(listing, title, body, photo_counts.get(listing.id, 0))
            if not bad:
                perfect += 1
            for flaw in bad:
                found[flaw] += 1

        print(f"живых объявлений: {len(rows)}")
        print(f"без единого изъяна: {perfect}")
        print(f"\nчего не хватает:")
        for flaw, count in found.most_common():
            print(f"  {flaw:<26} {count}")

        # Сколько останется, если требовать только самое важное
        core = sum(
            1 for listing, title, body in rows
            if (title and len(title) >= 8
                and (listing.price is not None or listing.is_free)
                and photo_counts.get(listing.id, 0))
        )
        print(f"\nс названием, ценой и фото: {core}")


if __name__ == "__main__":
    main()
