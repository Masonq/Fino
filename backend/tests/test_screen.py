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


def test_user_messages_are_cleaned_too():
    """
    Половина переписки — это сообщения человека: нажатия кнопок меню,
    тексты объявлений, правки. Без уборки они копятся, и одно живое
    сообщение бота тонет между ними.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "publisher.py").read_text()

    # убираем и команды, и присланные объявления, и правки
    assert source.count("await erase(") >= 8


def test_album_parts_all_erased():
    """Альбом приходит несколькими сообщениями — убрать надо все."""
    import inspect
    from app.bot.publisher import album_part

    source = inspect.getsource(album_part)
    assert "for part in parts:" in source
    assert "await erase(part)" in source


def test_erasing_never_breaks_the_flow():
    """
    Telegram даёт удалять чужие сообщения только двое суток. Более
    старые остаются — это не беда, и падать из-за этого нельзя.
    """
    import inspect
    from app.bot.screen import erase

    source = inspect.getsource(erase)
    assert "except Exception" in source


def test_no_reply_menu_at_all():
    """
    От меню под полем ввода отказались: Telegram держит либо его, либо
    кнопки сообщения, и на объявлениях оно всегда проигрывало. Плюс
    сообщение с ним нельзя переписать — они копились в переписке.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "publisher.py").read_text()

    assert "ReplyKeyboardMarkup" not in source
    assert "menu=main_menu(" not in source


def test_unfixable_message_is_replaced():
    """
    Сообщение с меню переписать нельзя. Тогда старое убираем и шлём
    новое — иначе живым остаётся давно ушедшее, а в переписке копятся
    близнецы.
    """
    import inspect
    from app.bot.screen import show

    source = inspect.getsource(show)
    assert "await forget(bot, chat_id)" in source
    assert source.count("_send_new(") >= 3


def test_common_actions_live_in_the_message():
    """
    Меню под полем ввода вытесняется кнопками сообщения — Telegram
    держит что-то одно. Поэтому общие действия кладём в саму карточку:
    так они видны всегда, а не через раз.
    """
    from app.bot.publisher import Draft, confirm_keyboard

    labels = [b.text for row in confirm_keyboard(Draft()).inline_keyboard
              for b in row]
    assert "Мои объявления" in labels
    assert "Помощь" in labels


def test_actions_are_always_in_the_message():
    """
    Кнопки в сообщении видны везде и одинаково — в отличие от меню под
    полем ввода, которое Telegram прячет, как только у сообщения
    появляются свои кнопки.
    """
    from app.bot.publisher import Draft, bottom_row, confirm_keyboard

    everywhere = {b.text for b in bottom_row()}
    assert "Мои объявления" in everywhere
    assert "Помощь" in everywhere

    # и та же строка стоит под карточкой объявления
    card = [b.text for row in confirm_keyboard(Draft()).inline_keyboard
            for b in row]
    assert everywhere <= set(card)
