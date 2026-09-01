"""
Web Push — уведомления напрямую от браузера, без Telegram и без почты.

Работает через стандартный Push API: браузер даёт разрешение и
регистрирует «подписку» (адрес пуш-сервиса + два ключа шифрования),
мы шлём на неё зашифрованное сообщение, сервис браузера доставляет
его на устройство, даже если сайт закрыт.
"""
import json
import logging

from py_vapid import Vapid
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.core.config import settings

log = logging.getLogger(__name__)

# Строим объект Vapid из PEM сами, один раз при первой отправке — не
# передаём саму строку ключа в webpush() напрямую. У pywebpush
# внутри (py_vapid.Vapid.from_string) наивное угадывание формата: если
# строка не путь к файлу, оно просто убирает переносы строк и
# декодирует ВСЮ строку как base64 — включая буквальный текст
# '-----BEGIN PRIVATE KEY-----', который в ней есть. Так это никогда
# не сработает с полным PEM (а именно в таком виде ключ хранится в
# .env — там он и остаётся, менять формат хранения не пришлось).
# Vapid.from_pem() читает PEM правильно — режет первую/последнюю
# строку (сами маркеры BEGIN/END), собирает то, что между ними.
_vapid_obj = None


def _get_vapid() -> Vapid | None:
    global _vapid_obj
    if _vapid_obj is not None:
        return _vapid_obj
    if not settings.vapid_private_key:
        return None
    try:
        _vapid_obj = Vapid.from_pem(settings.vapid_private_key.encode())
    except Exception as exc:                          # noqa: BLE001
        log.error("Не удалось прочитать VAPID-ключ: %s", exc)
        return None
    return _vapid_obj


def send_web_push(db: Session, user_id, title: str, body: str, link: str | None = None) -> int:
    """
    Шлёт на все подписки человека сразу — телефон и компьютер получат
    оба. Мёртвые подписки (410 Gone — браузер отписал сам, например
    после переустановки) стираем тут же, а не копим мусор в базе.
    """
    vapid = _get_vapid()
    if not vapid or not settings.vapid_public_key:
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
                vapid_private_key=vapid,
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
