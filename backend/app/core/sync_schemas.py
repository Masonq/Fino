"""
Схемы полей подразделов — из кода в базу.

    python3 -m app.core.sync_schemas            показать, что изменится
    python3 -m app.core.sync_schemas --apply    записать
    python3 -m app.core.sync_schemas --apply --all   и переписать отличающиеся

Без --all заполняем только пустые схемы: если у раздела в базе схема уже
есть и она не совпадает с кодом, значит, её правили на месте — молча
затирать это при каждой выкладке нельзя, только показываем расхождение.

Отдельно от seed_categories.py намеренно: тот заодно переписывает
названия, порядок и родителей, а на живой базе разделы уже двигали и
сливали вручную. Здесь трогаем одно поле — attribute_schema — и только у
разделов, перечисленных в SUB_SCHEMAS.

Объявления не трогаем: атрибуты, заполненные по старой схеме, остаются
как есть, лишние просто не показываются в форме.
"""
import argparse

from app.core.database import SessionLocal
from app.data.schemas import SUB_SCHEMAS, SUPERSEDED
from app.models import Category


def run(apply: bool, everything: bool = False) -> int:
    db = SessionLocal()
    changed = 0
    try:
        for slug, schema in sorted(SUB_SCHEMAS.items()):
            cat = db.query(Category).filter(Category.slug == slug).first()
            if cat is None:
                print(f"  нет в базе: {slug}")
                continue
            if (cat.attribute_schema or []) == schema:
                continue
            mine = [f.get("key") for f in (cat.attribute_schema or [])]
            ours_before = SUPERSEDED.get(slug) == mine
            if cat.attribute_schema and not everything and not ours_before:
                # Показываем, чем именно отличается, — иначе строка «не
                # трогаю» ничего не даёт: непонятно, кто прав, база или код.
                code = {f["key"]: f for f in schema}
                base = {f.get("key"): f for f in cat.attribute_schema}
                only_db = [k for k in base if k not in code]
                only_code = [k for k in code if k not in base]
                differ = [k for k in code if k in base and base[k] != code[k]]
                print(f"  {slug}: в базе своя схема — не трогаю")
                if only_db:
                    print(f"      только в базе: {only_db}")
                if only_code:
                    print(f"      только в коде: {only_code}")
                for k in differ:
                    diff = [name for name in sorted(set(base[k]) | set(code[k]))
                            if base[k].get(name) != code[k].get(name)]
                    print(f"      «{k}» отличается в: {diff}")
                if not (only_db or only_code or differ):
                    print("      те же поля, другой порядок")
                continue
            before = [f.get("key") for f in (cat.attribute_schema or [])]
            after = [f["key"] for f in schema]
            print(f"  {slug}: {before or 'от раздела'} → {after}")
            changed += 1
            if apply:
                cat.attribute_schema = schema
        if apply:
            db.commit()
        print(f"{'записано' if apply else 'изменится'}: {changed}"
              + ("" if apply else " (запуск с --apply запишет)"))
        return changed
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    run(args.apply, args.all)
