#!/usr/bin/env python3
"""
Сверяет ВЕРХНЕУРОВНЕВУЮ категорию каждого объявления с тем, что сейчас
выдаёт classify() (тот же разбор, что при импорте из Telegram — модель
+ словарные правила). Только отчёт, без --apply: правильный перенос
между разделами верхнего уровня — другая операция, чем между
подразделами (меняются admin допустимые атрибуты, deal_type и т.п.),
и объём тут должен быть небольшим — если он большой, это сигнал
перепроверить сам classify(), а не просто гнать перенос.

    python tools/audit-top-category.py
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_classify import classify  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        categories = {c.id: c for c in db.query(Category).all()}
        top_level = {c.id: c for c in categories.values() if c.parent_id is None}

        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source.isnot(None))
            .all()
        )

        changes = []
        moves = Counter()

        for listing, translation in rows:
            cat = categories.get(listing.category_id)
            parent = categories.get(cat.parent_id) if cat and cat.parent_id else None
            top = parent or cat
            if not top or top.id not in top_level:
                continue

            text = f"{translation.title or ''}\n{translation.description or ''}"
            guessed, score = classify(text)
            if not guessed or guessed == top.slug or score < 2:
                # Слабый сигнал (score<2) не считаем расхождением — это
                # ровно тот порог, которым сам импорт решает, доверять
                # ли разбору текста или оставить как есть.
                continue

            moves[f"{top.slug} -> {guessed}"] += 1
            changes.append((listing, translation, top.slug, guessed, score))

        print(f"объявлений всего (из телеграм-чатов): {len(rows)}")
        print(f"расхождений с текущей категорией: {len(changes)}")
        for move, count in moves.most_common(30):
            print(f"  {move}: {count}")

        print("\nпримеры (первые 40):")
        for listing, translation, old_slug, new_slug, score in changes[:40]:
            title = (translation.title or "")[:60]
            print(f"  [{old_slug} -> {new_slug}, уверенность {score}] {title}")

        print("\nЭто только отчёт — переносить между верхними разделами руками, "
              "после проверки каждого случая. Не --apply.")


if __name__ == "__main__":
    main()
