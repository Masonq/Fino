#!/usr/bin/env python3
"""
Убирает белый лист под картинками разделов.

В тёмной теме плитки стали тёмными, а картинки остались нарисованными
на белом: под предметом висел светлый квадрат с тенью. Часть файлов
вообще без прозрачности, у остальных белая дымка по краям.

Делается в два шага.

1. Фон. Заливка идёт от края внутрь и останавливается на первом же
   не-белом пикселе. Белое ВНУТРИ предмета (коробка, лист бумаги,
   корпус техники) не трогается — до него заливка не доходит.

2. Тень. Тень нарисована серым по белому, и на тёмном фоне она
   бессмысленна: это затемнение белого листа, которого больше нет.
   Идём от вырезанного фона вглубь, но только по серым пикселям
   (насыщенность почти нулевая) и не дальше 34 точек, и делаем их тем
   прозрачнее, чем они светлее. Цветное — то есть сам предмет — этим
   проходом не задевается, он останавливается на первом цветном
   пикселе.

    python3 tools/cut-cat-bg.py           # посчитать, ничего не менять
    python3 tools/cut-cat-bg.py --apply   # переписать файлы
"""
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

CAT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "cat"

# Пастельная зелень и лаванда на картинках заметно темнее 205 и заметно
# цветнее 12 — по гистограммам они под эти пороги не попадают.
WHITE_MIN = 205
GRAY_MAX = 12
# Тень: насколько тёмным может быть серый, который мы ещё считаем тенью,
# и как далеко от фона она может тянуться.
SHADOW_MIN = 110
SHADOW_SAT = 18
SHADOW_REACH = 34


def cut(img: Image.Image) -> tuple[Image.Image, float]:
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    def is_bg(x, y):
        r, g, b, a = px[x, y]
        if a < 8:
            return True
        return min(r, g, b) >= WHITE_MIN and max(r, g, b) - min(r, g, b) <= GRAY_MAX

    seen = [[False] * h for _ in range(w)]
    queue = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg(x, y) and not seen[x][y]:
                seen[x][y] = True
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(x, y) and not seen[x][y]:
                seen[x][y] = True
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny] and is_bg(nx, ny):
                seen[nx][ny] = True
                queue.append((nx, ny))

    near = [[False] * h for _ in range(w)]
    shadow_q = deque()
    for x in range(w):
        for y in range(h):
            if seen[x][y]:
                near[x][y] = True
                shadow_q.append((x, y, 0))
    while shadow_q:
        x, y, d = shadow_q.popleft()
        if d >= SHADOW_REACH:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not near[nx][ny]:
                r, g, b, _ = px[nx, ny]
                if max(r, g, b) - min(r, g, b) <= SHADOW_SAT and min(r, g, b) >= SHADOW_MIN:
                    near[nx][ny] = True
                    shadow_q.append((nx, ny, d + 1))

    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    cut_count = 0
    for x in range(w):
        for y in range(h):
            if seen[x][y]:
                mp[x, y] = 0
                cut_count += 1
            elif near[x][y]:
                r, g, b, _ = px[x, y]
                lum = (r + g + b) // 3
                mp[x, y] = max(0, min(255, (255 - lum) * 255 // (255 - SHADOW_MIN)))
    # Полпикселя размытия: резкая граница по порогу даёт зубцы.
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))

    alpha = img.getchannel("A")
    ap, mm = alpha.load(), mask.load()
    merged = Image.new("L", (w, h))
    m2 = merged.load()
    for x in range(w):
        for y in range(h):
            m2[x, y] = ap[x, y] * mm[x, y] // 255
    img.putalpha(merged)
    return img, cut_count / (w * h)


def main(apply: bool) -> None:
    files = sorted(CAT_DIR.glob("*.png"))
    touched = 0
    for f in files:
        out, share = cut(Image.open(f))
        if share < 0.02:
            continue
        touched += 1
        if apply:
            out.save(f, "PNG", optimize=True)
    print(f"{'переписано' if apply else 'нашлось'}: {touched} из {len(files)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
