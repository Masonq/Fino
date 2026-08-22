import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token, generate_code, hash_code, verify_code,
    hash_password, verify_password, get_current_user,
)
from app.core.database import get_db
from app.core.notify import send_code
from app.models import User, VerificationCode, VerifyChannel
from app.core.clock import utcnow

router = APIRouter(prefix="/api/auth", tags=["auth"])

CODE_TTL = timedelta(minutes=15)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)


# ---------- схемы ----------
class RequestCodeIn(BaseModel):
    destination: str          # email-адрес или telegram-идентификатор
    channel: VerifyChannel = VerifyChannel.email


class VerifyCodeIn(BaseModel):
    destination: str
    code: str
    display_name: str | None = None
    channel: VerifyChannel = VerifyChannel.email


class PasswordLoginIn(BaseModel):
    email: EmailStr
    password: str


class SetPasswordIn(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def check_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password_too_short")
        return v


class OAuthIn(BaseModel):
    provider: str             # google | apple | telegram | viber
    external_id: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "email_verified": user.email_verified,
        "role": user.role.value if user.role else None,
    }


# ---------- вход по коду ----------
@router.post("/request-code")
def request_code(payload: RequestCodeIn, db: Session = Depends(get_db)):
    destination = payload.destination.strip().lower()
    if not destination:
        raise HTTPException(400, "destination_required")

    # не даём засыпать человека кодами
    recent = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.destination == destination,
            VerificationCode.created_at > utcnow() - RESEND_COOLDOWN,
        )
        .first()
    )
    if recent:
        raise HTTPException(429, "too_many_requests")

    code = generate_code()
    db.add(VerificationCode(
        destination=destination,
        channel=payload.channel,
        code_hash=hash_code(code),
        expires_at=utcnow() + CODE_TTL,
    ))
    db.commit()

    send_code(destination, code, payload.channel)
    return {"status": "sent", "channel": payload.channel.value}


@router.post("/verify-code")
def verify_code_endpoint(payload: VerifyCodeIn, db: Session = Depends(get_db)):
    destination = payload.destination.strip().lower()

    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.destination == destination,
            VerificationCode.used.is_(False),
            VerificationCode.expires_at > utcnow(),
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(400, "code_expired")

    if record.attempts >= MAX_ATTEMPTS:
        raise HTTPException(429, "too_many_attempts")

    if not verify_code(payload.code.strip(), record.code_hash):
        record.attempts += 1
        db.commit()
        raise HTTPException(400, "invalid_code")

    record.used = True

    # находим или создаём пользователя
    if payload.channel == VerifyChannel.email:
        user = db.query(User).filter(User.email == destination).first()
        if not user:
            user = User(
                email=destination,
                display_name=payload.display_name or destination.split("@")[0],
                email_verified=True,
            )
            db.add(user)
        else:
            user.email_verified = True
    else:
        user = db.query(User).filter(User.telegram_id == destination).first()
        if not user:
            user = User(
                telegram_id=destination,
                display_name=payload.display_name or f"user{destination[-4:]}",
            )
            db.add(user)

    db.commit()
    db.refresh(user)

    return {"token": create_access_token(user.id), "user": _user_payload(user)}


# ---------- вход по паролю ----------
@router.post("/login")
def login(payload: PasswordLoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    # одинаковая ошибка в обоих случаях — чтобы нельзя было выяснить, есть ли такой email
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "invalid_credentials")
    if user.is_blocked:
        raise HTTPException(403, "user_blocked")

    return {"token": create_access_token(user.id), "user": _user_payload(user)}


@router.post("/set-password")
def set_password(
    payload: SetPasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.hashed_password = hash_password(payload.password)
    db.commit()
    return {"status": "ok"}


# ---------- внешние сервисы ----------
@router.post("/oauth")
def oauth_login(payload: OAuthIn, db: Session = Depends(get_db)):
    """
    Вход через Google / Apple / Telegram / Viber.
    Проверка подписи провайдера делается до вызова — здесь только связывание аккаунта.
    """
    field_map = {
        "google": User.google_id,
        "apple": User.apple_id,
        "telegram": User.telegram_id,
        "viber": User.viber_id,
    }
    if payload.provider not in field_map:
        raise HTTPException(400, "unknown_provider")

    column = field_map[payload.provider]
    user = db.query(User).filter(column == payload.external_id).first()

    # если аккаунта нет — пробуем связать по email, иначе создаём
    if not user and payload.email:
        user = db.query(User).filter(User.email == payload.email.lower()).first()

    if not user:
        user = User(
            display_name=payload.display_name or payload.provider.capitalize(),
            email=payload.email.lower() if payload.email else None,
            email_verified=bool(payload.email),
            avatar_url=payload.avatar_url,
        )
        db.add(user)

    setattr(user, column.key, payload.external_id)
    if payload.avatar_url and not user.avatar_url:
        user.avatar_url = payload.avatar_url

    db.commit()
    db.refresh(user)

    return {"token": create_access_token(user.id), "user": _user_payload(user)}


# ---------- профиль ----------
@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_payload(user)


class UpdateMeIn(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    default_language: str | None = None


@router.patch("/me")
def update_me(
    payload: UpdateMeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.display_name:
        user.display_name = payload.display_name.strip()[:120]
    if payload.phone is not None:
        user.phone = payload.phone.strip() or None
    if payload.default_language:
        user.default_language = payload.default_language
    db.commit()
    db.refresh(user)
    return _user_payload(user)
