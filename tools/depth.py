#!/usr/bin/env python3
"""
Показывает глубину по разделам.

Маркетплейсы начинают с узкого рынка не из скромности: человек,
зашедший за коляской и увидевший три объявления, не возвращается.
OpenTable выяснил, что нужно 50-100 предложений в одной зоне — тогда
поиск даёт достаточно, чтобы решить задачу.

Раздел с тремя объявлениями хуже, чем его отсутствие: он обещает выбор
и не даёт его.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models import Category, Listing, ListingStatus  # noqa: E402

# Ниже этого числа раздел пустует: поиск в нём почти ничего не даёт.
ENOUGH = 50


def name_of(value) -> str:
    if isinstance(value, dict):
        return value.get("ru") or next(iter(value.values()), "")
    return str(value or "")


with SessionLocal() as db:
    rows = (
        db.query(Category.name, Category.parent_id,
                 func.count(Listing.id),
                 func.count(Listing.id).filter(Listing.is_complete.is_(True)))
        .outerjoin(Listing, (Listing.category_id == Category.id)
                   & (Listing.status == ListingStatus.active))
        .group_by(Category.id, Category.name, Category.parent_id)
        .all()
    )

    top = [(name_of(n), total, full) for n, parent, total, full in rows
           if parent is None]
    top.sort(key=lambda x: -x[2])

    print(f"{'раздел':<28} {'всего':>7} {'полных':>7}")
    print("─" * 46)
    for name, total, full in top:
        mark = "" if full >= ENOUGH else "   ← пусто"
        print(f"{name[:28]:<28} {total:>7} {full:>7}{mark}")

    ready = sum(1 for _, _, full in top if full >= ENOUGH)
    print("─" * 46)
    print(f"разделов с выбором: {ready} из {len(top)}")
    print(f"\n  Раздел с тремя объявлениями хуже, чем его отсутствие:")
    print(f"  он обещает выбор и не даёт его.")
