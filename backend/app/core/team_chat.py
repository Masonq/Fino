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

# Ссылку даём только на наш чат: в письме от команды она кликается
# (см. ChatScreen), у обычных сообщений ссылки остаются текстом —
# кликабельная чужая ссылка в переписке это подарок мошеннику.
CHAT_URL = "https://t.me/Baraholka_Plonk"

GREETING = {
    "ru": (
        "# Привет! Это команда PLONK\n\n"
        "Мы — сервис объявлений в Сербии. Здесь продают и покупают вещи, "
        "сдают квартиры, ищут работу и мастеров.\n\n"
        "Своё объявление разместите за минуту — кнопкой **+** внизу экрана.\n\n"
        "# Пара вещей, которые стоит знать\n\n"
        "- Договаривайтесь здесь, в чате: останется след, если что-то пойдёт не так.\n"
        "- **Не переводите предоплату** незнакомым людям. Честный продавец подождёт встречи.\n"
        "- Увидели обман — жалоба прямо в объявлении, разберём.\n\n"
        "# Заходите в наш чат в Telegram\n\n"
        "Там свежие объявления и живое общение: " + CHAT_URL + "\n\n"
        "Ответьте сюда, если что-то не работает или непонятно. Читаем и отвечаем."
    ),
    "en": (
        "# Hi! This is the PLONK team\n\n"
        "We're a classifieds service in Serbia. People here sell and buy things, "
        "rent out flats, look for jobs and handymen.\n\n"
        "Posting your own ad takes a minute \u2014 the **+** button at the bottom.\n\n"
        "# A few things worth knowing\n\n"
        "- Keep the conversation here in chat: there's a record if anything goes wrong.\n"
        "- **Don't send prepayment** to strangers. An honest seller will wait for the meeting.\n"
        "- Spotted a scam? Report it right on the listing and we'll look into it.\n\n"
        "# Join our Telegram group\n\n"
        "Fresh listings and live chat: " + CHAT_URL + "\n\n"
        "Reply here if something doesn't work or isn't clear. We read and answer."
    ),
    "sr": (
        "# Zdravo! Ovo je tim PLONK\n\n"
        "Mi smo servis oglasa u Srbiji. Ovde se prodaje i kupuje, izdaju stanovi, "
        "tra\u017ee poslovi i majstori.\n\n"
        "Svoj oglas postavite za minut \u2014 dugmetom **+** dole.\n\n"
        "# Nekoliko stvari koje vredi znati\n\n"
        "- Dogovarajte se ovde, u \u0107askanju: ostaje trag ako ne\u0161to po\u0111e naopako.\n"
        "- **Ne \u0161aljite avans** nepoznatima. Po\u0161ten prodavac \u0107e sa\u010dekati susret.\n"
        "- Primetili prevaru \u2014 prijava je na samom oglasu, proveri\u0107emo.\n\n"
        "# Svratite u na\u0161u Telegram grupu\n\n"
        "Sve\u017ei oglasi i \u017eivo \u0107askanje: " + CHAT_URL + "\n\n"
        "Odgovorite ovde ako ne\u0161to ne radi ili nije jasno. \u010citamo i odgovaramo."
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
