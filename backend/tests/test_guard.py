"""
Присмотр за порядком в чате.

Главная опасность — наказать за обычное сообщение. Человек, которого
поправили ни за что, из чата уходит, а спамер вернётся с другого
аккаунта: цена ошибок несимметрична.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bot.guard import (  # noqa: E402
    NEWCOMER_HOURS, STRIKES_TO_KICK, note_repeat, watched, why_bad,
)


class FakeMessage:
    def __init__(self, text=None, forwarded=False, caption=None):
        self.text = text
        self.caption = caption
        self.forward_origin = object() if forwarded else None
        self.forward_from = None
        self.forward_from_chat = None


def test_ordinary_messages_are_left_alone():
    """Объявления и разговоры трогать нельзя."""
    for text in ("Продам стол письменный IKEA, 6000 динар",
                 "Здравствуйте, а диван ещё продаётся?",
                 "Спасибо, забрал!",
                 "Вот ссылка на объявление t.me/plonk"):
        assert why_bad(FakeMessage(text=text), False) is None, text


def test_spam_is_caught():
    assert why_bad(FakeMessage(text="Подписывайтесь на наш канал"), False)
    assert why_bad(FakeMessage(text="Заходи в чат t.me/spam"), True)
    assert why_bad(FakeMessage(text="ПРОДАМ СРОЧНО ДЁШЕВО ЗВОНИТЕ"), False)


def test_newcomer_rules_are_stricter():
    """
    Спамеры бьют сразу после входа. Но ссылка от старожила — обычное
    дело, и запрещать её всем незачем.
    """
    link = FakeMessage(text="Смотрите тут https://example.com/item")
    assert why_bad(link, True)          # новичку нельзя
    assert why_bad(link, False) is None  # своему можно


def test_repeat_needs_three_times():
    """
    Два раза бывает случайно: не отправилось — отправил снова. Третий
    раз это уже настойчивость.
    """
    watched.clear()
    assert not note_repeat(1, "куплю телефон")
    assert not note_repeat(1, "куплю телефон")
    assert note_repeat(1, "куплю телефон")

    # другое сообщение сбрасывает счёт
    watched.clear()
    note_repeat(2, "раз")
    note_repeat(2, "раз")
    assert not note_repeat(2, "два")


def test_punishment_is_a_ladder():
    """
    Сразу банить нельзя: половина нарушений — незнание правил, а не злой
    умысел.
    """
    assert STRIKES_TO_KICK >= 3


def test_newcomer_window_is_short():
    """Сутки отсекают спамеров, а настоящему продавцу столько не нужно."""
    assert NEWCOMER_HOURS <= 48


def test_spam_is_caught_everywhere():
    """
    Реклама ловится и в ветке разговоров: там можно всё, кроме неё.
    Проверка спама идёт до разделения веток.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "publisher.py").read_text()

    guard_at = source.index("if rules.guard_spam:")
    talk_at = source.index("if not rules.sweep_direct_posts or in_talk:")
    assert guard_at < talk_at


def test_talk_belongs_to_its_topic():
    """
    Объявления в ветке ищут глазами, и «ещё актуально?» под каждым
    третьим делает это невозможным. Разговоры — в свою ветку.
    """
    from app.core.partner_chats import BARAHOLKA_TEST, talk_topic

    assert talk_topic(BARAHOLKA_TEST) == 109

    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "publisher.py").read_text()
    assert "вопросы и разговоры — в ветке" in source.lower()
