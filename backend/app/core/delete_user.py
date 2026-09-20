#!/usr/bin/env python3
"""
Полное удаление людей из базы — вместе со всем, что на них висит.

В админке такого нет и не будет: обычно правильнее заблокировать, а не
стирать. Но у тестовых входов и мусорных регистраций никакой истории,
которую стоило бы хранить, нет, и в списке людей они только мешают.

Порядок удаления важен: сначала то, что ссылается на объявления,
потом сами объявления, потом то, что ссылается на человека, и только
в конце он сам. Иначе база откажет по внешнему ключу.

Что не удаляется, а обезличивается:
  • записи журнала действий — иначе из истории модерации пропадут
    решения, а они про объявления, а не про человека;
  • «кто пригласил» у других людей — сама реферальная связь исчезает,
    приглашённые остаются.

    python3 -m app.core.delete_user почта@пример.рф            # показать
    python3 -m app.core.delete_user "Имя Фамилия" --apply      # по имени
    python3 -m app.core.delete_user 123456789 --apply          # по Telegram
"""
import sys

from sqlalchemy import text

from app.core.database import SessionLocal

# Таблицы, где лежат строки про объявления этого человека.
LISTING_CHILDREN = (
    ("listing_photos", "listing_id"),
    ("listing_translations", "listing_id"),
    ("listing_view_daily", "listing_id"),
    ("listing_view_logs", "listing_id"),
    ("listing_signal_daily", "listing_id"),
    ("favorites", "listing_id"),
    ("promotions", "listing_id"),
    ("review_invites", "listing_id"),
    ("reports", "listing_id"),
    ("reviews", "listing_id"),
    ("tickets", "listing_id"),
    ("messages", "chat_id"),  # особый случай, см. ниже
    ("chats", "listing_id"),
)

# Таблицы, где лежат строки про самого человека: (таблица, колонка).
USER_ROWS = (
    ("messages", "sender_id"),
    ("chats", "buyer_id"),
    ("chats", "seller_id"),
    ("favorites", "user_id"),
    ("saved_searches", "user_id"),
    ("notifications", "user_id"),
    ("push_subscriptions", "user_id"),
    ("login_events", "user_id"),
    ("login_tickets", "user_id"),
    ("verification_codes", "user_id"),
    ("balance_topups", "user_id"),
    ("promotions", "user_id"),
    ("phone_reveals", "buyer_id"),
    ("phone_reveals", "seller_id"),
    ("blocked_users", "blocker_id"),
    ("blocked_users", "blocked_id"),
    ("seller_subscriptions", "subscriber_id"),
    ("seller_subscriptions", "seller_id"),
    ("review_invites", "user_id"),
    ("review_invites", "target_id"),
    ("reviews", "author_id"),
    ("reviews", "target_id"),
    ("reports", "reporter_id"),
    ("reports", "target_user_id"),
    ("doc_verification_requests", "user_id"),
    ("ticket_messages", "author_id"),
    ("tickets", "user_id"),
)


def columns(db, table: str) -> set:
    rows = db.execute(text(
        "select column_name from information_schema.columns where table_name = :t"
    ), {"t": table}).fetchall()
    return {r[0] for r in rows}


def main(who: list[str], apply: bool) -> None:
    """Кого удалять — почта, номер в Telegram или имя целиком.

    Раньше искали только по почте, и людей, вошедших через Telegram,
    этим инструментом было не достать: у них почты нет вовсе.
    """
    db = SessionLocal()
    try:
        users = db.execute(text(
            """
            select id, email, display_name from users
             where lower(coalesce(email, '')) = any(:e)
                or lower(coalesce(display_name, '')) = any(:e)
                or lower(coalesce(company_name, '')) = any(:e)
                or coalesce(telegram_id::text, '') = any(:raw)
            """
        ), {"e": [x.lower() for x in who], "raw": who}).fetchall()
        if not users:
            print("не нашёл таких людей")
            return
        ids = [u[0] for u in users]
        for u in users:
            print(f"• {u[2] or '—'} <{u[1] or 'без почты'}>")

        listing_ids = [r[0] for r in db.execute(text(
            "select id from listings where owner_id = any(:u)"), {"u": ids}).fetchall()]
        chat_ids = [r[0] for r in db.execute(text(
            "select id from chats where buyer_id = any(:u) or seller_id = any(:u)"
            " or listing_id = any(:l)"),
            {"u": ids, "l": listing_ids or [None]}).fetchall()]
        print(f"объявлений: {len(listing_ids)}, переписок: {len(chat_ids)}")

        if not apply:
            print("\nэто был показ. Чтобы удалить, добавьте --apply")
            return

        # 1. Всё, что висит на переписках и объявлениях.
        if chat_ids:
            db.execute(text("delete from messages where chat_id = any(:c)"), {"c": chat_ids})
            db.execute(text("delete from chats where id = any(:c)"), {"c": chat_ids})
        if listing_ids:
            for table, col in LISTING_CHILDREN:
                if table in ("messages", "chats"):
                    continue
                if col not in columns(db, table):
                    continue
                db.execute(text(f"delete from {table} where {col} = any(:l)"), {"l": listing_ids})
            db.execute(text("delete from listings where id = any(:l)"), {"l": listing_ids})

        # 2. Всё, что висит на самом человеке.
        for table, col in USER_ROWS:
            if col not in columns(db, table):
                continue
            db.execute(text(f"delete from {table} where {col} = any(:u)"), {"u": ids})

        # 3. Обезличиваем то, что стирать нельзя.
        if "actor_id" in columns(db, "audit_log"):
            db.execute(text("update audit_log set actor_id = null where actor_id = any(:u)"),
                       {"u": ids})
        if "referred_by" in columns(db, "users"):
            db.execute(text("update users set referred_by = null where referred_by = any(:u)"),
                       {"u": ids})

        db.execute(text("delete from users where id = any(:u)"), {"u": ids})
        db.commit()
        print(f"удалено людей: {len(ids)}")
    finally:
        db.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        raise SystemExit(1)
    main(args, "--apply" in sys.argv)
