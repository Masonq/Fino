#!/usr/bin/env python3
"""
Убирает нелепые цены, записанные пересчётом.

Модель брала число из названия модели — «Odyssey G5 2560», «iPad 10» —
и выдавала его за цену. Автомобиль за 23 евро и ноутбук за 92 выглядят
обманом, и лучше пустая цена, чем такая.

    python tools/fix-absurd-prices.py           # посмотреть
    python tools/fix-absurd-prices.py --apply   # убрать
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.price_ai import _absurd  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.price.isnot(None),
                    Listing.status != ListingStatus.archived)
            .all()
        )

        doomed = []
        for listing, translation in rows:
            currency = (listing.currency.value if listing.currency else "RSD")
            if _absurd(float(listing.price), currency.upper(),
                       translation.title or "", translation.description or ""):
                doomed.append((listing, translation.title, listing.price,
                               currency))

        print(f"объявлений с ценой: {len(rows)}")
        print(f"нелепых:            {len(doomed)}")

        for _, title, price, currency in doomed[:30]:
            sign = "€" if currency.upper() == "EUR" else "RSD"
            print(f"  {int(price):>8} {sign:<4} {(title or '')[:48]}")

        if not doomed:
            return
        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        for listing, _, _, _ in doomed:
            # Пустая цена честнее нелепой: человек хотя бы спросит, а
            # «автомобиль за 23 евро» он сочтёт обманом и уйдёт.
            listing.price = None
        db.commit()
        print(f"\nубрано цен: {len(doomed)}")


if __name__ == "__main__":
    main()
