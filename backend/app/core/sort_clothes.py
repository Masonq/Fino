"""
Раскладывает одежду по разделам, глядя на фотографию.

В «Одежде» застряли пятьсот объявлений: «Куртка Zara», «Футболка Lime»,
«Джинсы adidas». Вещь названа, а пол — нет, и по заголовку не понять,
женское это или мужское. Раскладка по словам тут бессильна, а разделы
внутри «Женского» и «Мужского» стоят пустыми.

Зато это видно на фотографии. Нейросеть смотрит снимок и отвечает двумя
словами: пол и вид вещи. Из них складывается раздел — «женское» плюс
«куртка» даёт women-outerwear.

Правила осторожности:

  • не уверена — оставляем как есть. Пусть объявление висит в «Одежде»,
    это лучше, чем попасть в мужской раздел женской вещи;

  • объявления без фотографии не трогаем вовсе: смотреть не на что;

  • переносы, сделанные руками, не отменяем — как и везде;

  • ничего не меняем без ключа --apply.

Запуск:
    python3 -m app.core.sort_clothes --limit 20          # показать
    python3 -m app.core.sort_clothes --limit 20 --apply  # перенести
"""
import argparse
import os

from sqlalchemy import text

from app.core.database import SessionLocal

# Что спрашиваем у нейросети. Ответ нужен коротким и предсказуемым:
# длинные рассуждения тут только мешают разбирать.
PROMPT = """Посмотри на фотографию одежды и ответь ровно двумя словами через пробел.

Первое слово — для кого вещь: women, men или unclear.
Второе слово — что это: dresses, skirts, tops, shirts, knitwear,
outerwear, pants, suits, underwear, sportswear или unclear.

Если сомневаешься хоть в чём-то — пиши unclear. Ошибиться хуже, чем
промолчать.

Больше ничего не пиши: только два слова."""

# Из пары «пол + вид» складываем раздел.
SECTIONS = {
    ("women", "dresses"): "women-dresses",
    ("women", "skirts"): "women-skirts",
    ("women", "tops"): "women-tops",
    ("women", "shirts"): "women-shirts",
    ("women", "knitwear"): "women-knitwear",
    ("women", "outerwear"): "women-outerwear",
    ("women", "pants"): "women-pants",
    ("women", "suits"): "women-suits",
    ("women", "underwear"): "women-underwear",
    ("women", "sportswear"): "women-sportswear",
    ("men", "tops"): "men-tops",
    ("men", "shirts"): "men-shirts",
    ("men", "knitwear"): "men-knitwear",
    ("men", "outerwear"): "men-outerwear",
    ("men", "pants"): "men-pants",
    ("men", "suits"): "men-suits",
    ("men", "underwear"): "men-underwear",
    ("men", "sportswear"): "men-sportswear",
}


def run(apply: bool, limit: int) -> None:
    from app.core.ai_title import _ask_gemini_photos
    from app.core.config import settings
    from app.models import Category, Listing, ListingPhoto, ListingStatus

    with SessionLocal() as db:
        fashion = db.query(Category).filter(Category.slug == "fashion").first()
        if not fashion:
            print("раздела «Одежда» нет")
            return

        slugs = {row[1]: row[0] for row in db.execute(text(
            "select id, slug from categories"))}

        moved_by_hand = {
            row[0] for row in db.execute(text(
                "select distinct target_id from audit_log "
                "where action = 'listing.move'"))
        }

        rows = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.active,
                    Listing.category_id == fashion.id)
            .limit(limit)
            .all()
        )

        done = unclear = skipped = 0
        for listing in rows:
            if str(listing.id) in moved_by_hand:
                skipped += 1
                continue

            photo = (
                db.query(ListingPhoto)
                .filter(ListingPhoto.listing_id == listing.id)
                .order_by(ListingPhoto.sort_order)
                .first()
            )
            if not photo:
                skipped += 1
                continue

            path = os.path.join(settings.media_dir,
                                photo.url.rsplit("/", 1)[-1])
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                skipped += 1
                continue

            title = ""
            if listing.translations:
                title = next((t.title for t in listing.translations
                              if t.language == "ru" and t.title), "")

            answer = _ask_gemini_photos(f"{PROMPT}\n\nЗаголовок: {title}", [data])
            if not answer:
                unclear += 1
                continue

            parts = answer.strip().lower().split()
            if len(parts) < 2:
                unclear += 1
                continue

            target = SECTIONS.get((parts[0], parts[1]))
            if not target or target not in slugs:
                unclear += 1
                print(f"  ? {title[:44]:46s} — {' '.join(parts[:2])}")
                continue

            print(f"  → {target:18s} {title[:44]}")
            done += 1
            if apply:
                listing.category_id = slugs[target]

        if apply:
            db.commit()

        print()
        print(f"разобрано: {done}")
        print(f"не поняла: {unclear}")
        print(f"пропущено (без фото или перенесено руками): {skipped}")
        if not apply:
            print("\nэто был показ, ничего не перенесено. "
                  "Для переноса — с ключом --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run(args.apply, args.limit)
