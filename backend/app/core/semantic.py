"""
Поиск по смыслу — клиент службы plonk-embed и индекс векторов объявлений в памяти.

Как работает: у каждого живого объявления есть вектор (таблица listing_embeddings, заполняет app.semantic_index).
Запрос превращаем в вектор той же моделью и ищем ближайшие объявления скалярным произведением — numpy по всей
матрице за миллисекунды (тысячи объявлений × 384 числа). Отдельная база векторов (pgvector) на нашем объёме не нужна.

Всё «мягкое»: служба не отвечает, векторов ещё нет — поиск работает как раньше, по словам.
"""
import hashlib
import threading
import time

import json
import urllib.request

import numpy as np

EMBED_URL = "http://127.0.0.1:8011/embed"
DIM = 384
# Пороги сходства (косинус) для paraphrase-multilingual-MiniLM: близкие по смыслу вещи — от ~0,5, «то же самое
# другими словами» — от ~0,65. Берём не ниже MIN и не дальше GAP от лучшего совпадения, чтобы не тащить хвост.
MIN_SIM = 0.5
GAP = 0.18
_cache = {"at": 0.0, "ids": [], "mat": np.zeros((0, DIM), dtype=np.float32)}
_qcache: dict[str, tuple[float, list]] = {}
_lock = threading.Lock()


def text_for(title: str | None, description: str | None) -> str:
    return ((title or "").strip() + ". " + (description or "").strip()[:300]).strip(". ")


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf8")).hexdigest()


def embed(texts: list[str], timeout: float = 3.0) -> np.ndarray | None:
    try:
        req = urllib.request.Request(EMBED_URL, data=json.dumps({"texts": texts}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return np.asarray(json.loads(r.read())["vectors"], dtype=np.float32)
    except Exception:  # noqa: BLE001 — служба лежит или грузится: молча без смысла
        return None


def _matrix(db):
    """Матрица векторов живых объявлений — обновляется раз в 5 минут в каждом процессе сайта."""
    now = time.time()
    if now - _cache["at"] < 300 and _cache["ids"]:
        return _cache["ids"], _cache["mat"]
    with _lock:
        if now - _cache["at"] < 300 and _cache["ids"]:
            return _cache["ids"], _cache["mat"]
        from sqlalchemy import text as sql
        rows = db.execute(sql("""select e.listing_id, e.vec from listing_embeddings e
                                  join listings l on l.id = e.listing_id where l.status = 'active'""")).fetchall()
        ids = [r[0] for r in rows]
        mat = (np.frombuffer(b"".join(bytes(r[1]) for r in rows), dtype=np.float32).reshape(len(rows), DIM)
               if rows else np.zeros((0, DIM), dtype=np.float32))
        _cache.update(at=now, ids=ids, mat=mat)
        return ids, mat


def similar_ids(db, query: str, limit: int = 120) -> list:
    """Объявления, близкие по смыслу к запросу, — от самых близких; пусто, если служба недоступна."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    hit = _qcache.get(q)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    ids, mat = _matrix(db)
    if not ids:
        return []
    v = embed([q], timeout=1.5)
    if v is None or not len(v):
        return []
    sims = mat @ v[0]
    order = np.argsort(-sims)[:limit]
    best = float(sims[order[0]]) if len(order) else 0.0
    out = [ids[i] for i in order if sims[i] >= MIN_SIM and sims[i] >= best - GAP]
    if len(_qcache) > 500:
        _qcache.clear()
    _qcache[q] = (time.time(), out)
    return out
