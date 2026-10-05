"""
Служба смысловых векторов (plonk-embed): одна модель в памяти на весь сервер, а не по копии в каждом процессе сайта.

Модель — sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 через fastembed (ONNX, без PyTorch): 50+ языков,
в том числе русский, сербский (кириллица и латиница) и английский, 384 числа на текст, ~220 МБ на диске, ~0,5 ГБ в памяти.
Похожие по смыслу тексты на разных языках получают близкие векторы — «диван», «софа», «kauč», «sofa».

Слушает только 127.0.0.1:8011. Запуск: uvicorn app.embed_service:app --port 8011 --workers 1
"""
import threading

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
app = FastAPI(title="plonk-embed", docs_url=None, redoc_url=None)
_model = None
_lock = threading.Lock()


def _get():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding
                _model = TextEmbedding(MODEL_NAME, threads=2)
    return _model


@app.on_event("startup")
def _warm():
    # модель грузится в фоне: служба отвечает /health сразу, а первый запрос не ждёт загрузки дольше нужного
    threading.Thread(target=_get, daemon=True).start()


class EmbedIn(BaseModel):
    texts: list[str]


@app.get("/health")
def health():
    return {"ready": _model is not None, "model": MODEL_NAME}


@app.post("/embed")
def embed(body: EmbedIn):
    texts = [(t or "")[:1000] for t in body.texts][:256]
    if not texts:
        return {"vectors": []}
    try:
        vecs = np.asarray(list(_get().embed(texts, batch_size=32)), dtype=np.float32)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"model_unavailable: {e}") from e
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9  # единичная длина: сходство = скалярное произведение
    return {"vectors": vecs.round(6).tolist()}
