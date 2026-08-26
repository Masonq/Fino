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


def test_logo_is_absolute():
    """
    Относительный путь почтовая служба не найдёт — на месте картинки
    будет пустой квадрат.
    """
    import re

    letter = _code_letter("482915")
    link = re.search(r'<img src="([^"]+)"', letter).group(1)

    assert link.startswith("http")             # полный, а не /logo.png
    assert link.endswith("logo-mark.png")


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
