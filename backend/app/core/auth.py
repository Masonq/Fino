import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

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
def create_access_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "exp": utcnow() + ACCESS_TTL,
        "iat": utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> tuple[uuid.UUID, int] | None:
    """Возвращает (id пользователя, версия токена в самом токене) — версию
    сверяет с текущей уже get_current_user, тут только достаём из JWT.
    Старые токены, выпущенные до появления поля "tv" (до этой правки),
    не несут его вовсе — .get(..., 0) читает их как версию 0, ту же,
    что и у only что созданных пользователей: не рвём вход тем, кто уже
    был залогинен на момент раскатки этой правки."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return uuid.UUID(payload["sub"]), payload.get("tv", 0)
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

    decoded = decode_token(token)
    if not decoded:
        raise HTTPException(401, "invalid_token")
    user_id, token_ver = decoded

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(401, "user_not_found")
    # Версия в токене устарела — где-то был выход из аккаунта уже после
    # того, как этот конкретный токен выпустили. Тот же ответ, что и на
    # заведомо неверный токен: с точки зрения того, кто его предъявляет,
    # разницы нет — токен просто больше не работает.
    if token_ver != user.token_version:
        raise HTTPException(401, "invalid_token")
    if user.is_blocked:
        raise HTTPException(403, "user_blocked")

    # Отмечаем активность, но не чаще раза в минуту — иначе запись в базу
    # на каждый запрос, а их десятки в минуту.
    now = utcnow()
    if not user.last_seen_at or (now - user.last_seen_at).total_seconds() > 60:
        user.last_seen_at = now
        # Человек пришёл — значит сводки по поискам читает. Счётчик
        # неоткрытых обнуляем: иначе тот, кто заходит сам, через три
        # дня перестал бы их получать.
        if user.search_digest_ignored:
            user.search_digest_ignored = 0
        db.commit()

    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Для экранов, которые работают и без входа (лента, поиск)."""
    token = _token_from_request(request)
    if not token:
        return None
    decoded = decode_token(token)
    if not decoded:
        return None
    user_id, token_ver = decoded
    user = db.query(User).get(user_id)
    if not user or token_ver != user.token_version:
        return None
    # Заблокированный — всё равно что не вошедший.
    #
    # Раньше здесь проверки не было, и человек после блокировки
    # продолжал листать ленту, открывать объявления и писать в
    # переписки: обязательный вход блокировку ловил, а этот —
    # необязательный, через который работает лента, — нет.
    #
    # Возвращаем None, а не ошибку: страницы, доступные всем, должны
    # открываться и гостю. Всё, что требует входа, отсечётся на
    # обязательной проверке.
    if user.is_blocked:
        return None
    return user


def require_named_user(user: User = Depends(get_current_user)) -> User:
    """
    Тот же вошедший человек, но со сброшенным именем ему сюда нельзя.

    Модератор сбрасывает имя, когда оно непристойное или нечитаемое
    (ряды значков во всю строку). Пока новое не введено, человек может
    ходить по сайту и читать, но не выкладывать объявления и не писать
    продавцам: имя видно и там, и там.
    """
    if getattr(user, "must_rename", False):
        raise HTTPException(403, "must_rename")
    return user
