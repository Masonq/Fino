"""Что написано в объявлениях без города."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('/opt/fino/backend')))

from app.core.database import SessionLocal
from app.models import Listing, ListingStatus, ListingTranslation

with SessionLocal() as db:
    rows = (
        db.query(ListingTranslation.title, ListingTranslation.description)
        .join(Listing, Listing.id == ListingTranslation.listing_id)
        .filter(Listing.city.is_(None),
                Listing.status != ListingStatus.archived,
                ListingTranslation.language == Listing.source_language)
        .limit(12).all()
    )
    for title, body in rows:
        tail = " ".join((body or "").split())[-90:]
        print(f"— {title[:44]}")
        print(f"  …{tail}\n")
