#!/usr/bin/env python3
"""
Проставляет цену объявлениям, у которых её нет.

Цену часто пишут голым числом в начале строки: «2000 Аутокоманда»,
«8000 за 2 стула». Разбор их не брал, и объявление уходило в ленту с
пустым ценником — а по такому не звонят.

    python tools/fill-prices.py            # посмотреть, сколько найдётся
    python tools/fill-prices.py --apply    # проставить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_parse import extract_price  # noqa: E402
from app.models import (  # noqa: E402
    Currency, Listing, ListingStatus, ListingTranslation,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="записать")
    ap.add_argument("--show", type=int, default=12)
    args = ap.parse_args()

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.price.is_(None),
                    Listing.is_free.is_(False),
                    Listing.status != ListingStatus.archived)
            .all()
        )

        found, changes = Counter(), []
        for listing, translation in rows:
            text = f"{translation.title or ''}\n{translation.description or ''}"
            price, currency = extract_price(text)
            if price:
                found[currency or "RSD"] += 1
                changes.append((listing, price, currency or "RSD"))

        print(f"объявлений без цены: {len(rows)}")
        print(f"цена нашлась у:      {len(changes)}")
        if found:
            print("\nв какой валюте:")
            for currency, count in found.most_common():
                print(f"  {currency:<6} {count}")

        if changes:
            print(f"\nпримеры (первые {args.show}):")
            for listing, price, currency in changes[:args.show]:
                title = next(
                    (t.title for t in listing.translations
                     if t.language == listing.source_language), "")
                print(f"  {int(price):>8} {currency}  {title[:52]}")

        if not changes:
            return
        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        for listing, price, currency in changes:
            listing.price = price
            # Доллары у нас не хранятся: в Белграде торгуют в динарах и
            # евро, а доллар пишут по привычке. Считаем его евро — это
            # ближе к истине, чем динары.
            listing.currency = Currency.eur if currency in ("EUR", "USD") \
                else Currency.rsd
        db.commit()
        print(f"\nпроставлено: {len(changes)}")


if __name__ == "__main__":
    main()
