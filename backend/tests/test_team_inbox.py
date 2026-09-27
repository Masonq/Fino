"""
Ответы людей на письмо команды доходят до того, кто их читает.

Войти в аккаунт «Команда PLONK» нельзя: человек ответил, а в админке
не появлялось ничего.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.team_chat import TEAM_KIND, greet, team_user  # noqa: E402
from app.models import Chat, Message, User, UserRole  # noqa: E402
from app.routers.team_inbox import inbox, reply, thread  # noqa: E402


def _person(db):
    u = User(id=uuid.uuid4(), display_name="Человек", role=UserRole.buyer,
             email=f"p{uuid.uuid4().hex[:8]}@example.rs")
    db.add(u)
    db.commit()
    return u


def _staff(db):
    u = User(id=uuid.uuid4(), display_name="Модератор", role=UserRole.moderator,
             email=f"m{uuid.uuid4().hex[:8]}@example.rs")
    db.add(u)
    db.commit()
    return u


def _answer(db, chat, person, text="А как продлить объявление?"):
    db.add(Message(id=uuid.uuid4(), chat_id=chat.id, sender_id=person.id,
                   text=text, created_at=utcnow()))
    chat.last_message_at = utcnow()
    db.commit()


def test_answer_shows_up_and_can_be_replied_to():
    db = SessionLocal()
    try:
        staff = _staff(db)
        person = _person(db)
        greet(db, person, "ru")
        team = team_user(db)
        chat = db.query(Chat).filter(Chat.buyer_id == person.id).one()

        # Пока человек не ответил, разговора в ящике нет: отвечать нечему.
        mine = [i for i in inbox(False, 200, staff, db)["items"] if i["id"] == str(chat.id)]
        assert not mine

        _answer(db, chat, person)
        item = next(i for i in inbox(False, 200, staff, db)["items"] if i["id"] == str(chat.id))
        assert item["unread"] == 1 and item["person"]["name"] == "Человек"

        # Открыли — прочитано.
        opened = thread(chat.id, staff, db)
        assert len(opened["messages"]) == 2
        assert not db.query(Message).filter(
            Message.chat_id == chat.id, Message.sender_id != team.id,
            Message.is_read.is_(False)).count()

        class Payload:
            text = "Продлить можно в «Моих объявлениях»."

        reply(chat.id, Payload(), staff, db)
        last = (db.query(Message).filter(Message.chat_id == chat.id)
                .order_by(Message.created_at.desc()).first())
        assert last.sender_id == team.id and last.kind == TEAM_KIND
    finally:
        db.close()


def test_only_staff_can_read_the_teams_mail():
    from fastapi import HTTPException

    from app.routers.team_inbox import require_staff

    db = SessionLocal()
    try:
        person = _person(db)
        try:
            require_staff(person)
            raise AssertionError("обычный человек не должен видеть чужую переписку")
        except HTTPException as error:
            assert error.status_code == 403
    finally:
        db.close()


def test_team_cannot_be_blocked():
    """
    Команда — единственный канал, которым мы пишем человеку. Если её
    заблокировать, он перестанет получать и ответы на свои вопросы.
    """
    import asyncio

    from fastapi import HTTPException

    from app.routers.chats import block_participant

    db = SessionLocal()
    try:
        person = _person(db)
        greet(db, person, "ru")
        chat = db.query(Chat).filter(Chat.buyer_id == person.id).one()
        try:
            asyncio.run(block_participant(chat.id, person, db))
            raise AssertionError("команду не должно быть возможно заблокировать")
        except HTTPException as error:
            assert error.status_code == 400 and error.detail == "cannot_block_team"
    finally:
        db.close()


def test_chat_list_marks_the_team_chat():
    """По этому признаку в списке рисуется логотип, а меню прячется."""
    from app.routers.chats import _is_team_chat

    db = SessionLocal()
    try:
        person = _person(db)
        greet(db, person, "ru")
        chat = db.query(Chat).filter(Chat.buyer_id == person.id).one()
        assert _is_team_chat(db, chat)
    finally:
        db.close()
