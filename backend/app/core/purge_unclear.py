"""
Уборка объявлений, по которым не понять, что продают.

Заголовок ничего не говорит («Белград», «Продам», «Там много всего
интересного»), описание пустое или в пару слов — открывать такую
карточку человеку незачем, а в ленте она занимает место.

Скрипт сперва только показывает. Удаление — отдельным ключом и всегда
после того, как список посмотрели глазами: записи стираются насовсем,
вместе со снимками на диске.

Три группы, потому что решения по ним разные:

  и то и другое — заголовок непонятен И описание короче порога. Самый
                   бесспорный мусор: сведений о товаре нет вообще;
  только заголовок — описание нормальное, товар в нём назван. Такую
                   карточку правильнее переименовать, а не удалять;
  только описание — заголовок понятен («Диван IKEA»), описания нет.
                   Обычное дело для простых вещей, удалять не за что.

Объявления с перепиской или в избранном не трогаем никогда: там уже
завязались люди.

Запуск:
    python3 -m app.core.purge_unclear                  # только показать
    python3 -m app.core.purge_unclear --apply          # удалить группу «и то и другое»
    python3 -m app.core.purge_unclear --apply --scope title
"""
import argparse
import os

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Listing, ListingStatus, ListingTranslation

# Ниже этого описание ничего не описывает. Тот же порог, что стоит на
# публикации новых объявлений (DESCRIPTION_MIN в listings.py).
SHORT_DESCRIPTION = 20

LINKED_TABLES = (
    "listing_photos", "favorites", "reviews", "reports", "promotions",
    "listing_view_logs", "listing_view_daily", "listing_signal_daily",
    "tickets", "review_invites", "listing_translations",
)


def _groups(db):
    """Раскладываем непонятные объявления по трём группам."""
    from app.routers.listings import title_is_clear

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(
            Listing.status == ListingStatus.active,
            ListingTranslation.language == "ru",
        )
        .all()
    )

    both, title_only, description_only = [], [], []
    for listing, tr in rows:
        bad_title = not title_is_clear(tr.title)
        bad_description = len((tr.description or "").strip()) < SHORT_DESCRIPTION
        if bad_title and bad_description:
            both.append((listing, tr))
        elif bad_title:
            title_only.append((listing, tr))
        elif bad_description:
            description_only.append((listing, tr))
    return {"и то и другое": both, "только заголовок": title_only,
            "только описание": description_only}


def _busy(db, ids) -> set:
    """У кого уже есть переписка или кто у кого-то в избранном."""
    if not ids:
        return set()
    rows = db.execute(text("""
        select distinct listing_id from chats where listing_id = any(:ids)
        union
        select distinct listing_id from favorites where listing_id = any(:ids)
    """), {"ids": list(ids)})
    return {row[0] for row in rows}


def show(db) -> dict:
    groups = _groups(db)
    total = (
        db.query(Listing)
        .filter(Listing.status == ListingStatus.active)
        .count()
    )
    print(f"всего активных объявлений: {total}\n")

    for name, items in groups.items():
        ids = [l.id for l, _ in items]
        busy = _busy(db, ids)
        from_chats = sum(1 for l, _ in items if l.external_source == "telegram")
        print(f"{name}: {len(items)} "
              f"(из чатов {from_chats}, своих {len(items) - from_chats}, "
              f"с перепиской или в избранном {len(busy)} — их не трогаем)")
        for listing, tr in items[:12]:
            mark = " [есть переписка]" if listing.id in busy else ""
            desc = (tr.description or "").strip().replace("\n", " ")
            print(f"    {tr.title!r} | описание: {desc[:60]!r}{mark}")
        if len(items) > 12:
            print(f"    ... и ещё {len(items) - 12}")
        print()
    return groups


def purge(db, items) -> int:
    """Удаляет насовсем: записи, связи и снимки с диска."""
    ids = [l.id for l, _ in items]
    busy = _busy(db, ids)
    targets = [i for i in ids if i not in busy]
    if not targets:
        return 0

    files = [row[0] for row in db.execute(
        text("select url from listing_photos where listing_id = any(:ids)"),
        {"ids": targets})]
    for table in LINKED_TABLES:
        db.execute(text(f"delete from {table} where listing_id = any(:ids)"),
                   {"ids": targets})
    db.execute(text("delete from listings where id = any(:ids)"), {"ids": targets})
    db.commit()

    for url in files:
        path = os.path.join(settings.media_dir, url.rsplit("/", 1)[-1])
        try:
            os.remove(path)
        except OSError:
            pass
    print(f"удалено объявлений: {len(targets)}, снимков стёрто: {len(files)}")
    return len(targets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="удалить (необратимо)")
    parser.add_argument("--scope", default="both",
                        choices=("both", "title", "description"),
                        help="какую группу удалять")
    args = parser.parse_args()

    with SessionLocal() as db:
        groups = show(db)
        if not args.apply:
            print("это был показ, ничего не изменено. "
                  "Для удаления добавьте --apply")
        else:
            key = {"both": "и то и другое", "title": "только заголовок",
                   "description": "только описание"}[args.scope]
            purge(db, groups[key])
