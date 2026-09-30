"""
Деньги и бонусы лежат раздельно.

Условия обещают: бонус нельзя вывести и вернуть деньгами, а внесённые деньги
возвращаются там, где этого требует закон. Пока всё было одним числом,
исполнить это было нечем.
"""
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import split_balances, wallet  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import User, UserRole  # noqa: E402


class U:
    def __init__(self, balance=0, bonus=0):
        self.balance, self.bonus_balance = Decimal(balance), Decimal(bonus)


def test_bonus_is_spent_before_money():
    u = U(balance=500, bonus=300)
    assert wallet.charge(u, 150) == (Decimal(150), Decimal(0))
    assert (u.bonus_balance, u.balance) == (150, 500)


def test_a_purchase_can_span_both_accounts():
    u = U(balance=500, bonus=100)
    assert wallet.charge(u, 300) == (Decimal(100), Decimal(200))
    assert (u.bonus_balance, u.balance) == (0, 300)


def test_not_enough_changes_nothing():
    u = U(balance=100, bonus=100)
    with pytest.raises(ValueError):
        wallet.charge(u, 250)
    assert (u.bonus_balance, u.balance) == (100, 100)


def test_total_and_view_split_the_two_parts():
    u = U(balance=200, bonus=300)
    assert wallet.total(u) == 500
    assert wallet.view(u) == {"balance": 500.0, "money": 200.0, "bonus": 300.0}


def test_deposit_and_bonus_go_to_their_own_accounts():
    u = U()
    wallet.deposit(u, 500)
    wallet.grant_bonus(u, 300)
    assert (u.balance, u.bonus_balance) == (500, 300)


def test_welcome_and_referral_rewards_are_bonuses_not_money():
    from app.core import referrals, welcome_bonus
    import inspect

    assert "grant_bonus" in inspect.getsource(welcome_bonus.reward_first_listing)
    assert "grant_bonus" in inspect.getsource(referrals.reward_referral_if_first_listing)
    for module in (welcome_bonus, referrals):
        assert ".balance = " not in inspect.getsource(module), "бонус не должен попадать на денежный счёт"


def test_a_topup_credits_money_not_bonus():
    import inspect

    from app.routers import promotions

    assert "wallet.deposit" in inspect.getsource(promotions)


# ─── перенос старых балансов ─────────────────────────────────────────────
def _user(db, **kw):
    u = User(id=uuid.uuid4(), display_name="Старый", role=UserRole.buyer,
             email=f"w{uuid.uuid4().hex[:8]}@example.rs", **kw)
    db.add(u)
    db.commit()
    return u


def test_old_balances_are_split_by_history_and_it_is_repeatable():
    db = SessionLocal()
    try:
        # Получил подарок 300 и внёс 500 сам: на балансе лежало 800
        both = _user(db, welcome_bonus_given=True, balance=800)
        # Только внёс деньги
        cash = _user(db, balance=500)
        # Подарок уже потратил (300 на продвижение) — осталось только внесённое
        from app.core.clock import utcnow
        from app.models import Currency, Listing, ListingStatus, Promotion, PromotionStatus, PromotionType, Category

        cat = db.query(Category).first() or Category(id=uuid.uuid4(), slug="wl", name={"ru": "x"})
        db.add(cat)
        spender = _user(db, welcome_bonus_given=True, balance=500)
        listing = Listing(id=uuid.uuid4(), owner_id=spender.id, category_id=cat.id, source_language="ru",
                          status=ListingStatus.active, city="wl", price=10, currency=Currency.eur,
                          published_at=utcnow(), created_at=utcnow())
        db.add(listing)
        db.flush()
        db.add(Promotion(listing_id=listing.id, user_id=spender.id, type=PromotionType.highlight,
                         status=PromotionStatus.paid, price_paid=300, currency="RSD", payment_id=None))
        db.commit()

        split_balances.run(apply=True)
        db.expire_all()
        assert (db.get(User, both.id).bonus_balance, db.get(User, both.id).balance) == (300, 500)
        assert (db.get(User, cash.id).bonus_balance, db.get(User, cash.id).balance) == (0, 500)
        assert (db.get(User, spender.id).bonus_balance, db.get(User, spender.id).balance) == (0, 500), \
            "подарок уже потрачен — на балансе остались только внесённые деньги"

        again = split_balances.run(apply=True)
        db.expire_all()
        assert (db.get(User, both.id).bonus_balance, db.get(User, both.id).balance) == (300, 500), \
            "повторный запуск ничего не меняет"
        assert again["skipped"] >= 1
    finally:
        db.close()


def test_the_report_does_not_change_anything():
    db = SessionLocal()
    try:
        u = _user(db, welcome_bonus_given=True, balance=300)
        split_balances.run(apply=False)
        db.expire_all()
        assert (db.get(User, u.id).bonus_balance, db.get(User, u.id).balance) == (0, 300)
    finally:
        db.close()
