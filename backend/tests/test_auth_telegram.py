"""
Вход на сайт по ссылке из бота.

Человек публиковал через бота и нигде не регистрировался. Заставлять его
придумывать пароль ради того, чтобы посмотреть своё же объявление, —
верный способ потерять его насовсем.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.auth_telegram import TTL, _tickets, issue  # noqa: E402


def test_key_is_hard_to_guess():
    """Ссылку присылают в переписке — подобрать её не должно быть можно."""
    key = issue(12345, "Максим")
    assert len(key) >= 20
    assert issue(12345, "Максим") != key       # каждый раз новый


def test_key_works_once():
    """
    Переписку могут переслать. Использованная ссылка не должна впускать
    второй раз.
    """
    key = issue(777, "Анна")
    assert _tickets.pop(key, None) is not None
    assert _tickets.pop(key, None) is None


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


def test_invite_is_not_pushy():
    """
    После первой публикации человек только что сделал дело — звать его
    куда-то значит мешать. И зовём один раз.
    """
    import inspect
    from app.bot.publisher import INVITE_AFTER, maybe_invite

    assert INVITE_AFTER >= 2
    source = inspect.getsource(maybe_invite)
    assert "invited.add" in source
    assert "if user.id in invited" in source
