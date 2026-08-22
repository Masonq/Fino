import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta

from jose import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.core.clock import utcnow

ALGORITHM = "HS256"
ACCESS_TTL = timedelta(days=30)


# --- пароли ---
# Используем PBKDF2 из стандартной библиотеки: не тянем лишних зависимостей,
# при этом это медленный алгоритм с солью, пригодный для хранения паролей.
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("pbkdf2$"):
        return False
    _, salt, expected = stored.split("$", 2)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000)
    return hmac.compare_digest(digest.hex(), expected)


# --- коды подтверждения ---
def generate_code() -> str:
    """Шестизначный код. secrets, а не random — код не должен быть предсказуем."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str) -> str:
    return hashlib.sha256(f"{settings.secret_key}:{code}".encode()).hexdigest()


def verify_code(code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code), stored_hash)


# --- токены ---
def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": utcnow() + ACCESS_TTL,
        "iat": utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return uuid.UUID(payload["sub"])
    except Exception:
        return None


# --- зависимости FastAPI ---
def _token_from_request(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(401, "not_authenticated")

    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(401, "invalid_token")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(401, "user_not_found")
    if user.is_blocked:
        raise HTTPException(403, "user_blocked")

    # Отмечаем активность, но не чаще раза в минуту — иначе запись в базу
    # на каждый запрос, а их десятки в минуту.
    now = utcnow()
    if not user.last_seen_at or (now - user.last_seen_at).total_seconds() > 60:
        user.last_seen_at = now
        db.commit()

    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Для экранов, которые работают и без входа (лента, поиск)."""
    token = _token_from_request(request)
    if not token:
        return None
    user_id = decode_token(token)
    if not user_id:
        return None
    return db.query(User).get(user_id)
