"""
Пишет марки в заголовках с большой буквы.

«палатка quechua arpenaz», «монитор iiyama», «юбка maccain sport» —
латиница строчными выглядит небрежно, будто человек торопился и не
перечитал. А марка это первое, за что цепляется глаз при выборе.

Новые заголовки правятся при починке (retitle.py и retitle_by_photo.py),
а этот проход — для тех, что уже лежат в базе.

Правило не трогает: модели с цифрами («g2730hsu», «m1»), единицы («gb»,
«mm»), слова, уже написанные заглавными целиком («SHEIN»), и
устоявшиеся написания — «MacBook» не станет «Macbook».

Запуск:
    python3 -m app.core.fix_brand_case            # показать
    python3 -m app.core.fix_brand_case --apply    # поправить
"""
import argparse

from app.core.database import SessionLocal


def run(apply: bool, limit: int) -> None:
    from app.core.title_rules import capitalize_brands
    from app.models import Listing, ListingStatus, ListingTranslation

    with SessionLocal() as db:
        rows = (
            db.query(ListingTranslation)
            .join(Listing, Listing.id == ListingTranslation.listing_id)
            .filter(Listing.status == ListingStatus.active,
                    ListingTranslation.title.isnot(None))
            .limit(limit)
            .all()
        )

        changed = 0
        for tr in rows:
            fixed = capitalize_brands(tr.title)
            if fixed == tr.title:
                continue

            print(f"  {tr.title[:42]:44s} → {fixed[:42]}")
            changed += 1
            if apply:
                tr.title = fixed

        if apply:
            db.commit()

        print()
        print(f"просмотрено: {len(rows)}")
        print(f"поправлено: {changed}")
        if not apply:
            print("\nэто был показ, ничего не записано. "
                  "Для правки — с ключом --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=100000)
    args = parser.parse_args()
    run(args.apply, args.limit)
