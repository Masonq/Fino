#!/usr/bin/env python3
"""
Убирает фотографии, на которые не ссылается ни одно объявление.

Снимки скачиваются раньше, чем становится ясно, попадёт ли объявление в
ленту: дубль виден только при записи, чужой водяной знак — на третьем
кадре из пяти. Всё, что успели сохранить до отказа, оставалось на диске
навсегда.

Теперь заход убирает за собой сам, но накопленное за прежние месяцы лежит
на месте. Этот сценарий его находит и удаляет.

    python tools/clean-media.py           # показать, сколько лишнего
    python tools/clean-media.py --apply   # удалить

Без --apply ничего не трогает.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.listing import ListingPhoto  # noqa: E402


def used_names(db) -> set[str]:
    """Имена файлов, на которые ссылаются объявления."""
    names = set()
    for url, thumb in db.query(ListingPhoto.url, ListingPhoto.thumbnail_url).all():
        for link in (url, thumb):
            if link:
                names.add(link.rsplit("/", 1)[-1])
    return names


# Фото загружаются на сервер сразу при выборе в форме создания
# объявления — раньше самой публикации, пока человек ещё дописывает
# описание и цену. В это окно файл уже на диске, а ListingPhoto в базе
# появится только на финальной отправке — без запаса по возрасту заход
# посреди чужого черновика стёр бы фото прямо из-под человека. Несколько
# часов с запасом на самую медленную заполненную форму.
MIN_AGE_HOURS = 6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="удалить лишнее; без него только показывает")
    args = ap.parse_args()

    media = Path(settings.media_dir)
    if not media.exists():
        raise SystemExit(f"Папки со снимками нет: {media}")

    with SessionLocal() as db:
        used = used_names(db)

    cutoff = time.time() - MIN_AGE_HOURS * 3600
    total = orphan = skipped_fresh = 0
    freed = 0
    victims: list[Path] = []
    for path in media.iterdir():
        if not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".mp4"):
            continue
        total += 1
        if path.name in used:
            continue
        if path.stat().st_mtime > cutoff:
            # Свежее MIN_AGE_HOURS — может быть чей-то ещё не
            # отправленный черновик, не трогаем.
            skipped_fresh += 1
            continue
        orphan += 1
        freed += path.stat().st_size
        victims.append(path)

    print(f"снимков на диске:      {total}")
    print(f"ничьих:                {orphan}")
    if skipped_fresh:
        print(f"свежих (пропущены):    {skipped_fresh}  (младше {MIN_AGE_HOURS} ч)")
    print(f"занимают:              {freed / 1024 / 1024:.1f} МБ")

    if not victims:
        return
    if not args.apply:
        print("\n  (ничего не удалено — добавьте --apply)")
        return

    removed = 0
    for path in victims:
        try:
            os.remove(path)
            removed += 1
        except OSError as exc:
            print(f"  не удалось удалить {path.name}: {exc}")
    print(f"\nудалено: {removed}")


if __name__ == "__main__":
    main()
