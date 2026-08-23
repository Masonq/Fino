"""
Уборка объявлений мимо бота.

Главная опасность здесь — убрать лишнее. Под объявлениями спрашивают
«ещё есть?», договариваются о встрече, благодарят: это жизнь чата, и без
неё барахолка мертва. Поэтому проверяем прежде всего то, что НЕ должно
убираться.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bot.sweeper import looks_like_listing  # noqa: E402


class FakeMessage:
    def __init__(self, text=None, photo=None, reply=None, caption=None):
        self.text = text
        self.caption = caption
        self.photo = photo
        self.reply_to_message = reply


class FakeReply:
    forum_topic_created = None


def test_listings_are_swept():
    for text in ("Продам стол письменный IKEA MICKE, 6000 динар, Земун",
                 "Утюг philips azur gc4544/80, 3000 динар, мощность 2600w",
                 "Отдам даром детские вещи 74-80 размер, самовывоз Вождовац"):
        assert looks_like_listing(FakeMessage(text=text)), text


def test_conversation_is_left_alone():
    """Без разговоров барахолка мертва — их трогать нельзя."""
    for text in ("а ещё есть?",
                 "Спасибо, договорились",
                 "Здравствуйте! Скажите, торг возможен?",
                 "Кто-нибудь знает хорошего мастера по холодильникам?"):
        assert not looks_like_listing(FakeMessage(text=text)), text


def test_replies_are_conversation():
    """Ответ на чужое сообщение — почти всегда разговор."""
    assert not looks_like_listing(FakeMessage(
        text="Добрый день, а можно посмотреть сегодня вечером?",
        reply=FakeReply()))


def test_short_message_is_not_a_listing():
    assert not looks_like_listing(FakeMessage(text="Продам"))
    assert not looks_like_listing(FakeMessage(text="ок"))


def test_photo_with_description_is_a_listing():
    """Фотография с описанием — объявление, даже без явной цены."""
    assert looks_like_listing(FakeMessage(
        photo=[object()], text="Диван раскладной, самовывоз Земун"))
    # а фотография без слов — скорее всего просто картинка в разговоре
    assert not looks_like_listing(FakeMessage(photo=[object()], text=""))


def test_sweeping_is_off_by_default():
    """Хозяйничать в чужом чате без разрешения владельца нельзя."""
    from app.core.chat_rules import ChatRules

    assert ChatRules().sweep_direct_posts is False


def test_text_is_given_back():
    """
    Сообщение удалено — пересылать нечего, а набирать заново человек не
    станет. Текст возвращаем ему обратно, чтобы он его скопировал.
    """
    import inspect
    from app.bot.sweeper import sweep

    source = inspect.getsource(sweep)
    # текст отдаётся блоком: по нажатию копируется целиком
    assert "<pre>" in source
    # и придерживается, если в личку написать не дали
    assert "rescued[author.id]" in source
