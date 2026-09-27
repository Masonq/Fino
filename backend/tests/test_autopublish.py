"""
Автопубликация: кого пропускаем сразу, а кого — модератору.

До этого каждое объявление ждало ручной проверки, и на живом сайте
объявление настоящего человека пролежало 6,5 часов.
"""
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.autopublish import TRUSTED_APPROVED, decide  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Category, Listing, ListingStatus, ListingTranslation, User, UserRole  # noqa: E402


def _category(db):
    cat = db.query(Category).first()
    if cat is None:
        cat = Category(id=uuid.uuid4(), slug="test-cat", name={"ru": "Тест"})
        db.add(cat)
        db.commit()
    return cat


def _user(db, verified=False):
    u = User(id=uuid.uuid4(), display_name="Продавец", role=UserRole.buyer,
             email=f"a{uuid.uuid4().hex[:8]}@example.rs", document_verified=verified)
    db.add(u)
    db.commit()
    return u


def _listing(db, owner, title="Велосипед Trek FX 2", body="Почти новый, ездил один сезон."):
    l = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=_category(db).id,
                source_language="ru", status=ListingStatus.pending_moderation, city="beograd")
    db.add(l)
    db.flush()
    db.add(ListingTranslation(listing_id=l.id, language="ru", title=title, description=body))
    db.commit()
    db.refresh(l)
    return l


def test_newcomer_still_goes_to_the_moderator():
    """Первое объявление смотрим сами, даже если текст чистый."""
    db = SessionLocal()
    try:
        owner = _user(db)
        listing = _listing(db, owner)
        with patch("app.core.moderation_ai.check", return_value=("ok", "")):
            ok, why = decide(db, listing, owner)
        assert not ok and "перв" in why
    finally:
        db.close()


def test_verified_seller_with_clean_text_goes_live():
    db = SessionLocal()
    try:
        owner = _user(db, verified=True)
        listing = _listing(db, owner)
        with patch("app.core.moderation_ai.check", return_value=("ok", "")):
            ok, _ = decide(db, listing, owner)
        assert ok
    finally:
        db.close()


def test_known_seller_is_one_with_several_approved():
    db = SessionLocal()
    try:
        owner = _user(db)
        for _ in range(TRUSTED_APPROVED):
            old = _listing(db, owner)
            from app.core.clock import utcnow
            old.status, old.published_at = ListingStatus.active, utcnow()
        db.commit()
        listing = _listing(db, owner)
        with patch("app.core.moderation_ai.check", return_value=("ok", "")):
            ok, _ = decide(db, listing, owner)
        assert ok
    finally:
        db.close()


def test_suspicious_text_never_goes_live():
    db = SessionLocal()
    try:
        owner = _user(db, verified=True)
        listing = _listing(db, owner)
        for verdict in ("reject", "unsure"):
            with patch("app.core.moderation_ai.check", return_value=(verdict, "причина")):
                ok, why = decide(db, listing, owner)
            assert not ok and "проверка" in why
    finally:
        db.close()


def test_broken_checker_does_not_publish_blindly():
    db = SessionLocal()
    try:
        owner = _user(db, verified=True)
        listing = _listing(db, owner)
        with patch("app.core.moderation_ai.check", side_effect=RuntimeError("нет сети")):
            ok, why = decide(db, listing, owner)
        assert not ok and "не отработала" in why
    finally:
        db.close()
