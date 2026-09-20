"""
Слияние разделов-дублей.

Сеялка новых разделов сверяла их по коду, а не по названию, и завела
шесть пар одного и того же: «Стройматериалы» дважды, «Автосервис и
шиномонтаж» дважды, «Охота и рыбалка» рядом с «Рыбалка и охота» и так
далее. Человек при размещении видел два одинаковых раздела и выбирал
наугад, а объявления одной темы расходились по двум полкам.

Оставляем раздел из основного справочника (app/data/subcategories.py),
дубль убираем. Перед удалением переносим на оставшийся всё, что на дубле
висит: подразделы, объявления и сохранённые поиски.

Запуск:
    python3 -m app.core.merge_duplicate_categories            # показать
    python3 -m app.core.merge_duplicate_categories --apply    # слить
"""
import argparse

from sqlalchemy import text

from app.core.database import SessionLocal

# (оставить, убрать)
PAIRS = [
    ("water", "boats"),
    ("building", "building-materials"),
    ("auto-services", "car-service"),
    ("childcare", "nannies"),
    ("fishing-hunting", "hunting-fishing"),
    ("components", "pc-parts"),
]


def run(apply: bool) -> None:
    db = SessionLocal()
    try:
        done = 0
        for keep_slug, drop_slug in PAIRS:
            keep = db.execute(text("select id, name->>'ru' from categories where slug=:s"), {"s": keep_slug}).first()
            drop = db.execute(text("select id, name->>'ru' from categories where slug=:s"), {"s": drop_slug}).first()
            if not drop:
                print(f"  · {drop_slug}: уже нет — пропускаю")
                continue
            if not keep:
                # Сливать не во что: оставляем как есть,
                # лучше дубль, чем потерянный раздел.
                print(f"  ! {keep_slug}: основного раздела нет — {drop_slug} не трогаю")
                continue

            kids = db.execute(text("select count(*) from categories where parent_id=:d"), {"d": drop.id}).scalar()
            ads = db.execute(text("select count(*) from listings where category_id=:d"), {"d": drop.id}).scalar()
            searches = db.execute(
                text("select count(*) from saved_searches where filters->>'category_slug'=:s"), {"s": drop_slug}
            ).scalar()
            print(f"  {drop[1]} ({drop_slug}) → {keep[1]} ({keep_slug}): "
                  f"подразделов {kids}, объявлений {ads}, сохранённых поисков {searches}")

            if not apply:
                continue
            db.execute(text("update categories set parent_id=:k where parent_id=:d"), {"k": keep.id, "d": drop.id})
            db.execute(text("update listings set category_id=:k where category_id=:d"), {"k": keep.id, "d": drop.id})
            db.execute(
                text("update saved_searches set filters = jsonb_set(filters::jsonb, '{category_slug}', to_jsonb(cast(:k as text)))"
                     " where filters->>'category_slug'=:s"),
                {"k": keep_slug, "s": drop_slug},
            )
            db.execute(text("delete from categories where id=:d"), {"d": drop.id})
            done += 1

        if apply:
            db.commit()
            print(f"\nслито пар: {done}")
        else:
            print("\nэто показ, ничего не менялось. Для слияния — с ключом --apply")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
