#!/usr/bin/env python3
"""
Проставляет attributes.brand у уже существующих объявлений «Авто» —
раньше при импорте из Telegram марка не распознавалась вовсе, только
год/пробег/коробка. Логика распознавания (_guess_car_brand в
tg_parse.py) взята из общего списка марок, что и в выпадающем списке
на лендинге «Авто» — иначе список фильтровал бы по пустому полю.

Трогает только объявления из телеграм-чатов и только там, где brand
ещё не проставлен — размещённые через сайт объявления пишут марку сами
на форме публикации, поверх них не пишем.

    python tools/backfill-car-brand.py            # посмотреть, что найдётся
    python tools/backfill-car-brand.py --apply     # применить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_parse import _guess_car_brand  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", type=int, default=30)
    args = ap.parse_args()

    with SessionLocal() as db:
        categories = {c.id: c for c in db.query(Category).all()}

        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source.isnot(None))
            .order_by(Listing.created_at.desc())
            .all()
        )

        changes = []
        found = Counter()
        not_found = 0

        for listing, translation in rows:
            cat = categories.get(listing.category_id)
            parent = categories.get(cat.parent_id) if cat and cat.parent_id else None
            top_slug = parent.slug if parent else (cat.slug if cat else None)
            if top_slug != "auto":
                continue
            if (listing.attributes or {}).get("brand"):
                continue

            text = f"{translation.title or ''}\n{translation.description or ''}"
            brand = _guess_car_brand(text)
            if not brand:
                not_found += 1
                continue

            found[brand] += 1
            changes.append((listing, translation, brand))

        print(f"объявлений «Авто» без марки (из телеграм-чатов): {len(changes) + not_found}")
        print(f"распознано: {len(changes)}, не распознано: {not_found}")
        for brand, count in found.most_common(30):
            print(f"  {brand}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, translation, brand in changes[:args.show]:
            print(f"  [{brand}] {(translation.title or '')[:60]}")

        if not args.apply:
            print("\nэто был сухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, translation, brand in changes:
            attrs = dict(listing.attributes or {})
            attrs["brand"] = brand
            listing.attributes = attrs

        db.commit()
        print(f"\nобновлено: {len(changes)}")


if __name__ == "__main__":
    main()
