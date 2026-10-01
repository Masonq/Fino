"""
Одно фото у разных продавцов: перцептивный хеш (dHash).

Обычный хеш файла ловит только побайтные копии; перепрошитое или уменьшенное чужое фото проходило. Старая тревога
«same_photo» вдобавок работала только для импорта из чатов, а импорт выключен — по сути ничего не ловила.
"""
import io
import os
import sys
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import photo_hash  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Category, Currency, Listing, ListingPhoto, ListingStatus, User, UserRole  # noqa: E402


def photo(seed: int, size=(800, 600)) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, (12, 16, 3), dtype=np.uint8)
    return Image.fromarray(base).resize(size, Image.BICUBIC)


def saved(img: Image.Image, fmt="WEBP", quality=80) -> str:
    os.makedirs(settings.media_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ 'webp' if fmt == 'WEBP' else 'jpg'}"
    img.save(os.path.join(settings.media_dir, name), fmt, quality=quality)
    return f"https://plonk.rs/media/{name}"


def test_the_same_photo_recompressed_and_shrunk_stays_close_and_other_photos_are_far():
    a = photo(1)
    copy = a.resize((400, 300)).filter(ImageFilter.GaussianBlur(0.6))
    buffer = io.BytesIO()
    copy.convert("RGB").save(buffer, "JPEG", quality=45)
    copy = Image.open(io.BytesIO(buffer.getvalue()))
    assert photo_hash.distance(photo_hash.dhash_image(a), photo_hash.dhash_image(copy)) <= photo_hash.MAX_DISTANCE
    assert photo_hash.distance(photo_hash.dhash_image(a), photo_hash.dhash_image(photo(2))) > 12


def test_uniform_pictures_are_not_matched_with_everything():
    assert not photo_hash.informative(photo_hash.dhash_image(Image.new("RGB", (400, 300), (240, 240, 240))))


def _listing(db, owner, url):
    cat = db.query(Category).first()
    listing = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=cat.id, source_language="ru", status=ListingStatus.active,
                      city="beograd", price=10, currency=Currency.eur, created_at=utcnow(), published_at=utcnow())
    db.add(listing)
    db.flush()
    db.add(ListingPhoto(listing_id=listing.id, url=url, thumbnail_url=url))
    db.commit()
    return listing


def test_hash_is_computed_on_save_and_reuse_found_only_between_different_sellers():
    seed = int(uuid.uuid4().int % 10_000) + 100
    original = photo(seed)
    with SessionLocal() as db:
        first = User(id=uuid.uuid4(), display_name="честный", role=UserRole.buyer, email=f"a{uuid.uuid4().hex[:6]}@x.rs")
        thief = User(id=uuid.uuid4(), display_name="чужое фото", role=UserRole.buyer, email=f"b{uuid.uuid4().hex[:6]}@x.rs")
        db.add_all([first, thief])
        db.commit()
        own = _listing(db, first, saved(original))
        own_second = _listing(db, first, saved(original.resize((600, 450)), quality=60))     # тот же продавец — не тревога
        stolen = _listing(db, thief, saved(original.resize((500, 375)), fmt="JPEG", quality=50))
        hashes = [p.dhash for p in db.query(ListingPhoto).filter(ListingPhoto.listing_id.in_([own.id, stolen.id]))]
        assert all(hashes) and len(hashes) == 2, "хеш посчитан при сохранении"
        pairs = photo_hash.find_reuse(db, days=1, limit=50)
        own_id, own_second_id, stolen_id = str(own.id), str(own_second.id), str(stolen.id)
    keys = {tuple(sorted((p["listing_id"], p["other_id"]))) for p in pairs}
    assert tuple(sorted((own_id, stolen_id))) in keys
    assert tuple(sorted((own_id, own_second_id))) not in keys, "у одного продавца повтор своих фото — не тревога"


def test_admin_alerts_lead_to_the_listing():
    front = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "AdminAlerts.jsx"
    assert "photo_reuse: (a) => `/go/${a.listing_id}`" in front.read_text(encoding="utf-8")
    deploy = (Path(__file__).resolve().parents[2] / "tools" / "deploy.sh").read_text(encoding="utf-8")
    assert "python3 -m app.core.photo_hash --apply" in deploy
