"""
Чинит непонятные заголовки, глядя на фотографию.

«Серый новый -700 XL», «Одежда, размер 32, Врачар», «Майк с Тему» —
человек не поймёт, что продают, пока не откроет. Сто пятьдесят таких
помечены безнадёжными и ждут удаления: нейросеть не смогла собрать
заголовок из описания, потому что описания часто нет вовсе.

Но есть фотография. На ней видно вещь, а иногда и размер с ярлыка.
Разбор одежды по снимкам это уже показал: нейросеть отличает блузку от
футболки и балетки от кед.

Что делаем: показываем ей снимок и просим назвать вещь так, как назвал
бы продавец. Из ответа собираем заголовок, добавляя размер и марку,
если они были в старом.

Осторожность:

  • не уверена — оставляем как есть. Плохой заголовок лучше неверного:
    «Свитер» вместо кроссовок отпугнёт того, кому кроссовки нужны;

  • берём только помеченные безнадёжными: у остальных заголовок и так
    сносный, а запас нейросети невелик;

  • пометку снимаем при успехе, чтобы объявление не удалили ночью;

  • ничего не меняем без ключа --apply.

Запуск:
    python3 -m app.core.retitle_by_photo --limit 20
    python3 -m app.core.retitle_by_photo --limit 20 --apply
"""
import argparse
import os
import re

from sqlalchemy import text

from app.core.database import SessionLocal

PROMPT = """Посмотри на фотографию и назови вещь так, как назвал бы её
продавец в объявлении.

Правила:
— пиши по-русски, с большой буквы;
— два-четыре слова: что это и какое («Свитер шерстяной серый»);
— не выдумывай марку, размер и состояние: только то, что видно;
— если на снимке не одна вещь, а несколько — назови главную;
— если не понимаешь, что на снимке, ответь одним словом: unclear.

Больше ничего не пиши: только название."""

# Что вынимаем из старого заголовка, чтобы не потерять.
SIZE_RE = re.compile(r"\b(XS|S|M|L|XL|XXL|\d{2,3}\s?(размер|р-р|см))\b", re.I)


def run(apply: bool, limit: int) -> None:
    from app.core.ai_title import ask_photo
    from app.core.config import settings
    from app.core.retitle import FAILED_ACTION
    from app.models import (AuditEntry, Listing, ListingPhoto, ListingStatus,
                            ListingTranslation)

    with SessionLocal() as db:
        hopeless = [
            row[0] for row in db.execute(text(
                "select distinct target_id from audit_log where action = :a"),
                {"a": FAILED_ACTION})
        ]
        if not hopeless:
            print("безнадёжных заголовков нет")
            return

        rows = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.active,
                    Listing.id.in_(hopeless))
            .limit(limit)
            .all()
        )

        fixed = unclear = skipped = 0
        for listing in rows:
            tr = next((t for t in listing.translations
                       if t.language == "ru"), None)
            if not tr or not tr.title:
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

            path = os.path.join(settings.media_dir, photo.url.rsplit("/", 1)[-1])
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                skipped += 1
                continue

            answer = ask_photo(PROMPT, data) or ask_photo(PROMPT, data)
            if not answer or "unclear" in answer.lower():
                unclear += 1
                continue

            name = " ".join(answer.strip().strip('"').split())[:60]
            if len(name) < 4:
                unclear += 1
                continue

            # Размер из старого заголовка дописываем: он там был не зря.
            size = SIZE_RE.search(tr.title or "")
            if size and size.group(0).lower() not in name.lower():
                name = f"{name}, {size.group(0)}"

            print(f"  {tr.title[:34]:36s} → {name}")
            fixed += 1

            if apply:
                tr.title = name
                # Пометку снимаем: заголовок починен, удалять объявление
                # ночью больше не за что.
                db.query(AuditEntry).filter(
                    AuditEntry.action == FAILED_ACTION,
                    AuditEntry.target_id == str(listing.id),
                ).delete(synchronize_session=False)

        if apply:
            db.commit()

        print()
        print(f"починено: {fixed}")
        print(f"не поняла: {unclear}")
        print(f"пропущено (без фото): {skipped}")
        if not apply:
            print("\nэто был показ, ничего не записано. "
                  "Для починки — с ключом --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run(args.apply, args.limit)
