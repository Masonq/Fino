#!/usr/bin/env python3
"""
Переводит объявления, у которых есть не все три языка.

Публичные переводчики один за другим закрылись, и лента накопилась
одноязычной. Теперь перевод делает нейросеть, но сама она возьмётся
только за новые объявления — старые надо догнать.

    python tools/translate-missing.py            # посмотреть, сколько таких
    python tools/translate-missing.py --limit 200  # перевести двести

Идёт медленно: между запросами к нейросети выдерживается пауза, иначе
бесплатный тариф отвечает отказом. Двести объявлений — примерно полчаса.
Прерывать можно: переведённое сохраняется по ходу.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.translate import LANGS, translate_listing  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def missing(db, limit: int | None = None) -> list[Listing]:
    """Объявления, у которых языков меньше трёх. Живые — первыми."""
    counts = (
        db.query(ListingTranslation.listing_id,
                 func.count(ListingTranslation.language).label("langs"))
        .group_by(ListingTranslation.listing_id)
        .subquery()
    )
    query = (
        db.query(Listing)
        .join(counts, counts.c.listing_id == Listing.id)
        .filter(counts.c.langs < len(LANGS))
        # Сначала то, что видно людям: архив и черновики подождут
        .order_by((Listing.status != ListingStatus.active),
                  Listing.created_at.desc())
    )
    return query.limit(limit).all() if limit else query.all()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="сколько объявлений перевести за раз")
    args = ap.parse_args()

    with SessionLocal() as db:
        pending = missing(db, args.limit)
        total_left = (
            db.query(func.count(func.distinct(ListingTranslation.listing_id)))
            .scalar() or 0
        )

        if not args.limit:
            everything = missing(db)
            by_status = Counter(l.status.value for l in everything)
            print(f"без полного перевода: {len(everything)}")
            for status, count in by_status.most_common():
                print(f"  {status:<20} {count}")
            print("\nПеревести: python tools/translate-missing.py --limit 200")
            return

        print(f"переводим {len(pending)} объявлений "
              f"(всего с переводами: {total_left})")

        done = failed = 0
        for number, listing in enumerate(pending, 1):
            try:
                added = translate_listing(db, listing)
                if added:
                    done += 1
                else:
                    failed += 1
            except Exception as exc:                    # noqa: BLE001
                failed += 1
                print(f"  {listing.id}: {exc}")

            if number % 10 == 0:
                print(f"  {number}/{len(pending)} — переведено {done}, "
                      f"не вышло {failed}")

        print(f"\nготово: переведено {done}, не вышло {failed}")
        if failed:
            print("Не вышедшие — обычно исчерпанный дневной лимит. "
                  "Запустите завтра ещё раз.")


if __name__ == "__main__":
    main()
