"""
Значок активного продавца.

У площадок вроде OLX и Etsy такой значок работает как множитель: он не
заменяет качество объявления, но при прочих равных решает выбор.
Ключевое там — он не покупается. Наш тоже: только за поведение.

Что нужно, чтобы его получить:

1. Отвечать быстро — в среднем в течение дня. Покупатель, которому не
   ответили, уходит к следующему, и никакой значок этого не исправит.
2. Не иметь подтверждённых жалоб за последние полгода.
3. Иметь хотя бы три объявления и хотя бы один отзыв — иначе о человеке
   попросту нечего сказать.

Чего в списке нет намеренно: денег и продвижения. Значок, который можно
купить, перестаёт что-либо значить — а вместе с ним обесцениваются и
остальные знаки на площадке.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.reply_speed import reply_speed

# Отвечать в среднем не дольше суток. Порог мягкий намеренно: человек
# продаёт диван, а не держит службу поддержки — он спит, работает и
# бывает в отпуске.
MAX_REPLY_MINUTES = 60 * 24

# Жалобы смотрим за полгода: старая история не должна висеть вечно, но и
# забываться через месяц ей рано.
COMPLAINTS_WINDOW = timedelta(days=180)

MIN_LISTINGS = 3
MIN_REVIEWS = 1


def is_active_seller(db: Session, user_id) -> bool:
    """Заслужил ли человек значок. Считаем на лету, ничего не храним."""
    from app.models import Listing, ListingStatus, Report, User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    if (user.rating_count or 0) < MIN_REVIEWS:
        return False

    listings = (
        db.query(Listing)
        .filter(Listing.owner_id == user_id,
                Listing.status.in_((ListingStatus.active, ListingStatus.sold)))
        .count()
    )
    if listings < MIN_LISTINGS:
        return False

    # Считаем только те жалобы, по которым служебный раздел принял меры.
    #
    # Просто поданная жалоба ничего не доказывает: пожаловаться можно и
    # со зла, и по недоразумению. Наказывать за неё значком — значит
    # отдать его в руки любому недовольному.
    from app.models.trust import ReportStatus

    complaints = (
        db.query(Report)
        .filter(Report.target_user_id == user_id,
                Report.created_at >= utcnow() - COMPLAINTS_WINDOW,
                Report.status == ReportStatus.action_taken)
        .count()
    )
    if complaints:
        return False

    speed = reply_speed(db, user_id)
    if not speed or speed["median_minutes"] > MAX_REPLY_MINUTES:
        return False

    return True
