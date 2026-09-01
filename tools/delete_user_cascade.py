"""
Полное удаление пользователя — вместе со всем, что на него ссылается.
Для тестовых/мусорных аккаунтов, не для настоящих людей: у настоящего
человека есть реальная история (переписка, отзывы), которую стирать
не стоит — см. force в DELETE /listings/{id} и listing_has_history,
та же логика тут просто применена к самому пользователю.

Собрано по всем моделям с ForeignKey("users.id") — 17 файлов, нашёл
grep'ом, не наугад: audit, balance_topup, blocked_user, chat,
document_verification, favorites, listing, login_event, notification,
phone_reveal, promotion, push_subscription, review_invite,
seller_subscription, support, trust, user (self — referred_by).

Запуск на сервере:
    cd /opt/fino/backend && source venv/bin/activate && python3 ../tools/delete_user_cascade.py email@example.com
    (добавь --dry-run, чтобы сперва посмотреть, что удалится, не трогая базу)
"""
import sys

sys.path.insert(0, ".")
from app.core.database import SessionLocal
from app.models import (
    User, Listing, ListingTranslation, ListingViewDaily, ListingViewLog,
    ListingSignalDaily, Favorite, Promotion, Chat, Message,
    AuditEntry, BalanceTopup, BlockedUser, DocVerificationRequest,
    LoginEvent, Notification, PhoneReveal, ReviewInvite,
    SellerSubscription, Ticket, TicketMessage, Review, Report,
    PushSubscription,
)


def main(email: str, dry_run: bool) -> None:
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"Пользователь с почтой {email} не найден")
        db.close()
        return

    uid = user.id
    print(f"Удаляю: {user.display_name} ({email}), id={uid}\n")

    lids = [l.id for l in db.query(Listing).filter(Listing.owner_id == uid).all()]
    chat_ids = [
        c.id for c in db.query(Chat)
        .filter((Chat.listing_id.in_(lids)) | (Chat.buyer_id == uid) | (Chat.seller_id == uid))
        .all()
    ]
    ticket_ids = [
        t.id for t in db.query(Ticket)
        .filter((Ticket.user_id == uid) | (Ticket.assignee_id == uid))
        .all()
    ]

    # (модель, фильтр) — порядок важен: сначала то, что ссылается на
    # объявления/чаты/тикеты этого человека, потом сами объявления/
    # чаты/тикеты, и только в конце — сам пользователь.
    plan = [
        (Message, Message.chat_id.in_(chat_ids)),
        (Chat, Chat.id.in_(chat_ids)),
        (ListingViewDaily, ListingViewDaily.listing_id.in_(lids)),
        (ListingViewLog, ListingViewLog.listing_id.in_(lids)),
        (ListingSignalDaily, ListingSignalDaily.listing_id.in_(lids)),
        (Favorite, Favorite.listing_id.in_(lids)),
        (Promotion, Promotion.listing_id.in_(lids)),
        (ListingTranslation, ListingTranslation.listing_id.in_(lids)),
        (Listing, Listing.id.in_(lids)),
        (TicketMessage, TicketMessage.ticket_id.in_(ticket_ids)),
        (Ticket, Ticket.id.in_(ticket_ids)),
        (BalanceTopup, BalanceTopup.user_id == uid),
        (BlockedUser, (BlockedUser.blocker_id == uid) | (BlockedUser.blocked_id == uid)),
        (DocVerificationRequest, (DocVerificationRequest.user_id == uid) | (DocVerificationRequest.requested_by == uid)),
        (LoginEvent, LoginEvent.user_id == uid),
        (Notification, Notification.user_id == uid),
        (PhoneReveal, (PhoneReveal.seller_id == uid) | (PhoneReveal.buyer_id == uid)),
        (ReviewInvite, (ReviewInvite.user_id == uid) | (ReviewInvite.target_id == uid)),
        (SellerSubscription, (SellerSubscription.subscriber_id == uid) | (SellerSubscription.seller_id == uid)),
        (Review, (Review.author_id == uid) | (Review.target_id == uid)),
        (Report, (Report.reporter_id == uid) | (Report.target_user_id == uid)),
        (PushSubscription, PushSubscription.user_id == uid),
    ]

    for model, cond in plan:
        count = db.query(model).filter(cond).count()
        if count:
            print(f"  {model.__name__}: {count}")
            if not dry_run:
                db.query(model).filter(cond).delete(synchronize_session=False)

    referred = db.query(User).filter(User.referred_by == uid).count()
    if referred:
        print(f"  User.referred_by (обнуляю ссылку, самих людей не трогаю): {referred}")
        if not dry_run:
            db.query(User).filter(User.referred_by == uid).update(
                {User.referred_by: None}, synchronize_session=False)

    # Журнал служебных действий — не удаляем, обнуляем ссылку: имя
    # действовавшего уже сохранено рядом текстом (actor_name), запись
    # остаётся читаемой и без живой ссылки на аккаунт (см. комментарий
    # в самой модели — 'аккаунт может быть удалён позже').
    audit_count = db.query(AuditEntry).filter(AuditEntry.actor_id == uid).count()
    if audit_count:
        print(f"  AuditEntry.actor_id (обнуляю ссылку, запись остаётся, имя уже сохранено рядом): {audit_count}")
        if not dry_run:
            db.query(AuditEntry).filter(AuditEntry.actor_id == uid).update(
                {AuditEntry.actor_id: None}, synchronize_session=False)

    if not dry_run:
        db.query(User).filter(User.id == uid).delete()
        db.commit()
        print("\nУдалено.")
    else:
        print("\n--dry-run — база не тронута.")

    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 delete_user_cascade.py email@example.com [--dry-run]")
        sys.exit(1)
    main(sys.argv[1], dry_run="--dry-run" in sys.argv)
