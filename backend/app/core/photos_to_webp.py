"""
Пережимает уже лежащие фото из JPEG в WebP.

Новые фото сохраняются в WebP с момента правки в media.py, а старые —
тысячи файлов — остались в JPEG. Тот же кадр в WebP весит на
четверть-треть меньше при том же виде; лента из двадцати карточек это
двадцать превью, и на мобильном интернете разница ощутима.

Работает порциями и безопасно: файл сперва сохраняется в WebP, ссылки в
базе переводятся на него, и только потом старый JPEG удаляется. Упало
посередине — ничего не потеряно: у объявления либо старая ссылка на
живой JPEG, либо новая на живой WebP.

Запуск:
    python3 -m app.core.photos_to_webp             # только показать
    python3 -m app.core.photos_to_webp --apply     # пережать порцию
    python3 -m app.core.photos_to_webp --apply --limit 500
"""
import argparse
import os

from PIL import Image
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal

PENDING = """
    select id, url, thumbnail_url from listing_photos
    where (url like '%.jpg' or url like '%.jpeg')
      and is_video is not true
    order by id
    limit :limit
"""


def _local(url: str) -> str:
    return os.path.join(settings.media_dir, url.rsplit("/", 1)[-1])


def _to_webp(path: str, quality: int) -> str | None:
    """Сохраняет рядом .webp и возвращает его путь; None — если не вышло."""
    if not os.path.exists(path):
        return None
    target = os.path.splitext(path)[0] + ".webp"
    try:
        with Image.open(path) as img:
            img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
            img.save(target, "WEBP", quality=quality, method=4)
        return target
    except Exception:                                      # noqa: BLE001
        return None


def run(apply: bool, limit: int) -> None:
    with SessionLocal() as db:
        rows = db.execute(text(PENDING), {"limit": limit}).fetchall()
        total = db.execute(text(
            "select count(*) from listing_photos where url like '%.jp%g' "
            "and is_video is not true")).scalar()
        print(f"осталось в JPEG: {total}, в этой порции: {len(rows)}")

        if not apply:
            print("это был показ, ничего не изменено. Для пережатия добавьте --apply")
            return

        done = skipped = 0
        before = after = 0
        for photo_id, url, thumb_url in rows:
            full_src = _local(url)
            thumb_src = _local(thumb_url) if thumb_url else None

            full_dst = _to_webp(full_src, 84)
            thumb_dst = _to_webp(thumb_src, 80) if thumb_src and thumb_src != full_src else full_dst
            if not full_dst or not thumb_dst:
                skipped += 1
                continue

            before += os.path.getsize(full_src) + (
                os.path.getsize(thumb_src) if thumb_src and thumb_src != full_src else 0)
            after += os.path.getsize(full_dst) + (
                os.path.getsize(thumb_dst) if thumb_dst != full_dst else 0)

            new_url = url.rsplit(".", 1)[0] + ".webp"
            new_thumb = (thumb_url.rsplit(".", 1)[0] + ".webp") if thumb_url else new_url
            db.execute(text(
                "update listing_photos set url = :u, thumbnail_url = :t where id = :i"),
                {"u": new_url, "t": new_thumb, "i": photo_id})
            db.commit()

            # Старые файлы — только после того, как ссылки уже смотрят
            # на новые.
            for old in {full_src, thumb_src} - {None}:
                try:
                    os.remove(old)
                except OSError:
                    pass
            done += 1

        saved = before - after
        print(f"пережато: {done}, пропущено (файла нет или не читается): {skipped}")
        if before:
            print(f"было {before // 1024} КБ, стало {after // 1024} КБ — "
                  f"меньше на {saved * 100 // before}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    run(args.apply, args.limit)
