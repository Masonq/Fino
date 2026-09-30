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
    run(apply=True)
    again = run(apply=False)
    assert again["plan"]["none"] == 0 and again["plan"]["no_bonus"] == 0 and again["plan"]["no_button"] == 0, \
        "после рассылки писать больше некому"


# ─── кнопка «Разместить» и доведение писем до полного набора ─────────────
def test_the_gift_letter_carries_a_post_button_in_every_language():
    import re

    for lang, text in BONUS.items():
        buttons = re.findall(r"^\[\[(.+?)\|(/[A-Za-z0-9_/-]*)\]\]$", text, re.M)
        assert buttons and buttons[0][1] == "/post", lang
    assert "[[Разместить|/post]]" in BONUS["ru"]


def _person(db, **kw):
    u = User(id=uuid.uuid4(), display_name="Человек", role=UserRole.buyer,
             email=kw.pop("email", f"g{uuid.uuid4().hex[:8]}@example.rs"), **kw)
    db.add(u)
    db.commit()
    return u


def _team_msgs(db, user):
    from app.core.team_chat import team_chat_of

    chat = team_chat_of(db, user)
    return [] if chat is None else (db.query(Message).filter(Message.chat_id == chat.id)
                                    .order_by(Message.created_at).all())


def test_letters_are_brought_up_to_the_full_set_without_repeating():
    from app.core.clock import utcnow
    from app.core.team_chat import letter_state, sync_letters, team_chat_of, team_user
    from datetime import timedelta

    db = SessionLocal()
    try:
        # 1. Не писали вовсе
        a = _person(db)
        assert letter_state(db, a) == "none"
        assert sync_letters(db, a, "ru") == "none"
        assert letter_state(db, a) == "ok" and len(_team_msgs(db, a)) == 2

        # 2. Пришло только знакомство (так было у тех, кто зарегистрировался до письма о подарке)
        b = _person(db)
        greet(db, b, "ru")
        chat = team_chat_of(db, b)
        for m in _team_msgs(db, b)[1:]:
            db.delete(m)
        db.commit()
        assert letter_state(db, b) == "no_bonus"
        assert sync_letters(db, b, "ru") == "no_bonus"
        msgs = _team_msgs(db, b)
        assert len(msgs) == 2 and "[[" in msgs[-1].text, "добавилось одно письмо о подарке"

        # 3. Подарок пришёл, но без кнопки: дописываем на месте, второй раз не пишем
        c = _person(db)
        greet(db, c, "en")
        old = _team_msgs(db, c)[-1]
        old.text = old.text.split("\n\n[[")[0]              # как было до кнопки
        old.is_read = True
        db.commit()
        old_id = old.id
        assert letter_state(db, c) == "no_button"
        assert sync_letters(db, c, "ru") == "no_button"
        msgs = _team_msgs(db, c)
        assert len(msgs) == 2, "второе письмо не должно задвоиться"
        assert msgs[-1].id == old_id and msgs[-1].is_read is True, "то же сообщение, прочитанное осталось прочитанным"
        assert "[[Post a listing|/post]]" in msgs[-1].text, "язык письма сохраняется"

        # Повторный вызов ничего не меняет
        for user in (a, b, c):
            assert sync_letters(db, user, "ru") == "ok"
            assert len(_team_msgs(db, user)) == 2
        assert team_user(db)
    finally:
        db.close()


def test_the_broadcast_report_counts_and_sends_nothing():
    from app.core import greet_all

    db = SessionLocal()
    try:
        fresh = _person(db)
        people_before = len(_team_msgs(db, fresh))
        report = greet_all.run(apply=False)
        assert report["done"] == 0
        assert report["plan"]["none"] >= 1
        assert len(_team_msgs(db, fresh)) == people_before == 0, "отчёт ничего не отправляет"
    finally:
        db.close()


def test_the_broadcast_skips_service_blocked_and_the_team_and_is_repeatable():
    from app.core import greet_all
    from app.core.team_chat import letter_state, team_user

    db = SessionLocal()
    try:
        person = _person(db)
        blocked = _person(db, is_blocked=True)
        # Служебный аккаунт чата-источника: телефон tg…, войти нечем
        service = User(id=uuid.uuid4(), display_name="Чат", phone=f"tg{uuid.uuid4().int % 10**9}",
                       role=UserRole.seller_private)
        db.add(service)
        db.commit()

        assert greet_all.is_real_person(person)
        assert not greet_all.is_real_person(service)
        # Человек с телефоном на «tg», но с почтой — настоящий
        assert greet_all.is_real_person(User(display_name="x", phone="tg1", email="a@b.rs"))

        people, skipped = greet_all.audience(db)
        ids = {u.id for u in people}
        assert person.id in ids
        assert blocked.id not in ids and service.id not in ids and team_user(db).id not in ids
        assert skipped["заблокированные"] >= 1 and skipped["служебные аккаунты чатов"] >= 1

        first = greet_all.run(apply=True)
        assert first["done"] >= 1
        assert letter_state(db, person) == "ok"
        assert letter_state(db, blocked) == "none" and letter_state(db, service) == "none"
        assert greet_all.run(apply=True)["done"] == 0, "повторный запуск никому не пишет"
    finally:
        db.close()
