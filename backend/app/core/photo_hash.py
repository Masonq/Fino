"""
Одно и то же фото у разных продавцов — перцептивный хеш (dHash).

Мошенники берут чужие фото — с других сайтов и из чужих объявлений. Обычный хеш файла меняется от любой правки
(пересжали, уменьшили, обрезали подпись), поэтому он ловит только побайтные копии. dHash сравнивает яркость
соседних точек уменьшенной картинки 9×8: похожие на вид фото дают хеши, отличающиеся на несколько бит из 64.
Это тот же алгоритм, что difference hash в библиотеке imagehash, только на Pillow и numpy, которые уже стоят, —
без тяжёлых scipy и PyWavelets.

Хеш считается сам при сохранении любого фото объявления (событие before_insert: сайт, публикатор в Telegram,
импорт). Для уже загруженных — python3 -m app.core.photo_hash --apply (деплой запускает в фоне).
Тревога в админке: похожие фото (расстояние ≤ MAX_DISTANCE) у разных владельцев среди живых объявлений.
"""
import argparse
import os
from datetime import timedelta

import numpy as np
from PIL import Image
from sqlalchemy import event

from app.core.clock import utcnow
from app.core.config import settings
from app.models import Listing, ListingPhoto, ListingStatus

MAX_DISTANCE = 6
BANDS = 4                                    # 64 бита = 4 полосы по 16: похожие почти наверняка совпадут хоть в одной


def dhash_image(img: Image.Image) -> str:
    small = np.asarray(img.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def local_path(url: str | None) -> str | None:
    if not url or "/media/" not in url:
        return None
    path = os.path.join(settings.media_dir, url.split("?")[0].rsplit("/", 1)[-1])
    return path if os.path.exists(path) else None


def dhash_url(url: str | None) -> str | None:
    path = local_path(url)
    if not path:
        return None
    try:
        with Image.open(path) as img:
            return dhash_image(img)
    except Exception:  # noqa: BLE001 — битый файл не должен ломать сохранение объявления
        return None


def distance(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def informative(h: str) -> bool:
    """Однотонная картинка (заглушка, белый лист) даёт почти пустой хеш — по нему похожими оказались бы все."""
    ones = bin(int(h, 16)).count("1")
    return 6 <= ones <= 58


@event.listens_for(ListingPhoto, "before_insert")
def _hash_on_insert(mapper, connection, photo):  # noqa: ARG001
    if photo.dhash is None:
        photo.dhash = dhash_url(photo.thumbnail_url or photo.url)


def fill_missing(db, limit: int = 2000) -> int:
    done = 0
    for photo in db.query(ListingPhoto).filter(ListingPhoto.dhash.is_(None)).limit(limit):
        h = dhash_url(photo.thumbnail_url or photo.url)
        if h:
            photo.dhash = h
            done += 1
    db.commit()
    return done


def find_reuse(db, days: int = 30, limit: int = 10) -> list[dict]:
    """Пары живых объявлений разных владельцев с похожими фото: самые похожие первыми."""
    since = utcnow() - timedelta(days=days)
    rows = (db.query(ListingPhoto.dhash, Listing.id, Listing.owner_id)
            .join(Listing, Listing.id == ListingPhoto.listing_id)
            .filter(ListingPhoto.dhash.isnot(None), Listing.status == ListingStatus.active, Listing.created_at >= since)
            .all())
    buckets: dict[tuple[int, str], list[tuple[str, object, object]]] = {}
    for h, listing_id, owner_id in rows:
        if not informative(h):
            continue
        for band in range(BANDS):
            buckets.setdefault((band, h[band * 4:(band + 1) * 4]), []).append((h, listing_id, owner_id))
    pairs: dict[tuple, int] = {}
    for group in buckets.values():
        if len(group) < 2 or len(group) > 200:          # огромная корзина — общий фон, не находка
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                (ha, la, oa), (hb, lb, ob) = group[i], group[j]
                if oa == ob or la == lb:
                    continue
                d = distance(ha, hb)
                if d <= MAX_DISTANCE:
                    key = tuple(sorted((str(la), str(lb))))
                    pairs[key] = min(d, pairs.get(key, 99))
    found = sorted(pairs.items(), key=lambda kv: kv[1])[:limit]
    return [{"listing_id": a, "other_id": b, "distance": d} for (a, b), d in found]


if __name__ == "__main__":
    from app.core.database import SessionLocal

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as session:
        missing = session.query(ListingPhoto).filter(ListingPhoto.dhash.is_(None)).count()
        filled = fill_missing(session) if args.apply else 0
        found = find_reuse(session)
        print(f"фото без хеша: {missing}, посчитано: {filled}; пар похожих фото у разных продавцов: {len(found)}")
