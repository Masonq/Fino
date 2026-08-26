#!/usr/bin/env python3
"""
Ищет цены, выбивающиеся из ряда.

«Стол за 500 000 динар» проходит все прежние проверки: число в тексте
есть, нижней границы у столов нет. Но соседи знают: если два десятка
столов стоят от трёх до пятнадцати тысяч, где-то ошибка — приписан
лишний ноль или взято не то число.

Ничего не меняет: показывает список, а решать человеку. Цена бывает и
верной — дизайнерский стол дороже обычного вдесятеро.

    python tools/check-prices.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.price_sanity import is_outlier, median_price  # noqa: E402
from app.models import (  # noqa: E402
    Listing, ListingStatus, ListingTranslation,
)


def money(value, currency) -> str:
    sign = "€" if str(currency).lower().endswith("eur") else "RSD"
    return f"{int(value):,}".replace(",", " ") + f" {sign}"


def main() -> None:
    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation.title)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.price.isnot(None),
                    Listing.status == ListingStatus.active)
            .all()
        )

        # Медиану считаем по разделу и валюте разом: пересчитывать её
        # для каждого объявления значило бы тысячу запросов вместо
        # десятка.
        medians = {}
        found = []

        for listing, title in rows:
            key = (listing.category_id, listing.currency)
            if key not in medians:
                medians[key] = median_price(db, *key)

            side = is_outlier(float(listing.price), medians[key])
            if side:
                found.append((listing, title, side, medians[key]))

        print(f"объявлений с ценой: {len(rows)}")
        print(f"выбивается из ряда: {len(found)}")

        if not found:
            return

        print()
        for listing, title, side, median in sorted(
                found, key=lambda x: -float(x[0].price)):
            currency = listing.currency.value if listing.currency else ""
            print(f"  {money(listing.price, currency):>14} "
                  f"({side} медианы {money(median, currency)})  "
                  f"{(title or '')[:40]}")

        print("\n  Ничего не изменено: цена бывает и верной —")
        print("  дизайнерский стол дороже обычного вдесятеро.")


if __name__ == "__main__":
    main()
