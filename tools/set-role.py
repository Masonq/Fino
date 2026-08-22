#!/usr/bin/env python3
"""
Назначает человеку роль — обычно себе роль владельца.

Первый владелец сервиса не может появиться через саму админку: чтобы
менять роли, нужно уже быть владельцем. Отсюда этот сценарий: он
работает на сервере, где доступ к базе и так есть у того, кто им владеет.

    python tools/set-role.py --list                 # кто есть в базе
    python tools/set-role.py you@mail.com --admin   # сделать владельцем
    python tools/set-role.py +381601234567 --moderator
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import or_  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models import User, UserRole  # noqa: E402


def show_people(db, limit: int) -> None:
    """Кто вообще есть — чтобы не гадать, каким адресом заводился вход."""
    people = (
        db.query(User)
        # служебные аккаунты чатов не показываем: это не люди
        .filter(~User.phone.like("tg%") | User.phone.is_(None))
        .order_by(User.created_at.desc())
        .limit(limit)
        .all()
    )
    if not people:
        print("В базе пока никого нет — сначала войдите в приложение.")
        return
    print(f"{'роль':<16} {'имя':<24} контакты")
    for user in people:
        contacts = " ".join(filter(None, (user.email, user.phone))) or "—"
        print(f"{user.role.value:<16} {(user.display_name or '')[:24]:<24} {contacts}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("who", nargs="?",
                    help="почта, телефон или имя — по чему найти человека")
    ap.add_argument("--list", action="store_true", help="показать, кто есть в базе")
    ap.add_argument("--admin", action="store_true", help="сделать владельцем")
    ap.add_argument("--moderator", action="store_true", help="сделать модератором")
    ap.add_argument("--buyer", action="store_true", help="снять служебные права")
    args = ap.parse_args()

    with SessionLocal() as db:
        if args.list or not args.who:
            show_people(db, 30)
            if not args.who:
                print("\nЗатем: python tools/set-role.py <почта или телефон> --admin")
            return

        needle = args.who.strip()
        found = (
            db.query(User)
            .filter(or_(User.email == needle, User.phone == needle,
                        User.display_name == needle))
            .all()
        )
        if not found:
            like = f"%{needle}%"
            found = (
                db.query(User)
                .filter(or_(User.email.ilike(like), User.phone.ilike(like),
                            User.display_name.ilike(like)))
                .all()
            )

        if not found:
            raise SystemExit(f"Никого не нашлось по «{needle}». "
                             "Посмотрите список: --list")
        if len(found) > 1:
            print(f"Под «{needle}» подходит несколько человек — уточните:")
            for user in found:
                print(f"  {user.email or user.phone or user.display_name}")
            return

        user = found[0]
        role = (UserRole.admin if args.admin
                else UserRole.moderator if args.moderator
                else UserRole.buyer if args.buyer
                else None)
        if role is None:
            print(f"{user.display_name}: сейчас роль «{user.role.value}»")
            print("Добавьте --admin, --moderator или --buyer, чтобы изменить.")
            return

        was = user.role.value
        user.role = role
        db.commit()
        print(f"{user.display_name or user.email}: {was} → {role.value}")
        if role == UserRole.admin:
            print("\nРазделы админки теперь открыты — они в профиле, "
                  "внизу, под заголовком «Служебное».")


if __name__ == "__main__":
    main()
