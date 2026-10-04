"""
Картинки разделов на сплошном хромакее (пурпурный #FF00FF или зелёный #00FF00):
python3 tools/key_art.py <вход> <выход.png> [размер]

 1. Цвет фона — медиана по рамке кадра.
 2. Прозрачность — по «перевесу» цвета фона (для пурпурного min(R,B)-G, для зелёного G-max(R,B)):
    тень на фоне (тёмно-пурпурная) тоже уходит, нейтральные цвета предмета не трогаются.
 3. Кайма: у края предмета снимаем оттенок фона (despill).
 4. С --glass фон, видный сквозь стекло (окна машины), закрашиваем тёмным стеклом; без него просветы прозрачные.
 5. Обрезка по содержимому, почти без полей, уменьшение, края — как в clean_art.
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from clean_art import fix_edges


def key_out(path_in, path_out, size=512, glass=False):
    rgb = np.asarray(Image.open(path_in).convert('RGB')).astype(np.float32)
    border = np.concatenate([rgb[:8].reshape(-1, 3), rgb[-8:].reshape(-1, 3), rgb[:, :8].reshape(-1, 3), rgb[:, -8:].reshape(-1, 3)])
    key = np.median(border, axis=0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    if key[1] > key[0] and key[1] > key[2]:
        dom = g - np.maximum(r, b); kind = 'green'
    else:
        dom = np.minimum(r, b) - g; kind = 'magenta'
    lo, hi = 45.0, 120.0
    a = 1 - np.clip((dom - lo) / (hi - lo), 0, 1)
    # фон — только то, что связано с краем кадра; внутренние «окна» с фоном — стекло
    bgsure = dom > hi * 0.8
    lab, _ = ndimage.label(bgsure)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    outside = np.isin(lab, list(edge))
    inner = (a < 1) & ~ndimage.binary_dilation(outside, iterations=3)
    obj = ndimage.binary_fill_holes(~outside)
    inner &= obj
    out = rgb.copy()
    # despill по всей картинке, где есть перевес цвета фона
    spill = np.clip(dom, 0, None)
    if kind == 'green':
        out[..., 1] -= spill
    else:
        out[..., 0] -= spill; out[..., 2] -= spill
    if glass and inner.any():
        lum = out[inner].mean(axis=1, keepdims=True)
        out[inner] = np.clip(lum * 0.35 + np.array([38, 41, 47]), 0, 255)
        a[inner] = 1
    A = np.dstack([np.clip(out, 0, 255), a * 255]).astype(np.uint8)
    im = Image.fromarray(A, 'RGBA')
    bb = im.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox()
    im = im.crop(bb)
    w, h = im.size; p = int(max(w, h) * 0.005)
    c = Image.new('RGBA', (w + 2 * p, h + 2 * p), (0, 0, 0, 0)); c.paste(im, (p, p))
    c.thumbnail((size, size), Image.LANCZOS)
    c = fix_edges(c)
    c.save(path_out, optimize=True)
    return {'key': [int(x) for x in key], 'kind': kind, 'glass_px': int(inner.sum()), 'size': c.size}


if __name__ == '__main__':
    # --glass: фон сквозь стекло закрасить тёмным стеклом (машины); иначе внутренние просветы прозрачные
    args = [x for x in sys.argv[1:] if x != '--glass']
    print(key_out(args[0], args[1], int(args[2]) if len(args) > 2 else 512, glass='--glass' in sys.argv))
