import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models import Review, User, Listing, Chat, ReviewInvite

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewIn(BaseModel):
    target_id: uuid.UUID
    listing_id: uuid.UUID | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


def recalc_rating(db: Session, user_id: uuid.UUID) -> None:
    """Пересчитываем средний рейтинг продавца после изменения отзывов."""
    row = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.target_id == user_id, Review.is_published.is_(True))
        .one()
    )
    user = db.query(User).get(user_id)
    if user:
        user.rating_avg = round(float(row[0] or 0), 2)
        user.rating_count = int(row[1] or 0)


@router.get("/user/{user_id}")
def user_reviews(
    user_id: uuid.UUID,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = (db.query(Review)
         .filter(Review.target_id == user_id, Review.is_published.is_(True))
         .order_by(Review.created_at.desc()))
    total = q.count()
    rows = q.offset(offset).limit(limit).all()

    authors = {
        u.id: u for u in db.query(User).filter(User.id.in_([r.author_id for r in rows])).all()
    } if rows else {}

    # разбивка по звёздам — чтобы показать распределение
    breakdown = {i: 0 for i in range(1, 6)}
    for rating, cnt in (
        db.query(Review.rating, func.count(Review.id))
        .filter(Review.target_id == user_id, Review.is_published.is_(True))
        .group_by(Review.rating)
        .all()
    ):
        breakdown[int(rating)] = int(cnt)

    user = db.query(User).get(user_id)

    return {
        "total": total,
        "rating_avg": float(user.rating_avg) if user else 0,
        "rating_count": int(user.rating_count) if user else 0,
        "breakdown": breakdown,
        "items": [
            {
                "id": str(r.id),
                "rating": r.rating,
                "comment": r.comment,
                "author_name": authors.get(r.author_id).display_name if authors.get(r.author_id) else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/can-review/{target_id}")
def can_review(
    target_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Можно ли оставить отзыв: был ли контакт и не оставлен ли отзыв ранее."""
    if target_id == user.id:
        return {"can": False, "reason": "self"}

    already = db.query(Review).filter(
        Review.author_id == user.id, Review.target_id == target_id
    ).first()
    if already:
        return {"can": False, "reason": "already"}

    contacted = db.query(Chat).filter(
        or_(
            (Chat.buyer_id == user.id) & (Chat.seller_id == target_id),
            (Chat.seller_id == user.id) & (Chat.buyer_id == target_id),
        )
    ).first()
    if not contacted:
        return {"can": False, "reason": "no_contact"}

    return {"can": True}


@router.post("")
def create_review(
    payload: ReviewIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.target_id == user.id:
        raise HTTPException(400, "self_review")

    already = db.query(Review).filter(
        Review.author_id == user.id, Review.target_id == payload.target_id
    ).first()
    if already:
        raise HTTPException(400, "already_reviewed")

    # Отзыв только после реального общения — иначе рейтинг легко накрутить
    contacted = db.query(Chat).filter(
        or_(
            (Chat.buyer_id == user.id) & (Chat.seller_id == payload.target_id),
            (Chat.seller_id == user.id) & (Chat.buyer_id == payload.target_id),
        )
    ).first()
    if not contacted:
        raise HTTPException(403, "no_contact")

    review = Review(
        author_id=user.id,
        target_id=payload.target_id,
        listing_id=payload.listing_id,
        rating=payload.rating,
        comment=(payload.comment or "").strip()[:2000] or None,
        verified_contact=True,
        created_at=datetime.utcnow(),
    )
    db.add(review)
    db.flush()

    # Взаимное раскрытие: если вторая сторона уже оставила отзыв по этой же
    # сделке — публикуем оба сразу. Если нет — ждём её или истечения срока.
    counterpart = db.query(Review).filter(
        Review.author_id == payload.target_id,
        Review.target_id == user.id,
        Review.listing_id == payload.listing_id,
        Review.is_published.is_(False),
    ).first()
    if counterpart:
        now = datetime.utcnow()
        counterpart.is_published = True
        counterpart.published_at = now
        review.is_published = True
        review.published_at = now
        recalc_rating(db, user.id)

    # закрываем приглашение, если отзыв оставлен по нему
    invite = db.query(ReviewInvite).filter(
        ReviewInvite.user_id == user.id,
        ReviewInvite.target_id == payload.target_id,
        ReviewInvite.responded.is_(False),
    ).first()
    if invite:
        invite.responded = True

    db.flush()
    recalc_rating(db, payload.target_id)
    db.commit()

    return {"status": "ok", "id": str(review.id)}


@router.post("/invite/{chat_id}/dismiss")
def dismiss_invite(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Человек не хочет оставлять отзыв — больше по этой сделке не спрашиваем."""
    invite = db.query(ReviewInvite).filter(
        ReviewInvite.chat_id == chat_id, ReviewInvite.user_id == user.id
    ).first()
    if invite:
        invite.dismissed = True
        db.commit()
    return {"status": "ok"}


def publish_expired(db: Session, wait_days: int = 7) -> int:
    """
    Вторая сторона так и не ответила за неделю — публикуем односторонний отзыв.
    Иначе честный отзыв о недобросовестном продавце никогда не увидит свет:
    ему достаточно просто промолчать.
    """
    cutoff = datetime.utcnow() - timedelta(days=wait_days)
    pending = db.query(Review).filter(
        Review.is_published.is_(False),
        Review.created_at < cutoff,
    ).all()

    targets = set()
    for r in pending:
        r.is_published = True
        r.published_at = datetime.utcnow()
        targets.add(r.target_id)

    for t in targets:
        recalc_rating(db, t)
    db.commit()
    return len(pending)
