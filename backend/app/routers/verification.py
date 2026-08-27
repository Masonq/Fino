import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.clock import utcnow
from app.models import DocVerificationRequest, DocVerificationStatus, User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verification", tags=["verification"])

DIDIT_HOST = "https://verification.didit.me"
# 5 минут — тот же порог, что Didit сам приводит в примере проверки
# подписи: старее считаем попыткой повтора запроса, не настоящим
# вебхуком.
WEBHOOK_MAX_AGE = 300


@router.get("/me")
def my_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Статус для самого человека — показать в профиле."""
    if user.document_verified:
        return {"status": "verified"}

    pending = (
        db.query(DocVerificationRequest)
        .filter(
            DocVerificationRequest.user_id == user.id,
            DocVerificationRequest.status == DocVerificationStatus.pending,
        )
        .first()
    )
    if pending:
        return {"status": "pending"}

    last = (
        db.query(DocVerificationRequest)
        .filter(DocVerificationRequest.user_id == user.id)
        .order_by(DocVerificationRequest.created_at.desc())
        .first()
    )
    if last and last.status == DocVerificationStatus.rejected:
        return {"status": "rejected", "reason": last.reject_reason}

    return {"status": "none"}


@router.post("/start")
def start(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Заводит сессию проверки у Didit и отдаёт ссылку — человек снимает
    документ и селфи уже там, к нам ни то ни другое не попадает вовсе.
    """
    if not settings.didit_api_key or not settings.didit_workflow_id:
        raise HTTPException(503, "verification_not_configured")

    if user.document_verified:
        raise HTTPException(400, "already_verified")

    existing_pending = (
        db.query(DocVerificationRequest)
        .filter(
            DocVerificationRequest.user_id == user.id,
            DocVerificationRequest.status == DocVerificationStatus.pending,
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(400, "already_pending")

    callback = f"{settings.public_base_url}/api/verification/webhook"
    body = json.dumps({
        "workflow_id": settings.didit_workflow_id,
        "callback": callback,
        "vendor_data": str(user.id),
    }).encode()
    req_obj = urllib.request.Request(
        f"{DIDIT_HOST}/v2/session/",
        data=body,
        headers={
            "X-Api-Key": settings.didit_api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req_obj, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        log.warning("Didit отклонил создание сессии для %s: %s %s",
                   user.id, exc.code, exc.read()[:300])
        raise HTTPException(502, "verification_unavailable")
    except Exception as exc:
        log.warning("не удалось создать сессию Didit для %s: %s", user.id, exc)
        raise HTTPException(502, "verification_unavailable")

    req = DocVerificationRequest(user_id=user.id, session_id=data["session_id"])
    db.add(req)
    db.commit()
    return {"url": data["url"]}


def _verify_signature(raw_body: bytes, signature: str | None, timestamp: str | None) -> bool:
    if not signature or not timestamp or not settings.didit_webhook_secret:
        return False
    try:
        if abs(int(time.time()) - int(timestamp)) > WEBHOOK_MAX_AGE:
            return False
    except ValueError:
        return False

    expected = hmac.new(
        settings.didit_webhook_secret.encode("utf-8"), raw_body, hashlib.sha256,
    ).hexdigest()
    # Сравнение постоянного времени — иначе разница во времени ответа
    # выдаёт правильные символы подписи один за другим.
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def webhook(request: Request):
    """
    Сюда стучится сам Didit, не человек из приложения — без входа, но
    с проверкой подписи вместо него. Обязательно сверяем подпись по
    сырым байтам тела: разбор в JSON и сборка обратно меняют пробелы
    и порядок ключей, и подпись перестаёт совпадать.
    """
    raw = await request.body()
    if not _verify_signature(raw, request.headers.get("x-signature"),
                             request.headers.get("x-timestamp")):
        raise HTTPException(401, "bad_signature")

    payload = await request.json()
    session_id = payload.get("session_id")
    status = payload.get("status")
    if not session_id or not status:
        return {"status": "ignored"}

    db = SessionLocal()
    try:
        req = db.query(DocVerificationRequest).filter(
            DocVerificationRequest.session_id == session_id,
        ).first()
        if not req or req.status != DocVerificationStatus.pending:
            # Уже решено раньше (или сессия не наша) — Didit иногда
            # шлёт один и тот же статус повторно, второй раз просто
            # подтверждаем приём, не трогая ничего.
            return {"status": "ok"}

        if status == "Approved":
            user = db.query(User).get(req.user_id)
            if user:
                user.document_verified = True
            req.status = DocVerificationStatus.approved
            req.reviewed_at = utcnow()
            db.commit()
            try:
                from app.core.notifications import notify_doc_verification
                if user:
                    notify_doc_verification(db, user.id, True)
            except Exception:
                pass

        elif status in ("Declined", "Abandoned"):
            decision = payload.get("decision") or {}
            warnings = (decision.get("id_verification") or {}).get("warnings") or []
            reason = warnings[0]["short_description"] if warnings else None

            req.status = DocVerificationStatus.rejected
            req.reject_reason = reason
            req.reviewed_at = utcnow()
            db.commit()
            try:
                from app.core.notifications import notify_doc_verification
                notify_doc_verification(db, req.user_id, False, reason)
            except Exception:
                pass

        # Остальные статусы (Not Started/In Progress/In Review) — это
        # промежуточные шаги самой сессии, не решение; ничего не меняем,
        # ждём следующего вебхука.
        return {"status": "ok"}
    finally:
        db.close()
