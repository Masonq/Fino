"""
Разослать письмо от команды тем, кто зарегистрировался раньше.

    python3 -m app.core.greet_all            посчитать, кому уйдёт
    python3 -m app.core.greet_all --apply    отправить

Разово: новичкам письмо приходит само при регистрации. Повторный
запуск никому не пишет второй раз — greet сам это проверяет.
"""
import argparse

from app.core.database import SessionLocal
from app.core.team_chat import greet, team_user
from app.models import Chat, User


def run(apply: bool) -> int:
    db = SessionLocal()
    try:
        team = team_user(db)
        db.commit()
        already = {c.buyer_id for c in db.query(Chat).filter(
            Chat.listing_id.is_(None), Chat.seller_id == team.id).all()}
        people = [u for u in db.query(User).filter(User.is_blocked.is_(False)).all()
                  if u.id not in already and u.id != team.id]
        print(f"без письма: {len(people)}")
        if not apply:
            print("запуск с --apply отправит")
            return len(people)
        sent = 0
        for user in people:
            # На том языке, которым человек пользуется на сайте.
            lang = getattr(user.default_language, "value", None) or "ru"
            greet(db, user, lang)
            sent += 1
            if sent % 200 == 0:
                print(f"  отправлено {sent}")
        print(f"отправлено: {sent}")
        return sent
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
