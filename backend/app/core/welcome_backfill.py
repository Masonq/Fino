"""
Довыдать подарок за первое объявление тем, кто его не получил: опубликовал объявление до появления подарка или
был проверенным продавцом (объявления публиковались без модерации, и подарок не срабатывал).

Кому: у человека есть хотя бы одно своё (не перенесённое из Telegram) опубликованное объявление, а подарка ещё
не было. Перенесённые из Telegram объявления не считаются — у таких «авторов» нет живого человека.

    python3 -m app.core.welcome_backfill            посмотреть, кому и сколько
    python3 -m app.core.welcome_backfill --apply    начислить (с уведомлением человеку)
"""
import argparse

from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.welcome_bonus import WELCOME_BONUS
from app.models import Listing, User


def run(apply: bool) -> None:
    db = SessionLocal()
    try:
        own = (db.query(Listing.owner_id, func.count(Listing.id))
               .filter(Listing.published_at.isnot(None), Listing.external_source.is_(None))
               .group_by(Listing.owner_id).all())
        ids = [uid for uid, n in own if n > 0]
        people = (db.query(User).filter(User.id.in_(ids), User.welcome_bonus_given.is_(False)).all()) if ids else []
        for u in people:
            print(f"{u.display_name or u.email or u.id} — бонусы сейчас {float(u.bonus_balance or 0):.0f} RSD")
            if apply:
                from app.core import wallet
                wallet.grant_bonus(u, WELCOME_BONUS)
                u.welcome_bonus_given = True
                db.commit()
                try:
                    from app.core.notifications import notify
                    notify(db, u.id, f"Дарим {WELCOME_BONUS:.0f} RSD на продвижение — за ваше первое объявление на PLONK. "
                                     f"Хватит на неделю выделенной карточки.", force=True)
                except Exception:  # noqa: BLE001
                    pass
        print(f"\nНе получили подарок: {len(people)}" + ("" if apply else ". Начислить: python3 -m app.core.welcome_backfill --apply")
              + (f"\nНачислено по {WELCOME_BONUS:.0f} RSD: {len(people)}" if apply else ""))
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    run(p.parse_args().apply)
