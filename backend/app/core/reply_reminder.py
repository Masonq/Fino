"""
Напоминание о молчании в переписке — мягкий пуш тому, кто не ответил.

Написали, а ответа нет SILENCE_HOURS — не факт, что забыли специально,
скорее просто не заметили среди прочего. Одно напоминание на одно и то
же неотвеченное сообщение, не на каждый заход скрипта — Chat.
silence_reminder_sent_for хранит id сообщения, под которое уже
напомнили; новый ответ или новое сообщение делает старую отметку
неактуальной сама по себе, простым сравнением id.

Запускается по расписанию:
    python3 -m app.core.reply_reminder
"""
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Chat, Message, User, Listing, ListingTranslation
from app.core.clock import utcnow

log = logging.getLogger(__name__)

SILENCE_HOURS = 24


def remind_silent_chats(db: Session) -> int:
    cutoff = utcnow() - timedelta(hours=SILENCE_HOURS)

    # Только переписки, где вообще было движение недавно достаточно
    # (не поднимаем то, что молчит уже месяцами — тому напоминание
    # только помешает, сделка явно не сложилась) и застряло именно в
    # окне ожидания ответа.
    chats = (
        db.query(Chat)
        .filter(Chat.last_message_at.isnot(None), Chat.last_message_at <= cutoff)
        .all()
    )
    if not chats:
        return 0

    from app.core.notifications import notify

    sent = 0
    for chat in chats:
        last = (
            db.query(Message)
            .filter(Message.chat_id == chat.id, Message.kind == "user")
            .order_by(Message.created_at.desc())
            .first()
        )
        # Системные сообщения (запрос звонка и т.п.) не считаются —
        # у них свой, отдельный путь уведомления.
        if not last or last.created_at > cutoff:
            continue
        if chat.silence_reminder_sent_for == last.id:
            continue   # уже напомнили именно об этом сообщении

        recipient_id = chat.seller_id if last.sender_id == chat.buyer_id else chat.buyer_id
        sender = db.query(User).get(last.sender_id)
        if not sender:
            continue

        listing = db.query(Listing).get(chat.listing_id)
        tr = None
        if listing:
            from app.routers.listings import pick_translation
            recipient = db.query(User).get(recipient_id)
            lang = getattr(recipient.default_language, "value", None) if recipient else "ru"
            tr = pick_translation(listing, lang or "ru")
        title = tr.title if tr else ""

        text = (
            f"<b>{sender.display_name}</b> ждёт ответа в переписке"
            + (f" про «{title}»" if title else "")
            + " уже больше суток"
        )
        try:
            if notify(db, recipient_id, text, link=f"/chat/{chat.id}"):
                sent += 1
        except Exception as exc:                     # noqa: BLE001
            log.warning("Напоминание о молчании не отправлено: %s", exc)
            continue

        chat.silence_reminder_sent_for = last.id

    # Коммитим независимо от sent: sent считает только реально ушедшие
    # во внешний канал (push/Telegram) — а пометка «уже напомнили» и
    # запись в колокольчик (её пишет сам notify() отдельным коммитом)
    # могли произойти и тогда, когда notify() вернул False (человек
    # был активен на сайте прямо в этот момент — увидит сам). Без
    # безусловного коммита тут эта пометка осталась бы не сохранённой,
    # и на следующий заход скрипт напомнил бы о том же сообщении снова.
    db.commit()
    if sent:
        log.info("Напоминаний о молчании отправлено: %s", sent)

    return sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        count = remind_silent_chats(session)
        print(f"Отправлено напоминаний: {count}")
    finally:
        session.close()
