#!/usr/bin/env python3
"""
Разбирает объявления заново: заголовок, цена, описание — за один вызов.

Раньше это делалось по частям, и каждая часть промахивалась своим
способом: в цене всплывало разрешение экрана, в заголовке первая
строка, в описании оставалось «подробнее на моём канале».

Модель видит объявление целиком и отвечает по строгой схеме. Всё, что
она вернула, проверяется: цена должна быть в тексте и быть похожей на
цену, заголовок — называть предмет, описание — не длиннее исходного.

    python tools/refresh-listings.py --limit 20    # посмотреть
    python tools/refresh-listings.py --apply       # применить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.listing_ai import parse, refused  # noqa: E402
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
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()

    with SessionLocal() as db:
        query = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .order_by(Listing.created_at.desc())
        )
        if args.limit:
            query = query.limit(args.limit)
        rows = query.all()

        kinds = Counter()
        changes = []

        for number, (listing, translation) in enumerate(rows, 1):
            old_title = translation.title or ""
            old_body = translation.description or ""

            got = parse(old_title, old_body)
            if not got:
                continue

            what = []
            if "title" in got and got["title"] != old_title:
                what.append("заголовок")
            if "price" in got:
                was = float(listing.price) if listing.price else None
                if was != got["price"]:
                    what.append("цена")
            if "description" in got and got["description"] != old_body:
                what.append("описание")

            if not what:
                continue

            for kind in what:
                kinds[kind] += 1
            changes.append((listing, translation, got, what))

            if number % 20 == 0:
                print(f"  разобрано {number} из {len(rows)}…")

        print(f"\nобъявлений: {len(rows)}")
        print(f"изменится:  {len(changes)}")
        for kind, count in kinds.most_common():
            print(f"  {kind:<12} {count}")

        # Что отвергли и почему. Одно общее число не покажет, где
        # модель промахивается чаще — а значит, что уточнять.
        rejected = {k: v for k, v in refused.items() if v}
        if rejected:
            print("\nотвергнуто моделью:")
            for kind, count in sorted(rejected.items(), key=lambda x: -x[1]):
                print(f"  {kind:<22} {count}")

        if changes:
            print(f"\nпримеры (первые {args.show}):")
            for listing, tr, got, what in changes[:args.show]:
                print(f"\n  {(tr.title or '')[:60]}")
                if "title" in what:
                    print(f"    → {got['title'][:60]}")
                if "цена" in what:
                    was = money(listing.price,
                                listing.currency.value if listing.currency else "")
                    print(f"    {was} → {money(got['price'], got['currency'])}")
                if "описание" in what:
                    was_len = len(tr.description or "")
                    print(f"    описание: {was_len} → {len(got['description'])} знаков")

        if not changes:
            return
        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        for listing, translation, got, _ in changes:
            if "title" in got:
                translation.title = got["title"]
            if "description" in got:
                translation.description = got["description"]
            if "price" in got:
                listing.price = got["price"]
                listing.currency = (Currency.eur if got["currency"] == "EUR"
                                    else Currency.rsd)
                listing.is_free = False
        db.commit()

        print(f"\nразобрано заново: {len(changes)}")


if __name__ == "__main__":
    main()
