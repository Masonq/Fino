"""
Запись входа — IP, устройство, страна/город.

Общая точка для обоих настоящих путей входа (код на email/telegram,
бот) — раньше вызывалась бы в двух местах отдельно и легко разошлась
бы после первой же правки одного из них.
"""
import json
import logging
import threading
import urllib.error
import urllib.request

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import LoginEvent

log = logging.getLogger(__name__)


def _client_ip(request: Request) -> str | None:
    # nginx кладёт настоящий IP в X-Real-IP (см. deploy/plonk.rs.conf) —
    # request.client.host за прокси был бы адресом самого nginx.
    return request.headers.get("x-real-ip") or (request.client.host if request.client else None)


def _geo_lookup(ip: str | None) -> tuple[str | None, str | None]:
    """
    Страна/город по IP — бесплатный ip-api.com, без ключа. Не блокируем
    вход, если сервис недоступен или ответил не тем: геоданные тут
    вспомогательные, не обязательное условие входа.
    """
    if not ip or ip in ("127.0.0.1", "::1"):
        return None, None
    try:
        with urllib.request.urlopen(
            f"http://ip-api.com/json/{ip}?fields=status,countryCode,city", timeout=3,
        ) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "success":
            return data.get("countryCode"), data.get("city")
    except Exception as exc:                     # noqa: BLE001
        log.info("геолокация IP не удалась: %s", exc)
    return None, None


def _fill_geo_later(event_id) -> None:
    """
    Достаёт страну/город после того, как вход уже случился — в
    отдельном потоке, со своей сессией. У бесплатного ip-api.com
    жёсткий лимит запросов в минуту: раньше это был синхронный вызов
    прямо внутри record_login(), и человек ждал ответа чужого сервиса,
    чтобы просто войти. При наплыве логинов, упёршихся в лимит, каждый
    вход стал бы занимать до 3 секунд разом на пустом месте.
    """
    from app.core.database import SessionLocal

    ip = None
    with SessionLocal() as db:
        event = db.query(LoginEvent).get(event_id)
        if not event:
            return
        ip = event.ip_address
    country, city = _geo_lookup(ip)
    if not country and not city:
        return
    with SessionLocal() as db:
        event = db.query(LoginEvent).get(event_id)
        if event:
            event.country = country
            event.city = city
            db.commit()


def record_login(request: Request, user_id, db: Session) -> None:
    ip = _client_ip(request)
    device_guid = request.headers.get("x-device-id")

    event = LoginEvent(user_id=user_id, ip_address=ip, device_guid=device_guid)
    db.add(event)
    db.commit()
    db.refresh(event)

    threading.Thread(target=_fill_geo_later, args=(event.id,), daemon=True).start()
