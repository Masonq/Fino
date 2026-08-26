#!/usr/bin/env python3
"""
Разбирает очередь объявлений на проверке.

Тысяча триста штук руками не пересмотреть, а одобрять вслепую нельзя:
среди перенесённых из чатов попадаются лекарства, документы и
мошенничество, и отвечать за это будет сайт.

Порядок: правила ловят явное мгновенно и бесплатно, остальное смотрит
нейросеть. Спорное не трогаем — оно остаётся человеку.

    python tools/moderate.py                 # посмотреть, что выйдет
    python tools/moderate.py --apply         # применить
    python tools/moderate.py --limit 100     # разобрать первую сотню
    python tools/moderate.py --rules-only    # без нейросети, быстро
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.moderation_ai import by_rules, check  # noqa: E402
from app.models import (  # noqa: E402
    Listing, ListingStatus, ListingTranslation,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="записать решения")
    ap.add_argument("--limit", type=int, default=0, help="сколько разобрать")
    ap.add_argument("--rules-only", action="store_true",
                    help="только правила, без нейросети")
    ap.add_argument("--show", type=int, default=15)
    args = ap.parse_args()

    with SessionLocal() as db:
        query = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status == ListingStatus.pending_moderation)
            .order_by(Listing.created_at.desc())
        )
        if args.limit:
            query = query.limit(args.limit)
        rows = query.all()

        print(f"на проверке: {len(rows)}")
        if not rows:
            return

        counts = Counter()
        rejected, unsure = [], []

        for number, (listing, translation) in enumerate(rows, 1):
            title = translation.title or ""
            body = translation.description or ""

            if args.rules_only:
                verdict = by_rules(title, body) or ("unsure", "правила молчат")
            else:
                verdict = check(title, body)

            decision, why = verdict
            counts[decision] += 1

            if decision == "reject":
                rejected.append((listing, title, why))
            elif decision == "unsure":
                unsure.append((listing, title, why))
            elif args.apply:
                listing.status = ListingStatus.active

            if args.apply and decision == "reject":
                # В архив, а не удаляем: решение принимала машина, и
                # человек должен иметь возможность его пересмотреть.
                listing.status = ListingStatus.archived

            if not args.rules_only and number % 25 == 0:
                print(f"  разобрано {number} из {len(rows)}…")

        print(f"\nодобрено:    {counts['ok']}")
        print(f"отклонено:   {counts['reject']}")
        print(f"сомнительно: {counts['unsure']}")

        if rejected:
            print(f"\nотклонённые (первые {args.show}):")
            for _, title, why in rejected[:args.show]:
                print(f"  {title[:48]:<50} {why[:40]}")

        if unsure:
            print(f"\nсомнительные остаются человеку "
                  f"(первые {min(5, len(unsure))}):")
            for _, title, why in unsure[:5]:
                print(f"  {title[:48]:<50} {why[:40]}")

        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        db.commit()
        print(f"\nзаписано: одобрено {counts['ok']}, "
              f"отклонено {counts['reject']}")
        print(f"осталось человеку: {counts['unsure']}")


if __name__ == "__main__":
    main()
