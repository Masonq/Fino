#!/usr/bin/env python3
"""
Пересобирает миниатюры из полных снимков.

Миниатюры делались в 400 точек, а карточка в ленте на плотном экране
просит около 570 настоящих пикселей: картинку растягивали, и фотография
выглядела мыльной. Новые объявления сохраняются правильно, но накопленные
надо пересобрать — полные снимки лежат рядом, так что скачивать заново
ничего не нужно.

    python tools/rebuild-thumbs.py            # посмотреть, сколько мелких
    python tools/rebuild-thumbs.py --apply    # пересобрать

Идёт быстро: пара тысяч снимков — минуты. Полные снимки не трогаются.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from PIL import Image  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.tg_import import THUMB_DIM  # noqa: E402

QUALITY = 82


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="пересобрать; без него только считает")
    args = ap.parse_args()

    media = Path(settings.media_dir)
    if not media.exists():
        raise SystemExit(f"Папки со снимками нет: {media}")

    small: list[Path] = []
    for thumb in media.glob("*_thumb.jpg"):
        try:
            with Image.open(thumb) as img:
                if max(img.size) < THUMB_DIM:
                    small.append(thumb)
        except Exception:                       # noqa: BLE001
            continue

    print(f"миниатюр мельче {THUMB_DIM} точек: {len(small)}")
    if not small:
        return
    if not args.apply:
        print("\n  (ничего не изменено — добавьте --apply)")
        return

    done = skipped = 0
    for number, thumb in enumerate(small, 1):
        # Полный снимок лежит рядом под тем же именем без «_thumb»
        full = thumb.with_name(thumb.name.replace("_thumb", ""))
        if not full.exists():
            skipped += 1
            continue
        try:
            with Image.open(full) as img:
                img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
                # Если и полный снимок мелкий, лучше оставить как есть:
                # растянуть его — та же мыльность, только тяжелее.
                if max(img.size) < THUMB_DIM:
                    skipped += 1
                    continue
                img.thumbnail((THUMB_DIM, THUMB_DIM))
                img.save(thumb, "JPEG", quality=QUALITY, optimize=True)
            done += 1
        except Exception as exc:                # noqa: BLE001
            skipped += 1
            print(f"  {thumb.name}: {exc}")

        if number % 200 == 0:
            print(f"  {number}/{len(small)}…")

    print(f"\nпересобрано: {done}, пропущено: {skipped}")
    if skipped:
        print("Пропущенные — те, у кого полный снимок мелкий или потерян.")


if __name__ == "__main__":
    main()
