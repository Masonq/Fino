"""
Слияние разделов-дублей и правка названий.

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
import json

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
    # Не дубль, а лишняя полка: «Личная гигиена» убрана по решению
    # владельца, её содержимое уходит в соседнее «Здоровье и уход».
    ("health", "personal-hygiene"),
    # «Строительство и ремонт» — двойник «Ремонта и строительства».
    # Сначала листья-двойники, потом сам раздел: оставшиеся ремёсла
    # (плиточник, маляр, столяр, ремонт под ключ) переедут под repair
    # вместе с ним.
    ("repair-plumbing", "con-plumber"),
    ("repair-electrical", "con-electric"),
    ("repair", "construction"),
    # Полки по маркам убраны: объявления уходят в сами «Телефоны».
    ("phones", "phones-iphone"),
    ("phones", "phones-samsung"),
    ("phones", "phones-xiaomi"),
    # Бытовая техника была заведена дважды. Старое дерево —
    # «Крупная техника» и «Мелкая техника» с подразделами внутри (август
    # и начало сентября); сеялка потом добавила те же холодильники и
    # стиралки плоско под саму «Бытовую технику». Сливаем новые плоские
    # в старые, где уже лежат объявления, а не наоборот.
    ("fridges", "app-fridge"),
    ("washing-machines", "app-washer"),
    ("stoves-ovens", "app-stove"),
    ("dishwashers", "app-dishwasher"),
    ("climate", "app-climate"),
    ("appliances-small", "app-small"),
    # Фен, плойка, машинка для стрижки — это красота, а не бытовая
    # техника: «Приборы для красоты» в разделе личных вещей существуют с
    # августа и ловили ровно те же слова. Полка в технике заведена
    # позже и только оттягивала на себя половину объявлений.
    ("beauty-devices", "personal-care-devices"),
]

# Новые названия для уже заведённых разделов. Сеялка названий не
# обновляет — она только добавляет недостающее по коду.
RENAMES = {
    # Было «Посуточно и на отдых» — читалось как обрывок фразы.
    "daily-rent": {"ru": "Посуточная аренда", "en": "Short-term rentals", "sr": "Izdavanje na dan"},
}


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
            # Переехавшие подразделы встают в конец списка, а не вперемешку
            # с хозяйскими: порядок у обоих наборов начинался с нуля.
            base = db.execute(
                text("select coalesce(max(sort_order), -1) + 1 from categories where parent_id=:k"), {"k": keep.id}
            ).scalar()
            db.execute(
                text("update categories set parent_id=:k, sort_order=sort_order+:b where parent_id=:d"),
                {"k": keep.id, "d": drop.id, "b": base},
            )
            db.execute(text("update listings set category_id=:k where category_id=:d"), {"k": keep.id, "d": drop.id})
            db.execute(
                text("update saved_searches set filters = jsonb_set(filters::jsonb, '{category_slug}', to_jsonb(cast(:k as text)))"
                     " where filters->>'category_slug'=:s"),
                {"k": keep_slug, "s": drop_slug},
            )
            db.execute(text("delete from categories where id=:d"), {"d": drop.id})
            done += 1

        renamed = 0
        for slug, name in RENAMES.items():
            row = db.execute(text("select name->>'ru' from categories where slug=:s"), {"s": slug}).first()
            if not row:
                print(f"  · {slug}: раздела нет — пропускаю")
                continue
            if row[0] == name["ru"]:
                continue
            print(f"  {row[0]} → {name['ru']} ({slug})")
            if apply:
                db.execute(
                    text("update categories set name = cast(:n as jsonb) where slug=:s"),
                    {"n": json.dumps(name, ensure_ascii=False), "s": slug},
                )
                renamed += 1

        if apply:
            db.commit()
            print(f"\nслито пар: {done}, переименовано: {renamed}")
        else:
            print("\nэто показ, ничего не менялось. Для слияния — с ключом --apply")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
