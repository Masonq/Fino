"""
Уборка ленты: чиним что можно, убираем что нельзя.

Три шага, по возрастанию необратимости:

1. Город из описания. Из 938 объявлений без города у 217 он написан
   прямо в тексте — просто не попал в поле при переносе. Их надо не
   выбрасывать, а дописать: товар настоящий, продавец живой.
2. Без фото — удаляем. Объявление без картинки на доске мёртвое: его не
   открывают, а место в ленте оно занимает.
3. Без города, где его нет нигде — удаляем. Доска по всей Сербии, и
   вещь неизвестно где никому не нужна.

Чего этот скрипт НЕ делает: не трогает объявления без цены. Больше
половины таких — услуги, ремонт и животные, где цены не бывает вовсе.
«Сантехник» без цены это нормальное объявление, а не мусор.

И не трогает то, по чему уже писали или добавили в избранное: там
завязались люди.

Запуск (сначала показать, потом делать):
    python3 -m app.core.feed_cleanup
    python3 -m app.core.feed_cleanup --apply
"""
import argparse
import os

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.tg_parse import extract_city

LINKED = (
    "listing_photos", "favorites", "reviews", "reports", "promotions",
    "listing_view_logs", "listing_view_daily", "listing_signal_daily",
    "tickets", "review_invites", "listing_translations",
)

NO_PHOTO = """
    select l.id from listings l
    where l.status = 'active'
      and not exists (select 1 from listing_photos p where p.listing_id = l.id)
"""

NO_CITY = """
    select l.id, t.description from listings l
    join listing_translations t on t.listing_id = l.id and t.language = 'ru'
    where l.status = 'active' and (l.city is null or l.city = '')
"""

BUSY = """
    select distinct listing_id from chats where listing_id = any(:ids)
    union
    select distinct listing_id from favorites where listing_id = any(:ids)
"""


def fill_cities(db, apply: bool) -> int:
    """Дописывает город тем, у кого он есть в описании."""
    found = []
    for listing_id, description in db.execute(text(NO_CITY)):
        city = extract_city(description or "")
        if city:
            found.append((listing_id, city))

    print(f"город нашёлся в описании: {len(found)}")
    for listing_id, city in found[:8]:
        print(f"    {str(listing_id)[:8]} → {city}")
    if len(found) > 8:
        print(f"    ... и ещё {len(found) - 8}")

    if apply and found:
        for listing_id, city in found:
            db.execute(text("update listings set city = :c where id = :i"),
                       {"c": city, "i": listing_id})
        db.commit()
    return len(found)


def purge(db, ids, apply: bool, label: str) -> int:
    """Удаляет объявления вместе со всем, что с ними связано."""
    ids = list(ids)
    if not ids:
        print(f"{label}: нечего убирать")
        return 0

    busy = {row[0] for row in db.execute(text(BUSY), {"ids": ids})}
    targets = [i for i in ids if i not in busy]
    print(f"{label}: {len(ids)}, из них с перепиской или в избранном "
          f"{len(busy)} — их оставляем, удалить {len(targets)}")

    if not apply or not targets:
        return len(targets)

    files = [row[0] for row in db.execute(
        text("select url from listing_photos where listing_id = any(:ids)"),
        {"ids": targets})]
    for table in LINKED:
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
    print(f"    удалено: {len(targets)}, снимков стёрто: {len(files)}")
    return len(targets)


def run(apply: bool) -> None:
    with SessionLocal() as db:
        total = db.execute(
            text("select count(*) from listings where status='active'")).scalar()
        print(f"активных объявлений: {total}\n")

        # Сперва город: он спасает часть тех, кто иначе попал бы под
        # удаление следующим шагом.
        fill_cities(db, apply)
        print()

        purge(db, [row[0] for row in db.execute(text(NO_PHOTO))],
              apply, "без фото")
        print()

        still_no_city = [row[0] for row in db.execute(text(NO_CITY))]
        purge(db, still_no_city, apply, "без города (и не нашлось в тексте)")

        if not apply:
            print("\nэто был показ, ничего не изменено. Для уборки добавьте --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="выполнить (удаление необратимо)")
    run(parser.parse_args().apply)
