"""
Web Push — уведомления напрямую от браузера, без Telegram и без почты.

Работает через стандартный Push API: браузер даёт разрешение и
регистрирует «подписку» (адрес пуш-сервиса + два ключа шифрования),
мы шлём на неё зашифрованное сообщение, сервис браузера доставляет
его на устройство, даже если сайт закрыт.
"""
import json
import logging

from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.core.config import settings

log = logging.getLogger(__name__)


def send_web_push(db: Session, user_id, title: str, body: str, link: str | None = None) -> int:
    """
    Шлёт на все подписки человека сразу — телефон и компьютер получат
    оба. Мёртвые подписки (410 Gone — браузер отписал сам, например
    после переустановки) стираем тут же, а не копим мусор в базе.
    """
    if not settings.vapid_private_key or not settings.vapid_public_key:
        return 0

    from app.models import PushSubscription

    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    if not subs:
        return 0

    payload = json.dumps({"title": title, "body": body, "link": link or "/"})
    sent = 0
    dead = []

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            sent += 1
        except WebPushException as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (404, 410):
                # Подписка больше не существует на стороне браузера —
                # отписался, снёс приложение, сменил устройство.
                dead.append(sub.id)
            else:
                log.warning("Web Push не доставлен (%s): %s", status, exc)
        except Exception as exc:                     # noqa: BLE001
            log.warning("Web Push: неожиданная ошибка: %s", exc)

    if dead:
        db.query(PushSubscription).filter(PushSubscription.id.in_(dead)).delete(synchronize_session=False)
        db.commit()

    return sent
