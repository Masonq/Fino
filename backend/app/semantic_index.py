"""
Заполняет listing_embeddings: векторы для новых и изменённых объявлений (python -m app.semantic_index).
Запускается таймером plonk-embed-index каждые 10 минут; за раз — до 3000 объявлений пачками по 64.
"""
import sys

import numpy as np

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.semantic import embed, text_for, text_hash
from app.models import Listing, ListingStatus
from app.models.embedding import ListingEmbedding


def _wait_ready(seconds: int = 600) -> bool:
    """Ждём, пока служба загрузит модель (в первый раз она скачивается — это минуты)."""
    import json
    import time
    import urllib.request
    end = time.time() + seconds
    while time.time() < end:
        try:
            if json.loads(urllib.request.urlopen("http://127.0.0.1:8011/health", timeout=5).read()).get("ready"):
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(5)
    return False


def run(limit: int = 3000) -> int:
    if not _wait_ready():
        print("служба plonk-embed не готова — попробуем в следующий раз")
        return 0
    db = SessionLocal()
    done = 0
    try:
        have = {lid: h for lid, h in db.query(ListingEmbedding.listing_id, ListingEmbedding.text_hash).all()}
        todo = []
        for l in db.query(Listing).filter(Listing.status == ListingStatus.active).order_by(Listing.published_at.desc().nullslast()).all():
            tr = next((t for t in l.translations if t.language == getattr(l.source_language, "value", l.source_language)), None) \
                or (l.translations[0] if l.translations else None)
            if not tr:
                continue
            txt = text_for(tr.title, tr.description)
            h = text_hash(txt)
            if have.get(l.id) != h:
                todo.append((l.id, txt, h))
            if len(todo) >= limit:
                break
        for i in range(0, len(todo), 64):
            part = todo[i:i + 64]
            vecs = embed([t for _, t, _ in part], timeout=120)
            if vecs is None:
                print("служба plonk-embed недоступна — попробуем в следующий раз")
                break
            for (lid, _, h), v in zip(part, vecs):
                row = db.get(ListingEmbedding, lid) or ListingEmbedding(listing_id=lid)
                row.vec, row.text_hash, row.updated_at = np.asarray(v, dtype=np.float32).tobytes(), h, utcnow()
                db.add(row)
            db.commit()
            done += len(part)
        print(f"векторов посчитано: {done} (ожидало: {len(todo)}, всего с векторами: {len(have) + done})")
    finally:
        db.close()
    return done


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 3000)
