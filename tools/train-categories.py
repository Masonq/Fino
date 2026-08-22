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
import json
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


LABELS = Path(__file__).resolve().parents[1] / "backend" / "ai-labels.jsonl"


def from_labels() -> list[tuple[str, str]]:
    """
    Пары из разметки нейросети.

    Учиться на категориях из базы нельзя: их расставили те самые правила,
    ошибки которых мы исправляем. Модель просто переняла бы их.
    """
    if not LABELS.exists():
        raise SystemExit(
            f"Нет файла разметки: {LABELS}\n"
            "Сначала разметьте объявления: python tools/label-with-ai.py"
        )
    out = []
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            out.append((row["text"], row["category"]))
        except (ValueError, KeyError):
            continue
    return out


def report(model: Model, tests: list[tuple[str, str]]) -> float:
    """
    Сколько объявлений модель относит верно и где ошибается.

    Возвращает долю верных среди тех, по которым она вообще решилась:
    именно по ней решается, допускать ли её к работе.
    """
    from app.core.category_model import MIN_MARGIN

    right = wrong = unsure = 0
    mistakes: Counter = Counter()
    # Считаем по каждому разделу: одежду модель узнаёт уверенно, а
    # детское путает с ней же — общая цифра это скрывает.
    per_category: dict[str, list[int]] = {}
    for text, expected in tests:
        slug, margin = model.raw_predict(text)
        if slug is None or margin < MIN_MARGIN:
            unsure += 1
            continue
        counts = per_category.setdefault(slug, [0, 0])
        counts[1] += 1
        if slug == expected:
            right += 1
            counts[0] += 1
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

    from app.core.category_model import MIN_ACCURACY, MIN_PER_CATEGORY

    print("\n  по разделам:")
    for slug, (ok, total) in sorted(per_category.items(),
                                    key=lambda kv: -kv[1][1]):
        share = ok * 100 // total
        verdict = ("доверяем" if total >= MIN_PER_CATEGORY
                   and ok / total >= MIN_ACCURACY else "молчит")
        print(f"    {slug:<14} {ok:>3}/{total:<4} ({share:>3}%)  {verdict}")

    model.by_category = {slug: tuple(counts)
                         for slug, counts in per_category.items()}
    decided = right + wrong
    return right / decided if decided else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", action="store_true",
                    help="учиться на разметке нейросети (backend/ai-labels.jsonl), "
                         "а не на категориях из базы — метки там чище")
    ap.add_argument("--check", action="store_true",
                    help="только проверить нынешнюю модель, не обучая заново")
    args = ap.parse_args()

    if args.labels:
        samples = from_labels()
        print(f"размечено нейросетью: {len(samples)}")
    else:
        with SessionLocal() as db:
            samples = collect(db)
        print(f"объявлений в базе: {len(samples)}")
        print("  внимание: метки здесь расставлены правилами, вместе с их\n"
              "  ошибками. Для настоящего обучения нужен --labels.")
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

    accuracy = report(model, tests)

    if not args.check:
        from app.core.category_model import MIN_ACCURACY, MIN_SAMPLES

        model.accuracy = accuracy
        model.samples = len(train)
        save(model)
        if model.trustworthy():
            trusted = ", ".join(sorted(model.trusted_categories()))
            print(f"\n  модель сохранена. Доверяем разделам: {trusted}")
            print("  в остальных работают правила")
        else:
            print("\n  модель сохранена, но к работе НЕ допущена:")
            print(f"  ни один раздел не набрал {MIN_ACCURACY * 100:.0f}% "
                  f"на {MIN_PER_CATEGORY}+ проверках.")
            print("  Пока работают правила — разметьте ещё объявлений:")
            print("  python tools/label-with-ai.py --limit 500")


if __name__ == "__main__":
    main()
