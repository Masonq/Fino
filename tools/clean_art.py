"""
Очистка картинок разделов от остатков фона генератора: python3 tools/clean_art.py <вход.png> <выход.png> [размер]

Генераторы рисуют предмет на цветном фоне (белом, пурпурном, синем…) и вырезают его — между деталями (перила,
спицы) остаётся кайма этого цвета. Что делаем:
 1. Белый фон, не вырезанный вовсе, — заливкой от краёв картинки (белое на самом предмете не трогаем).
 2. Цвет фона определяем сами: самый частый насыщенный цвет на границе с прозрачным.
 3. Пиксели близко к этому цвету — прозрачные; слегка окрашенные — возвращаем к нейтральному (despill).
 4. Обрезка по содержимому, уменьшение, полупрозрачные края берут цвет соседнего непрозрачного.
"""
import sys
from collections import Counter

import numpy as np
from PIL import Image
from scipy import ndimage


def remove_white_bg(a: np.ndarray) -> np.ndarray:
    rgb, al = a[..., :3].astype(int), a[..., 3]
    whiteish = (rgb.min(axis=2) > 235) & (al > 0)
    lab, _ = ndimage.label(whiteish)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    if edge:
        mask = np.isin(lab, list(edge))
        a[mask, 3] = 0
    return a


def key_color(a: np.ndarray):
    rgb, al = a[..., :3].astype(int), a[..., 3]
    transp = al < 20
    near = ndimage.binary_dilation(transp, iterations=3) & ~transp
    px = rgb[near]
    if len(px) == 0:
        return None
    mx, mn = px.max(axis=1), px.min(axis=1)
    sat = (mx - mn) / np.maximum(mx, 1)
    vivid = px[(sat > 0.55) & (mx > 120)]
    if len(vivid) < max(50, len(px) * 0.02):
        return None
    q = Counter(map(tuple, (vivid // 32)))
    bucket = np.array(q.most_common(1)[0][0])
    sel = vivid[np.all(vivid // 32 == bucket, axis=1)]
    key = sel.mean(axis=0)
    # 1) фоном бывает только «неестественный» цвет хромакея: пурпурный или ярко-зелёный.
    #    Коричневый, бежевый, цвет шерсти, дерева, кожи — никогда (иначе вырезается сам предмет).
    r, g, b = key
    magenta = r > 150 and b > 130 and g < 0.6 * min(r, b)
    green = g > 180 and r < 0.6 * g and b < 0.6 * g
    if not (magenta or green):
        return None
    # 2) цвет фона почти не встречается внутри самого предмета
    solid = ndimage.binary_erosion(al > 250, iterations=6)
    inner = rgb[solid]
    if len(inner) and (np.linalg.norm(inner - key, axis=1) < 70).mean() > 0.02:
        return None
    return key


def despill(a: np.ndarray, key) -> np.ndarray:
    rgb = a[..., :3].astype(float)
    k = np.array(key, dtype=float)
    kn = k / max(np.linalg.norm(k), 1)
    dist = np.linalg.norm(rgb - k, axis=2)
    a[dist < 70, 3] = 0                                  # почти цвет фона — это фон
    # фон пурпурный — явно пурпурные пиксели убираем где угодно (между прутьями перил, у горшков на балконах):
    # у тёплых цветов предмета (терракота, дерево, шерсть) синего мало — под это правило они не попадают
    if k[0] > 150 and k[2] > 130 and k[1] < 0.6 * min(k[0], k[2]):
        r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        a[(r_ > 140) & (b_ > 120) & (g_ < 0.62 * np.minimum(r_, b_)), 3] = 0
    # слегка окрашенные: убираем составляющую цвета фона сверх серого
    grey = rgb.mean(axis=2, keepdims=True)
    chroma = rgb - grey
    kc = k - k.mean()
    kcn = kc / max(np.linalg.norm(kc), 1)
    proj = (chroma * kcn).sum(axis=2, keepdims=True)
    spill = np.clip(proj, 0, None)
    # оттенок снимаем только у краёв предмета (до 6 точек от прозрачного) — там и бывает кайма;
    # внутри цвета не трогаем (иначе терракотовый горшок становился оливковым)
    edge = ndimage.binary_dilation(a[..., 3] < 20, iterations=6)
    tinted = (spill[..., 0] > 18) & (a[..., 3] > 0) & edge
    rgb[tinted] = (rgb - spill * kcn)[tinted]
    a[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    return a


def fix_edges(im: Image.Image) -> Image.Image:
    a = np.array(im)
    al = a[..., 3]
    solid = al >= 250
    if solid.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
        semi = (al > 0) & ~solid
        a[semi, :3] = a[iy[semi], ix[semi], :3]
    a[al == 0, :3] = 0
    return Image.fromarray(a)


def clean(path_in: str, path_out: str, size: int = 512) -> dict:
    a = np.array(Image.open(path_in).convert('RGBA'))
    a = remove_white_bg(a)
    key = key_color(a)
    if key is not None:
        a = despill(a, key)
        a = despill(a, key)  # второй проход — кайма, открывшаяся после первого
    im = Image.fromarray(a)
    bb = im.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox()
    im = im.crop(bb)
    w, h = im.size; p = int(max(w, h) * 0.04)
    c = Image.new('RGBA', (w + 2 * p, h + 2 * p), (0, 0, 0, 0)); c.paste(im, (p, p))
    c.thumbnail((size, size), Image.LANCZOS)
    c = fix_edges(c)
    c.save(path_out, optimize=True)
    return {'key': None if key is None else [int(x) for x in key], 'size': c.size}


if __name__ == '__main__':
    print(clean(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 512))
