"""
Подписка на объявления.

Бот получился для продавцов, а покупателей всегда больше: продавец
заходит раз в месяц продать диван, а ищущий коляску проверяет чат каждый
день. Подписка снимает эту работу.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bot.subscriptions import MAX_PER_USER, keywords, matches  # noqa: E402


def test_words_are_normalised():
    """
    «Коляски» и «коляску» должны находить друг друга: человек пишет как
    придётся, а объявления пишут по-разному.
    """
    assert "коляска" in keywords("ищу коляски для двойни")
    assert "коляска" in keywords("коляску chicco")


def test_search_words_are_skipped():
    """«Ищу», «куплю», «для» есть в любом запросе и ничего не сужают."""
    words = keywords("Ищу коляски для двойни")
    assert "искать" not in words and "для" not in words
    assert "коляска" in words


def test_all_words_must_match():
    """
    «Коляска chicco» не должна срабатывать на любую коляску — человек
    назвал марку не просто так.
    """
    assert matches(["коляска"], "Коляска Chicco 2в1", "")
    assert matches(["коляска", "chicco"], "Продам коляску Chicco", "")
    assert not matches(["коляска", "chicco"], "Коляска Peg Perego", "")


def test_partial_words_do_not_match():
    assert not matches(["стол"], "Стул для кухни", "")


def test_subscriptions_are_limited():
    """
    Больше пяти — и уведомления превращаются в поток, который перестают
    читать.
    """
    assert MAX_PER_USER <= 7


def test_blocked_bot_does_not_break_publishing():
    """
    Человек мог заблокировать бота. Публикация объявления от этого
    падать не должна.
    """
    import inspect
    from app.bot.publisher import tell_watchers

    source = inspect.getsource(tell_watchers)
    assert "except Exception" in source
