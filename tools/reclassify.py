#!/usr/bin/env python3
"""
Переставляет объявления по правильным разделам и подразделам.

tg_classify.py (через recategorize из tg_import.py) умеет определять и
категорию, и подкатегорию по тексту — но раньше это применялось только
один раз, в момент переноса объявления из телеграм-чата. Тема чата
обманывает регулярно (человек написал не в ту тему), а разбор с тех пор
мог и обучиться на новых данных (train-categories.py переобучает модель
по мере разметки). Этот скрипт прогоняет тот же разбор по уже
существующим объявлениям и подтягивает раздел к тому, что говорит текст,
а не история переноса.

Трогает только объявления, перенесённые из телеграм-чатов
(external_source не пусто): у объявлений, которые человек разместил сам и
выбрал раздел вручную, выбор не оспариваем — это его решение, а не догадка
парсера.

    python tools/reclassify.py --limit 300     # посмотреть, что изменится
    python tools/reclassify.py --apply         # применить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_import import recategorize  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=30)
    args = ap.parse_args()

    with SessionLocal() as db:
        categories = {c.slug: c for c in db.query(Category).all()}
        by_id = {c.id: c for c in categories.values()}

        query = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source.isnot(None))
            .order_by(Listing.created_at.desc())
        )
        if args.limit:
            query = query.limit(args.limit)
        rows = query.all()

        moves = Counter()
        changes = []

        for number, (listing, translation) in enumerate(rows, 1):
            title = translation.title or ""
            body = translation.description or ""
            current = by_id.get(listing.category_id)
            current_slug = current.slug if current else None
            current_parent = by_id.get(current.parent_id) if current and current.parent_id else None
            current_top = current_parent.slug if current_parent else current_slug

            guessed_top, guessed_sub = recategorize(title, body, current_top)
            if not guessed_top or guessed_top not in categories:
                continue

            target_slug = guessed_sub if (guessed_sub and guessed_sub in categories) else guessed_top
            if target_slug == current_slug:
                continue

            moves[f"{current_top or '—'} -> {guessed_top}"] += 1
            changes.append((listing, translation, target_slug, current_slug))

            if number % 100 == 0:
                print(f"  разобрано {number} из {len(rows)}…")

        print(f"\nобъявлений (из телеграм-чатов): {len(rows)}")
        print(f"переедет: {len(changes)}")
        for move, count in moves.most_common(20):
            print(f"  {move}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, translation, target_slug, current_slug in changes[:args.show]:
            title = (translation.title or "")[:60]
            print(f"  [{current_slug or '—'} -> {target_slug}] {title}")

        if not args.apply:
            print("\nэто был сухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, translation, target_slug, current_slug in changes:
            listing.category_id = categories[target_slug].id
        db.commit()
        print(f"\nпереставлено: {len(changes)}")


if __name__ == "__main__":
    main()
