"""
Разовый перевод уже загруженных HEIC-фото в WebP с превью.

    python3 -m app.core.convert_heic            показать, что найдено
    python3 -m app.core.convert_heic --apply    перевести

До плагина pillow-heif сервер сохранял HEIC как есть, без превью: такое фото видел только Safari. Здесь находим
их в объявлениях (адрес фото и превью), в сообщениях чатов и в аватарах, переводим в WebP теми же размерами,
что и при загрузке, и меняем ссылки. Исходник не удаляем — вдруг понадобится. Деплой запускает один раз.
"""
import argparse
import os

from PIL import Image
from sqlalchemy import or_

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import ListingPhoto, User
from app.routers.media import MAX_DIM, THUMB_DIM

HEIC = (".heic", ".heif")


def _is_heic(url) -> bool:
    return bool(url) and url.lower().split("?")[0].endswith(HEIC)


def convert_file(url: str) -> tuple[str, str] | None:
    """Переводит файл, на который указывает url, в WebP; возвращает (новый url, url превью) или None."""
    name = url.split("?")[0].rsplit("/", 1)[-1]
    src = os.path.join(settings.media_dir, name)
    if not os.path.exists(src):
        return None
    stem = os.path.splitext(name)[0]
    with Image.open(src) as img:
        img = img.convert("RGB")
        full = img.copy()
        full.thumbnail((MAX_DIM, MAX_DIM))
        full.save(os.path.join(settings.media_dir, f"{stem}.webp"), "WEBP", quality=84, method=4)
        thumb = img.copy()
        thumb.thumbnail((THUMB_DIM, THUMB_DIM))
        thumb.save(os.path.join(settings.media_dir, f"{stem}_thumb.webp"), "WEBP", quality=80, method=4)
    base = url.split("?")[0].rsplit("/", 1)[0]
    return f"{base}/{stem}.webp", f"{base}/{stem}_thumb.webp"


def run(apply: bool = False) -> dict:
    db = SessionLocal()
    stats = {"found": 0, "converted": 0, "missing": 0}
    try:
        photos = db.query(ListingPhoto).filter(or_(*[ListingPhoto.url.ilike(f"%{e}") for e in HEIC])).all()
        users = db.query(User).filter(or_(*[User.avatar_url.ilike(f"%{e}") for e in HEIC])).all()
        try:
            from app.models import Message
            messages = db.query(Message).filter(or_(*[Message.photo_url.ilike(f"%{e}") for e in HEIC])).all()
        except (ImportError, AttributeError):
            messages = []
        stats["found"] = len(photos) + len(users) + len(messages)
        if not apply:
            return stats
        for photo in photos:
            done = convert_file(photo.url)
            if not done:
                stats["missing"] += 1
                continue
            photo.url, photo.thumbnail_url = done
            stats["converted"] += 1
        for user in users:
            done = convert_file(user.avatar_url)
            if not done:
                stats["missing"] += 1
                continue
            user.avatar_url = done[1]
            stats["converted"] += 1
        for message in messages:
            done = convert_file(message.photo_url)
            if not done:
                stats["missing"] += 1
                continue
            message.photo_url = done[0]
            stats["converted"] += 1
        db.commit()
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    result = run(parser.parse_args().apply)
    print(f"HEIC найдено: {result['found']}, переведено: {result['converted']}, файла нет на диске: {result['missing']}")
