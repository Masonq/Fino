#!/usr/bin/env python3
"""
Проставляет attributes.brand и attributes.model у уже существующих
объявлений «Авто» — раньше при импорте из Telegram ни марка, ни модель
не распознавались вовсе, только год/пробег/коробка. Логика распознавания
(_guess_car_brand/_guess_car_model в tg_parse.py) — тот же список марок
и моделей, что и в выпадающих списках на лендинге «Авто», иначе списки
фильтровали бы по пустому полю.

Трогает только объявления из телеграм-чатов и только там, где поле ещё
не проставлено — размещённые через сайт объявления пишут марку/модель
сами на форме публикации, поверх них не пишем.

    python tools/backfill-car-brand.py            # посмотреть, что найдётся
    python tools/backfill-car-brand.py --apply     # применить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_parse import _guess_car_brand, _guess_car_model  # noqa: E402
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
        found_brand = Counter()
        found_model = Counter()
        brand_not_found = 0

        for listing, translation in rows:
            cat = categories.get(listing.category_id)
            parent = categories.get(cat.parent_id) if cat and cat.parent_id else None
            top_slug = parent.slug if parent else (cat.slug if cat else None)
            if top_slug != "auto":
                continue

            existing = listing.attributes or {}
            text = f"{translation.title or ''}\n{translation.description or ''}"

            new_attrs = {}
            brand = existing.get("brand")
            if not brand:
                brand = _guess_car_brand(text)
                if brand:
                    new_attrs["brand"] = brand
                    found_brand[brand] += 1
                else:
                    brand_not_found += 1

            if brand and not existing.get("model"):
                model = _guess_car_model(brand, text)
                if model:
                    new_attrs["model"] = model
                    found_model[f"{brand} {model}"] += 1

            if new_attrs:
                changes.append((listing, translation, new_attrs))

        print(f"объявлений «Авто» (из телеграм-чатов): {len(rows)}")
        print(f"новых марок: {sum(found_brand.values())}, новых моделей: {sum(found_model.values())}, марка не распознана: {brand_not_found}")
        print("\nмарки:")
        for brand, count in found_brand.most_common(30):
            print(f"  {brand}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, translation, new_attrs in changes[:args.show]:
            print(f"  {new_attrs} — {(translation.title or '')[:55]}")

        if not args.apply:
            print("\nэто был сухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, translation, new_attrs in changes:
            attrs = dict(listing.attributes or {})
            attrs.update(new_attrs)
            listing.attributes = attrs

        db.commit()
        print(f"\nобновлено: {len(changes)}")


if __name__ == "__main__":
    main()
