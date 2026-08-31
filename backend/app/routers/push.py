from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import User, PushSubscription

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key")
def vapid_public_key():
    """
    Публичный ключ — не секрет, но выдаём его через API, а не
    захардкоженным на фронте: сменить ключ (например если приватный
    когда-нибудь утечёт) можно будет одной переменной на сервере,
    без пересборки и передеплоя фронтенда.
    """
    return {"key": settings.vapid_public_key}


class SubscribeIn(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.post("/subscribe")
def subscribe(payload: SubscribeIn, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    existing = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == payload.endpoint)
        .first()
    )
    if existing:
        # Тот же браузер мог переподписаться (ключи меняются при
        # определённых условиях) или это был другой пользователь на
        # этом же устройстве — переносим на текущего.
        existing.user_id = user.id
        existing.p256dh = payload.p256dh
        existing.auth = payload.auth
    else:
        db.add(PushSubscription(
            user_id=user.id, endpoint=payload.endpoint,
            p256dh=payload.p256dh, auth=payload.auth,
        ))
    db.commit()
    return {"status": "subscribed"}


class UnsubscribeIn(BaseModel):
    endpoint: str


@router.post("/unsubscribe")
def unsubscribe(payload: UnsubscribeIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == payload.endpoint,
        PushSubscription.user_id == user.id,
    ).delete()
    db.commit()
    return {"status": "unsubscribed"}
