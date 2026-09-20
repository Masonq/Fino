"""
Комнаты в объявлениях — из чисел в словарь списка.

    python3 -m app.core.fix_rooms            показать
    python3 -m app.core.fix_rooms --apply    записать

Поле «Комнат» стало списком (студия, 1, 1.5, 2 …), а в объявлениях лежат
числа: 2, а не «2». Повторный запуск ничего не меняет.
"""
import argparse

from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.data.schemas import rooms_value
from app.models import Listing


def run(apply: bool) -> int:
    db = SessionLocal()
    changed = dropped = 0
    try:
        rows = db.query(Listing).filter(Listing.attributes.has_key("rooms")).all()  # noqa: W601
        for listing in rows:
            raw = listing.attributes.get("rooms")
            value = rooms_value(raw)
            if value == raw:
                continue
            if value is None:
                dropped += 1
                print(f"  {listing.id}: {raw!r} — не комнаты, убираю")
            changed += 1
            if apply:
                attrs = dict(listing.attributes)
                if value is None:
                    attrs.pop("rooms")
                else:
                    attrs["rooms"] = value
                listing.attributes = attrs
                flag_modified(listing, "attributes")
        if apply:
            db.commit()
        print(f"комнаты: {'исправлено' if apply else 'к исправлению'} {changed}"
              f" из {len(rows)}, из них убрано {dropped}")
        return changed
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
