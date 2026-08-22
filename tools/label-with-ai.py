#!/usr/bin/env python3
"""
Размечает объявления нейросетью — чтобы было на чём учить классификатор.

Первая попытка учить на категориях из базы дала шестьдесят процентов:
метки там расставлены теми же правилами, ошибки которых мы и хотим
исправить. Учиться на собственных ошибках нельзя.

Поэтому разметку делает модель: она читает объявление целиком и называет
раздел. Это медленно и упирается в дневной лимит, зато метки чистые.
Дальше на них обучается наш классификатор — быстрый, бесплатный и
работающий на каждом объявлении. Приём известный: дорогая модель учит
дешёвую, дешёвая работает.

    python tools/label-with-ai.py --limit 300     # разметить 300 штук
    python tools/label-with-ai.py --limit 300     # продолжить с того же места

Размеченное копится в backend/ai-labels.jsonl, повторно не переспрашивается.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.ai_title import guess_category  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_classify import KEYWORDS  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.listing import Listing, ListingTranslation  # noqa: E402

LABELS = Path(__file__).resolve().parents[1] / "backend" / "ai-labels.jsonl"


def already_done() -> set[str]:
    """Что уже размечено — переспрашивать незачем, лимит не резиновый."""
    if not LABELS.exists():
        return set()
    done = set()
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        try:
            done.add(json.loads(line)["id"])
        except (ValueError, KeyError):
            continue
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200,
                    help="сколько объявлений разметить за один раз")
    args = ap.parse_args()

    done = already_done()
    print(f"уже размечено: {len(done)}")

    with SessionLocal() as db:
        rows = (
            db.query(Listing.id, ListingTranslation.title,
                     ListingTranslation.description, Category.slug,
                     Category.parent_id)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .join(Category, Category.id == Listing.category_id)
            .filter(Listing.external_source == "telegram",
                    ListingTranslation.language == "ru")
            .all()
        )
        parents = {c.id: c.slug for c in db.query(Category).all()}

    # Берём по кругу из разных разделов. Подряд получается перекос: в
    # ленте одной одежды треть, и модель учится узнавать её, а про услуги
    # и животных не знает ничего.
    buckets: dict[str, list] = {}
    for listing_id, title, description, slug, parent_id in rows:
        key = parents.get(parent_id) or slug
        buckets.setdefault(key, []).append((listing_id, title, description))
    for items in buckets.values():
        random.shuffle(items)

    rows = []
    while any(buckets.values()):
        for key in list(buckets):
            if buckets[key]:
                rows.append(buckets[key].pop())
            else:
                del buckets[key]

    slugs = list(KEYWORDS)
    added = skipped = 0
    with LABELS.open("a", encoding="utf-8") as fh:
        for listing_id, title, description in rows:
            if added >= args.limit:
                break
            key = str(listing_id)
            if key in done:
                continue
            text = f"{title or ''}\n{description or ''}".strip()
            if len(text) < 25:
                continue

            slug = guess_category(text, slugs)
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
        print(f"модель не определила раздел: {skipped}")
    print(f"всего в наборе: {len(done) + added}")
    print("\nдальше: python tools/train-categories.py --labels")


if __name__ == "__main__":
    main()
