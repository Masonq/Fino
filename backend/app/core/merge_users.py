"""
Слияние двух учётных записей одного человека.

Как появляются два аккаунта. Человек заходил на сайт по почте, а потом
открыл публикатор в Telegram — там вход по подписи, и мы, не зная, что
это тот же человек, завели ему второго. Или наоборот: сперва писал
боту, потом зашёл на сайт с ноутбука и ввёл почту.

Ничего страшного не происходит до первой сделки: объявления лежат под
одним, переписка идёт под другим, отзыв приходит третьему. Дальше —
хуже: человек не понимает, почему «его» объявления пропали.

Поэтому — слияние. Один аккаунт остаётся, второй отдаёт ему всё и
исчезает. Что переносим: объявления, переписки, сообщения, избранное,
жалобы, отзывы, документы, платежи, подписки, уведомления, записи в
журнале. То есть всё, где стоит ссылка на человека, — иначе в базе
останутся осиротевшие записи, которые потом некому объяснить.

Чего не переносим: телефон и почту, если они уже есть у остающегося —
свои данные он вводил сам и в своём аккаунте; и роль сотрудника —
права не наследуются, их выдаёт человек.
"""
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import User

log = logging.getLogger(__name__)

# Где стоит ссылка на человека: таблица и столбцы. Список собран по
# внешним ключам на users.id — если появится новая таблица со ссылкой,
# её нужно дописать сюда, иначе после слияния там останутся записи,
# указывающие на удалённого.
LINKS: list[tuple[str, tuple[str, ...]]] = [
    ("listings", ("owner_id", "sold_to_user_id")),
    ("chats", ("buyer_id", "seller_id")),
    ("messages", ("sender_id",)),
    ("favorites", ("user_id",)),
    ("saved_searches", ("user_id",)),
    ("notifications", ("user_id",)),
    ("push_subscriptions", ("user_id",)),
    ("review_invites", ("user_id", "target_id")),
    ("reviews", ("author_id", "target_id")),
    ("reports", ("reporter_id", "target_user_id")),
    ("doc_verification_requests", ("user_id", "reviewed_by")),
    ("balance_topups", ("user_id",)),
    ("promotions", ("user_id",)),
    ("phone_reveals", ("seller_id", "buyer_id")),
    ("seller_subscriptions", ("subscriber_id", "seller_id")),
    ("blocked_users", ("blocker_id", "blocked_id")),
    ("tickets", ("user_id", "assigned_to")),
    ("ticket_messages", ("author_id",)),
    ("login_events", ("user_id",)),
    ("audit_log", ("actor_id",)),
]


def _columns(db: Session, table: str) -> set[str]:
    """Какие столбцы есть на самом деле: таблицы со временем меняются."""
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t"), {"t": table}).fetchall()
    return {r[0] for r in rows}


def merge_users(db: Session, keep: User, drop: User) -> dict:
    """
    Переносит всё с drop на keep и удаляет drop.

    Возвращает, что и сколько перенесли: слияние необратимо, и человек
    должен видеть, что именно с ним произошло.
    """
    if keep.id == drop.id:
        return {}

    moved: dict[str, int] = {}
    for table, columns in LINKS:
        existing = _columns(db, table)
        if not existing:
            continue                    # таблицы нет — пропускаем молча
        for column in columns:
            if column not in existing:
                continue
            result = db.execute(
                text(f"UPDATE {table} SET {column} = :keep WHERE {column} = :drop"),
                {"keep": keep.id, "drop": drop.id})
            if result.rowcount:
                moved[f"{table}.{column}"] = result.rowcount

    # Данные для связи: берём у исчезающего то, чего нет у остающегося.
    # Своё человек вводил сам, и затирать его чужим нельзя.
    if not keep.telegram_id and drop.telegram_id:
        keep.telegram_id = drop.telegram_id
    if not keep.email and drop.email:
        keep.email = drop.email
        keep.email_verified = drop.email_verified
    if not keep.phone and drop.phone:
        keep.phone = drop.phone
    if not keep.avatar_url and drop.avatar_url:
        keep.avatar_url = drop.avatar_url

    # Отметка о проверке личности — наследуется: документ проверяли у
    # того же человека, и заставлять его проходить сверку заново было
    # бы издевательством.
    if drop.document_verified:
        keep.document_verified = True

    # Переписки сами с собой после переноса: человек писал со второго
    # аккаунта на объявление первого. Оставлять их нельзя — в списке
    # появится беседа с самим собой.
    self_chats = db.execute(text(
        "DELETE FROM messages WHERE chat_id IN "
        "(SELECT id FROM chats WHERE buyer_id = :u AND seller_id = :u)"),
        {"u": keep.id})
    if self_chats.rowcount:
        moved["сообщения в беседах с самим собой удалены"] = self_chats.rowcount
    result = db.execute(text(
        "DELETE FROM chats WHERE buyer_id = :u AND seller_id = :u"), {"u": keep.id})
    if result.rowcount:
        moved["беседы с самим собой удалены"] = result.rowcount

    db.delete(drop)
    db.commit()
    log.info("объединены %s ← %s: %s", keep.id, drop.id, moved)
    return moved
