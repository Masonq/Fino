#!/usr/bin/env python3
"""Печатает заголовки всех объявлений по каждому подразделу — для
ручного визуального прохода, а не сравнения было/стало (то слепо к
багам, которые были в классификаторе с самого начала)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.database import SessionLocal
from app.models.category import Category
from app.models import Listing, ListingStatus, ListingTranslation

with SessionLocal() as db:
    categories = {c.id: c for c in db.query(Category).all()}
    subs = {c.id: c for c in categories.values() if c.parent_id}
    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation,
              (ListingTranslation.listing_id == Listing.id)
              & (ListingTranslation.language == Listing.source_language))
        .filter(Listing.status != ListingStatus.archived)
        .filter(Listing.external_source.isnot(None))
        .filter(Listing.category_id.in_(subs.keys()))
        .all()
    )
    by_sub = {}
    for l, tr in rows:
        sub = subs[l.category_id]
        parent = categories.get(sub.parent_id)
        key = f"{parent.slug if parent else '?'}/{sub.slug}"
        by_sub.setdefault(key, []).append(tr.title or "")

    for key in sorted(by_sub):
        titles = by_sub[key]
        print(f"\n=== {key} ({len(titles)}) ===")
        for t in titles:
            print(" ", t)
