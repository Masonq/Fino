"""
Недельная сводка продавцу: что было с его объявлениями.

Человек выложил вещь и замолчал. Её смотрят, сохраняют, иногда пишут —
а он об этом не знает, потому что за цифрами надо самому зайти на
страницу показателей, о которой он, скорее всего, не подозревает.

Раз в неделю мы рассказываем сами. Не «у вас 3 объявления» — это он и
так помнит, — а что с ними: сколько раз посмотрели, сколько сохранили,
сколько написали. И один вывод, если цифры говорят яснее слов:
смотрят, но не пишут, — почти всегда дело в цене.

Кому не пишем:
— у кого нет активных объявлений: рассказывать не о чем;
— у кого за неделю не было ни одного просмотра: «вас никто не
  посмотрел» — не новость, а плевок;
— кто получал сводку меньше шести дней назад.

    python3 -m app.core.seller_digest            разослать
    python3 -m app.core.seller_digest --dry-run  посмотреть, кому и что
"""
from app.core.plural import count as _cnt
import argparse
import logging
from datetime import timedelta

from sqlalchemy import func

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.models import (
    Chat, Favorite, Listing, ListingStatus, ListingViewDaily, User,
)

log = logging.getLogger(__name__)

# Не чаще раза в неделю. Чаще — и это уже не сводка, а назойливость:
# за три дня цифры почти не меняются, а сообщение приходит снова.
MIN_GAP = timedelta(days=6)


def _week_stats(db, user_id) -> dict | None:
    """Цифры за неделю по всем активным объявлениям человека."""
    since = utcnow() - timedelta(days=7)

    listings = (db.query(Listing)
                .filter(Listing.owner_id == user_id,
                        Listing.status == ListingStatus.active)
                .all())
    if not listings:
        return None

    ids = [l.id for l in listings]

    views = (db.query(func.coalesce(func.sum(ListingViewDaily.count), 0))
             .filter(ListingViewDaily.listing_id.in_(ids),
                     ListingViewDaily.day >= since.date())
             .scalar() or 0)
    if not views:
        return None

    saved = (db.query(func.count(Favorite.id))
             .filter(Favorite.listing_id.in_(ids),
                     Favorite.created_at >= since)
             .scalar() or 0)
    chats = (db.query(func.count(Chat.id))
             .filter(Chat.listing_id.in_(ids),
                     Chat.created_at >= since)
             .scalar() or 0)

    # Самое просматриваемое — о нём и говорим: сводка про «все
    # объявления вообще» не даёт человеку что-либо поправить.
    top_id, top_views = (
        db.query(ListingViewDaily.listing_id,
                 func.sum(ListingViewDaily.count).label("n"))
        .filter(ListingViewDaily.listing_id.in_(ids),
                ListingViewDaily.day >= since.date())
        .group_by(ListingViewDaily.listing_id)
        .order_by(func.sum(ListingViewDaily.count).desc())
        .first() or (None, 0)
    )
    top = next((l for l in listings if l.id == top_id), None)

    return {
        "views": int(views), "saved": int(saved), "chats": int(chats),
        "listings": len(listings), "top": top, "top_views": int(top_views),
    }


def _advice(stats: dict) -> str | None:
    """
    Один вывод — и только когда он честный.

    Придумывать совет к любым цифрам нельзя: «продолжайте в том же
    духе» человек читает один раз и больше сводку не открывает.
    """
    views, saved, chats = stats["views"], stats["saved"], stats["chats"]

    if views >= 30 and chats == 0 and saved == 0:
        return ("Смотрят, но не пишут и не сохраняют — обычно дело в цене "
                "или в том, чего не видно на снимках.")
    if views >= 20 and saved >= 3 and chats == 0:
        return ("Сохраняют, но не пишут — вещь нравится, а решиться мешает "
                "цена. Небольшая скидка часто сдвигает такие объявления.")
    if chats > 0 and chats >= max(1, views // 20):
        return None            # всё идёт как надо, советовать нечего
    return None


def _text(stats: dict) -> str:
    top = stats["top"]
    title = ""
    if top is not None and top.translations:
        tr = next((t for t in top.translations
                   if t.language == (top.source_language or "ru")),
                  top.translations[0])
        title = tr.title

    lines = ["<b>Ваши объявления за неделю</b>", ""]
    lines.append(f"Посмотрели: {stats['views']}")
    if stats["saved"]:
        lines.append(f"Сохранили: {stats['saved']}")
    lines.append(f"Написали: {stats['chats']}")

    if title and stats["top_views"]:
        lines += ["", f"Чаще всего смотрели «{title[:60]}» — "
                      f"{_cnt(stats['top_views'], 'раз', 'раза', 'раз')}."]

    advice = _advice(stats)
    if advice:
        lines += ["", advice]
    return "\n".join(lines)


def run(dry_run: bool = False, limit: int | None = None) -> int:
    db = SessionLocal()
    sent = 0
    try:
        # Кому вообще есть смысл писать: у кого есть активные
        # объявления. Остальных не трогаем.
        owners = (db.query(Listing.owner_id)
                  .filter(Listing.status == ListingStatus.active,
                          Listing.owner_id.isnot(None))
                  .distinct().all())
        for (owner_id,) in owners:
            if limit and sent >= limit:
                break
            user = db.query(User).get(owner_id)
            if not user or user.is_blocked:
                continue
            if user.seller_digest_at and utcnow() - user.seller_digest_at < MIN_GAP:
                continue

            stats = _week_stats(db, owner_id)
            if not stats:
                continue

            text = _text(stats)
            if dry_run:
                print(f"\n— {user.display_name}:\n{text}")
                sent += 1
                continue

            from app.core.notifications import notify

            notify(db, owner_id, text, allow_email=True,
                   subject="PLONK — ваши объявления за неделю",
                   link="/my", kind="digest")
            user.seller_digest_at = utcnow()
            db.commit()
            sent += 1
    finally:
        db.close()
    return sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    count = run(dry_run=args.dry_run, limit=args.limit)

    if not args.dry_run:
        from app.core.job_report import report

        report("сводка продавцам", done=count,
               skipped=None if count else
               "ни у кого не набралось просмотров за неделю")
    print(f"\nсводок: {count}")
