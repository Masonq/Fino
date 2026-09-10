"""
Убирает чужие ссылки из описаний объявлений.

Объявления приезжают из чатов, и люди оставляют в них ссылки: на свой
магазин, на маркетплейс, иногда на мошеннический сайт. Кликабельными
они у нас не становятся, но проверяющие читают текст страницы и видят
адрес — этого хватает, чтобы связать наш домен с чужим.

Так и вышло: Instagram стал показывать предупреждение о мошенническом
сайте, хотя по всем спискам безопасности plonk.rs чист.

Что делаем: вырезаем адреса из описаний, оставляя остальной текст. Имя
сайта при этом сохраняем словами — «магазин на wildberries» останется
понятным, просто без ссылки, по которой можно перейти.

Чего не трогаем: наши собственные адреса и телеграм-имена — они нужны,
чтобы человек нашёл продавца.

Запуск:
    python3 -m app.core.strip_links            # показать
    python3 -m app.core.strip_links --apply    # вырезать
"""
import argparse
import re

from app.core.database import SessionLocal

# Адреса в тексте. Ловим и с протоколом, и без — «www.shop.rs» и
# «shop.rs/tovar» узнаются так же, как «https://shop.rs».
LINK_RE = re.compile(
    r"""(?xi)
    \b(?:https?://|www\.)[^\s<>"']+
    |
    \b[a-z0-9][a-z0-9-]{1,60}\.(?:com|net|org|ru|rs|shop|store|site|online|
       info|biz|xyz|top|click|link|me|io|co|app)\b(?:/[^\s<>"']*)?
    """
)

# Свои адреса не трогаем: по ним человек находит нас же.
OURS = re.compile(r"(?i)\b(plonk\.rs|t\.me/|telegram\.me/)")


def clean(text: str) -> str:
    """Убирает чужие адреса, оставляя остальной текст."""
    if not text:
        return text

    def drop(match: re.Match) -> str:
        found = match.group(0)
        if OURS.search(found):
            return found

        # Имя сайта оставляем словом: «магазин на wildberries» без
        # адреса всё ещё понятно, а перейти по нему нельзя.
        host = re.sub(r"^https?://", "", found, flags=re.I)
        host = re.sub(r"^www\.", "", host, flags=re.I)
        name = host.split("/")[0].split(".")[0]
        return name if len(name) > 2 else ""

    cleaned = LINK_RE.sub(drop, text)
    # Пробелы после вырезания приводим в порядок.
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def run(apply: bool, limit: int) -> None:
    from app.models import Listing, ListingStatus, ListingTranslation

    with SessionLocal() as db:
        rows = (
            db.query(ListingTranslation)
            .join(Listing, Listing.id == ListingTranslation.listing_id)
            .filter(Listing.status == ListingStatus.active,
                    ListingTranslation.description.isnot(None))
            .limit(limit)
            .all()
        )

        changed = 0
        for tr in rows:
            fixed = clean(tr.description)
            if fixed == tr.description:
                continue

            was = " ".join((tr.description or "").split())
            now = " ".join(fixed.split())
            print(f"  {was[:46]:48s} → {now[:46]}")
            changed += 1
            if apply:
                tr.description = fixed

        if apply:
            db.commit()

        print()
        print(f"просмотрено: {len(rows)}")
        print(f"вычищено: {changed}")
        if not apply:
            print("\nэто был показ, ничего не записано. "
                  "Для правки — с ключом --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=100000)
    args = parser.parse_args()
    run(args.apply, args.limit)
