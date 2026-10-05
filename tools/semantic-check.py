"""Проверка поиска по смыслу на сервере: готова ли модель, сколько векторов и что находится по пробным запросам
(со степенью близости — по ней настраиваются пороги MIN_SIM/GAP в app/core/semantic.py).
Запуск: cd /opt/fino/backend && venv/bin/python ../tools/semantic-check.py"""
import json
import sys
import urllib.request

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.semantic import GAP, MIN_SIM, _matrix, embed  # noqa: E402
from app.models import ListingTranslation  # noqa: E402

try:
    print("служба:", json.loads(urllib.request.urlopen("http://127.0.0.1:8011/health", timeout=5).read()))
except Exception as e:  # noqa: BLE001
    print("служба не отвечает:", e); sys.exit(1)
db = SessionLocal()
ids, mat = _matrix(db)
print("объявлений с векторами:", len(ids))
titles = {}
for lid, t in db.query(ListingTranslation.listing_id, ListingTranslation.title).filter(ListingTranslation.listing_id.in_(ids)).all():
    titles.setdefault(lid, t)
for q in (sys.argv[1:] or ["софа", "sofa", "kauč", "детская коляска", "телефон", "машина", "работа официантом", "квартира у моря"]):
    v = embed([q.lower()], timeout=30)
    if v is None:
        print(q, "— нет ответа"); continue
    sims = mat @ v[0]
    top = np.argsort(-sims)[:6]
    best = float(sims[top[0]]) if len(top) else 0
    # ✓ — попадёт в выдачу по смыслу при нынешних порогах
    print(f"\n«{q}»:", " | ".join(f"{'✓' if sims[i] >= MIN_SIM and sims[i] >= best - GAP else '·'}{sims[i]:.2f} {str(titles.get(ids[i], ''))[:26]}" for i in top))
