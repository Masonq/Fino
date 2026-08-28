#!/usr/bin/env python3
"""
Размечает подкатегории нейросетью — для одного родительского раздела.

Тот же приём, что у label-with-ai.py на верхнем уровне (дорогая модель
учит дешёвую), только кандидаты — подкатегории конкретного родителя,
не все шестьдесят разом. Одна модель на всё путала бы «Авто» с
«Детьми» без всякой пользы: словари разных родителей не пересекаются
вовсе, и учить их вместе — не экономия, а помеха.

    python tools/label-subcategories-with-ai.py electronics --limit 300
    python tools/label-subcategories-with-ai.py electronics --limit 300   # продолжить

Размеченное копится в backend/ai-labels-sub-<родитель>.jsonl, повторно
не переспрашивается.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.ai_title import guess_category  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.listing import Listing, ListingTranslation  # noqa: E402

LABELS_DIR = Path(__file__).resolve().parents[1] / "backend"


def already_done(path: Path) -> set[str]:
    """Что уже размечено — переспрашивать незачем, лимит не резиновый."""
    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            done.add(json.loads(line)["id"])
        except (ValueError, KeyError):
            continue
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("parent_slug", help="родительский раздел, например electronics")
    ap.add_argument("--limit", type=int, default=200,
                    help="сколько объявлений разметить за один раз")
    args = ap.parse_args()

    labels_path = LABELS_DIR / f"ai-labels-sub-{args.parent_slug}.jsonl"
    done = already_done(labels_path)
    print(f"уже размечено: {len(done)}")

    with SessionLocal() as db:
        parent = db.query(Category).filter(Category.slug == args.parent_slug).first()
        if not parent or not parent.children:
            raise SystemExit(f"раздел {args.parent_slug!r} не найден или без подкатегорий")
        sub_slugs = [c.slug for c in parent.children]
        # Русское название рядом со слагом — без него нейросеть трактует
        # английское слово по-своему: «gadgets» превращалось в любой
        # гаджет вообще, хотя на сайте это «Товары для компьютера»,
        # раздел куда уже. См. docstring guess_category() в ai_title.py.
        sub_names = {c.slug: (c.name or {}).get("ru", c.slug) for c in parent.children}
        # И то, что уже разложено по подкатегориям (учимся на своих же
        # решениях правил — рискованно), и то, что ещё лежит в
        # родителе — размечаем всё вперемешку, чтобы модель не путала
        # то, что видела, с тем, что не видела вовсе.
        all_ids = {parent.id} | {c.id for c in parent.children}
        rows = (
            db.query(Listing.id, ListingTranslation.title, ListingTranslation.description)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(Listing.category_id.in_(all_ids),
                    ListingTranslation.language == "ru")
            .all()
        )

    random.shuffle(rows)

    added = skipped = 0
    with labels_path.open("a", encoding="utf-8") as fh:
        for listing_id, title, description in rows:
            if added >= args.limit:
                break
            key = str(listing_id)
            if key in done:
                continue
            text = f"{title or ''}\n{description or ''}".strip()
            if len(text) < 25:
                continue

            slug = guess_category(text, sub_slugs, names=sub_names)
            if not slug:
                skipped += 1
                continue
            fh.write(json.dumps({"id": key, "text": text[:1500],
                                 "category": slug}, ensure_ascii=False) + "\n")
            fh.flush()
            added += 1
            if added % 20 == 0:
                print(f"  размечено {added}...")

    print(f"\nразмечено за этот раз: {added}")
    if skipped:
        print(f"модель не определила подкатегорию: {skipped}")
    print(f"всего в наборе: {len(done) + added}")
    print(f"\nдальше: python tools/train-subcategories.py {args.parent_slug}")


if __name__ == "__main__":
    main()
