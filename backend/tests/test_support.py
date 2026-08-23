"""
Техподдержка.

Главное здесь — доступность: написать должен суметь и тот, кто не смог
войти, потому что у него как раз самая срочная беда.
"""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import TicketStatus, TicketTopic, UserRole  # noqa: E402


class FakeUser:
    def __init__(self, role=UserRole.buyer):
        self.role = role


def test_ticket_needs_a_way_to_answer():
    """Без обратного адреса обращение бесполезно обеим сторонам."""
    from app.routers.support import NewTicket

    ticket = NewTicket(subject="Не приходит код", body="Жду десять минут",
                       contact="me@mail.com")
    assert ticket.contact == "me@mail.com"
    # для вошедшего адрес берётся из профиля, поэтому поле необязательное
    assert NewTicket(subject="Не приходит код", body="Жду десять").contact is None


def test_ticket_text_has_limits():
    """
    Слишком короткое обращение разобрать нельзя, слишком длинное —
    признак того, что вставили лишнее.
    """
    from app.routers.support import NewTicket

    with pytest.raises(ValidationError):
        NewTicket(subject="?", body="Что-то не так")
    with pytest.raises(ValidationError):
        NewTicket(subject="Проблема", body="ой")
    with pytest.raises(ValidationError):
        NewTicket(subject="Проблема", body="х" * 5000)


def test_queue_is_for_staff_only():
    from app.routers.support import require_staff

    assert require_staff(FakeUser(UserRole.moderator))
    assert require_staff(FakeUser(UserRole.admin))
    for role in (UserRole.buyer, UserRole.seller_private, UserRole.guest):
        with pytest.raises(HTTPException):
            require_staff(FakeUser(role))


def test_statuses_cover_the_whole_path():
    """Написали — ответили — разобрались."""
    assert {s.value for s in TicketStatus} == {"open", "answered", "closed"}


def test_topics_help_see_what_breaks_often():
    """
    Тема нужна не для красоты: по ней видно, что чаще всего ломается.
    """
    assert {t.value for t in TicketTopic} == {
        "listing", "account", "payment", "abuse", "other"}


def test_routes_declared():
    from app.routers.support import router

    paths = {(tuple(sorted(r.methods)), r.path) for r in router.routes}
    assert (("POST",), "/api/support") in paths
    assert (("GET",), "/api/support/mine") in paths
    assert (("GET",), "/api/support/queue") in paths
    assert (("POST",), "/api/support/{ticket_id}/answer") in paths
    assert (("POST",), "/api/support/{ticket_id}/close") in paths
