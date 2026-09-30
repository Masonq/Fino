"""
Согласие на немедленное оказание услуги при покупке продвижения.

Закон о защите потребителей (Республика Сербия): потребитель вправе отказаться от договора,
заключённого на расстоянии, в течение 14 дней без объяснения причин; для услуги срок идёт с
заключения договора. Право теряется только когда услуга полностью оказана, если её оказание
началось после явной просьбы потребителя и его подтверждения, что он это знает. Без такого
подтверждения право сохраняется, а если о нём не предупредили — растягивается до 12 месяцев.
Поэтому услугу за деньги (картой или с денежной части баланса) без отметки не оформляем.
Бонусы, которыми целиком покрыта цена, — не платёж: отказываться не от чего.
"""
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Category, Currency, Listing, ListingStatus, Promotion, PromotionType, User, UserRole,
)
from app.routers import promotions  # noqa: E402


def _setup(db, balance=0, bonus=0):
    user = User(id=uuid.uuid4(), display_name="Покупатель", role=UserRole.buyer,
                email=f"c{uuid.uuid4().hex[:8]}@example.rs", balance=balance, bonus_balance=bonus)
    db.add(user)
    cat = db.query(Category).first() or Category(id=uuid.uuid4(), slug="cn", name={"ru": "x"})
    db.add(cat)
    db.flush()
    listing = Listing(id=uuid.uuid4(), owner_id=user.id, category_id=cat.id, source_language="ru",
                      status=ListingStatus.active, city="cn", price=10, currency=Currency.eur,
                      published_at=utcnow(), created_at=utcnow())
    db.add(listing)
    db.commit()
    return user, listing


def _buy(db, user, listing, **kw):
    body = promotions.PromoteIn(type=PromotionType.highlight, pay_method=kw.pop("pay_method", "balance"), **kw)
    return promotions.start_promotion(listing.id, body, user, db)


def test_paying_with_money_from_the_balance_needs_the_consent():
    db = SessionLocal()
    try:
        user, listing = _setup(db, balance=500)
        with pytest.raises(HTTPException) as error:
            _buy(db, user, listing)
        assert error.value.status_code == 400 and error.value.detail == "consent_required"
        db.refresh(user)
        assert user.balance == Decimal(500), "ничего не списано"
    finally:
        db.close()


def test_with_the_consent_it_is_recorded_with_a_time():
    db = SessionLocal()
    try:
        user, listing = _setup(db, balance=500)
        result = _buy(db, user, listing, consent_immediate=True)
        assert result["paid_from_balance"] is True
        promo = db.query(Promotion).filter(Promotion.listing_id == listing.id).one()
        assert promo.consent_immediate_at is not None
    finally:
        db.close()


def test_a_price_fully_covered_by_bonus_needs_no_consent():
    """Подарок не деньги: платить нечем, отказываться не от чего."""
    db = SessionLocal()
    try:
        user, listing = _setup(db, balance=0, bonus=300)
        result = _buy(db, user, listing)                  # цена highlight = 300
        assert result["paid_from_balance"] is True
        db.refresh(user)
        assert user.bonus_balance == Decimal(0)
    finally:
        db.close()


def test_bonus_that_only_partly_covers_the_price_still_needs_the_consent():
    db = SessionLocal()
    try:
        user, listing = _setup(db, balance=500, bonus=100)
        with pytest.raises(HTTPException) as error:
            _buy(db, user, listing)
        assert error.value.detail == "consent_required"
    finally:
        db.close()


def test_a_card_payment_is_refused_without_the_consent_before_calling_the_operator(monkeypatch):
    from app.core import site_settings

    db = SessionLocal()
    try:
        site_settings.set_value(db, site_settings.CARD_PAYMENTS, True, None)      # по умолчанию оплата картой выключена
        db.commit()
        user, listing = _setup(db)
        monkeypatch.setattr(promotions, "_yookassa_request",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("оператору звонить рано")))
        with pytest.raises(HTTPException) as error:
            _buy(db, user, listing, pay_method="yookassa")
        assert error.value.detail == "consent_required"
    finally:
        site_settings.set_value(db, site_settings.CARD_PAYMENTS, False, None)
        db.commit()
        db.close()


def test_topup_does_not_ask_for_the_consent():
    """Пополнение — не оказание услуги: деньги на балансе остаются возвратными, отказываться пока не от чего."""
    body = promotions.TopupIn(amount=500)
    assert not hasattr(body, "consent_immediate")


def test_the_frontend_sends_the_consent_and_blocks_the_buttons_without_it():
    root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    client = (root / "api" / "client.js").read_text(encoding="utf-8")
    assert "consent_immediate: consentImmediate" in client
    page = (root / "components" / "PromoteButton.jsx").read_text(encoding="utf-8")
    assert "startPromotion(listingId, selected, payMethod, agreed)" in page
    assert page.count("disabled={blocked") == 3, "все три кнопки оплаты закрыты без согласия"
