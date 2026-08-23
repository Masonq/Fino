#!/usr/bin/env python3
"""Что бот записал в базу — последние объявления из чата-партнёра."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.partner_chats import BARAHOLKA_TEST  # noqa: E402
from app.models import Listing, ListingTranslation  # noqa: E402

with SessionLocal() as db:
    rows = (
        db.query(Listing)
        .filter(Listing.external_chat == str(BARAHOLKA_TEST))
        .order_by(Listing.created_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        print("из этого чата ничего не записано")
    for listing in rows:
        translation = (
            db.query(ListingTranslation)
            .filter(ListingTranslation.listing_id == listing.id)
            .first()
        )
        price = ("бесплатно" if listing.is_free
                 else f"{listing.price} {listing.currency}"
                 if listing.price else "без цены")
        print(f"{listing.created_at.strftime('%H:%M')} | {price:<16} "
              f"| фото: {len(listing.photos)} | {listing.status.value}")
        print(f"   {translation.title if translation else '—'}")
        if translation and translation.description:
            print(f"   {translation.description[:70]}")
