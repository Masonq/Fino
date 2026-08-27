#!/usr/bin/env python3
"""Печатает каждое объявление по каждому подразделу: заголовок, кусок
описания и результат classify_sub (с пометкой ЛОВИТ/НЕ ЛОВИТ) — чтобы
проверять не только заголовки глазами, но видеть сразу, где алгоритм
и текущее место расходятся, включая случаи, спрятанные в описании."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.database import SessionLocal
from app.core.tg_classify import classify_sub
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
        title = tr.title or ""
        desc = (tr.description or "").replace("\n", " ")[:150]
        text = (tr.title or "") + "\n" + (tr.description or "")
        fresh = classify_sub(parent.slug if parent else "", text)
        mark = "OK" if fresh == sub.slug else f"!= {fresh}"
        by_sub.setdefault(key, []).append((title, desc, mark))

    for key in sorted(by_sub):
        items = by_sub[key]
        print(f"\n=== {key} ({len(items)}) ===")
        for title, desc, mark in items:
            print(f"  [{mark}] {title} :: {desc}")
