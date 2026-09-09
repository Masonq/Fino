"""
Раскладывает объявления по подразделам — прямо в нашей базе.

Разделов мы завели много, а раскладка при переносе о половине не знала:
холодильники, пылесосы, освещение, сантехника, няни, переводы, детский
транспорт валились в родительский раздел. Слова для них теперь
написаны, но накопившееся так и лежит не на своих местах.

Тот скрипт, что был раньше (tools/tg-reimport.py), ходит за
объявлениями в Telegram — это долго и требует связи. Здесь мы работаем
с тем, что уже есть у нас.

Что делает: берёт объявления, лежащие в разделе верхнего уровня или в
разделе с подразделами, и смотрит, не подходит ли какой-то подраздел
точнее. Подходит — переносит.

Чего не делает:

  • не трогает то, что переносили руками. В журнале есть запись
    listing.move, и живое решение сильнее угаданного;

  • не переносит из подраздела в подраздел. Если объявление уже лежит
    в «Мониторах», а раскладка думает про «Телевизоры» — оставляем:
    кто-то мог положить его туда осознанно, а ошибку в подразделе
    видно и глазами;

  • ничего не меняет без ключа --apply.

Запуск:
    python3 -m app.core.resort_listings            # показать
    python3 -m app.core.resort_listings --apply    # перенести
"""
import argparse
from collections import Counter

from sqlalchemy import text

from app.core.database import SessionLocal


def run(apply: bool, limit: int) -> None:
    from app.core.tg_classify import classify_sub
    from app.models import AuditEntry, Category, Listing, ListingStatus

    with SessionLocal() as db:
        # Разделы, у которых есть подразделы: объявление в таком разделе
        # почти наверняка можно уложить точнее.
        parents = {
            row[0]: row[1] for row in db.execute(text("""
                select c.id, c.slug from categories c
                where exists (select 1 from categories k where k.parent_id = c.id)
            """))
        }
        slugs = {row[1]: row[0] for row in db.execute(text(
            "select id, slug from categories"))}

        rows = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.active,
                    Listing.category_id.in_(list(parents)))
            .limit(limit)
            .all()
        )

        # Что переносили руками — не трогаем.
        moved_by_hand = {
            row[0] for row in db.execute(text(
                "select distinct target_id from audit_log "
                "where action = 'listing.move'"))
        }

        plan = []
        for listing in rows:
            if str(listing.id) in moved_by_hand:
                continue

            title = ""
            if listing.translations:
                title = next((t.title for t in listing.translations
                              if t.language == "ru" and t.title), "")
            if not title:
                continue

            parent_slug = parents[listing.category_id]
            guess = classify_sub(parent_slug, title.lower())
            if not guess or guess not in slugs or slugs[guess] == listing.category_id:
                continue

            plan.append((listing, parent_slug, guess, title))

        counts = Counter((p, g) for _, p, g, _ in plan)
        print(f"объявлений в разделах с подразделами: {len(rows)}")
        print(f"переедет: {len(plan)}\n")

        for (parent, target), count in counts.most_common():
            print(f"  {parent} → {target}: {count}")
            shown = [t for _, p, g, t in plan if p == parent and g == target][:3]
            for title in shown:
                print(f"      {' '.join(title.split())[:56]}")
            print()

        if not apply:
            print("это был показ, ничего не перенесено. "
                  "Для переноса — с ключом --apply")
            return

        for listing, _, target, _ in plan:
            listing.category_id = slugs[target]
        db.commit()
        print(f"перенесено: {len(plan)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()
    run(args.apply, args.limit)
