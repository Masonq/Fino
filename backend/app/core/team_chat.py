"""
Письмо от команды новичку — первым сообщением в его чатах.

Не уведомление и не письмо на почту: человек заходит в «Сообщения» и
видит там живой разговор, в котором ему уже написали. Отвечать можно —
ответы приходят в тот же аккаунт, его читает тот, кто разбирает
поддержку.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Chat, Message, User, UserRole

log = logging.getLogger(__name__)

# Аккаунт, от лица которого приходит письмо. Заводится сам при первом
# обращении — отдельного шага при выкладке не нужно.
TEAM_EMAIL = "team@plonk.rs"
TEAM_NAME = "Команда PLONK"

GREETING = {
    "ru": (
        "Привет! Это команда PLONK — сервиса объявлений для Сербии.\n\n"
        "Здесь продают и покупают вещи, сдают квартиры, ищут работу и мастеров. "
        "Объявление размещается за минуту, кнопкой «+» внизу.\n\n"
        "Пара вещей, которые стоит знать:\n"
        "• Переписывайтесь и договаривайтесь здесь, в чате — так остаётся след, если что-то пойдёт не так.\n"
        "• Не переводите предоплату незнакомым людям. Честный продавец подождёт встречи.\n"
        "• Увидели обман — жалоба прямо в объявлении, разберём.\n\n"
        "Ответьте сюда, если что-то не работает или непонятно. Читаем и отвечаем."
    ),
    "en": (
        "Hi! This is the PLONK team — classifieds for Serbia.\n\n"
        "People here sell and buy things, rent out flats, look for jobs and handymen. "
        "Posting takes a minute — the “+” button at the bottom.\n\n"
        "A few things worth knowing:\n"
        "• Keep the conversation here in chat — there's a record if anything goes wrong.\n"
        "• Don't send prepayment to strangers. An honest seller will wait for the meeting.\n"
        "• Spotted a scam? Report it right on the listing and we'll look into it.\n\n"
        "Reply here if something doesn't work or isn't clear. We read and answer."
    ),
    "sr": (
        "Zdravo! Ovo je tim PLONK — oglasi za Srbiju.\n\n"
        "Ovde se prodaje i kupuje, izdaju stanovi, traže poslovi i majstori. "
        "Oglas se postavlja za minut, dugmetom „+“ dole.\n\n"
        "Nekoliko stvari koje vredi znati:\n"
        "• Dogovarajte se ovde, u ćaskanju — ostaje trag ako nešto pođe naopako.\n"
        "• Ne šaljite avans nepoznatima. Pošten prodavac će sačekati susret.\n"
        "• Primetili prevaru — prijava je na samom oglasu, proverićemo.\n\n"
        "Odgovorite ovde ako nešto ne radi ili nije jasno. Čitamo i odgovaramo."
    ),
}


# Пометка на самом сообщении, а не сверка отправителя с аккаунтом
# команды: так письмо узнаётся в любом процессе и без запроса в базу.
TEAM_KIND = "team"


def is_team_message(message) -> bool:
    return (getattr(message, "kind", None) or "") == TEAM_KIND


def team_user(db: Session) -> User:
    user = db.query(User).filter(User.email == TEAM_EMAIL).first()
    if user is None:
        user = User(
            id=uuid.uuid4(), email=TEAM_EMAIL, display_name=TEAM_NAME,
            email_verified=True, role=UserRole.admin,
        )
        db.add(user)
        db.flush()
    return user


def greet(db: Session, user: User, lang: str = "ru") -> None:
    """
    Пишет новичку от лица команды. Тихо ничего не делает, если письмо
    уже было: регистрация не должна падать из-за приветствия.
    """
    try:
        team = team_user(db)
        if team.id == user.id:
            return
        exists = db.query(Chat).filter(
            Chat.listing_id.is_(None),
            Chat.seller_id == team.id,
            Chat.buyer_id == user.id,
        ).first()
        if exists:
            return
        now = utcnow()
        chat = Chat(id=uuid.uuid4(), listing_id=None, buyer_id=user.id,
                    seller_id=team.id, last_message_at=now)
        db.add(chat)
        db.flush()
        db.add(Message(id=uuid.uuid4(), chat_id=chat.id, sender_id=team.id,
                       kind=TEAM_KIND,
                       text=GREETING.get(lang, GREETING["ru"]), created_at=now))
        db.commit()
    except Exception:
        db.rollback()
        log.warning("не удалось отправить письмо от команды", exc_info=True)
