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
from app.core.team_chat import BONUS, GREETING, TEAM_KIND, greet, is_team_message  # noqa: E402
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
        messages = (db.query(Message).filter(Message.chat_id == chats[0].id)
                    .order_by(Message.created_at).all())
        # Два письма: про сервис и про подарок. Второе отдельным
        # сообщением — так оно читается как новость, а не как реклама
        # в конце правил.
        assert len(messages) == 2
        assert [m.kind for m in messages] == [TEAM_KIND, TEAM_KIND]
        assert messages[1].text == BONUS["ru"]
    finally:
        db.close()


def test_greeting_speaks_the_users_language():
    db = SessionLocal()
    try:
        for lang in ("ru", "en", "sr"):
            user = _fresh_user(db)
            greet(db, user, lang)
            chat = db.query(Chat).filter(Chat.buyer_id == user.id).one()
            texts = [m.text for m in db.query(Message)
                     .filter(Message.chat_id == chat.id)
                     .order_by(Message.created_at).all()]
            assert texts == [GREETING[lang], BONUS[lang]]
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


def test_letter_is_written_in_markup_the_chat_can_render():
    """
    Письмо рисуется с заголовками и списком (см. teamText в
    ChatScreen). Разметка должна остаться в тексте: без неё оно снова
    станет стеной текста с «•».
    """
    for lang, text in list(GREETING.items()) + list(BONUS.items()):
        lines = text.split("\n")
        assert any(line.startswith("# ") for line in lines), lang
        assert "**" in text, lang
        assert "•" not in text, f"{lang}: точку списка рисует разметка, а не символ"

    # Список пунктов есть в первом письме — правила читаются списком.
    for lang, text in GREETING.items():
        assert any(line.startswith("- ") for line in text.split("\n")), lang


def test_bulk_greeting_skips_those_who_already_got_it():
    from app.core.greet_all import run

    db = SessionLocal()
    try:
        user = _fresh_user(db)
        greet(db, user, "ru")
    finally:
        db.close()
    first = run(apply=True)
    assert run(apply=False) == 0, "повторный запуск не должен писать второй раз"
    assert first >= 0
