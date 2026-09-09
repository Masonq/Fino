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
outerwear, pants, suits, underwear, sportswear, shoes, bags, hats,
gloves, belts, glasses, umbrella, jewelry или unclear.

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
    # Обувь тоже по полу: женские босоножки и мужские ботинки в одной
    # куче искать неудобно.
    ("women", "shoes"): "women-shoes",
    ("men", "shoes"): "men-shoes",
}

# Вещи, которым пол не нужен.
#
# Кеды остаются кедами независимо от того, чьи они, и раздел «Обувь» у
# нас общий. Раньше такие объявления уходили в «не поняла»: нейросеть
# честно писала unclear про пол, и мы их пропускали — хотя вид вещи она
# определила верно.
GENDERLESS = {
    # Обуви здесь нет: у неё теперь свои разделы внутри пола. Если пол
    # не определился, обувь уйдёт в общий раздел ниже — он оставлен как
    # запасной, пока живых объявлений от людей мало.
    "bags": "bags",
    "hats": "hats-scarves",
    "gloves": "gloves",
    "belts": "belts",
    "glasses": "glasses",
    "umbrella": "umbrellas",
    "jewelry": "watches",
}


# Куда класть вещь, если пол не определился, а вид понятен.
FALLBACK = {"shoes": "shoes"}


def run(apply: bool, limit: int) -> None:
    from app.core.ai_title import ask_photo
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

            # Пробуем дважды.
            #
            # Треть снимков не укладывалась даже в шестьдесят секунд, и
            # объявление просто терялось. Вторая попытка обычно
            # проходит: нейросеть не отказывает, она бывает занята.
            answer = ask_photo(f"{PROMPT}\n\nЗаголовок: {title}", data)
            if not answer:
                answer = ask_photo(f"{PROMPT}\n\nЗаголовок: {title}", data)

            if not answer:
                unclear += 1
                continue

            # Ищем свои слова где угодно в ответе.
            #
            # Модель бывает многословна: то обернёт ответ в кавычки, то
            # начнёт с пояснения. Просить её молчать бесполезно —
            # проще найти в тексте то, что нам нужно.
            words = answer.strip().lower().replace('"', " ").split()
            gender = next((w for w in words if w in ("women", "men")), None)
            kinds = {k[1] for k in SECTIONS} | set(GENDERLESS)
            kind = next((w for w in words if w in kinds), None)

            if not kind:
                unclear += 1
                print(f"  ? {title[:44]:46s} — {answer.strip()[:40]}")
                continue

            # Обувь, сумки и аксессуары кладём без оглядки на пол: раздел
            # у них общий.
            if kind in GENDERLESS:
                target = GENDERLESS[kind]
            elif gender:
                target = SECTIONS.get((gender, kind))
            elif kind in FALLBACK:
                # Пол не определился, но вещь ясна: кладём в общий
                # раздел. Обувь без пола в «Обуви» лучше, чем в
                # «Одежде» вперемешку с платьями.
                target = FALLBACK[kind]
            else:
                unclear += 1
                print(f"  ? {title[:44]:46s} — пол не ясен ({kind})")
                continue
            if not target or target not in slugs:
                unclear += 1
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
