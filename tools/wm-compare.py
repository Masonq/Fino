"""
Сравнивает снимки с водяным знаком и без него.

Принимает имена файлов со знаком; остальные снимки в папке считаются
чистыми. Печатает по нескольким мерам, насколько те и другие расходятся, —
по этому и выбирается признак, а не наугад.

    python3 tools/wm-compare.py файл1.jpg файл2.jpg ...
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "media")


def measures(path: str) -> dict:
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]

    gray = a.mean(2)
    sat = a.max(2) - a.min(2)

    # Полоса, где HaloOglasi ставит логотип
    mid = (slice(int(h*0.38), int(h*0.62)), slice(int(w*0.22), int(w*0.80)))
    # Для сравнения — верх и низ кадра, куда знак не достаёт
    out = np.concatenate([gray[:int(h*0.25)].ravel(), gray[int(h*0.78):].ravel()])
    out_sat = np.concatenate([sat[:int(h*0.25)].ravel(), sat[int(h*0.78):].ravel()])

    # Знак осветляет и обесцвечивает, а ещё «приглаживает» — под ним падает
    # local contrast, потому что поверх лежит ровная полупрозрачная заливка
    def detail(block):
        dx = np.abs(np.diff(block, axis=1)).mean()
        dy = np.abs(np.diff(block, axis=0)).mean()
        return (dx + dy) / 2

    return {
        "ярче":     float(gray[mid].mean() - out.mean()),
        "бледнее":  float(out_sat.mean() - sat[mid].mean()),
        "глаже":    float(detail(gray[int(h*0.25):int(h*0.75)]) - detail(gray[mid])),
        "детали":   float(detail(gray[mid])),
    }


def main() -> None:
    marked = set(sys.argv[1:])
    if not marked:
        print("укажи имена файлов со знаком"); return

    files = [f for f in sorted(glob.glob(os.path.join(MEDIA, "*.jpg"))) if "_thumb" not in f]
    groups = {"СО ЗНАКОМ": [], "чистые": []}
    for f in files:
        key = "СО ЗНАКОМ" if os.path.basename(f) in marked else "чистые"
        if key == "чистые" and len(groups[key]) >= 60:
            continue
        groups[key].append(measures(f))

    keys = ["ярче", "бледнее", "глаже", "детали"]
    print(f"{'':12} " + "".join(f"{k:>12}" for k in keys))
    for name, rows in groups.items():
        if not rows:
            continue
        avg = [np.mean([r[k] for r in rows]) for k in keys]
        rng = [f"{np.percentile([r[k] for r in rows], 10):.1f}..{np.percentile([r[k] for r in rows], 90):.1f}" for k in keys]
        print(f"{name:12} " + "".join(f"{v:12.1f}" for v in avg) + f"   ({len(rows)} шт)")
        print(f"{'  разброс':12} " + "".join(f"{v:>12}" for v in rng))


if __name__ == "__main__":
    main()
