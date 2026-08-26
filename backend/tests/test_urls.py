"""
Понятные адреса объявлений.

Человек видит адрес в поисковой выдаче под заголовком и по нему решает,
нажимать ли. Набор цифр читается как случайная страница, а название вещи
— как то, что он искал.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.urls import listing_id_from, listing_path, slugify  # noqa: E402


def test_russian_becomes_readable_latin():
    """
    Кириллицу браузеры кодируют в нечитаемую кашу вида %D1%81%D1%82.
    Пишем латиницей — так, как читают на дорожных знаках.
    """
    assert slugify("Стол письменный") == "stol-pismennyy"
    assert slugify("Коляска Chicco") == "kolyaska-chicco"


def test_empty_words_are_dropped():
    """«Продам», «в отличном состоянии» есть в половине объявлений."""
    assert "prodam" not in slugify("Продам стол письменный")
    assert "sostoyanii" not in slugify("Диван в отличном состоянии")


def test_address_is_short():
    """
    Длинный адрес обрезается в выдаче и хуже запоминается. Трёх-пяти
    слов довольно, чтобы понять, о чём страница.
    """
    long_title = "Продам очень красивый большой удобный раскладной диван"
    assert len(slugify(long_title)) <= 60


def test_path_shows_where_and_what():
    """
    Город и раздел впереди: адрес показывает, где вещь и что это, а
    поисковику даёт понять устройство сайта.
    """
    path = listing_path("45e17e58-e7c8-4f24-9642-6a55b878023a",
                        "Стол письменный IKEA MICKE", "beograd", "mebel")

    assert path == "/beograd/mebel/stol-pismennyy-ikea-micke-45e17e58"


def test_id_survives_a_renamed_title():
    """
    Название могли поправить, и адрес разойдётся с нынешним — но хвост
    ключа остаётся, и объявление найдётся по нему.
    """
    path = listing_path("45e17e58-e7c8-4f24-9642-6a55b878023a",
                        "Совсем другое название", "beograd", "mebel")

    assert listing_id_from(path) == "45e17e58"


def test_nothing_but_safe_characters():
    """
    Пробелы, знаки и надстрочные буквы браузеры кодируют, и адрес
    становится нечитаемым.
    """
    slug = slugify("Ćевапи & пљескавица (2 шт!)")

    assert all(c.isalnum() and c.isascii() or c == "-" for c in slug), slug
