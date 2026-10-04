#!/usr/bin/env python3
"""
Форма и заполненность картинок разделов (frontend/public/cat/*.png) — для размера на плитке (artFit.artBox):
{"раздел": [ширина/высота, доля непрозрачного]}. Пишется в frontend/src/data/catArt.json и native/src/catArt.json.
Запускается сам из key_art.py после каждой картинки; вручную: python3 tools/art_manifest.py
"""
import json, os
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
        out[f[:-4]] = [round(im.width / im.height, 3), round(float(a.mean()), 3)]
    return out


def write():
    data = json.dumps(build(), ensure_ascii=False, separators=(',', ':')) + '\n'
    for p in ('frontend/src/data/catArt.json', 'native/src/catArt.json'):
        with open(os.path.join(ROOT, p), 'w') as fh:
            fh.write(data)
    return data


if __name__ == '__main__':
    print(len(json.loads(write())), 'картинок')
