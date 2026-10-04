#!/usr/bin/env python3
"""
Плитки разделов без картинки — по настоящему дереву разделов с сервера (часть подразделов заведена
в админке и в коде её нет, как «Детский транспорт»). Какие плитки видны — тем же правилом, что сетка
на сайте (gridRows в CategoryLanding.jsx, телефон 375): короткие названия по три в ряд, длинные парами,
не больше трёх рядов, последняя клетка — «Все категории». У «Бизнеса» видны все.
Запчасти — чипы без картинок, их не считаем.

    python3 tools/missing-art.py
"""
import json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'frontend', 'public', 'cat')
API = os.environ.get('PLONK_API', 'http://127.0.0.1:8002/api/categories?lang=ru')

have = {f[:-4] for f in os.listdir(CAT) if f.endswith('.png')}
tree = json.load(urllib.request.urlopen(API, timeout=20))
miss = []


def name(n):
    v = n.get('name')
    return (v.get('ru') if isinstance(v, dict) else v) or n['slug']


import re

def one_line(n):
    # oneLineWidth из artFit.js: самый широкий шрифт, широкие буквы ×1,4
    ws = [w for w in n.split() if w]
    return sum((len(w) + 0.4 * len(re.findall('[мжшщюфыМЖШЩЮФЫmwMW]', w))) * 9.9 for w in ws) + 4 * (len(ws) - 1) + 2


def visible(kids, narrow_text=89):
    wide = lambda k: one_line(name(k)) > narrow_text
    nq = [k for k in kids if not wide(k)]
    wq = [k for k in kids if wide(k)]
    rows = []
    while (nq or wq) and len(rows) < 3:
        next_narrow = bool(nq) and (not wq or kids.index(nq[0]) < kids.index(wq[0]))
        if next_narrow and len(nq) >= 3:
            rows.append([nq.pop(0) for _ in range(3)])
        elif not next_narrow and len(wq) >= 2:
            rows.append([wq.pop(0) for _ in range(2)])
        else:
            a, b = (nq, wq) if next_narrow else (wq, nq)
            rows.append(([a.pop(0)] if a else []) + ([b.pop(0)] if b else []))
    if (nq or wq) and rows:
        rows[-1][-1] = None
    return [k for r in rows for k in r if k]


def walk(node, path):
    kids = node.get('children') or []
    if not kids or node['slug'] == 'car-parts':
        return
    shown = kids if node['slug'] == 'business' else visible(kids)
    for k in shown:
        if k['slug'] not in have:
            miss.append(f"{path} > {name(k)} = {k['slug']}")
    for k in kids:
        walk(k, f"{path} > {name(k)}")


for top in tree:
    if top['slug'] not in have:
        miss.append(f"главная > {name(top)} = {top['slug']}")
    walk(top, name(top))
print(f'без картинки: {len(miss)}')
print('\n'.join(miss))
