#!/usr/bin/env python3
"""
То же самое, что backfill-subcategory.py, но на третьем уровне —
пересчитывает по classify_sub2 объявления, которые лежат ровно в
подразделе второго уровня (parts-engine и его четверо соседей внутри
"Запчасти" и т.д.), и раскидывает их по третьему.

Раньше третий уровень существовал только в данных (для лендингов и
картинок), classify_sub2 его не считал вовсе — все объявления,
пришедшие ДО того, как он появился, так и остались на втором уровне.
Этот скрипт — разовая уборка накопившегося; новые объявления, что
приходят через tg_import.py, third-level получают уже при импорте.

    python tools/backfill-subcategory2.py <slug раздела 2 уровня>   # сухой прогон
    python tools/backfill-subcategory2.py <slug> --apply             # применить
    python tools/backfill-subcategory2.py --all                      # сухой прогон по всем сразу
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_classify import classify_sub2, SUB2_KEYWORDS  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def run_for_parent(db, parent2_slug: str, apply: bool, show: int) -> None:
    categories = {c.id: c for c in db.query(Category).all()}
    parent2 = next((c for c in categories.values() if c.slug == parent2_slug), None)
    if not parent2:
        print(f"нет такого подраздела: {parent2_slug}")
        return
    subs3 = {c.id: c for c in categories.values() if c.parent_id == parent2.id}
    if not subs3:
        print(f"{parent2_slug}: третьего уровня нет, пропуск")
        return

    # Только объявления, лежащие РОВНО на втором уровне (сам parent2) —
    # уже разложенные по третьему трогать незачем, это была бы уже не
    # уборка накопившегося, а пересмотр решённого.
    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation,
              (ListingTranslation.listing_id == Listing.id)
              & (ListingTranslation.language == Listing.source_language))
        .filter(Listing.status != ListingStatus.archived)
        .filter(Listing.external_source.isnot(None))
        .filter(Listing.category_id == parent2.id)
        .order_by(Listing.created_at.desc())
        .all()
    )

    changes = []
    moves = Counter()

    for listing, translation in rows:
        text = f"{translation.title or ''}\n{translation.description or ''}"
        fresh_slug = classify_sub2(parent2_slug, text)
        if not fresh_slug:
            continue
        fresh_cat = next((c for c in subs3.values() if c.slug == fresh_slug), None)
        if not fresh_cat:
            continue
        moves[f"{parent2_slug} -> {fresh_slug}"] += 1
        changes.append((listing, fresh_cat, translation))

    print(f"\n=== {parent2_slug} === объявлений без третьего уровня: {len(rows)}")
    print(f"переедет: {len(changes)}")
    for move, count in moves.most_common(20):
        print(f"  {move}: {count}")
    if changes:
        print(f"  примеры (первые {show}):")
        for listing, fresh_cat, translation in changes[:show]:
            title = (translation.title or "")[:60]
            print(f"    [-> {fresh_cat.slug}] {title}")

    if apply and changes:
        for listing, fresh_cat, translation in changes:
            listing.category_id = fresh_cat.id
        db.commit()
        print(f"  обновлено: {len(changes)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("parent2_slug", nargs="?", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", type=int, default=25)
    args = ap.parse_args()

    with SessionLocal() as db:
        if args.all:
            for slug in SUB2_KEYWORDS:
                run_for_parent(db, slug, args.apply, args.show)
        elif args.parent2_slug:
            run_for_parent(db, args.parent2_slug, args.apply, args.show)
        else:
            print("Укажи подраздел 2 уровня (напр. car-parts) или --all")


if __name__ == "__main__":
    main()
