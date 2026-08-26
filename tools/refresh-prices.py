#!/usr/bin/env python3
"""
Пересчитывает цены накопленных объявлений.

Правила разбора чинились не раз: MacBook за 2200 считался динарами,
размер «р.37» становился ценой, голое число в начале строки не бралось
вовсе. Записанные цены от этого не поменялись — их нужно пересчитать.

Заголовки не трогаем: они местами написаны нейросетью и лучше, чем даёт
разбор. Переразбор их только испортит.

    python tools/refresh-prices.py            # что изменится
    python tools/refresh-prices.py --apply    # применить
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


def money(value, currency) -> str:
    if value is None:
        return "—"
    sign = "€" if str(currency).lower().endswith("eur") else "RSD"
    return f"{int(value):,}".replace(",", " ") + f" {sign}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="записать")
    ap.add_argument("--show", type=int, default=25)
    args = ap.parse_args()

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .all()
        )

        changes = []
        kinds = Counter()

        for listing, translation in rows:
            text = f"{translation.title or ''}\n{translation.description or ''}"
            price, currency = extract_price(text)

            was_price = float(listing.price) if listing.price else None
            was_currency = (listing.currency.value
                            if listing.currency else None)

            if price is None:
                continue                         # цену не нашли — не трогаем
            if was_price == price and (was_currency or "").upper() == (currency or "RSD"):
                continue

            # Что именно поменялось — чтобы видеть, чинит ли правка то,
            # ради чего затевалась.
            if was_price is None:
                kinds["цена появилась"] += 1
            elif was_price != price:
                kinds["цена другая"] += 1
            else:
                kinds["валюта другая"] += 1

            changes.append((listing, translation, was_price, was_currency,
                            price, currency or "RSD"))

        print(f"объявлений:   {len(rows)}")
        print(f"изменится:    {len(changes)}")
        if kinds:
            print()
            for kind, count in kinds.most_common():
                print(f"  {kind:<18} {count}")

        if changes:
            print(f"\nпримеры (первые {args.show}):")
            for _, tr, was_p, was_c, price, currency in changes[:args.show]:
                print(f"  {money(was_p, was_c):>12} → {money(price, currency):<12}"
                      f"  {(tr.title or '')[:44]}")

        if not changes:
            return
        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        for listing, _, _, _, price, currency in changes:
            listing.price = price
            # Доллары не храним: в Белграде торгуют в динарах и евро, а
            # доллар пишут по привычке. Считаем его евро.
            listing.currency = (Currency.eur if currency in ("EUR", "USD")
                                else Currency.rsd)
            listing.is_free = False
        db.commit()

        print(f"\nпересчитано: {len(changes)}")


if __name__ == "__main__":
    main()
