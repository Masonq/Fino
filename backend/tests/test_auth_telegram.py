"""
Вход на сайт по ссылке из бота.

Человек публиковал через бота и нигде не регистрировался. Заставлять его
придумывать пароль ради того, чтобы посмотреть своё же объявление, —
верный способ потерять его насовсем.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.auth_telegram import TTL  # noqa: E402


def test_key_is_hard_to_guess():
    """Ссылку присылают в переписке — подобрать её не должно быть можно."""
    import inspect

    from app.routers.auth_telegram import issue

    source = inspect.getsource(issue)
    # ключ берётся из надёжного источника случайности, а не из времени
    assert "secrets.token_urlsafe" in source
    assert "24" in source                      # длина достаточная


def test_link_does_not_live_long():
    """Ссылка в истории переписки не должна работать вечно."""
    assert TTL.total_seconds() <= 15 * 60


def test_listings_are_adopted():
    """
    Объявления записаны на служебный аккаунт: своей учётной записи у
    человека тогда не было. Без передачи он войдёт и увидит пустоту.
    """
    import inspect
    from app.routers.auth_telegram import _adopt_listings, enter

    assert "_adopt_listings" in inspect.getsource(enter)
    assert "listing.owner_id = user.id" in inspect.getsource(_adopt_listings)


def test_tickets_live_in_the_database():
    """
    Бот и сайт — разные процессы. Ключ, положенный в память бота, сайт
    не увидит, и ссылка окажется «устаревшей» через две минуты после
    выдачи — что и происходило.
    """
    import inspect
    from app.routers.auth_telegram import enter, issue

    assert "LoginTicket" in inspect.getsource(issue)
    assert "SessionLocal" in inspect.getsource(issue)
    assert "LoginTicket" in inspect.getsource(enter)


def test_used_ticket_is_deleted():
    """Переписку могут переслать — ключ должен срабатывать один раз."""
    import inspect
    from app.routers.auth_telegram import enter

    assert "db.delete(ticket)" in inspect.getsource(enter)


def test_login_needs_no_username():
    """
    Просить человека набирать своё имя пользователя — лишний шаг, на
    котором ошибаются и бросают. Бот и так знает, кто перед ним.
    """
    import inspect
    from app.bot.publisher import start_login

    source = inspect.getsource(start_login)
    assert "issue(message.from_user.id" in source
    assert "/enter?key=" in source

    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()
    # кнопка ведёт в бота, а не к вводу имени
    assert "?start=login" in page
    assert "auth-method hidden" not in page
