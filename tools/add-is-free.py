#!/usr/bin/env python3
"""
Добавляет объявлениям признак «отдают даром» и проставляет его старым.

«Цена не указана» и «бесплатно» — разные вещи: мимо первого читатель
проходит, второе его как раз заинтересует. Признак берём из текста
объявления, поэтому старые размечаются на месте, без переноса заново.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_parse import looks_free  # noqa: E402
from app.models import Listing, ListingTranslation  # noqa: E402

with SessionLocal() as db:
    db.execute(text(
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS "
        "is_free BOOLEAN NOT NULL DEFAULT FALSE"
    ))
    db.commit()
    print("колонка is_free на месте")

    rows = (
        db.query(Listing, ListingTranslation.title, ListingTranslation.description)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(Listing.price.is_(None), Listing.is_free.is_(False))
        .all()
    )

    marked = 0
    for listing, title, description in rows:
        if looks_free(f"{title or ''}\n{description or ''}"):
            listing.is_free = True
            marked += 1
    db.commit()
    print(f"помечено как «отдают даром»: {marked} из {len(rows)} без цены")
