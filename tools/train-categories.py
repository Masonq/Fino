#!/usr/bin/env python3
"""
Учит классификатор разделов на уже разобранных объявлениях.

Разметка берётся из базы: категория объявления, которое прошло импорт с
совпадением темы чата и догадки правил. Такое совпадение — двойная
проверка, и как метка она надёжнее одиночной догадки.

    python tools/train-categories.py            # обучить и проверить
    python tools/train-categories.py --check    # только проверить нынешнюю

Модель кладётся в backend/category-model.json — файл читается на месте,
пересылать никуда не нужно. Обучение занимает секунды и не требует
сторонних библиотек.
"""
import argparse
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.category_model import Model, load, save  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.listing import Listing, ListingTranslation  # noqa: E402

# Меньше этого числа примеров на раздел — учить нечему: модель запомнит
# случайные слова вместо признаков.
MIN_PER_CATEGORY = 15
# Доля объявлений, отложенных для проверки. На них модель не учится, и
# по ним видно, как она поведёт себя с незнакомым текстом.
TEST_SHARE = 0.2


def collect(db) -> list[tuple[str, str]]:
    """Пары «текст объявления — раздел» из базы."""
    rows = (
        db.query(ListingTranslation.title, ListingTranslation.description,
                 Category.slug, Category.parent_id)
        .join(Listing, Listing.id == ListingTranslation.listing_id)
        .join(Category, Category.id == Listing.category_id)
        .filter(Listing.external_source == "telegram",
                ListingTranslation.language == "ru")
        .all()
    )
    samples = []
    parents = {c.id: c.slug for c in db.query(Category).all()}
    for title, description, slug, parent_id in rows:
        text = f"{title or ''}\n{description or ''}".strip()
        if len(text) < 25:
            continue
        # Учим по родительскому разделу: подкатегорий шестьдесят, и
        # примеров на каждую не наберётся.
        samples.append((text, parents.get(parent_id) or slug))
    return samples


def report(model: Model, tests: list[tuple[str, str]]) -> None:
    """Сколько объявлений модель относит верно и где ошибается."""
    from app.core.category_model import MIN_MARGIN

    right = wrong = unsure = 0
    mistakes: Counter = Counter()
    for text, expected in tests:
        slug, margin = model.predict(text)
        if slug is None or margin < MIN_MARGIN:
            unsure += 1
        elif slug == expected:
            right += 1
        else:
            wrong += 1
            mistakes[f"{expected} → {slug}"] += 1

    total = len(tests) or 1
    print(f"\n  верно      {right:4}  ({right * 100 // total}%)")
    print(f"  неверно    {wrong:4}  ({wrong * 100 // total}%)")
    print(f"  не уверена {unsure:4}  ({unsure * 100 // total}%) — уйдут к правилам")
    if mistakes:
        print("\n  чаще всего путает:")
        for pair, count in mistakes.most_common(8):
            print(f"    {pair:<34} {count}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="только проверить нынешнюю модель, не обучая заново")
    args = ap.parse_args()

    with SessionLocal() as db:
        samples = collect(db)

    print(f"объявлений в базе: {len(samples)}")
    by_category = Counter(slug for _, slug in samples)
    for slug, count in by_category.most_common():
        mark = "" if count >= MIN_PER_CATEGORY else "  — мало примеров"
        print(f"  {slug:<16} {count}{mark}")

    samples = [s for s in samples if by_category[s[1]] >= MIN_PER_CATEGORY]
    if len(samples) < 100:
        raise SystemExit(
            "\nДля обучения нужно хотя бы сто объявлений в разделах с "
            "достаточным числом примеров. Дайте импорту поработать."
        )

    random.seed(20260822)          # чтобы проверка повторялась
    random.shuffle(samples)
    edge = int(len(samples) * (1 - TEST_SHARE))
    train, tests = samples[:edge], samples[edge:]

    if args.check:
        model = load()
        if model is None:
            raise SystemExit("Обученной модели нет — запустите без --check.")
        print(f"\nпроверка нынешней модели на {len(tests)} объявлениях:")
    else:
        model = Model.train(train)
        print(f"\nобучено на {len(train)}, проверка на {len(tests)}:")

    report(model, tests)

    if not args.check:
        save(model)
        print("\n  модель сохранена")


if __name__ == "__main__":
    main()
