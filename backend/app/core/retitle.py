"""
Переписывание непонятных заголовков.

В ленте копятся названия, по которым не понять, что продают:
«Электроника», «Продам», «Чикнула свой фикус — слишком разросся»,
«Hutschenreuther». Само объявление при этом нормальное — предмет назван
в описании, просто заголовком стала первая строка поста.

Порядок такой:

1. Правила (build_title). Они собирают название из фактов описания и
   ничего не стоят. Ими же строятся заголовки при переносе из чатов,
   так что результат будет привычного вида.
2. Нейросеть — только для того, с чем правила не справились. Провайдеры
   и лимиты берутся из ai_title.py: там уже есть очередь из нескольких
   ключей и переход на следующего, когда у одного кончился запас.

Что получилось, проверяем тем же title_is_clear, которым отбирали:
новый заголовок должен быть понятнее старого, иначе оставляем как было.
Менять плохое на другое плохое незачем.

Прежний заголовок пишем в журнал действий — любую правку видно и можно
отследить.

Запуск (сначала вхолостую, ничего не меняя):
    python3 -m app.core.retitle --dry-run
    python3 -m app.core.retitle --limit 50
"""
import argparse

from app.core.ai_title import improve
from app.core.audit import record
from app.core.database import SessionLocal
from app.core.tg_parse import build_title
from app.models import Category, Listing, ListingStatus, ListingTranslation

# Сколько объявлений разбираем за прогон. Ограничение бережёт суточный
# запас у провайдеров: он общий с переносом объявлений из чатов, и
# выбрать его весь одной уборкой значило бы оставить без заголовков
# новые объявления, которые приедут ночью.
DEFAULT_LIMIT = 50


def _candidates(db, limit: int):
    """Активные объявления, чей русский заголовок ничего не говорит."""
    from app.routers.listings import title_is_clear

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(
            Listing.status == ListingStatus.active,
            ListingTranslation.language == "ru",
        )
        .all()
    )
    out = [(l, t) for l, t in rows if not title_is_clear(t.title)]
    return out[:limit]


def _better_title(db, listing, translation) -> tuple[str | None, str]:
    """Новый заголовок и то, чем он получен: правилами или моделью."""
    from app.routers.listings import title_is_clear

    text = (translation.description or "").strip()
    if not text:
        # Из пустоты название не сочинить, а выдумывать за продавца
        # нельзя: объявление станет обещать то, чего в нём нет.
        return None, "нет описания"

    category = db.get(Category, listing.category_id)
    parent = db.get(Category, category.parent_id) if category and category.parent_id else None
    root_slug = parent.slug if parent else (category.slug if category else None)
    sub_slug = category.slug if parent else None

    by_rules = build_title(root_slug, sub_slug, text, listing.attributes or {})
    if by_rules and title_is_clear(by_rules):
        return by_rules, "правила"

    answer = improve(text, translation.title)
    title = (answer.get("title") or "").strip()
    if title and title_is_clear(title):
        return title, "нейросеть"

    return None, "не вышло"


def run(limit: int = DEFAULT_LIMIT, dry_run: bool = False) -> int:
    changed = 0
    with SessionLocal() as db:
        items = _candidates(db, limit)
        print(f"непонятных заголовков к разбору: {len(items)}")

        for listing, translation in items:
            new_title, how = _better_title(db, listing, translation)
            if not new_title or new_title == translation.title:
                print(f"  — {translation.title[:40]!r}: {how}")
                continue

            print(f"  {how}: {translation.title[:36]!r} → {new_title[:44]!r}")
            changed += 1
            if dry_run:
                continue

            was = translation.title
            translation.title = new_title[:255]
            db.flush()
            record(
                db, None, "listing_retitled",
                target_type="listing", target_id=str(listing.id),
                was=was, now=new_title, how=how,
            )

        if not dry_run:
            db.commit()

    print(f"{'нашлось бы' if dry_run else 'переписано'}: {changed}")
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true",
                        help="показать, что получилось бы, ничего не меняя")
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)
