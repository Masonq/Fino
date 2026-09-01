"""
Приводит заголовки уже опубликованных квартир к единому формату —
«N-комнатная квартира, X м²» — тому же, что теперь собирается сам на
шаге размещения (см. isApartment в PostAd.jsx) и что уже давно
собирает разбор объявлений из Telegram (compose_title в tg_parse.py).

Категория определяется не по жёсткому слагу 'flats', а по самой схеме
атрибутов (area_m2 + rooms) — так же, как и на сайте: подхватит любой
будущий похожий подраздел без правки скрипта.

Без площади заголовок не собрать — такие объявления пропускаются и
перечисляются в конце отдельно, руками их не трогаем.

Запуск на сервере:
    cd /opt/fino/backend && source venv/bin/activate && python3 ../tools/normalize_apartment_titles.py
    (добавь --dry-run, чтобы сперва посмотреть, что изменится, не трогая базу)
"""
import sys

sys.path.insert(0, ".")
from app.core.database import SessionLocal
from app.models import Listing, ListingTranslation, Category

TITLE_TEMPLATES = {
    "ru": {"rooms": "{n}-комнатная квартира", "no_rooms": "Квартира", "area": "{head}, {area} м²"},
    "en": {"rooms": "{n}-room apartment", "no_rooms": "Apartment", "area": "{head}, {area} m²"},
    "sr": {"rooms": "Stan sa {n} sobe", "no_rooms": "Stan", "area": "{head}, {area} m²"},
}


def _fmt_num(v):
    """
    4.0 -> '4', 4.5 -> '4.5' — та же терпимость, что и у JS-шаблонных
    строк на фронте (там `${4.0}` сам даёт '4'), Python f-string так
    не умеет и без этого печатал бы «4.0-комнатная квартира».
    """
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(f)
    except (TypeError, ValueError):
        return str(v)


def build_title(lang: str, rooms, area) -> str:
    t = TITLE_TEMPLATES.get(lang, TITLE_TEMPLATES["ru"])
    head = t["rooms"].format(n=_fmt_num(rooms)) if rooms else t["no_rooms"]
    return t["area"].format(head=head, area=_fmt_num(area))


def main(dry_run: bool) -> None:
    db = SessionLocal()

    apartment_category_ids = {
        c.id for c in db.query(Category).all()
        if {"area_m2", "rooms"} <= {f.get("key") for f in (c.attribute_schema or [])}
    }
    if not apartment_category_ids:
        print("Ни одной категории с полями area_m2+rooms не нашлось — проверь схему.")
        db.close()
        return

    listings = (
        db.query(Listing)
        .filter(Listing.category_id.in_(apartment_category_ids))
        .all()
    )
    print(f"Квартир найдено: {len(listings)}")

    skipped_no_area = []
    changed = 0
    unchanged = 0

    for listing in listings:
        area = (listing.attributes or {}).get("area_m2")
        if not area:
            skipped_no_area.append(listing.id)
            continue
        rooms = (listing.attributes or {}).get("rooms")

        translations = (
            db.query(ListingTranslation)
            .filter(ListingTranslation.listing_id == listing.id)
            .all()
        )
        for tr in translations:
            new_title = build_title(tr.language, rooms, area)
            if tr.title == new_title:
                unchanged += 1
                continue
            changed += 1
            if dry_run:
                print(f"  [{tr.language}] {tr.title!r} -> {new_title!r}")
            else:
                tr.title = new_title

    if not dry_run:
        db.commit()
    db.close()

    print(f"\n{'Изменилось бы' if dry_run else 'Изменено'} переводов заголовка: {changed}")
    print(f"Уже в нужном формате: {unchanged}")
    print(f"Пропущено без площади: {len(skipped_no_area)}")
    if skipped_no_area:
        print("  id объявлений без площади (не трогали):")
        for lid in skipped_no_area[:20]:
            print(f"    {lid}")
        if len(skipped_no_area) > 20:
            print(f"    ...и ещё {len(skipped_no_area) - 20}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
