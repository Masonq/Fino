"""
Сводка владельцу чата: что происходит с его барахолкой.

Владелец согласился пустить бота — значит вправе знать, что тот делает.
Без этого он видит только поток постов и не понимает, помогает бот или
засоряет ленту.

Считаем по объявлениям, опубликованным через бота: сколько всего, в
какие ветки, кто публикует чаще других. Последнее важнее прочего — один
человек с десятком объявлений в день заметен сразу, и владелец должен
узнать об этом от нас, а не от недовольных читателей.
"""
from datetime import timedelta

from sqlalchemy import func

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.partner_chats import topic_name
from app.models import Category, Listing, ListingStatus, User


def build(chat_id: int, days: int = 7) -> str:
    """Собирает сводку за последние дни."""
    since = utcnow() - timedelta(days=days)

    with SessionLocal() as db:
        base = db.query(Listing).filter(
            Listing.external_chat == str(chat_id),
            Listing.created_at >= since,
        )
        total = base.count()
        if not total:
            return (f"За {days} дней через бота не опубликовали ничего.\n\n"
                    "Если объявления в чате есть, значит люди пишут их "
                    "по-старому — и бот не мешает.")

        sold = base.filter(Listing.status == ListingStatus.sold).count()

        # По разделам — так видно, чего в чате больше всего
        by_category = (
            db.query(Category.slug, func.count(Listing.id))
            .join(Listing, Listing.category_id == Category.id)
            .filter(Listing.external_chat == str(chat_id),
                    Listing.created_at >= since)
            .group_by(Category.slug)
            .order_by(func.count(Listing.id).desc())
            .limit(6)
            .all()
        )

        # Кто публикует чаще всех. Не для наказания: владелец сам решит,
        # спам это или человек просто разбирает кладовку.
        by_author = (
            db.query(User.display_name, func.count(Listing.id))
            .join(Listing, Listing.owner_id == User.id)
            .filter(Listing.external_chat == str(chat_id),
                    Listing.created_at >= since)
            .group_by(User.display_name)
            .order_by(func.count(Listing.id).desc())
            .limit(5)
            .all()
        )

        without_price = base.filter(Listing.price.is_(None),
                                    Listing.is_free.is_(False)).count()

    lines = [
        f"<b>Барахолка за {days} дней</b>",
        "",
        f"Опубликовано через бота: <b>{total}</b>",
    ]
    if sold:
        lines.append(f"Помечено проданными: {sold}")
    if without_price:
        lines.append(f"Без цены: {without_price}")

    if by_category:
        lines += ["", "<b>Чего больше всего</b>"]
        for slug, count in by_category:
            lines.append(f"  {slug} — {count}")

    if by_author:
        lines += ["", "<b>Кто публикует чаще</b>"]
        for name, count in by_author:
            # Пометка появляется, когда человек заметно выделяется: это
            # повод посмотреть, а не повод блокировать.
            mark = "  ← много" if count >= max(5, total // 3) else ""
            lines.append(f"  {name or 'без имени'} — {count}{mark}")

    return "\n".join(lines)
