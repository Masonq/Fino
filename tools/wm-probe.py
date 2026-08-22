"""
Пробник: ищет водяной знак HaloOglasi на уже скачанных фотографиях.

Нужен, чтобы подобрать признак на настоящих файлах, а не на глаз. Печатает
по каждому снимку несколько мер — по ним видно, какая из них разделяет
снимки со знаком и без.

    python3 tools/wm-probe.py [сколько]
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageOps, ImageEnhance

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

WORDS = ("halooglasi", "oglasi", "nekretnine", "srbiji", "broj 1")


def probe(path: str) -> dict:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    gray = im.convert("L")

    # Полоса, где у HaloOglasi стоит знак: середина по высоте, почти вся ширина
    band = gray.crop((int(w*0.15), int(h*0.32), int(w*0.9), int(h*0.72)))
    band = band.resize((band.width*2, band.height*2), Image.LANCZOS)
    band = ImageEnhance.Contrast(ImageOps.autocontrast(band, cutoff=1)).enhance(2.2)

    found = []
    if HAS_OCR:
        text = pytesseract.image_to_string(band, lang="eng").lower()
        found = [word for word in WORDS if word in text]

    # Насколько середина «выбелена» относительно остального кадра: знак
    # полупрозрачно-белый и поднимает яркость, снижая насыщенность
    a = np.asarray(im).astype(np.float32)
    sat = a.max(2) - a.min(2)
    mid = slice(int(h*0.38), int(h*0.62)), slice(int(w*0.25), int(w*0.78))
    wash = float(sat.mean() - sat[mid].mean())
    bright = float(a[mid].mean() - a.mean())

    return {"ocr": found, "wash": wash, "bright": bright, "size": f"{w}x{h}"}


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    files = sorted(glob.glob("./media/*.jpg"))
    files = [f for f in files if "_thumb" not in f][:limit]
    if not HAS_OCR:
        print("pytesseract не установлен — распознавание пропущено\n")
    print(f"{'файл':38} {'размер':>11} {'выбелено':>9} {'ярче':>7}  найденные слова")
    for f in files:
        r = probe(f)
        mark = "  <<< ЗНАК" if r["ocr"] else ""
        print(f"{os.path.basename(f):38} {r['size']:>11} {r['wash']:9.1f} {r['bright']:7.1f}  {','.join(r['ocr'])}{mark}")


if __name__ == "__main__":
    main()
