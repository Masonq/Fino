"""
Вход в приложение через Telegram: приложение придумывает ключ, бот подтверждает его (issue с key), приложение
обменивает ключ на вход через /api/auth/telegram/enter. Ключ одноразовый; небезопасный ключ не принимается.
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.routers.auth_telegram import issue  # noqa: E402


def test_app_key_is_used_and_exchanged_once():
    client = TestClient(app)
    key = secrets.token_urlsafe(24)
    assert client.post("/api/auth/telegram/enter", json={"key": key}).status_code == 400, "до подтверждения в боте — нет входа"
    assert issue(987654321000 + secrets.randbelow(1000), "Тест Приложение", None, key=key) == key
    r = client.post("/api/auth/telegram/enter", json={"key": key})
    assert r.status_code == 200 and r.json().get("access_token")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).status_code == 200
    assert client.post("/api/auth/telegram/enter", json={"key": key}).status_code == 400, "ключ одноразовый"


def test_unsafe_key_is_replaced():
    k = issue(987654322000 + secrets.randbelow(1000), "Тест", None, key="bad key/../x")
    assert k != "bad key/../x" and len(k) >= 24
