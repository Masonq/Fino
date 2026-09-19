"""
Перевод накопленных балансов в динары.

Баланс заводился в рублях: сто рублей за поднятие объявления. Теперь
цены в динарах, а числа в базе сами не изменились — у человека
записано «300», и это триста рублей, а не триста динаров.

Оставить как есть нельзя: триста динаров — это два поднятия, тогда
как оплачено было три. Пересчитываем один раз по курсу Центробанка,
тем же, по которому берём деньги в платёжной системе.

Округляем вверх. Разница выходит в копейки, и отдать её человеку
правильнее, чем забрать: он платил настоящими деньгами, а мы меняем
правила уже после.

    python3 -m app.core.rebalance --dry-run   посмотреть, что выйдет
    python3 -m app.core.rebalance --apply     пересчитать
"""
import argparse
import logging
from decimal import Decimal, ROUND_CEILING

from app.core.currency import rsd_per_rub
from app.core.database import SessionLocal
from app.models import User

log = logging.getLogger(__name__)


def run(apply: bool) -> dict:
    rate = rsd_per_rub()          # сколько динаров в рубле
    db = SessionLocal()
    counts = {"с балансом": 0, "пересчитано": 0, "было рублей": Decimal(0),
              "стало динаров": Decimal(0)}
    try:
        people = db.query(User).filter(User.balance > 0).all()
        for user in people:
            counts["с балансом"] += 1
            rubles = Decimal(str(user.balance))
            dinars = (rubles * rate).quantize(Decimal("1"), rounding=ROUND_CEILING)

            counts["было рублей"] += rubles
            counts["стало динаров"] += dinars
            counts["пересчитано"] += 1

            print(f"  {user.display_name or user.id}: "
                  f"{rubles:.0f} руб → {dinars} RSD")
            if apply:
                user.balance = dinars

        if apply:
            db.commit()
    finally:
        db.close()
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(apply=args.apply and not args.dry_run)
    print()
    for key, value in result.items():
        print(f"{key}: {value}")
    if not args.apply or args.dry_run:
        print("\nэто был показ. Чтобы применить, добавьте --apply")
