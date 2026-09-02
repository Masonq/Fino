"""
Ежедневная уборка повторов из чатов.

Отсев при переносе работает на входе (см. store в tg_import.py), но
пропускает всё, что он не в силах распознать: снимок переснят,
заголовок переписан, объявление вернулось через месяц — за пределами
окна проверки. Такие повторы копятся в ленте молча.

Правило то же, по которому мы разбирали дубли вручную: одинаковые
автор, заголовок и цена. Совпадение всех трёх у разных вещей — редкость;
у одной и той же вещи, выложенной повторно, — обычное дело.

В группе остаётся одно объявление: активное и самое свежее. Свежее, а
не первое: у объявления недельной давности хуже позиция в ленте и
меньше доверия у покупателя, а речь про одну и ту же вещь.

Остальные архивируются, а не удаляются. Архив обратим: запись остаётся
в базе, открывается по прямой ссылке, просто не висит в ленте. Удалять
молча, по расписанию, без глаз человека — слишком.

Объявления, по которым есть переписка или избранное, не трогаем вовсе:
там уже завязались люди, и прятать такое из ленты нельзя.

Запуск: python3 -m app.core.dedup_sweep
"""
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models import Listing, ListingStatus

# Сколько записей за раз. Ограничение на всякий случай: если правило
# однажды начнёт срабатывать слишком широко, ущерб за один прогон
# останется обозримым, а в журнале это будет видно.
MAX_PER_RUN = 200

DUPLICATES = text("""
    select id from (
        select l.id,
               row_number() over (
                   partition by l.external_author, t.title, coalesce(l.price, -1)
                   order by l.created_at desc, l.external_message_id desc
               ) rn
        from listings l
        join listing_translations t
          on t.listing_id = l.id and t.language = 'ru'
        where l.external_source = 'telegram'
          and l.status = 'active'
          and (l.external_author, t.title, coalesce(l.price, -1)) in (
              select l2.external_author, t2.title, coalesce(l2.price, -1)
              from listings l2
              join listing_translations t2
                on t2.listing_id = l2.id and t2.language = 'ru'
              where l2.external_source = 'telegram' and l2.status = 'active'
              group by 1, 2, 3
              having count(*) > 1
          )
    ) x
    where rn > 1
""")

BUSY = text("""
    select distinct listing_id from chats where listing_id = any(:ids)
    union
    select distinct listing_id from favorites where listing_id = any(:ids)
""")


def sweep() -> int:
    with SessionLocal() as db:
        ids = [row[0] for row in db.execute(DUPLICATES)]
        if not ids:
            print("повторов нет")
            return 0

        busy = {row[0] for row in db.execute(BUSY, {"ids": ids})}
        targets = [i for i in ids if i not in busy][:MAX_PER_RUN]
        if not targets:
            print(f"найдено {len(ids)}, все с перепиской или в избранном — не трогаем")
            return 0

        count = (
            db.query(Listing)
            .filter(Listing.id.in_(targets))
            .update({Listing.status: ListingStatus.archived}, synchronize_session=False)
        )
        db.commit()
        print(f"найдено {len(ids)}, пропущено с перепиской {len(busy)}, "
              f"в архив {count}")
        return count


if __name__ == "__main__":
    sweep()
