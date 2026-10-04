#!/usr/bin/env python3
"""
Форма и заполненность картинок разделов (frontend/public/cat/*.png) — для размера на плитке (artFit.artBox):
{"раздел": [ширина/высота, доля непрозрачного, метка содержимого, профиль верха по 24 колонкам]}. Пишется в frontend/src/data/catArt.json и native/src/catArt.json.
Запускается сам из key_art.py после каждой картинки; вручную: python3 tools/art_manifest.py
"""
import hashlib, json, os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'frontend', 'public', 'cat')


def build():
    out = {}
    for f in sorted(os.listdir(CAT)):
        if not f.endswith('.png'):
            continue
        im = Image.open(os.path.join(CAT, f))
        a = np.asarray(im.convert('RGBA').getchannel('A'), dtype=np.float32) / 255
        # третье — метка содержимого для адреса (?v=…): поменялась картинка — поменялся адрес, кэш браузера
        # и приложения её не держит
        with open(os.path.join(CAT, f), 'rb') as fh:
            v = hashlib.sha1(fh.read()).hexdigest()[:8]
        # четвёртое — профиль верха: в каждой из 24 колонок, на какой доле высоты начинается сам предмет (1 — колонка
        # пустая). По нему картинка может подняться под надпись там, где у неё пусто, не задевая буквы
        m = a > 0.35
        cols = np.array_split(np.arange(im.width), 24)
        prof = []
        for c in cols:
            rows = np.where(m[:, c].any(axis=1))[0]
            prof.append(round(float(rows[0]) / im.height, 2) if len(rows) else 1)
        out[f[:-4]] = [round(im.width / im.height, 3), round(float(a.mean()), 3), v, prof]
    return out


def write():
    data = json.dumps(build(), ensure_ascii=False, separators=(',', ':')) + '\n'
    for p in ('frontend/src/data/catArt.json', 'native/src/catArt.json'):
        with open(os.path.join(ROOT, p), 'w') as fh:
            fh.write(data)
    return data


if __name__ == '__main__':
    print(len(json.loads(write())), 'картинок')
