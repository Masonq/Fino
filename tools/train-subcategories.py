#!/usr/bin/env python3
"""
Учит классификатор подкатегорий — для одного родительского раздела.

Тот же приём, что у train-categories.py на верхнем уровне, только
модель отдельная на каждого родителя, а не одна на все шестьдесят
подкатегорий сразу: словари разных родителей не пересекаются, каждому
хватит меньшего числа примеров, чем понадобилось бы одной общей модели.

    python tools/train-subcategories.py electronics            # обучить и проверить
    python tools/train-subcategories.py electronics --check    # только проверить нынешнюю

Модель кладётся в backend/category-model-sub-<родитель>.json.
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.category_model import Model, load_sub, save_sub, SUB_MIN_SAMPLES  # noqa: E402

# Ниже этого числа на подкатегорию — учить нечему, модель запомнит
# случайные слова вместо признаков. Ниже, чем у верхнего уровня (там 15):
# подкатегорий на родителя меньше, и каждая может себе позволить чуть
# меньше засчитываемых примеров, не теряя надёжность непропорционально.
MIN_PER_CATEGORY = 10
TEST_SHARE = 0.2

LABELS_DIR = Path(__file__).resolve().parents[1] / "backend"


def load_labels(parent_slug: str) -> list[tuple[str, str]]:
    path = LABELS_DIR / f"ai-labels-sub-{parent_slug}.jsonl"
    if not path.exists():
        return []
    samples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            samples.append((row["text"], row["category"]))
        except (ValueError, KeyError):
            continue
    return samples


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("parent_slug", help="родительский раздел, например electronics")
    ap.add_argument("--check", action="store_true", help="только проверить нынешнюю модель")
    args = ap.parse_args()

    if args.check:
        model = load_sub(args.parent_slug)
        if model is None:
            print(f"модели для {args.parent_slug!r} нет или она не допущена к работе")
            return
        print(f"точность: {model.accuracy:.1%}, примеров: {model.samples}")
        print("доверенные подкатегории:", model.trusted_categories())
        return

    samples = load_labels(args.parent_slug)
    print(f"размеченных примеров: {len(samples)}")
    if not samples:
        raise SystemExit(
            f"нет размеченных данных — сначала: "
            f"python tools/label-subcategories-with-ai.py {args.parent_slug}"
        )

    counts = Counter(slug for _, slug in samples)
    print("по подкатегориям:", dict(counts))
    thin = [slug for slug, n in counts.items() if n < MIN_PER_CATEGORY]
    if thin:
        print(f"мало примеров (нужно {MIN_PER_CATEGORY}+): {thin}")

    random.shuffle(samples)
    split = int(len(samples) * (1 - TEST_SHARE))
    train_samples, test_samples = samples[:split], samples[split:]
    if not train_samples or not test_samples:
        raise SystemExit("данных слишком мало, даже чтобы отложить проверку")

    model = Model.train(train_samples)

    # Точность по каждой подкатегории отдельно — общая цифра обманчива:
    # телефоны модель узнаёт уверенно, а планшеты путает с ними же, и
    # незачем запрещать ей первое из-за второго.
    by_category: dict[str, list[int]] = {}
    right = total = 0
    for text, true_slug in test_samples:
        guessed, _ = model.raw_predict(text)
        bucket = by_category.setdefault(true_slug, [0, 0])
        bucket[1] += 1
        total += 1
        if guessed == true_slug:
            bucket[0] += 1
            right += 1
    model.by_category = {slug: tuple(v) for slug, v in by_category.items()}
    model.accuracy = right / total if total else 0.0
    model.samples = len(samples)

    print(f"\nточность на проверке: {model.accuracy:.1%} ({right} из {total})")
    print("доверенные подкатегории:", model.trusted_categories())
    if model.samples < SUB_MIN_SAMPLES:
        print(
            f"\nвнимание: {model.samples} примеров меньше порога {SUB_MIN_SAMPLES} — "
            "модель сохранится, но classify_sub() не станет её применять, "
            "пока данных не наберётся больше."
        )

    save_sub(args.parent_slug, model)
    print(f"\nсохранено: category-model-sub-{args.parent_slug}.json")


if __name__ == "__main__":
    main()
