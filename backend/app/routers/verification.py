import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.clock import utcnow
from app.models import DocVerificationRequest, DocVerificationStatus, DocVerificationKind, User
from app.routers.moderation import require_moderator

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verification", tags=["verification"])

DIDIT_HOST = "https://verification.didit.me"
# 5 минут — тот же порог, что Didit сам приводит в примере проверки
# подписи: старее считаем попыткой повтора запроса, не настоящим
# вебхуком.
WEBHOOK_MAX_AGE = 300
# Сколько ждать, прежде чем считать «на проверке» брошенной сессией и
# разрешить начать заново. Живой документ + селфи занимают минуты —
# час с большим запасом. Без этого порога человек, вышедший на
# середине (закрыл вкладку, не дошёл до конца на стороне Didit — там
# решать ещё нечего, вебхука с решением просто не будет никогда),
# оставался бы с вечным «на проверке» без единого способа попробовать
# снова.
STALE_PENDING_HOURS = 1


def _create_session(workflow_id: str, user_id, callback: str) -> dict:
    """Общая точка создания сессии — используется и первой проверкой,
    и повторной сверкой лица по запросу модератора."""
    body = json.dumps({
        "workflow_id": workflow_id,
        "callback": callback,
        "vendor_data": str(user_id),
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
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        log.warning("Didit отклонил создание сессии для %s: %s %s",
                   user_id, exc.code, exc.read()[:300])
        raise HTTPException(502, "verification_unavailable")
    except Exception as exc:
        log.warning("не удалось создать сессию Didit для %s: %s", user_id, exc)
        raise HTTPException(502, "verification_unavailable")


def _record_session(db: Session, user_id, session_id: str, kind, requested_by=None) -> None:
    """
    Запись заявки на проверку по сессии Didit. Didit может вернуть уже существующую сессию — ту же
    незавершённую проверку (у нас она старше STALE_PENDING_HOURS и считается устаревшей, у Didit — ещё жива).
    Раньше это была вторая вставка с тем же session_id → нарушение уникальности → 500, и в приложении
    «Подтвердить личность» молча не работало. Теперь сессия того же человека переиспользуется: снова
    «на проверке», свежее время; чужая сессия (не должно случаться) — отказ без падения.
    """
    req = db.query(DocVerificationRequest).filter(DocVerificationRequest.session_id == session_id).first()
    if req:
        if req.user_id != user_id:
            log.warning("Didit вернул чужую сессию %s для %s", session_id, user_id)
            raise HTTPException(502, "verification_unavailable")
        req.status = DocVerificationStatus.pending
        req.kind = kind
        req.created_at = utcnow()
        req.reject_reason = None
        req.reviewed_at = None
        if requested_by is not None:
            req.requested_by = requested_by
    else:
        db.add(DocVerificationRequest(user_id=user_id, session_id=session_id, kind=kind, requested_by=requested_by))
    db.commit()


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
            DocVerificationRequest.created_at >= utcnow() - timedelta(hours=STALE_PENDING_HOURS),
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
            DocVerificationRequest.created_at >= utcnow() - timedelta(hours=STALE_PENDING_HOURS),
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(400, "already_pending")

    # callback — не адрес вебхука (тот настроен отдельно, на уровне
    # приложения в кабинете Didit), а куда вернуть человека браузером
    # после того, как он закончит на стороне Didit.
    data = _create_session(settings.didit_workflow_id, user.id, f"{settings.site_base_url}/profile")

    _record_session(db, user.id, data["session_id"], DocVerificationKind.initial)
    return {"url": data["url"]}


@router.post("/moderation/{user_id}/reverify")
def request_reverify(
    user_id: uuid.UUID,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """
    Модератор запрашивает у уже проверенного человека повторную сверку
    лица — например, заподозрив, что аккаунт продали или передали
    кому-то другому. Значок должен принадлежать конкретному человеку,
    а не путешествовать вместе с логином и паролем.

    Лёгкий workflow: только Liveness + Face Match, без пересъёмки
    документа — сверяет с биометрией, уже сохранённой у Didit с первой
    проверки. Ссылку получает не модератор, а сам человек — уведомлением.
    """
    if not settings.didit_api_key:
        raise HTTPException(503, "verification_not_configured")

    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(404, "not_found")
    if not target.document_verified:
        raise HTTPException(400, "not_verified")

    existing_pending = (
        db.query(DocVerificationRequest)
        .filter(
            DocVerificationRequest.user_id == user_id,
            DocVerificationRequest.status == DocVerificationStatus.pending,
            DocVerificationRequest.created_at >= utcnow() - timedelta(hours=STALE_PENDING_HOURS),
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(400, "already_pending")

    data = _create_session(settings.didit_reverify_workflow_id, user_id,
                           f"{settings.site_base_url}/profile")

    _record_session(db, user_id, data["session_id"], DocVerificationKind.reverify, requested_by=moderator.id)

    try:
        from app.core.notifications import notify_reverify_requested
        notify_reverify_requested(db, user_id, data["url"])
    except Exception:
        pass
    return {"status": "requested"}


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

        user = db.query(User).get(req.user_id)

        if status == "Approved":
            req.status = DocVerificationStatus.approved
            req.reviewed_at = utcnow()
            # У initial — это и есть момент, когда появляется отметка.
            # У reverify она уже стояла: подтверждение просто оставляет
            # её как есть, ничего дополнительно включать не нужно.
            if req.kind == DocVerificationKind.initial and user:
                user.document_verified = True
            db.commit()
            try:
                from app.core.notifications import notify_doc_verification
                if user and req.kind == DocVerificationKind.initial:
                    notify_doc_verification(db, user.id, True)
            except Exception:
                pass

        elif status in ("Declined", "Abandoned", "Expired"):
            decision = payload.get("decision") or {}
            warnings = (decision.get("id_verification") or {}).get("warnings") or []
            reason = warnings[0]["short_description"] if warnings else None

            req.status = DocVerificationStatus.rejected
            req.reject_reason = reason
            req.reviewed_at = utcnow()
            # У reverify отказ — не «не подтвердили с первого раза», а
            # прямой повод снять уже стоящую отметку: лицо не совпало
            # с тем, что было при первой проверке, или человек так и
            # не прошёл её вовсе.
            if req.kind == DocVerificationKind.reverify and user:
                user.document_verified = False
            db.commit()
            try:
                from app.core.notifications import notify_doc_verification
                notify_doc_verification(db, req.user_id, False, reason,
                                        revoked=(req.kind == DocVerificationKind.reverify))
            except Exception:
                pass

        # Остальные статусы (Not Started/In Progress/In Review) — это
        # промежуточные шаги самой сессии, не решение; ничего не меняем,
        # ждём следующего вебхука.
        return {"status": "ok"}
    finally:
        db.close()
