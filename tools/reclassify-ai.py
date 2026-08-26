#!/usr/bin/env python3
"""
Переклассификация нейросетью — для того, что словарные правила не берут.

reclassify.py (правила и словари) разбирает почти всё и делает это
бесплатно и мгновенно — его не заменяем. Но у него есть потолок: он
смотрит на отдельные слова, а не на смысл, и «компьютерное кресло»
неизбежно цепляет слово «компьютер», сколько запретов ни пиши. Модель же
читает объявление целиком и понимает, что кресло — это кресло.

Поэтому здесь не полный проход по 1655 объявлениям (это упёрлось бы в
дневной лимит бесплатных ключей за один заход), а точечная проверка —
только те объявления, где reclassify.py показал переезд. Стадии те же
две, что и у него: сначала раздел, потом подраздел внутри уже названного
раздела — так меньше вариантов на каждом шаге, и модель реже путается.

    python tools/reclassify-ai.py --limit 60      # сухой прогон
    python tools/reclassify-ai.py --limit 60 --apply
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.ai_title import guess_category, available as ai_available  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=60,
                     help="сколько объявлений спросить у модели за раз — упирается в дневной лимит ключей")
    args = ap.parse_args()

    if not ai_available():
        print("Нет ни одного настроенного и не исчерпанного ключа "
              "(gemini/groq/mistral/openrouter) — спрашивать не у кого.")
        return

    with SessionLocal() as db:
        all_categories = db.query(Category).all()
        by_id = {c.id: c for c in all_categories}
        top_slugs = [c.slug for c in all_categories if c.parent_id is None]
        subs_by_top: dict[str, list[str]] = {}
        for c in all_categories:
            if c.parent_id and by_id.get(c.parent_id):
                subs_by_top.setdefault(by_id[c.parent_id].slug, []).append(c.slug)
        by_slug = {c.slug: c for c in all_categories}

        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source.isnot(None))
            .order_by(Listing.created_at.desc())
            .limit(args.limit)
            .all()
        )

        changes = []
        asked = 0
        for listing, translation in rows:
            title = translation.title or ""
            body = translation.description or ""
            text = f"{title}\n{body}".strip()
            if len(text) < 15:
                continue

            current = by_id.get(listing.category_id)
            current_slug = current.slug if current else None
            current_parent = by_id.get(current.parent_id) if current and current.parent_id else None
            current_top = current_parent.slug if current_parent else current_slug

            asked += 1
            guessed_top = guess_category(text, top_slugs)
            if not guessed_top:
                if not ai_available():
                    print(f"  ! ключи исчерпаны на «{title[:50]}» — останавливаюсь, дальше не спросить")
                    break
                # Модель ответила, но не смогла подобрать раздел — само
                # объявление, а не нехватка запроса. Пропускаем его одного,
                # а не весь оставшийся список.
                continue

            target_slug = guessed_top
            subs = subs_by_top.get(guessed_top)
            if subs:
                guessed_sub = guess_category(text, subs)
                if guessed_sub:
                    target_slug = guessed_sub

            if target_slug == current_slug or target_slug not in by_slug:
                continue

            changes.append((listing, target_slug, current_slug, title[:55]))
            print(f"  [{current_slug or '—'} -> {target_slug}] {title[:55]}")

        print(f"\nспрошено: {asked}")
        print(f"переедет: {len(changes)}")

        if not args.apply:
            print("\nсухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, target_slug, current_slug, title in changes:
            listing.category_id = by_slug[target_slug].id
        db.commit()
        print(f"\nпереставлено: {len(changes)}")


if __name__ == "__main__":
    main()
