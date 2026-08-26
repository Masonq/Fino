#!/usr/bin/env python3
"""
Удаляет объявления, которые не годятся для сайта.

Кривой заголовок — «Hutschenreuther», «Времени суток», «Наш капитан
поможет» — это обрубок из чата, а не объявление. Держать их незачем: в
ленту они не попадают, а в поиске только мешают.

    python tools/drop-broken.py           # показать, что удалится
    python tools/drop-broken.py --apply   # удалить

Удаление необратимо, поэтому без --apply сценарий только показывает
список. Снимки тоже убираются — иначе они останутся лежать ничьими.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Listing, ListingPhoto, ListingStatus, ListingTranslation,
)
from app.routers.listings import title_is_clear  # noqa: E402


def broken(db):
    """Объявления с негодным заголовком."""
    rows = (
        db.query(Listing, ListingTranslation.title)
        .join(ListingTranslation,
              (ListingTranslation.listing_id == Listing.id)
              & (ListingTranslation.language == Listing.source_language))
        .filter(Listing.status != ListingStatus.archived)
        .all()
    )
    return [(listing, title) for listing, title in rows
            if not title_is_clear(title)]


def forget_photos(db, listing_id) -> int:
    """
    Убирает снимки объявления с диска.

    Иначе они остаются лежать ничьими: место занято, а показать их
    больше негде.
    """
    dropped = 0
    photos = db.query(ListingPhoto).filter(
        ListingPhoto.listing_id == listing_id).all()

    for photo in photos:
        for link in (photo.url, photo.thumbnail_url):
            if not link:
                continue
            name = link.rsplit("/", 1)[-1]
            path = os.path.join(settings.media_dir, name)
            try:
                os.remove(path)
                dropped += 1
            except OSError:
                pass
    return dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="удалить (необратимо)")
    ap.add_argument("--show", type=int, default=25,
                    help="сколько заголовков показать")
    args = ap.parse_args()

    with SessionLocal() as db:
        doomed = broken(db)
        total = db.query(Listing).filter(
            Listing.status != ListingStatus.archived).count()

        print(f"объявлений всего:   {total}")
        print(f"негодных:           {len(doomed)}")
        if not doomed:
            return

        print(f"\nчто удалится (первые {args.show}):")
        for listing, title in doomed[:args.show]:
            print(f"  {title[:70]}")

        if not args.apply:
            print("\n  Ничего не удалено. Проверьте список — удаление")
            print("  необратимо. Затем добавьте --apply.")
            return

        from sqlalchemy import text

        photos_dropped = 0
        for listing, _ in doomed:
            photos_dropped += forget_photos(db, listing.id)

            # На объявление ссылаются девять таблиц: избранное, чаты,
            # жалобы, отзывы. Без их уборки база не даст удалить —
            # ссылка в никуда хуже мусорного объявления.
            for table in ("listing_photos", "listing_translations",
                          "favorites", "chats", "reports", "reviews",
                          "review_invites", "promotions", "tickets"):
                db.execute(
                    text(f"DELETE FROM {table} WHERE listing_id = :id"),
                    {"id": str(listing.id)},
                )
            db.delete(listing)
        db.commit()

        print(f"\nудалено объявлений: {len(doomed)}")
        print(f"убрано снимков:     {photos_dropped}")
        print(f"осталось:           {total - len(doomed)}")


if __name__ == "__main__":
    main()
