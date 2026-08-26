#!/usr/bin/env python3
"""
Пересчитывает подкатегорию внутри «Электроники» по обновлённым правилам
(classify_sub в tg_classify.py) — раньше «клавиатур» было ключевым словом
«Компьютеров», и туда утаскивало клавиатуры, комплекты клавиатура+мышь+
наушники и прочую периферию, которой там не место. Теперь это слово
(вместе с мышью, роутером, принтером, докстанцией, гарнитурой) ведёт в
«Гаджеты и аксессуары» — подраздел, для этого и заведённый.

Трогает только объявления из телеграм-чатов, у категории — прямая
подкатегория «Электроники» (не сама «Электроника» без подраздела — там
менять нечего, и не другой раздел).

    python tools/backfill-electronics-sub.py            # что изменится
    python tools/backfill-electronics-sub.py --apply     # применить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_classify import classify_sub  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", type=int, default=40)
    args = ap.parse_args()

    with SessionLocal() as db:
        categories = {c.id: c for c in db.query(Category).all()}
        electronics_subs = {c.id: c for c in categories.values()
                             if c.parent_id and categories.get(c.parent_id)
                             and categories[c.parent_id].slug == "electronics"}

        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source.isnot(None))
            .filter(Listing.category_id.in_(electronics_subs.keys()))
            .order_by(Listing.created_at.desc())
            .all()
        )

        changes = []
        moves = Counter()

        for listing, translation in rows:
            current_sub = electronics_subs[listing.category_id]
            text = f"{translation.title or ''}\n{translation.description or ''}"
            fresh_slug = classify_sub("electronics", text)
            if not fresh_slug or fresh_slug == current_sub.slug:
                continue
            fresh_cat = next((c for c in electronics_subs.values() if c.slug == fresh_slug), None)
            if not fresh_cat:
                continue
            moves[f"{current_sub.slug} -> {fresh_slug}"] += 1
            changes.append((listing, translation, current_sub.slug, fresh_cat))

        print(f"объявлений в подразделах «Электроники» (из телеграм-чатов): {len(rows)}")
        print(f"изменится: {len(changes)}")
        for move, count in moves.most_common(20):
            print(f"  {move}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, translation, old_slug, fresh_cat in changes[:args.show]:
            title = (translation.title or "")[:60]
            print(f"  [{old_slug} -> {fresh_cat.slug}] {title}")

        if not args.apply:
            print("\nэто был сухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, translation, old_slug, fresh_cat in changes:
            listing.category_id = fresh_cat.id

        db.commit()
        print(f"\nобновлено: {len(changes)}")


if __name__ == "__main__":
    main()
