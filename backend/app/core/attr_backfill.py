"""
Довод переводов характеристик у уже опубликованных объявлений (цвет, материал и т. п. — раньше не переводились).
Запуск на сервере: ./venv/bin/python -m app.core.attr_backfill — без --apply только считает, с --apply переводит и сохраняет.
"""
import sys

from app.core.database import SessionLocal
from app.core.translate import _translate_attributes
from app.models import Listing, ListingStatus


def main(apply: bool) -> None:
    db = SessionLocal()
    rows = db.query(Listing).filter(Listing.status == ListingStatus.active, Listing.attributes.isnot(None)).all()
    touched = 0
    for listing in rows:
        try:
            if _translate_attributes(listing, listing.source_language or "ru"):
                touched += 1
                if apply:
                    db.commit()
                else:
                    db.rollback()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print("пропуск", listing.id, exc)
    print(f"объявлений с новыми переводами характеристик: {touched} из {len(rows)}" + ("" if apply else " (проба, без сохранения)"))


if __name__ == "__main__":
    main("--apply" in sys.argv)
