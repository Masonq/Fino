"""
Отсев фотографий с водяным знаком HaloOglasi.

Знак у них крупный, лежит поперёк середины кадра и убирается только с
потерей самой картинки: под ним мебель и стены, а не однородный фон.
Поэтому объявления с такими снимками не переносим вовсе — заодно это
отсеивает перепечатки от агентств: хозяин квартиры снимает на телефон, а не
скачивает фото с чужой площадки.

Образец знака добыт усреднением снимков одного объявления: содержимое
комнат при сложении гасит друг друга, а знак — единственное общее —
проявляется. Ни яркость, ни насыщенность, ни детализация знак не выдают:
у снимков со знаком и без эти меры полностью пересекаются.
"""
import os

import numpy as np
from PIL import Image

SIZE = (800, 600)
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wm-template.npy")

# Со знаком выходит 0.40..0.51, без него -0.03..+0.02. Порог посередине:
# запас с обеих сторон такой, что случайное совпадение исключено.
THRESHOLD = 0.20

_template: np.ndarray | None = None
_loaded = False


def _highpass(im: Image.Image) -> np.ndarray:
    """Мелкий рисунок кадра: крупные пятна убираем, кромки знака остаются."""
    a = np.asarray(im.convert("L").resize(SIZE, Image.LANCZOS)).astype(np.float32)
    blur = np.asarray(
        Image.fromarray(a.astype(np.uint8))
        .resize((SIZE[0] // 16, SIZE[1] // 16), Image.LANCZOS)
        .resize(SIZE, Image.LANCZOS)
    ).astype(np.float32)
    return a - blur


def _normalized(a: np.ndarray) -> np.ndarray:
    return (a - a.mean()) / (a.std() + 1e-6)


def _load() -> np.ndarray | None:
    global _template, _loaded
    if not _loaded:
        _loaded = True
        if os.path.exists(TEMPLATE_PATH):
            _template = _normalized(np.load(TEMPLATE_PATH))
    return _template


def score(im: Image.Image) -> float:
    """Насколько снимок похож на несущий знак. Без образца — всегда 0."""
    template = _load()
    if template is None:
        return 0.0
    return float((_normalized(_highpass(im)) * template).mean())


def has_watermark(im: Image.Image) -> bool:
    return score(im) >= THRESHOLD
