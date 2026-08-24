"""
Исправление опечаток в названии.

Главная опасность — исправить то, что опечаткой не было. Название вещи,
марка, редкое слово: там ошибка неотличима от замысла, а испортить чужой
текст хуже, чем оставить его как есть.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.spellfix import fix  # noqa: E402


def test_obvious_typos_are_fixed():
    """
    Опечатка в первом слове стоит дороже всех: вещь не найдут поиском и
    пролистают в ленте. При этом человек её не видит.
    """
    for wrong, right in (("Скорода новая", "Сковорода"),
                         ("холодилник Bosch", "холодильник"),
                         ("Телефн Samsung", "Телефон")):
        out, changes = fix(wrong)
        assert right.lower() in out.lower(), wrong
        assert changes, wrong


def test_correct_words_are_left_alone():
    """Правильное слово в любом падеже трогать нельзя."""
    for text in ("Продам сковороду", "Кастрюля 5 л",
                 "Сковорода антипригарная", "Продам холодильник"):
        out, changes = fix(text)
        assert out == text, text
        assert not changes


def test_brands_and_models_untouched():
    """
    В марке опечатка неотличима от названия: «Merida» — это марка, а не
    ошибка в слове «мебель».
    """
    for text in ("Велосипед Merida 27.5", "Продам стол IKEA MICKE",
                 "iPhone 13 Pro 256gb"):
        out, changes = fix(text)
        assert out == text, text


def test_short_words_untouched():
    """
    У коротких слов одна буква разницы — это уже другое слово, а не
    опечатка: «кот» и «код», «дом» и «том».
    """
    for text in ("Продам кот", "Дом в Земуне", "Три стула"):
        _, changes = fix(text)
        assert not changes, text


def test_changes_are_reported():
    """
    Молча менять чужие слова нельзя: человек должен видеть, что
    получилось, и успеть возразить.
    """
    _, changes = fix("Скорода новая")
    assert changes
    was, now = changes[0]
    assert was.lower().startswith("скор")
    assert now.lower().startswith("сковород")
