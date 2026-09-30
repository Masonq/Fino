"""
Разделить старые балансы на деньги и бонусы. Разово.

    python3 -m app.core.split_balances            отчёт, ничего не меняет
    python3 -m app.core.split_balances --apply    выполнить

Раньше бонусы и пополнения лежали в одном числе. Восстанавливаем по истории:
  бонусов выдано  = подарок за первое объявление (если выдан)
                    + награда за приглашение (за свою и за каждого приглашённого);
  потрачено с баланса = продвижения, оплаченные с баланса (без payment_id, в RSD);
  бонусов осталось = выдано − потрачено (списывали бонусы первыми, как и теперь),
  но не больше текущего баланса; остальное — деньги.

Где история не сходится с балансом (ручные правки, старые рублёвые записи),
отчёт говорит об этом отдельной строкой — такие случаи стоит проверить глазами.
Повторный запуск безопасен: у кого бонусный счёт уже не пуст, ничего не меняется.
"""
import argparse
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.referrals import REFERRAL_BONUS
from app.core.welcome_bonus import WELCOME_BONUS
from app.models import Promotion, PromotionStatus, User


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def granted_bonus(db, user: User) -> Decimal:
    """Сколько бонусов человеку выдано за всё время (по отметкам о выдаче)."""
    granted = Decimal(0)
    if user.welcome_bonus_given:
        granted += WELCOME_BONUS
    if user.referral_reward_given and user.referred_by:
        granted += REFERRAL_BONUS                                 # награда приглашённого
    invited = db.query(User).filter(User.referred_by == user.id, User.referral_reward_given.is_(True)).count()
    return granted + REFERRAL_BONUS * invited                     # награда пригласившего


def spent_from_balance(db, user: User) -> Decimal:
    """Сколько потрачено с баланса на продвижение (без платежей картой: у тех есть payment_id)."""
    spent = Decimal(0)
    for promo in db.query(Promotion).filter(Promotion.user_id == user.id):
        if promo.payment_id is None and promo.currency == "RSD" and promo.status in (
                PromotionStatus.paid, PromotionStatus.pending):
            spent += _d(promo.price_paid)
    return spent


def reconstruct(db, user: User) -> dict:
    granted = granted_bonus(db, user)
    spent = spent_from_balance(db, user)
    balance = _d(user.balance)
    bonus = min(balance, max(Decimal(0), granted - spent))
    return {"granted": granted, "spent": spent, "balance": balance, "bonus": bonus, "money": balance - bonus}


def run(apply: bool = False) -> dict:
    db = SessionLocal()
    try:
        moved = skipped = 0
        total_bonus = total_money = Decimal(0)
        review = []
        for user in db.query(User).filter(User.balance > 0).all():
            if _d(user.bonus_balance) > 0:
                skipped += 1
                continue
            r = reconstruct(db, user)
            if r["bonus"] <= 0:
                total_money += r["money"]
                continue
            moved += 1
            total_bonus += r["bonus"]
            total_money += r["money"]
            if r["granted"] - r["spent"] > r["balance"]:
                review.append(f"  {user.display_name}: по истории бонусов больше, чем на балансе "
                              f"({r['granted'] - r['spent']} > {r['balance']}) — взято {r['bonus']}")
            if apply:
                user.bonus_balance = r["bonus"]
                user.balance = r["money"]
        if apply:
            db.commit()
        verb = "перенесено" if apply else "будет перенесено"
        print(f"Людей с балансом, где есть бонус: {moved} ({verb}); уже разделено раньше: {skipped}")
        print(f"Итого бонусами: {total_bonus} RSD, деньгами: {total_money} RSD")
        for line in review:
            print(line)
        return {"moved": moved, "skipped": skipped, "bonus": total_bonus, "money": total_money}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
