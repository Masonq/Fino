#!/usr/bin/env python3
"""
Проставляет город объявлениям, у которых его нет.

Треть объявлений записана без города, хотя в тексте он есть: район
называют почти всегда — «Земун», «Врачар», «Нови Београд». Для
объявлений это важнее, чем кажется: за диваном на другой конец города не
поедут, и без района человек просто листает дальше.

    python tools/fill-cities.py            # посмотреть, сколько найдётся
    python tools/fill-cities.py --apply    # проставить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_parse import parse  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    args = ap.parse_args()

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.city.is_(None),
                    Listing.status != ListingStatus.archived)
            .all()
        )

        found = Counter()
        changes = []
        for listing, translation in rows:
            # Разбираем то же, что человек написал: заголовок и описание.
            text = f"{translation.title or ''}\n{translation.description or ''}"
            city = parse(text).get("city")
            if city:
                found[city] += 1
                changes.append((listing, city))

        print(f"объявлений без города: {len(rows)}")
        print(f"город нашёлся у:       {len(changes)}")
        if found:
            print("\nчто нашлось:")
            for city, count in found.most_common(10):
                print(f"  {city:<16} {count}")

        if not changes:
            return
        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        for listing, city in changes:
            listing.city = city
        db.commit()
        print(f"\nпроставлено: {len(changes)}")


if __name__ == "__main__":
    main()
