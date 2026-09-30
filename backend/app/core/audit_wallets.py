"""
Сверка кошельков: не ушли ли бонусы в настоящие деньги.

    python3 -m app.core.audit_wallets            показать только тех, у кого что-то не сходится
    python3 -m app.core.audit_wallets --all      показать всех
    python3 -m app.core.audit_wallets --limit 5  показать не больше пяти подробных строк (по умолчанию 15)

Читает базу и ничего не меняет.

Главный признак утечки — простой: деньги на счёте не могут превышать то, что человек когда-либо внёс сам. Пополнение
пишется отдельной записью (BalanceTopup), поэтому «внесено» известно точно. Если денег больше — в них попало то, чего
человек не вносил: например, бонус, оставшийся в общем счёте после того, как балансы делили.

Три проверки на каждого человека (D — внесено оплаченными пополнениями, G — выдано бонусов, S — потрачено с баланса):
  1. деньги ≤ D                          иначе — «денег больше, чем внесено» (утечка бонуса в деньги);
  2. деньги + бонусы = D + G − S         иначе — баланс менялся в обход учёта, или запись пропала;
  3. бонусы ≤ G − (потрачено бонусами)   иначе — бонусов больше, чем выдано.
Списываются сначала бонусы, потом деньги, поэтому «ожидаемые деньги» = D − max(0, S − G).
Если деньги выше ожидаемых, но не выше D — это «проверить»: так бывает, когда до разделения тратили в другом порядке.
"""
import argparse
import sys
from dataclasses import dataclass, field
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.split_balances import granted_bonus, spent_from_balance
from app.models import BalanceTopup, BalanceTopupStatus, User

TOL = Decimal("0.01")

TEXT = {
    "MONEY_ABOVE_DEPOSITS": "денег больше, чем человек когда-либо внёс: бонус мог попасть в деньги",
    "MISMATCH": "деньги + бонусы не равны внесено + выдано − потрачено: баланс менялся в обход учёта",
    "BONUS_EXCESS": "бонусов больше, чем ему выдано",
    "NEGATIVE": "отрицательный остаток",
    "CHECK": "денег больше ожидаемого при порядке «бонусы первыми», но не больше внесённого — проверить",
    "REVIEW_CURRENCY": "есть оплаченные пополнения не в динарах — пересчитать вручную",
}
SERIOUS = {"MONEY_ABOVE_DEPOSITS", "MISMATCH", "BONUS_EXCESS", "NEGATIVE"}


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


@dataclass
class Verdict:
    user: User
    deposits: Decimal
    granted: Decimal
    spent: Decimal
    money: Decimal
    bonus: Decimal
    expected_money: Decimal
    expected_bonus: Decimal
    problems: list[str] = field(default_factory=list)

    @property
    def serious(self) -> bool:
        return any(p in SERIOUS for p in self.problems)


def audit_user(db, user: User) -> Verdict:
    paid = (db.query(BalanceTopup)
            .filter(BalanceTopup.user_id == user.id, BalanceTopup.status == BalanceTopupStatus.paid).all())
    deposits = sum((_d(t.amount) for t in paid if t.currency == "RSD"), Decimal(0))
    foreign = any(t.currency != "RSD" for t in paid)
    granted = granted_bonus(db, user)
    spent = spent_from_balance(db, user)
    bonus_used = min(granted, spent)
    expected_bonus = granted - bonus_used
    expected_money = max(Decimal(0), deposits - (spent - bonus_used))       # меньше нуля быть не может: такое значит «не хватает записей»
    money, bonus = _d(user.balance), _d(user.bonus_balance)

    problems: list[str] = []
    if money < 0 or bonus < 0:
        problems.append("NEGATIVE")
    if foreign:
        problems.append("REVIEW_CURRENCY")
    else:
        if money > deposits + TOL:
            problems.append("MONEY_ABOVE_DEPOSITS")
        elif money > expected_money + TOL:
            problems.append("CHECK")
        if abs((money + bonus) - (deposits + granted - spent)) > TOL:
            problems.append("MISMATCH")
        if bonus > expected_bonus + TOL:
            problems.append("BONUS_EXCESS")
    return Verdict(user, deposits, granted, spent, money, bonus, expected_money, expected_bonus, problems)


def run(show_all: bool = False, limit: int = 15) -> list[Verdict]:
    db = SessionLocal()
    try:
        verdicts = []
        for user in db.query(User).all():
            v = audit_user(db, user)
            if v.money or v.bonus or v.deposits or v.granted or v.spent:
                verdicts.append(v)
        bad = [v for v in verdicts if v.problems]
        serious = [v for v in verdicts if v.serious]
        print(f"Проверено людей с балансом или движениями: {len(verdicts)}")
        print(f"Деньги на счетах: {sum(v.money for v in verdicts)} RSD;  внесено за всё время: {sum(v.deposits for v in verdicts)} RSD")
        print(f"Бонусы на счетах: {sum(v.bonus for v in verdicts)} RSD;  выдано за всё время: {sum(v.granted for v in verdicts)} RSD;  потрачено с баланса: {sum(v.spent for v in verdicts)} RSD")
        print(f"Не сходится: {len(serious)} (важное), к проверке: {len(bad) - len(serious)}")
        # Сначала важное, потом «проверить»; на телефоне длинный список не нужен — итог сверху, подробности урезаны.
        rows = sorted(verdicts if show_all else bad, key=lambda v: ("MONEY_ABOVE_DEPOSITS" not in v.problems, not v.serious, str(v.user.display_name)))       # сначала утечки
        for v in rows[:limit]:
            who = f"{v.user.display_name} [{str(v.user.id)[:8]}]"
            print(f"\n  {who}")
            print(f"    деньги {v.money} (ожидалось не больше {v.expected_money}, внесено {v.deposits});  бонусы {v.bonus} (ожидалось {v.expected_bonus}, выдано {v.granted});  потрачено {v.spent}")
            for p in v.problems:
                print(f"    ! {TEXT[p]}")
        if len(rows) > limit:
            print(f"\n  …и ещё {len(rows) - limit}. Покажу больше: --limit {len(rows)}")
        leaks = [v for v in verdicts if "MONEY_ABOVE_DEPOSITS" in v.problems]
        if leaks:
            print(f"\nБонус мог оказаться в деньгах у {len(leaks)} чел.: денег на счёте больше, чем человек когда-либо внёс.")
        else:
            print("\nДенег больше, чем внесено, ни у кого нет: бонусы в настоящие деньги не попали.")
        return verdicts
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()
    result = run(args.all, args.limit)
    sys.exit(1 if any(v.serious for v in result) else 0)
