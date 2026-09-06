import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models import User, UserRole, Language, BlockedUser, SellerSubscription

router = APIRouter(prefix="/api/users", tags=["users"])


class QuickIdentifyIn(BaseModel):
    phone: str
    display_name: str




@router.get("/{user_id}/public")
def public_profile(user_id: uuid.UUID, lang: str = "ru", db: Session = Depends(get_db),
                    viewer: User | None = Depends(get_current_user_optional)):
    """
    Открытая карточка продавца: то, по чему покупатель решает, иметь ли дело.

    Ни телефона, ни почты — контакты появляются только через чат, иначе
    страница продавца превращается в базу для сбора номеров.
    """
    from app.models import Listing, ListingStatus

    user = db.query(User).get(user_id)
    if not user or user.is_blocked:
        raise HTTPException(404, "not_found")

    active = (
        db.query(Listing)
        .filter(Listing.owner_id == user.id, Listing.status == ListingStatus.active)
        .count()
    )

    is_subscribed = False
    if viewer and viewer.id != user.id:
        is_subscribed = (
            db.query(SellerSubscription)
            .filter(SellerSubscription.subscriber_id == viewer.id,
                    SellerSubscription.seller_id == user.id)
            .first() is not None
        )

    from app.core.reply_speed import reply_speed, speed_label

    speed = reply_speed(db, user.id)
    reply = {"label": speed_label(speed["median_minutes"]),
             "answered": speed["answered"]} if speed else None

    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "is_company": user.role == UserRole.seller_business,
        "company_name": user.company_name if user.role == UserRole.seller_business else None,
        "company_description": user.company_description if user.role == UserRole.seller_business else None,
        "document_verified": user.document_verified,
        "company_verified": user.company_verified,
        "rating_avg": float(user.rating_avg or 0),
        "rating_count": int(user.rating_count or 0),
        "active_listings": active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        "is_subscribed": is_subscribed,
        # Как быстро отвечает — по своим же перепискам.
        #
        # Люди ждут ответа быстро, и там, где он приходит скоро, чаще
        # доходит до сделки. Показываем не точные минуты, а порядок:
        # «обычно отвечает в течение часа». Точная цифра звучала бы как
        # обещание, которого продавец не давал.
        #
        # Пока ответов меньше трёх — не показываем ничего: два быстрых
        # ответа это случайность, а не отзывчивость.
        "reply_speed": reply,
    }


@router.post("/{user_id}/subscribe")
def subscribe_to_seller(user_id: uuid.UUID, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user_id == user.id:
        raise HTTPException(400, "cannot_subscribe_self")
    seller = db.query(User).get(user_id)
    if not seller or seller.is_blocked:
        raise HTTPException(404, "not_found")

    existing = (
        db.query(SellerSubscription)
        .filter(SellerSubscription.subscriber_id == user.id,
                SellerSubscription.seller_id == user_id)
        .first()
    )
    if not existing:
        db.add(SellerSubscription(subscriber_id=user.id, seller_id=user_id))
        db.commit()
    return {"status": "subscribed"}


@router.delete("/{user_id}/subscribe")
def unsubscribe_from_seller(user_id: uuid.UUID, user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    (
        db.query(SellerSubscription)
        .filter(SellerSubscription.subscriber_id == user.id,
                SellerSubscription.seller_id == user_id)
        .delete()
    )
    db.commit()
    return {"status": "unsubscribed"}


class ProfileEdit(BaseModel):
    """Что человек может поменять о себе сам."""
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    default_language: Language | None = None
    # Компания — для тех, кто продаёт как бизнес. Проверку по реестру
    # это не отменяет: название человек пишет сам, а галочку ставим мы.
    company_name: str | None = Field(default=None, max_length=255)
    # Описание на витрине — под названием, покупатель видит его первым.
    company_description: str | None = Field(default=None, max_length=2000)
    # Для звонка через чат (см. chats.py) — без него вся функция
    # скрыта целиком, нечего раскрывать покупателю. Формат — как
    # прислал фронтенд (код страны уже вписан туда же, не отдельным
    # полем): +381 плюс цифры, но заставлять именно этот формат тут
    # незачем — просто нормализуем и проверяем, что не занят.
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, v):
        # min_length в Field проверяет строку ДО обрезки пробелов —
        # «  a  » (4 символа) проходил бы, хотя после strip() внизу
        # это один символ. Обрезаем здесь же, до самой проверки длины.
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("too_short")
        return v


@router.get("/me")
def my_profile(user: User = Depends(get_current_user)):
    """Свои данные — для страницы профиля."""
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "role": user.role.value,
        "default_language": user.default_language.value,
        "email_verified": user.email_verified,
        "company_name": user.company_name,
        "company_description": user.company_description,
        "company_verified": user.company_verified,
        "rating_avg": round(user.rating_avg or 0, 2),
        "rating_count": user.rating_count,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.patch("/me")
def edit_profile(
    payload: ProfileEdit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Правка своих данных.

    Меняем только то, что прислали: пустое поле означает «не трогать», а
    не «стереть» — иначе правка имени обнулила бы всё остальное.
    """
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url or None
    if payload.default_language is not None:
        user.default_language = payload.default_language
    if payload.company_name is not None:
        name = payload.company_name.strip()
        # Впервые становится бизнес-аккаунтом именно сейчас — не был
        # им раньше и не персонал. На уже действующий бизнес-аккаунт
        # (правит своё же название) эта проверка второй раз не действует.
        becoming_business = bool(
            name and user.role not in (UserRole.moderator, UserRole.admin, UserRole.seller_business)
        )
        if becoming_business and not user.document_verified:
            # Витрина, значок компании, доверие покупателя — всё это
            # не выдаём просто по факту того, что кто-то напечатал
            # название в поле. Сначала подтвердить, что за аккаунтом
            # стоит реальный, проверенный человек.
            raise HTTPException(400, "verify_identity_first")
        # Название поменяли — прежняя проверка к нему не относится.
        if name != (user.company_name or ""):
            user.company_verified = False
        user.company_name = name or None
        if becoming_business:
            user.role = UserRole.seller_business
    if payload.company_description is not None:
        user.company_description = payload.company_description.strip() or None
    if payload.phone is not None:
        phone = payload.phone.strip()
        if phone:
            taken = (
                db.query(User)
                .filter(User.phone == phone, User.id != user.id)
                .first()
            )
            if taken:
                raise HTTPException(400, "phone_already_used")
            user.phone = phone
        else:
            user.phone = None

    db.commit()
    return my_profile(user)


@router.get("/me/referrals")
def my_referrals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Сколько людей привёл и скольким уже начислен бонус — id для самой
    ссылки (plonk.rs/?ref=<id>) строится на фронте из user.id, тут
    только счётчик, отдельным эндпоинтом: не вешаем лишний COUNT-запрос
    на /auth/me, который дёргается при каждой загрузке приложения.
    """
    total = db.query(User).filter(User.referred_by == user.id).count()
    rewarded = db.query(User).filter(
        User.referred_by == user.id, User.referral_reward_given.is_(True)).count()
    return {"invited_total": total, "invited_rewarded": rewarded}


@router.get("/blocked")
def list_blocked(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Кого сам заблокировал — раньше это можно было увидеть и снять
    только изнутри конкретного чата (кнопка «Разблокировать» в
    шапке переписки), отдельной страницы со списком не было вовсе.
    """
    rows = (
        db.query(BlockedUser, User)
        .join(User, User.id == BlockedUser.blocked_id)
        .filter(BlockedUser.blocker_id == user.id)
        .order_by(BlockedUser.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": str(blocked.id),
                "display_name": blocked.display_name,
                "avatar_url": blocked.avatar_url,
                "blocked_at": bu.created_at.isoformat(),
            }
            for bu, blocked in rows
        ]
    }


@router.post("/blocked/{blocked_id}/unblock")
def unblock_user(
    blocked_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Та же операция, что и кнопка внутри чата (chats.py:unblock_participant),
    только не требует открывать конкретную переписку, чтобы её найти."""
    db.query(BlockedUser).filter(
        BlockedUser.blocker_id == user.id,
        BlockedUser.blocked_id == blocked_id,
    ).delete()
    db.commit()
    return {"status": "unblocked"}
