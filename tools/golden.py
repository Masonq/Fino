#!/usr/bin/env python3
"""
Эталонный набор: замер качества парсера на живых объявлениях.

Тесты проверяют, что не сломались известные случаи. Но они ничего не
говорят о главном: стало ли лучше в целом. Каждая правка чинит один
случай и может испортить десять других, а увидеть это можно только на
живых объявлениях — и только если сравнивать с чем-то постоянным.

Эталон — сотня объявлений с проверенным разбором. Прогон показывает
долю совпадений и перечисляет расхождения. Правка, которая ухудшила
цифру, видна сразу, а не через неделю в ленте.

    python tools/golden.py --build 100    # собрать эталон из базы
    python tools/golden.py                # замерить нынешний разбор
    python tools/golden.py --diff         # показать расхождения

Собранный эталон нужно просмотреть глазами и поправить, где разбор был
неверен, — иначе замер закрепит нынешние ошибки.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.tg_classify import classify, classify_sub  # noqa: E402
from app.core.tg_parse import parse  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "backend" / "golden-set.jsonl"

# Что сравниваем. Заголовок и категория — то, что видно в ленте; цена и
# город — то, по чему ищут.
FIELDS = ("title", "price", "currency", "city", "category")


def discover(limit: int) -> list[dict]:
    """Берёт объявления из базы и раскладывает нынешним разбором."""
    from app.core.database import SessionLocal
    from app.models.listing import Listing, ListingTranslation

    with SessionLocal() as db:
        rows = (
            db.query(Listing.id, ListingTranslation.description)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(Listing.external_source == "telegram",
                    ListingTranslation.language == "ru")
            .limit(limit * 3)
            .all()
        )

    out = []
    for listing_id, description in rows:
        text = (description or "").strip()
        if len(text) < 30 or len(out) >= limit:
            continue
        out.append({"id": str(listing_id), "text": text[:1500],
                    **_current(text)})
    return out


def _current(text: str) -> dict:
    """Как разбирает объявление нынешний парсер."""
    parsed = parse(text)
    category, _ = classify(text)
    return {
        "title": parsed.get("title"),
        "price": parsed.get("price"),
        "currency": parsed.get("currency"),
        "city": parsed.get("city"),
        "category": category,
        "sub": classify_sub(category or "", text),
    }


def load() -> list[dict]:
    if not GOLDEN.exists():
        raise SystemExit(
            f"Эталона нет: {GOLDEN}\n"
            "Соберите его: python tools/golden.py --build 100"
        )
    return [json.loads(line) for line in
            GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]


def measure(show_diff: bool) -> None:
    rows = load()
    same = {field: 0 for field in FIELDS}
    diffs: list[tuple[str, str, object, object]] = []

    for row in rows:
        now = _current(row["text"])
        for field in FIELDS:
            if now.get(field) == row.get(field):
                same[field] += 1
            else:
                diffs.append((row["text"][:46], field,
                              row.get(field), now.get(field)))

    total = len(rows) or 1
    print(f"эталон: {total} объявлений\n")
    for field in FIELDS:
        share = same[field] * 100 // total
        mark = "" if share >= 95 else ("  ← стоит посмотреть" if share >= 85
                                       else "  ← расхождений много")
        print(f"  {field:<10} совпало {same[field]:>3}/{total}  ({share}%){mark}")

    if diffs:
        print(f"\nрасхождений: {len(diffs)}")
        if show_diff:
            for text, field, was, now in diffs[:40]:
                print(f"  {field:<9} было {str(was)[:28]!r:<30} "
                      f"стало {str(now)[:28]!r}")
                print(f"            {text}")
        else:
            print("  (покажет --diff)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", type=int, metavar="N",
                    help="собрать эталон из N объявлений базы")
    ap.add_argument("--diff", action="store_true",
                    help="показать сами расхождения, а не только счёт")
    args = ap.parse_args()

    if args.build:
        rows = discover(args.build)
        GOLDEN.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8")
        print(f"собрано: {len(rows)} → {GOLDEN}")
        print("\nПросмотрите файл и поправьте строки, где разбор неверен:\n"
              "иначе замер закрепит нынешние ошибки как эталон.")
        return

    measure(args.diff)


if __name__ == "__main__":
    main()
