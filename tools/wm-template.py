"""
Извлекает водяной знак из нескольких снимков и проверяет, ловится ли он.

Знак у всех фотографий одного источника одинаков и стоит на одном месте, а
содержимое кадров разное. Поэтому если сложить снимки и усреднить, комнаты
взаимно погасятся, а знак — единственное общее — проявится. Полученный
образец сохраняется картинкой и тут же проверяется на всей папке.

    python3 tools/wm-template.py файл1.jpg файл2.jpg ...
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "media")
SIZE = (800, 600)          # общий размер, к которому приводим кадры
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wm-template.png")


def highpass(path: str) -> np.ndarray:
    """Мелкий рисунок кадра: крупные пятна убираем, кромки знака остаются."""
    im = Image.open(path).convert("L").resize(SIZE, Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    blur = np.asarray(
        Image.fromarray(a.astype(np.uint8)).resize((SIZE[0]//16, SIZE[1]//16), Image.LANCZOS)
             .resize(SIZE, Image.LANCZOS)
    ).astype(np.float32)
    return a - blur


def normalized(a: np.ndarray) -> np.ndarray:
    return (a - a.mean()) / (a.std() + 1e-6)


def main() -> None:
    marked = sys.argv[1:]
    if len(marked) < 3:
        print("нужно хотя бы три файла со знаком"); return

    stack = [highpass(os.path.join(MEDIA, name)) for name in marked]
    template = np.mean(stack, axis=0)

    vis = np.clip((template - template.min()) / (template.ptp() + 1e-6) * 255, 0, 255)
    Image.fromarray(vis.astype(np.uint8)).save(OUT)
    print(f"образец сохранён: {OUT}")
    print(f"выраженность образца: {template.std():.2f} "
          f"(у одиночного кадра около {stack[0].std():.2f})")

    tn = normalized(template)
    files = [f for f in sorted(glob.glob(os.path.join(MEDIA, "*.jpg"))) if "_thumb" not in f]
    marked_set = set(marked)

    scores = {"СО ЗНАКОМ": [], "чистые": []}
    for f in files:
        key = "СО ЗНАКОМ" if os.path.basename(f) in marked_set else "чистые"
        if key == "чистые" and len(scores[key]) >= 80:
            continue
        scores[key].append(float((normalized(highpass(f)) * tn).mean()))

    for name, values in scores.items():
        if not values:
            continue
        v = np.array(values)
        print(f"{name:11} среднее {v.mean():+.3f}  "
              f"разброс {np.percentile(v,5):+.3f}..{np.percentile(v,95):+.3f}  "
              f"худшее {v.min():+.3f}  лучшее {v.max():+.3f}  ({len(v)} шт)")


if __name__ == "__main__":
    main()
