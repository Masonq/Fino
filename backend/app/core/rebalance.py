"""
Перевод накопленных балансов в плонки.

Баланс заводился в рублях: сто рублей за поднятие объявления. Потом мы
перешли на динары, а теперь на свою валюту — плонки, по десять динаров
за штуку. Числа в базе от этого сами не изменились: у человека
по-прежнему записано «300», и это триста рублей, а не триста плонков.

Оставить как есть нельзя: триста плонков — это двадцать поднятий,
тогда как оплачено было три. Поэтому пересчитываем один раз по
цепочке, которой деньги и пришли: рубли → динары по курсу → плонки по
десять.

Округляем вверх. Разница выходит в копейки, и отдать её человеку
правильнее, чем забрать: он платил настоящими деньгами, а мы меняем
правила уже после.

    python3 -m app.core.rebalance --dry-run   посмотреть, что выйдет
    python3 -m app.core.rebalance --apply     пересчитать
"""
import argparse
import logging
from decimal import Decimal, ROUND_CEILING

from app.core.currency import RSD_IN_PLONK, rsd_per_rub
from app.core.database import SessionLocal
from app.models import User

log = logging.getLogger(__name__)


def run(apply: bool) -> dict:
    rate = rsd_per_rub()          # сколько динаров в рубле
    db = SessionLocal()
    counts = {"с балансом": 0, "пересчитано": 0, "было рублей": Decimal(0),
              "стало плонков": Decimal(0)}
    try:
        people = db.query(User).filter(User.balance > 0).all()
        for user in people:
            counts["с балансом"] += 1
            rubles = Decimal(str(user.balance))
            plonks = ((rubles * rate) / RSD_IN_PLONK).quantize(
                Decimal("1"), rounding=ROUND_CEILING)

            counts["было рублей"] += rubles
            counts["стало плонков"] += plonks
            counts["пересчитано"] += 1

            print(f"  {user.display_name or user.id}: "
                  f"{rubles:.0f} руб → {plonks} плонков")
            if apply:
                user.balance = plonks

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
