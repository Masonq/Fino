"""
Не ушли ли бонусы в настоящие деньги.

Ответ даёт не вера в код, а сверка с записями: деньги на счёте не могут превышать то, что человек внёс сам
(оплаченные пополнения), а деньги + бонусы обязаны сходиться с «внесено + выдано − потрачено».

Тесты делают три вещи:
  1. гоняют настоящие потоки (подарок за первое объявление, награда за друга, пополнение через вебхук, покупка) и
     убеждаются, что деньги при этом не растут от бонусов;
  2. подставляют заведомо испорченные счета и убеждаются, что сверка их ловит (иначе она бесполезна);
  3. следят, чтобы в код не добавили новый путь, который пишет в денежный счёт или выдаёт бонус.
"""
import asyncio
import re
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import referrals, split_balances, wallet, welcome_bonus  # noqa: E402
from app.core.audit_wallets import audit_user  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    BalanceTopup, BalanceTopupStatus, Category, Currency, Listing, ListingStatus, Promotion, PromotionStatus,
    PromotionType, User, UserRole,
)
from app.routers import promotions  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


def person(db, name="Аудит", **kw):
    u = User(id=uuid.uuid4(), display_name=name, role=UserRole.buyer, email=f"a{uuid.uuid4().hex[:8]}@example.rs", **kw)
    db.add(u)
    db.commit()
    return u


def listing_of(db, owner, status=ListingStatus.active):
    cat = db.query(Category).first() or Category(id=uuid.uuid4(), slug="au", name={"ru": "x"})
    db.add(cat)
    db.flush()
    listing = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=cat.id, source_language="ru", status=status,
                      city="au", price=10, currency=Currency.eur, published_at=utcnow(), created_at=utcnow())
    db.add(listing)
    db.commit()
    return listing


def paid_topup(db, user, amount, currency="RSD", status=BalanceTopupStatus.paid):
    db.add(BalanceTopup(user_id=user.id, amount=amount, currency=currency, status=status, payment_id=f"p-{uuid.uuid4().hex[:10]}"))
    db.commit()


def spent(db, user, listing, price):
    db.add(Promotion(listing_id=listing.id, user_id=user.id, type=PromotionType.highlight, status=PromotionStatus.paid,
                     price_paid=price, currency="RSD", payment_id=None))
    db.commit()


# ─── 1. настоящие потоки: деньги от бонусов не растут ─────────────────────────────────────────
def test_welcome_gift_goes_to_bonus_never_to_money(db):
    user = person(db)
    listing = listing_of(db, user)
    assert welcome_bonus.reward_first_listing(db, listing) is True
    db.refresh(user)
    assert (user.balance, user.bonus_balance) == (0, welcome_bonus.WELCOME_BONUS)
    assert welcome_bonus.reward_first_listing(db, listing) is False, "второй раз не выдаём"
    db.refresh(user)
    assert user.bonus_balance == welcome_bonus.WELCOME_BONUS and user.balance == 0
    assert audit_user(db, user).problems == []


def test_referral_reward_goes_to_bonus_of_both_sides(db):
    referrer = person(db, "Пригласил")
    invited = person(db, "Приглашённый", referred_by=referrer.id)
    listing = listing_of(db, invited)
    assert referrals.reward_referral_if_first_listing(db, listing) is True
    db.refresh(referrer)
    db.refresh(invited)
    for side in (referrer, invited):
        assert (side.balance, side.bonus_balance) == (0, referrals.REFERRAL_BONUS)
        assert audit_user(db, side).problems == []


class FakeRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def test_a_paid_topup_goes_to_money_only_and_a_repeated_notice_pays_nothing_twice(db, monkeypatch):
    user = person(db, bonus_balance=300)
    payment_id = f"pay-{uuid.uuid4().hex[:8]}"
    db.add(BalanceTopup(user_id=user.id, amount=500, currency="RSD", status=BalanceTopupStatus.pending, payment_id=payment_id))
    db.commit()
    monkeypatch.setattr(promotions, "_yookassa_request", lambda *a, **k: {"status": "succeeded", "metadata": {"kind": "balance_topup"}})
    for _ in range(3):                                                    # ЮKassa вправе прислать уведомление несколько раз
        asyncio.run(promotions.yookassa_webhook(FakeRequest({"object": {"id": payment_id}})))
    db.refresh(user)
    assert (user.balance, user.bonus_balance) == (500, 300), "пополнение — в деньги, один раз; бонус не тронут"


def test_spending_takes_bonus_first_and_never_turns_bonus_into_money(db):
    user = person(db, balance=500, bonus_balance=100)
    from_bonus, from_money = wallet.charge(user, 250)
    assert (from_bonus, from_money) == (Decimal(100), Decimal(150))
    assert (user.balance, user.bonus_balance) == (350, 0)


# ─── 2. сверка ловит испорченные счета ───────────────────────────────────────────────────────
def test_an_honest_wallet_passes(db):
    user = person(db, welcome_bonus_given=True, balance=500, bonus_balance=150)     # внёс 500, подарок 300, потратил 150
    paid_topup(db, user, 500)
    spent(db, user, listing_of(db, user), 150)
    assert audit_user(db, user).problems == []


def test_a_gift_left_inside_the_money_is_caught(db):
    """Подарок 300 лежит в общем счёте: человек ничего не вносил, а «денег» у него 300."""
    user = person(db, welcome_bonus_given=True, balance=300, bonus_balance=0)
    verdict = audit_user(db, user)
    assert "MONEY_ABOVE_DEPOSITS" in verdict.problems and verdict.serious


def test_money_that_exceeds_deposits_is_caught_even_without_any_gift_flag(db):
    """Бонус выдан в обход отметок (правка руками): денег 100, внесено 0 — всё равно видно."""
    user = person(db, balance=100)
    assert "MONEY_ABOVE_DEPOSITS" in audit_user(db, user).problems


def test_a_topup_credited_but_never_paid_is_caught(db):
    """Зачислили, а платёж в статусе ожидания: в «внесено» он не попадает, деньги окажутся лишними."""
    user = person(db, balance=500)
    paid_topup(db, user, 500, status=BalanceTopupStatus.pending)
    assert "MONEY_ABOVE_DEPOSITS" in audit_user(db, user).problems


def test_bonus_from_nowhere_is_caught(db):
    user = person(db, balance=500, bonus_balance=100)
    paid_topup(db, user, 500)
    problems = audit_user(db, user).problems
    assert "BONUS_EXCESS" in problems and "MISMATCH" in problems


def test_money_out_of_thin_air_breaks_conservation(db):
    user = person(db, balance=450)
    paid_topup(db, user, 500)                                    # внёс 500, а денег 450 и нигде не потрачено
    assert "MISMATCH" in audit_user(db, user).problems


def test_a_foreign_currency_topup_is_flagged_for_a_human_not_guessed(db):
    user = person(db, balance=100)
    paid_topup(db, user, 100, currency="RUB")
    assert audit_user(db, user).problems == ["REVIEW_CURRENCY"]


# ─── 3. разделение старых балансов не пускает бонус в деньги ───────────────────────────────────
def test_after_the_split_the_legacy_gift_sits_in_bonus_not_in_money(db):
    """До разделения всё лежало одним числом: внёс 500 + подарок 300 = 800. После — 500 деньгами и 300 бонусом."""
    user = person(db, welcome_bonus_given=True, balance=800)
    paid_topup(db, user, 500)
    assert "MONEY_ABOVE_DEPOSITS" in audit_user(db, user).problems, "до разделения сверка честно показывает проблему"
    split_balances.run(apply=True)
    db.refresh(user)
    assert (user.balance, user.bonus_balance) == (500, 300)
    assert audit_user(db, user).problems == []


def test_split_handles_referral_gifts_and_a_partly_spent_gift(db):
    referrer = person(db, "Реферер", balance=200)
    invited = person(db, "Гость", referred_by=referrer.id, referral_reward_given=True, welcome_bonus_given=True, balance=500)
    paid_topup(db, invited, 100)
    spent(db, invited, listing_of(db, invited), 200)             # приглашённому выдано 200+300=500, внёс 100, потратил 200 → осталось 400
    invited.balance = Decimal(400)
    db.commit()
    split_balances.run(apply=True)
    for u in (referrer, invited):
        db.refresh(u)
    assert (referrer.balance, referrer.bonus_balance) == (0, 200), "награда пригласившего — в бонус"
    assert (invited.balance, invited.bonus_balance) == (100, 300), "внесённые 100 остались деньгами, подарок — бонусом"


def test_the_ruble_converter_refuses_to_run_after_the_split(db):
    """Старый перевод рублей в динары умножил бы уже динарные суммы на курс: +20% «настоящих» денег."""
    from app.core import rebalance

    person(db, balance=100, bonus_balance=50)                      # хотя бы у одного есть бонусный счёт — балансы уже разделены
    before = db.query(User).filter(User.balance > 0).count()
    with pytest.raises(SystemExit) as stop:
        rebalance.run(apply=True)
    assert "Отказ" in str(stop.value)
    assert db.query(User).filter(User.balance > 0).count() == before


# ─── 4. никто не добавил новый путь ────────────────────────────────────────────────────────────
def _hits(pattern):
    found = {}
    for path in APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(pattern, text):
            found.setdefault(path.name, []).append(text[:match.start()].count("\n") + 1)
    return found


def test_only_the_wallet_and_the_one_time_tools_write_to_the_money_account():
    assert set(_hits(r"\.balance\s*(?:=|\+=|-=)(?!=)")) <= {"wallet.py", "split_balances.py", "rebalance.py"}


def test_only_the_wallet_and_the_split_write_to_the_bonus_account():
    assert set(_hits(r"\.bonus_balance\s*(?:=|\+=|-=)(?!=)")) <= {"wallet.py", "split_balances.py"}


def test_gifts_are_granted_only_by_the_welcome_and_the_referral_functions():
    assert set(_hits(r"\bgrant_bonus\(")) <= {"wallet.py", "welcome_bonus.py", "referrals.py"}


def test_money_is_deposited_only_by_the_payment_webhook():
    assert set(_hits(r"wallet\.deposit\(")) == {"promotions.py"}


def test_there_is_no_raw_sql_touching_the_balances():
    assert not _hits(r"(?i)UPDATE\s+users\s+SET[^;]*balance")


def test_expected_money_is_never_negative_and_a_missing_record_is_not_called_a_leak(db):
    """Потрачено больше, чем есть записей о пополнениях: это «не хватает записей», а не утечка бонуса."""
    user = person(db, balance=0, bonus_balance=0)
    spent(db, user, listing_of(db, user), 300)                       # потратил 300, а пополнений в базе нет
    verdict = audit_user(db, user)
    assert verdict.expected_money == 0
    assert "MONEY_ABOVE_DEPOSITS" not in verdict.problems and "MISMATCH" in verdict.problems


def test_the_audit_tool_only_reads():
    source = (APP / "core" / "audit_wallets.py").read_text(encoding="utf-8")
    assert "commit(" not in source and "db.add(" not in source and ".balance =" not in source
