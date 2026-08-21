"""
Ежедневная сводка по почте.

Письмо на каждое событие — прямой путь в спам, а это ударит и по кодам
входа, которые идут по той же почте. Поэтому копим события за сутки
и отправляем одно письмо: сколько сообщений, что нового по подпискам,
что решила модерация.

Запускается раз в сутки:
    python3 -m app.core.digest
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    User, Chat, Message, Listing, ListingStatus,
    SavedSearch, ReviewInvite,
)

log = logging.getLogger(__name__)

PERIOD = timedelta(hours=24)

# Не шлём сводку тому, кто заходил за это время — он всё видел сам
SEEN_RECENTLY = timedelta(hours=12)


def collect(db: Session, user: User, since: datetime) -> dict:
    """Собирает, что произошло у человека за период."""
    # непрочитанные сообщения
    chats = db.query(Chat).filter(
        (Chat.buyer_id == user.id) | (Chat.seller_id == user.id)
    ).all()
    chat_ids = [c.id for c in chats]

    unread = 0
    if chat_ids:
        unread = db.query(func.count(Message.id)).filter(
            Message.chat_id.in_(chat_ids),
            Message.sender_id != user.id,
            Message.is_read.is_(False),
            Message.created_at > since,
            Message.kind == "user",
        ).scalar() or 0

    # новое по подпискам
    searches = db.query(SavedSearch).filter(
        SavedSearch.user_id == user.id,
        SavedSearch.notify_enabled.is_(True),
    ).all()

    matches = []
    if searches:
        from app.core.search_alerts import matches as fits
        fresh = (
            db.query(Listing)
            .filter(
                Listing.status == ListingStatus.active,
                Listing.published_at > since,
                Listing.owner_id != user.id,
            )
            .limit(200)
            .all()
        )
        for s in searches:
            found = [
                l for l in fresh
                if fits(l, s.filters or {}, list(l.translations or []))
            ]
            if found:
                matches.append((s.name, found[:3], len(found)))

    # ждём отзыва
    pending_reviews = db.query(ReviewInvite).filter(
        ReviewInvite.user_id == user.id,
        ReviewInvite.responded.is_(False),
        ReviewInvite.dismissed.is_(False),
    ).count()

    return {"unread": unread, "matches": matches, "pending_reviews": pending_reviews}


def render(data: dict) -> tuple[str, str] | None:
    """Собирает тему и текст письма. None — если писать не о чем."""
    lines = []

    if data["unread"]:
        n = data["unread"]
        lines.append(f"Новых сообщений: {n}")

    for name, listings, total in data["matches"]:
        lines.append(f"\nПо поиску «{name}» — новых объявлений: {total}")
        for l in listings:
            tr = (l.translations or [None])[0]
            title = tr.title if tr else "Объявление"
            price = f" — {l.price:.0f} {l.currency}" if l.price else ""
            lines.append(f"  • {title}{price}")

    if data["pending_reviews"]:
        lines.append(f"\nЖдём вашего отзыва по сделкам: {data['pending_reviews']}")

    if not lines:
        return None

    # тема должна говорить, что внутри — иначе письмо не откроют
    if data["unread"] and data["matches"]:
        subject = f"PLONK: {data['unread']} сообщений и новые объявления"
    elif data["unread"]:
        subject = f"PLONK: новых сообщений — {data['unread']}"
    elif data["matches"]:
        subject = "PLONK: новые объявления по вашим поискам"
    else:
        subject = "PLONK: ждём ваш отзыв"

    body = "\n".join(lines)
    return subject, body


def send_digests(db: Session) -> int:
    """Проходит по всем, кому есть что сказать, и отправляет сводку."""
    since = datetime.utcnow() - PERIOD
    active_cutoff = datetime.utcnow() - SEEN_RECENTLY

    # только те, у кого есть почта и нет Telegram: у кого есть Telegram,
    # уже получили уведомления мгновенно
    users = db.query(User).filter(
        User.email.isnot(None),
        User.telegram_id.is_(None),
        User.is_blocked.is_(False),
    ).all()

    sent = 0
    for user in users:
        if user.last_seen_at and user.last_seen_at > active_cutoff:
            continue   # заходил недавно, всё видел

        data = collect(db, user, since)
        rendered = render(data)
        if not rendered:
            continue

        subject, body = rendered
        try:
            from app.core.notify import _send_email_text
            _send_email_text(user.email, subject, body)
            sent += 1
        except Exception as exc:
            log.warning("Сводка не доставлена %s: %s", user.email, exc)

    log.info("Сводок отправлено: %s", sent)
    return sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        count = send_digests(session)
        print(f"Отправлено сводок: {count}")
    finally:
        session.close()
