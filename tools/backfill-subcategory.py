#!/usr/bin/env python3
"""
То же самое, что backfill-electronics-sub.py, но для любого раздела —
пересчитывает подкатегорию по текущим правилам classify_sub и
показывает/применяет расхождения. Раздел без подраздела (None) тоже
считается расхождением, если сейчас объявление лежит в каком-то
подразделе — «нет уверенности» означает «не должно быть в подразделе
вовсе», а не «оставить как есть».

    python tools/backfill-subcategory.py <slug раздела>              # сухой прогон
    python tools/backfill-subcategory.py <slug раздела> --apply       # применить
    python tools/backfill-subcategory.py --all                        # сухой прогон по всем разделам сразу
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_classify import classify_sub, SUB_KEYWORDS  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def run_for_parent(db, parent_slug: str, apply: bool, show: int) -> None:
    categories = {c.id: c for c in db.query(Category).all()}
    parent = next((c for c in categories.values() if c.slug == parent_slug), None)
    if not parent:
        print(f"нет такого раздела: {parent_slug}")
        return
    subs = {c.id: c for c in categories.values() if c.parent_id == parent.id}
    if not subs:
        print(f"{parent_slug}: подразделов нет, пропуск")
        return

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation,
              (ListingTranslation.listing_id == Listing.id)
              & (ListingTranslation.language == Listing.source_language))
        .filter(Listing.status != ListingStatus.archived)
        .filter(Listing.external_source.isnot(None))
        .filter(Listing.category_id.in_(subs.keys()))
        .order_by(Listing.created_at.desc())
        .all()
    )

    changes = []
    moves = Counter()

    for listing, translation in rows:
        current_sub = subs[listing.category_id]
        text = f"{translation.title or ''}\n{translation.description or ''}"
        fresh_slug = classify_sub(parent_slug, text)

        if fresh_slug == current_sub.slug:
            continue
        if not fresh_slug:
            moves[f"{current_sub.slug} -> {parent_slug} (без подраздела)"] += 1
            changes.append((listing, translation, current_sub.slug, parent))
            continue

        fresh_cat = next((c for c in subs.values() if c.slug == fresh_slug), None)
        if not fresh_cat:
            continue
        moves[f"{current_sub.slug} -> {fresh_slug}"] += 1
        changes.append((listing, translation, current_sub.slug, fresh_cat))

    print(f"\n=== {parent_slug} === объявлений в подразделах (из телеграм-чатов): {len(rows)}")
    print(f"изменится: {len(changes)}")
    for move, count in moves.most_common(20):
        print(f"  {move}: {count}")
    if changes:
        print(f"  примеры (первые {show}):")
        for listing, translation, old_slug, fresh_cat in changes[:show]:
            title = (translation.title or "")[:60]
            print(f"    [{old_slug} -> {fresh_cat.slug}] {title}")

    if apply and changes:
        for listing, translation, old_slug, fresh_cat in changes:
            listing.category_id = fresh_cat.id
        db.commit()
        print(f"  обновлено: {len(changes)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("parent_slug", nargs="?", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", type=int, default=25)
    args = ap.parse_args()

    with SessionLocal() as db:
        if args.all:
            for slug in SUB_KEYWORDS:
                run_for_parent(db, slug, args.apply, args.show)
        elif args.parent_slug:
            run_for_parent(db, args.parent_slug, args.apply, args.show)
        else:
            print("Укажи раздел (напр. auto) или --all")


if __name__ == "__main__":
    main()
