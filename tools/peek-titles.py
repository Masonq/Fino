#!/usr/bin/env python3
"""
Показывает заголовки, которые проходят в ленту.

Правила угадать заранее нельзя: каждый промах открывает новый вид
кривизны. Смотреть надо на живых объявлениях.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 60

with SessionLocal() as db:
    rows = (
        db.query(ListingTranslation.title)
        .join(Listing, Listing.id == ListingTranslation.listing_id)
        .filter(Listing.status == ListingStatus.active,
                Listing.is_complete.is_(True),
                ListingTranslation.language == Listing.source_language)
        .order_by(Listing.created_at.desc())
        .limit(limit)
        .all()
    )
    for (title,) in rows:
        print(title)
