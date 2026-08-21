import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import User, UserRole, Language

router = APIRouter(prefix="/api/users", tags=["users"])


class QuickIdentifyIn(BaseModel):
    phone: str
    display_name: str


@router.post("/quick")
def quick_identify(payload: QuickIdentifyIn, db: Session = Depends(get_db)):
    """ВРЕМЕННАЯ заглушка вместо полноценной авторизации.
    Возвращает существующего пользователя по телефону или создаёт нового —
    без пароля и без верификации SMS. Заменить на JWT + OTP в следующей итерации
    (см. roadmap в README). Нужна только чтобы форма публикации объявления
    могла сохранять owner_id, а не просто рисовать UI.
    """
    user = db.query(User).filter(User.phone == payload.phone).first()
    if user:
        return {"id": str(user.id), "phone": user.phone, "display_name": user.display_name}

    user = User(
        id=uuid.uuid4(),
        phone=payload.phone,
        hashed_password="",
        display_name=payload.display_name,
        role=UserRole.seller_private,
        default_language=Language.ru,
        phone_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "phone": user.phone, "display_name": user.display_name}
