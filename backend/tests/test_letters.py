"""
Письма.

Почтовые службы не грузят внешние стили, а половина из них режет то,
чего не понимает. Поэтому всё вписано прямо в разметку — как в
девяностых, но иначе письмо развалится.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.notify import _code_letter  # noqa: E402


def test_code_is_the_main_thing():
    """
    Код — единственное, ради чего человек открыл письмо. Он должен быть
    виден сразу, крупно, без поиска глазами.
    """
    letter = _code_letter("482915")

    assert "482915" in letter
    # крупно и с разрядкой: код переписывают руками
    assert "font-size:32px" in letter
    assert "letter-spacing" in letter


def test_styles_are_inline():
    """
    Внешние стили почта не загрузит, и письмо приедет голым текстом.
    """
    letter = _code_letter("482915")

    assert "<link" not in letter
    assert "<style" not in letter
    assert 'style="' in letter


def test_no_images_at_all():
    """
    Письмо с одним изображением и коротким текстом почтовые службы
    считают подозрительным, да и картинки многие не грузят вовсе.
    Логотип рисуем разметкой.
    """
    letter = _code_letter("482915")

    assert "<img" not in letter
    assert "background:#0E9F6E" in letter       # знак вместо картинки


def test_no_links_in_code_letter():
    """
    Apple отклонял письмо целиком: «554 5.7.1 [HM07] Message rejected
    due to local policy». Код вместе с кликабельной ссылкой в одном
    письме — классический рисунок фишингового письма («вот код, вот
    ссылка, подтвердите вход»). Убрали единственную ссылку, что была в
    письме (подвал вёл на сайт) — теперь их нет вовсе, код только
    переписывают руками.
    """
    letter = _code_letter("482915")

    assert "<a href" not in letter
    assert "href=" not in letter


def test_plain_text_stays_too():
    """
    Часть людей читает почту без разметки: для них письмо должно
    остаться понятным.
    """
    import inspect
    from app.core.notify import _send_via_resend

    source = inspect.getsource(_send_via_resend)
    assert '"text"' in source
    assert 'letter["html"] = html' in source


def test_subject_has_no_code():
    """
    Код крупно в письме, откуда его удобно скопировать. Дважды одно и
    то же выглядит небрежно.
    """
    from app.core.notify import SUBJECT

    assert "{code}" not in SUBJECT
    assert "—" not in SUBJECT               # к лишним знакам почта придирчива


def test_letter_has_a_reply_address():
    """
    Письмо, на которое некому ответить, почтовые службы считают
    рассылкой.
    """
    import inspect
    from app.core.notify import _send_via_resend

    assert "reply_to" in inspect.getsource(_send_via_resend)
