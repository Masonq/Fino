#!/usr/bin/env python3
"""
Правит адрес в ссылках на снимки.

Ссылки складываются из адреса, записанного в настройках. Стоит его
поменять — и снимки, сохранённые раньше, перестают находиться: страница
ищет их там, где их нет.

    python tools/fix-photo-urls.py http://89.208.113.147:8002
    python tools/fix-photo-urls.py http://89.208.113.147:8002 --apply

Без --apply только показывает, что изменится.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.models import ListingPhoto  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="адрес, по которому отдаются снимки")
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    with SessionLocal() as db:
        photos = db.query(ListingPhoto).all()
        wrong = [p for p in photos
                 if p.url and not p.url.startswith(base + "/media/")]

        print(f"снимков всего:      {len(photos)}")
        print(f"с чужим адресом:    {len(wrong)}")
        if wrong:
            print(f"\nбыло:  {wrong[0].url}")
            print(f"будет: {base}/media/{wrong[0].url.rsplit('/', 1)[-1]}")

        if not wrong:
            return
        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        for photo in wrong:
            for field in ("url", "thumbnail_url"):
                link = getattr(photo, field, None)
                if link:
                    setattr(photo, field, f"{base}/media/{link.rsplit('/', 1)[-1]}")
        db.commit()
        print(f"\nисправлено: {len(wrong)}")


if __name__ == "__main__":
    main()
