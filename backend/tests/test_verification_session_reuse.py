"""
«Подтвердить личность» падало с 500: Didit вернул ту же незавершённую сессию, а сервер пытался вставить
её второй раз (уникальный session_id). Теперь сессия того же человека переиспользуется и ссылка отдаётся.
"""
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.auth import create_access_token  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.models.document_verification import DocVerificationRequest, DocVerificationStatus  # noqa: E402
from app.routers import verification  # noqa: E402


def test_same_didit_session_twice_is_reused_not_a_500(monkeypatch):
    monkeypatch.setattr(settings, "didit_api_key", "k", raising=False)
    monkeypatch.setattr(settings, "didit_workflow_id", "w", raising=False)
    sid = f"sess-{uuid.uuid4().hex[:10]}"
    monkeypatch.setattr(verification, "_create_session", lambda wf, uid, cb: {"session_id": sid, "url": f"https://verify.didit.me/{sid}"})
    with SessionLocal() as db:
        u = User(display_name="ver", email=f"ver-{uuid.uuid4().hex[:6]}@example.com"); db.add(u); db.commit(); db.refresh(u)
        token, uid = create_access_token(u.id, u.token_version), u.id
    client = TestClient(app, raise_server_exceptions=False)
    h = {"Authorization": f"Bearer {token}"}
    r1 = client.post("/api/verification/start", headers=h)
    assert r1.status_code == 200 and r1.json()["url"].endswith(sid)
    # прошло больше STALE_PENDING_HOURS — у нас заявка «устарела», у Didit сессия ещё жива и возвращается та же
    with SessionLocal() as db:
        req = db.query(DocVerificationRequest).filter(DocVerificationRequest.session_id == sid).one()
        req.created_at = utcnow() - timedelta(hours=verification.STALE_PENDING_HOURS + 1)
        db.commit()
    r2 = client.post("/api/verification/start", headers=h)
    assert r2.status_code == 200, r2.text
    with SessionLocal() as db:
        rows = db.query(DocVerificationRequest).filter(DocVerificationRequest.user_id == uid).all()
        assert len(rows) == 1 and rows[0].status == DocVerificationStatus.pending
