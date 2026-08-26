#!/usr/bin/env python3
"""
Добавляет признак полноты и проставляет его накопленным объявлениям.

Полное объявление — с названием, ценой и фотографией. Такие идут в ленте
первыми: человек, попавший на обрубки, второй раз не придёт.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func, text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.routers.listings import title_is_clear  # noqa: E402
from app.models import (  # noqa: E402
    Listing, ListingPhoto, ListingStatus, ListingTranslation,
)

with SessionLocal() as db:
    db.execute(text(
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS "
        "is_complete BOOLEAN NOT NULL DEFAULT FALSE"
    ))
    db.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_listings_is_complete "
        "ON listings (is_complete)"
    ))
    db.commit()
    print("колонка is_complete на месте")

    photos = dict(
        db.query(ListingPhoto.listing_id, func.count(ListingPhoto.id))
        .group_by(ListingPhoto.listing_id).all()
    )

    rows = (
        db.query(Listing, ListingTranslation.title)
        .join(ListingTranslation,
              (ListingTranslation.listing_id == Listing.id)
              & (ListingTranslation.language == Listing.source_language))
        .filter(Listing.status != ListingStatus.archived)
        .all()
    )

    complete = 0
    for listing, title in rows:
        # «Hutschenreuther» — марка без вещи: человек не поймёт, что
        # продают, пока не откроет. В ленте таким не место.
        good = bool(
            title_is_clear(title)
            and (listing.price is not None or listing.is_free)
            and photos.get(listing.id, 0)
        )
        listing.is_complete = good
        complete += good
    db.commit()

    print(f"полных объявлений: {complete} из {len(rows)}")
