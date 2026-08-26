#!/usr/bin/env python3
"""
Показывает объявления без цены — что в них написано.

Цену часто пишут словами внутри описания: «отдам за 2000», «5 евро за
штуку», «договоримся». Разбор их не находит, и объявление уходит в ленту
с пустым ценником — а по такому не звонят.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 30

with SessionLocal() as db:
    rows = (
        db.query(ListingTranslation.title, ListingTranslation.description)
        .join(Listing, Listing.id == ListingTranslation.listing_id)
        .filter(Listing.status == ListingStatus.active,
                Listing.price.is_(None),
                Listing.is_free.is_(False),
                ListingTranslation.language == Listing.source_language)
        .limit(limit)
        .all()
    )
    for title, body in rows:
        text = " ".join((body or "").split())
        print(f"— {title[:56]}")
        print(f"  {text[:150]}\n")
