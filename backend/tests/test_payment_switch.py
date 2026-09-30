"""
Переключатель оплаты картой в админке.

У владельца нет зарегистрированного предпринимателя или фирмы, а брать деньги за услуги от потребителей как частное
лицо рискованно (налоги, права потребителей, обязанность назвать поставщика услуги). Поэтому оплата картой по
умолчанию ВЫКЛЮЧЕНА, а включает её владелец из админки, когда будет готов. Выключено — сервер отказывает и в
пополнении, и в оплате продвижения картой, а сайт прячет «Пополнить» и кнопку карты. Остаются продвижение за
бонусы и за уже внесённый баланс: деньги, которые человек внёс раньше, у него не отбирают.
"""
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import site_settings  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditEntry, Category, Currency, Listing, ListingStatus, PromotionType, User, UserRole,
)
from app.routers import admin_settings, promotions  # noqa: E402

FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


@pytest.fixture()
def db():
    session = SessionLocal()
    site_settings.set_value(session, site_settings.CARD_PAYMENTS, False, None)
    session.commit()
    yield session
    site_settings.set_value(session, site_settings.CARD_PAYMENTS, False, None)      # общая база: оставляем как по умолчанию
    session.commit()
    session.close()


def _user(db, role=UserRole.buyer, **kw):
    u = User(id=uuid.uuid4(), display_name=f"Тест {role.value}", role=role,
             email=f"s{uuid.uuid4().hex[:8]}@example.rs", **kw)
    db.add(u)
    db.commit()
    return u


def _enable(db):
    site_settings.set_value(db, site_settings.CARD_PAYMENTS, True, None)
    db.commit()


def test_card_payments_are_off_by_default(db):
    site_settings.set_value(db, site_settings.CARD_PAYMENTS, False, None)
    db.commit()
    db.query(site_settings.SiteSetting).filter_by(key=site_settings.CARD_PAYMENTS).delete()   # как на свежей базе: строки нет
    db.commit()
    site_settings.reset_cache()
    assert site_settings.card_payments_enabled(db) is False


def test_the_owner_switches_it_and_the_change_is_journaled(db):
    admin = _user(db, UserRole.admin)
    on = admin_settings.set_card_payments(admin_settings.CardPaymentsIn(enabled=True), admin, db)
    assert on["card_payments_enabled"] is True and on["updated_by"] == admin.display_name
    assert site_settings.card_payments_enabled(db) is True
    off = admin_settings.set_card_payments(admin_settings.CardPaymentsIn(enabled=False), admin, db)
    assert off["card_payments_enabled"] is False
    actions = [row.action for row in db.query(AuditEntry).filter(AuditEntry.target_id == site_settings.CARD_PAYMENTS)
               .order_by(AuditEntry.created_at.desc()).limit(2)]
    assert set(actions) == {"settings_card_payments_on", "settings_card_payments_off"}


def test_only_the_owner_can_read_or_change_it():
    from app.routers.admin_users import require_admin

    with SessionLocal() as db:
        for role in (UserRole.buyer, UserRole.moderator):
            person = _user(db, role)
            with pytest.raises(HTTPException) as error:
                require_admin(person)
            assert error.value.status_code == 403
    routes = {route.path: route for route in admin_settings.router.routes}
    assert "/api/admin/settings" in routes and "/api/admin/settings/card-payments" in routes
    for route in routes.values():
        assert any(dep.call is require_admin for dep in route.dependant.dependencies), route.path


def test_topup_is_refused_while_off_and_allowed_when_on(db, monkeypatch):
    user = _user(db)
    with pytest.raises(HTTPException) as error:
        promotions.start_topup(promotions.TopupIn(amount=500), user, db)
    assert error.value.status_code == 400 and error.value.detail == "payments_disabled"

    _enable(db)
    monkeypatch.setattr(promotions, "_yookassa_request",
                        lambda *a, **k: {"id": "pay-1", "confirmation": {"confirmation_url": "https://pay.example/1"}})
    import app.core.currency as currency
    monkeypatch.setattr(currency, "rsd_to_rub", lambda amount: Decimal("1.00"))
    monkeypatch.setattr(currency, "rsd_per_rub", lambda: Decimal("1.5"))
    result = promotions.start_topup(promotions.TopupIn(amount=500), user, db)
    assert result["confirmation_url"] == "https://pay.example/1"


def _listing(db, owner):
    cat = db.query(Category).first() or Category(id=uuid.uuid4(), slug="ps", name={"ru": "x"})
    db.add(cat)
    db.flush()
    listing = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=cat.id, source_language="ru",
                      status=ListingStatus.active, city="ps", price=10, currency=Currency.eur,
                      published_at=utcnow(), created_at=utcnow())
    db.add(listing)
    db.commit()
    return listing


def test_paying_for_promotion_by_card_is_refused_while_off_even_with_consent(db, monkeypatch):
    owner = _user(db)
    listing = _listing(db, owner)
    monkeypatch.setattr(promotions, "_yookassa_request", lambda *a, **k: (_ for _ in ()).throw(AssertionError("оператору звонить нельзя")))
    body = promotions.PromoteIn(type=PromotionType.highlight, pay_method="yookassa", consent_immediate=True)
    with pytest.raises(HTTPException) as error:
        promotions.start_promotion(listing.id, body, owner, db)
    assert error.value.detail == "payments_disabled"


def test_bonus_and_deposited_balance_still_work_while_card_payments_are_off(db):
    """Выключена только карта: подаренные бонусы и уже внесённые деньги тратить по-прежнему можно."""
    owner = _user(db, bonus_balance=300)
    listing = _listing(db, owner)
    result = promotions.start_promotion(listing.id, promotions.PromoteIn(type=PromotionType.highlight, pay_method="balance"), owner, db)
    assert result["paid_from_balance"] is True

    depositor = _user(db, balance=500)
    listing2 = _listing(db, depositor)
    body = promotions.PromoteIn(type=PromotionType.highlight, pay_method="balance", consent_immediate=True)
    assert promotions.start_promotion(listing2.id, body, depositor, db)["paid_from_balance"] is True


def test_the_wallet_tells_the_site_whether_cards_are_on(db):
    person = _user(db)
    assert promotions.my_balance(person, db)["payments_enabled"] is False
    _enable(db)
    assert promotions.my_balance(person, db)["payments_enabled"] is True


def test_the_site_hides_top_up_and_card_payment_when_off():
    balance = (FRONT / "components" / "BalanceCard.jsx").read_text(encoding="utf-8")
    assert "wallet?.payments_enabled === false" in balance and "balance-topup-off" in balance
    promo = (FRONT / "components" / "PromoteButton.jsx").read_text(encoding="utf-8")
    assert "data?.payments_enabled !== false" in promo
    assert "{cardsOn && (" in promo and "disabled={blocked || !cardsOn}" in promo


def test_the_settings_page_is_wired_for_the_owner_only():
    app = (FRONT / "App.jsx").read_text(encoding="utf-8")
    assert 'path="/admin/settings"' in app
    profile = (FRONT / "pages" / "Profile.jsx").read_text(encoding="utf-8")
    i = profile.index('to="/admin/settings"')
    assert "user.role === 'admin'" in profile[max(0, i - 120):i], "строка «Настройки» видна только владельцу"
    page = (FRONT / "pages" / "AdminSettings.jsx").read_text(encoding="utf-8")
    assert "window.confirm(t('settings.confirm_on'))" in page, "включение оплаты — с вопросом"


def test_every_new_string_exists_in_all_three_languages():
    import json

    keys = [("settings", k) for k in ("title", "card_title", "on", "off", "card_text", "warn_on", "confirm_on", "changed", "never", "no_access")]
    keys += [("balance", "topup_off"), ("promo", "cards_off"), ("promo", "err_payments_off"),
             ("audit", "act", "settings_card_payments_on"), ("audit", "act", "settings_card_payments_off")]
    for lang in ("ru", "en", "sr"):
        data = json.loads((FRONT / "i18n" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
        for path in keys:
            node = data
            for part in path:
                node = node[part]
            assert isinstance(node, str) and node, (lang, path)
