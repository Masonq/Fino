"""
Запись входа — IP, устройство, страна/город.

Общая точка для обоих настоящих путей входа (код на email/telegram,
бот) — раньше вызывалась бы в двух местах отдельно и легко разошлась
бы после первой же правки одного из них.
"""
import json
import logging
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


def record_login(request: Request, user_id, db: Session) -> None:
    ip = _client_ip(request)
    device_guid = request.headers.get("x-device-id")
    country, city = _geo_lookup(ip)

    db.add(LoginEvent(
        user_id=user_id, ip_address=ip, device_guid=device_guid,
        country=country, city=city,
    ))
    db.commit()
