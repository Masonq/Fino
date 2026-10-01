"""
Фото HEIC с iPhone.

Раньше Pillow HEIC не читал, и сервер сохранял его как есть, без превью: такое фото видел только Safari, а в
Chrome, на Android и на компьютерах оно было битым. Теперь плагин pillow-heif переводит HEIC в WebP с превью,
как любое другое фото; уже загруженные HEIC переводит разовая задача (деплой запускает её один раз).
"""
import asyncio
import io
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pillow_heif = pytest.importorskip("pillow_heif")
from PIL import Image  # noqa: E402
from starlette.datastructures import UploadFile  # noqa: E402

from app.core import convert_heic  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Category, Currency, Listing, ListingPhoto, ListingStatus, User, UserRole  # noqa: E402
from app.routers import media  # noqa: E402


def heic_bytes(size=(1200, 900), color=(30, 160, 110)) -> bytes:
    buffer = io.BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", size, color)).save(buffer, quality=60)
    data = buffer.getvalue()
    assert b"ftyp" in data[:16], "это настоящий HEIC-контейнер"
    return data


def test_an_iphone_heic_upload_becomes_webp_with_a_thumbnail():
    os.makedirs(settings.media_dir, exist_ok=True)
    with SessionLocal() as db:
        user = User(id=uuid.uuid4(), display_name="heic", role=UserRole.buyer, email=f"h{uuid.uuid4().hex[:6]}@x.rs")
        db.add(user)
        db.commit()
        result = asyncio.run(media.upload_photo(file=UploadFile(io.BytesIO(heic_bytes()), filename="IMG_0001.HEIC"), user=user))
    assert result["url"].endswith(".webp") and result["thumbnail_url"].endswith("_thumb.webp")
    full = os.path.join(settings.media_dir, result["url"].rsplit("/", 1)[-1])
    thumb = os.path.join(settings.media_dir, result["thumbnail_url"].rsplit("/", 1)[-1])
    with Image.open(full) as im:
        assert im.format == "WEBP" and max(im.size) <= media.MAX_DIM
    with Image.open(thumb) as im:
        assert max(im.size) <= media.THUMB_DIM


def test_old_heic_photos_are_converted_once_and_links_updated():
    os.makedirs(settings.media_dir, exist_ok=True)
    stem = uuid.uuid4().hex
    with open(os.path.join(settings.media_dir, f"{stem}.heic"), "wb") as f:
        f.write(heic_bytes((800, 600)))
    with SessionLocal() as db:
        owner = User(id=uuid.uuid4(), display_name="old-heic", role=UserRole.buyer, email=f"o{uuid.uuid4().hex[:6]}@x.rs",
                     avatar_url=f"https://plonk.rs/media/{stem}.heic")
        db.add(owner)
        db.flush()
        cat = db.query(Category).first()
        listing = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=cat.id, source_language="ru",
                          status=ListingStatus.active, city="beograd", price=10, currency=Currency.eur)
        db.add(listing)
        db.flush()
        photo = ListingPhoto(listing_id=listing.id, url=f"https://plonk.rs/media/{stem}.heic", thumbnail_url=f"https://plonk.rs/media/{stem}.heic")
        db.add(photo)
        db.commit()
        photo_id, owner_id = photo.id, owner.id
    assert convert_heic.run(apply=False)["found"] >= 2
    stats = convert_heic.run(apply=True)
    assert stats["converted"] >= 2
    with SessionLocal() as db:
        photo = db.get(ListingPhoto, photo_id)
        assert photo.url == f"https://plonk.rs/media/{stem}.webp" and photo.thumbnail_url == f"https://plonk.rs/media/{stem}_thumb.webp"
        assert db.get(User, owner_id).avatar_url.endswith(f"{stem}_thumb.webp")
    assert os.path.exists(os.path.join(settings.media_dir, f"{stem}.heic")), "исходник не удаляем"


def test_requirements_pin_a_pillow_heif_that_works_with_our_pillow():
    req = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text(encoding="utf-8")
    assert "pillow-heif==0.18.0" in req and "Pillow==10.4.0" in req
    deploy = (Path(__file__).resolve().parents[2] / "tools" / "deploy.sh").read_text(encoding="utf-8")
    assert "python3 -m app.core.convert_heic --apply && touch /opt/fino/.heic-converted" in deploy
