"""
Метка «Ниже рынка»: обещание покупателю, поэтому планка высокая.

Лучше пропустить хорошую цену, чем повесить метку на обычную: после
первой ошибки ей перестанут верить.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.price_marks import MIN_SAMPLE, mark_from_check, run  # noqa: E402
from app.models import (  # noqa: E402
    Category, Currency, Listing, ListingStatus, ListingTranslation, User, UserRole,
)


def _check(**kw):
    base = {"verdict": "cheap", "based_on": 12, "median_eur": 100.0}
    base.update(kw)
    return base


def test_clearly_cheap_gets_the_mark():
    assert mark_from_check(_check(), 70.0) == "below"


def test_slightly_cheaper_does_not():
    """Ниже четверти выборки, но всего на 5% ниже медианы — это не «ниже рынка»."""
    assert mark_from_check(_check(), 95.0) is None


def test_small_sample_does_not():
    assert mark_from_check(_check(based_on=MIN_SAMPLE - 1), 50.0) is None
    assert mark_from_check(_check(based_on=MIN_SAMPLE), 50.0) == "below"


def test_fair_and_expensive_and_missing_do_not():
    for verdict in ("fair", "expensive", None):
        assert mark_from_check(_check(verdict=verdict), 10.0) is None
    assert mark_from_check({}, 10.0) is None
    assert mark_from_check(_check(median_eur=0), 10.0) is None


def test_refresh_marks_only_the_cheap_one_and_clears_stale():
    db = SessionLocal()
    try:
        cat = db.query(Category).first() or Category(id=uuid.uuid4(), slug="pm", name={"ru": "Т"})
        db.add(cat)
        owner = User(id=uuid.uuid4(), display_name="Продавец", role=UserRole.buyer,
                     email=f"pm{uuid.uuid4().hex[:8]}@example.rs")
        db.add(owner)
        db.commit()

        def make(price, title="Велосипед горный"):
            l = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=cat.id,
                        source_language="ru", status=ListingStatus.active, city="pmtest",
                        price=price, currency=Currency.eur, is_free=False,
                        published_at=utcnow(), created_at=utcnow())
            db.add(l)
            db.flush()
            db.add(ListingTranslation(listing_id=l.id, language="ru", title=title,
                                      description="Хороший велосипед, ездил мало."))
            return l

        normal = [make(100 + i) for i in range(12)]
        cheap = make(50)
        stale = make(101)
        stale.price_mark = "below"          # метка осталась с прошлых времён
        db.commit()

        run()
        db.expire_all()
        assert db.get(Listing, cheap.id).price_mark == "below"
        assert all(db.get(Listing, l.id).price_mark is None for l in normal)
        assert db.get(Listing, stale.id).price_mark is None, "устаревшая метка снимается"
    finally:
        db.close()
