"""
Утренняя сводка сотрудникам в Telegram.

Заходить в админку, чтобы узнать, есть ли работа, — само по себе
работа. Раз в сутки бот пишет каждому модератору и владельцу, что
накопилось: очередь, сколько ждёт самое старое, жалобы, обращения,
новые люди за сутки и тревоги. Если разбирать нечего и тревог нет —
не пишет вовсе: сводка, которая приходит каждый день с одним и тем же
«всё спокойно», перестаёт читаться на третий день.

Запускается по расписанию:
    python3 -m app.core.staff_digest
"""
import logging
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.models import (
    Chat, Listing, ListingStatus, Report, Ticket, TicketStatus, User, UserRole,
)

log = logging.getLogger(__name__)

# Молчим, пока в очереди меньше этого — пять объявлений модератор
# разберёт и без напоминания.
QUIET_UNDER = 5
# Часы, после которых очередь считается запущенной.
STALE_HOURS = 24


def build(db: Session) -> str | None:
    now = utcnow()
    day = now - timedelta(hours=24)

    pending = (db.query(func.count(Listing.id))
               .filter(Listing.status == ListingStatus.pending_moderation).scalar() or 0)
    oldest = (db.query(func.min(Listing.created_at))
              .filter(Listing.status == ListingStatus.pending_moderation).scalar())
    stale_hours = round((now - oldest).total_seconds() / 3600) if oldest else 0

    reports = (db.query(func.count(Report.id))
               .filter(Report.resolved_at.is_(None)).scalar() or 0)
    tickets = (db.query(func.count(Ticket.id))
               .filter(Ticket.status != TicketStatus.closed).scalar() or 0)
    flagged = (db.query(func.count(Chat.id))
               .filter(Chat.flagged_at.isnot(None), Chat.flag_cleared_at.is_(None)).scalar() or 0)
    new_users = (db.query(func.count(User.id))
                 .filter(User.created_at >= day).scalar() or 0)
    published = (db.query(func.count(Listing.id))
                 .filter(Listing.published_at >= day).scalar() or 0)

    urgent = pending >= QUIET_UNDER or reports or tickets or flagged or stale_hours >= STALE_HOURS
    if not urgent:
        return None

    lines = ["<b>PLONK — сводка за сутки</b>", ""]
    if pending:
        tail = f", старейшее ждёт {stale_hours} ч" if stale_hours else ""
        lines.append(f"На модерации: <b>{pending}</b>{tail}")
    if reports:
        lines.append(f"Жалобы без ответа: <b>{reports}</b>")
    if tickets:
        lines.append(f"Обращения в поддержку: <b>{tickets}</b>")
    if flagged:
        lines.append(f"Подозрительные переписки: <b>{flagged}</b>")
    lines.append("")
    lines.append(f"За сутки: новых людей — {new_users}, объявлений в ленте — {published}")
    lines.append("")
    lines.append("https://plonk.rs/moderation")
    return "\n".join(lines)


def send_digest(db: Session) -> int:
    text = build(db)
    if not text:
        log.info("Сводка не нужна — разбирать нечего")
        return 0

    from app.core.notifications import _send_telegram

    staff = (db.query(User)
             .filter(User.role.in_((UserRole.moderator, UserRole.admin)),
                     User.telegram_id.isnot(None),
                     User.is_blocked.is_(False))
             .all())
    sent = 0
    for person in staff:
        if _send_telegram(person.telegram_id, text):
            sent += 1
    log.info("Сводка отправлена: %s из %s", sent, len(staff))
    return sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        send_digest(db)
