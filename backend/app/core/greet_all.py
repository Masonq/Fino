"""
Довести письма команды до всех, кто зарегистрировался раньше.

    python3 -m app.core.greet_all            ОТЧЁТ: кому что уйдёт, ничего не отправляет
    python3 -m app.core.greet_all --apply    выполнить

Сначала проверка, потом отправка. Отчёт разбирает каждого человека по
тому, что у него уже есть:
  - полное письмо   — чата с командой нет вовсе, придут оба письма;
  - только подарок  — знакомство пришло раньше, письма о подарке нет;
  - только кнопка   — письмо о подарке пришло, но без кнопки «Разместить»:
                      дописывается на месте, второй раз не пишем;
  - уже в порядке   — ничего не трогаем.

Не считаем «зарегистрированными»: заблокированных, самих себя (аккаунт
команды) и служебные аккаунты чатов-источников — по одному на чат, в них
никто не входит, письмо ушло бы в пустоту.

Повторный запуск после --apply ничего не отправляет.
"""
import argparse

from app.core.database import SessionLocal
from app.core.team_chat import letter_state, sync_letters, team_user
from app.models import User

LABELS = {
    "none": "полное письмо (оба)",
    "no_bonus": "только письмо о подарке",
    "no_button": "только кнопка «Разместить» в уже пришедшем",
    "ok": "уже в порядке",
}


def is_real_person(user: User) -> bool:
    """
    Служебный аккаунт чата-источника: телефон вида tg123…, и больше ни одного
    способа войти. Настоящий человек входит хотя бы одним из них.
    """
    has_login = any((user.email, user.telegram_id, user.google_id, user.apple_id, user.viber_id))
    service = (user.phone or "").startswith("tg") and not has_login
    return not service


def audience(db):
    """(люди, сколько исключено по причинам)"""
    team = team_user(db)
    db.commit()
    skipped = {"заблокированные": 0, "служебные аккаунты чатов": 0}
    people = []
    for user in db.query(User).order_by(User.created_at).all():
        if user.id == team.id:
            continue
        if user.is_blocked:
            skipped["заблокированные"] += 1
        elif not is_real_person(user):
            skipped["служебные аккаунты чатов"] += 1
        else:
            people.append(user)
    return people, skipped


def run(apply: bool = False) -> dict:
    db = SessionLocal()
    try:
        people, skipped = audience(db)
        plan = {key: 0 for key in LABELS}
        for user in people:
            plan[letter_state(db, user)] += 1

        print(f"Зарегистрировано людей: {len(people)}"
              + "".join(f" (не считаю: {k} — {v})" for k, v in skipped.items() if v))
        for key, label in LABELS.items():
            print(f"  {label}: {plan[key]}")
        todo = sum(v for k, v in plan.items() if k != "ok")
        if not apply:
            print(f"\nК отправке: {todo}. Ничего не отправлено. Выполнить: добавьте --apply")
            return {"plan": plan, "skipped": skipped, "done": 0}

        done = 0
        for user in people:
            lang = getattr(user.default_language, "value", None) or "ru"
            if sync_letters(db, user, lang) != "ok":
                done += 1
                if done % 100 == 0:
                    print(f"  готово {done} из {todo}")
        print(f"\nВыполнено: {done}")
        return {"plan": plan, "skipped": skipped, "done": done}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
