"""
Письмо от команды новичку.

Первое, что человек видит в «Сообщениях» после регистрации — разговор,
в котором ему уже написали. Чат без объявления: речь о самом PLONK.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.core.team_chat import GREETING, TEAM_KIND, greet, is_team_message  # noqa: E402
from app.models import Chat, Message, User, UserRole  # noqa: E402


def _fresh_user(db):
    user = User(id=uuid.uuid4(), display_name="Новичок",
                email=f"t{uuid.uuid4().hex[:8]}@example.rs", role=UserRole.buyer)
    db.add(user)
    db.commit()
    return user


def test_greeting_arrives_once():
    db = SessionLocal()
    try:
        user = _fresh_user(db)
        greet(db, user, "ru")
        greet(db, user, "ru")  # повторный вход не должен слать второе
        chats = db.query(Chat).filter(Chat.buyer_id == user.id).all()
        assert len(chats) == 1
        assert chats[0].listing_id is None, "письмо не про объявление"
        messages = db.query(Message).filter(Message.chat_id == chats[0].id).all()
        assert len(messages) == 1
        assert messages[0].kind == TEAM_KIND
    finally:
        db.close()


def test_greeting_speaks_the_users_language():
    db = SessionLocal()
    try:
        for lang in ("ru", "en", "sr"):
            user = _fresh_user(db)
            greet(db, user, lang)
            chat = db.query(Chat).filter(Chat.buyer_id == user.id).one()
            text = db.query(Message).filter(Message.chat_id == chat.id).one().text
            assert text == GREETING[lang]
    finally:
        db.close()


def test_team_letter_is_not_flagged_as_a_scam():
    """
    Письмо предупреждает про предоплату и уход в другой мессенджер —
    ровно про то, что ищет проверка сообщений. Оно получало
    предупреждение само на себя.
    """
    from app.core.chat_risk import risk_of
    from app.routers.chats import _risk_for

    assert risk_of(GREETING["ru"]) is not None, "проверка и правда срабатывает на этом тексте"

    class Fake:
        kind = TEAM_KIND
        text = GREETING["ru"]

    assert is_team_message(Fake())
    assert _risk_for(Fake()) is None
