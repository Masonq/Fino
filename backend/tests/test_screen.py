"""
Одно живое сообщение бота.

Если каждый ответ — новое сообщение, через десяток объявлений переписка
превращается в ленту, где не найти нужное. Поэтому бот переписывает одно
и то же сообщение под текущий шаг.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_reply_is_rewritten_not_repeated():
    """
    Ответы бота на шаги — приветствие, вопрос, разбор, карточка — идут в
    одно сообщение, а не копятся.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "publisher.py").read_text()

    # ответы на шаги идут через живое сообщение
    assert source.count("await show(") >= 10
    # прямые отправки остаются там, где иначе нельзя: меню под полем
    # ввода, подсказки в самом чате, приглашение со ссылкой
    assert source.count("await message.answer(") <= 8


def test_results_stay_in_the_chat():
    """
    Итог публикации со ссылками остаётся навсегда: за ним человек
    возвращается в переписку. Живым его считать нельзя.
    """
    import inspect
    from app.bot.publisher import publish

    source = inspect.getsource(publish)
    assert "fresh=True" in source


def test_photo_change_starts_a_new_message():
    """
    Сообщение со снимком и без него Telegram переписывать друг в друга
    не даёт: при смене вида старое убирается и шлётся новое.
    """
    import inspect
    from app.bot.screen import show

    source = inspect.getsource(show)
    assert "bool(photo) == had_photo" in source
    assert "await forget(" in source


def test_unchanged_text_is_not_an_error():
    """
    Текст мог не измениться — Telegram считает это ошибкой, но для нас
    всё в порядке, и в журнал это писать незачем.
    """
    import inspect
    from app.bot.screen import show

    assert '"not modified" in str(exc)' in inspect.getsource(show)
