"""
Понятные адреса объявлений.

Человек видит адрес в поисковой выдаче под заголовком и по нему решает,
нажимать ли. Набор цифр читается как случайная страница, а название вещи
— как то, что он искал.
"""
import ast
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


def test_every_listing_response_has_a_path():
    """
    Адрес собирается в приложении, а не на сайте: иначе одна выдача
    отдаёт понятный, другая забывает, и половина ссылок ведёт не туда.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    # Границы функции берём разбором кода, а не отсчётом строк.
    # Раньше тут читались ровно 24 строки после «def serialize» — и
    # тест начал падать не потому, что адрес пропал, а потому что
    # сериализатор оброс полями и «path» уехал на 27-ю строку. Правило
    # осталось верным, мерка сломалась: у ast границы функции точные,
    # сколько бы полей в неё ни добавили.
    tree = ast.parse(source)
    blocks = [
        ast.get_source_segment(source, node)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "serialize"
    ]
    for node, block in zip(
        [n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "serialize"],
        blocks,
    ):
        assert '"path"' in block, f"выдача на строке {node.lineno} без адреса"

    assert len(blocks) >= 4


def test_path_shape_never_changes():
    """
    Треть объявлений записана без города. Адрес из разного числа частей
    пришлось бы разбирать по-разному, и страница просто не открывалась
    — сайт ждал три части, а получал две.
    """
    without_city = listing_path("45e17e58-e7c8-4f24-9642-6a55b878023a",
                                "2 велосипедных шлема", None, "bikes")
    without_anything = listing_path("45e17e58-e7c8-4f24-9642-6a55b878023a",
                                    "Что-то", None, None)

    assert without_city.count("/") == 3
    assert without_anything.count("/") == 3
    # и ключ всё равно находится
    assert listing_id_from(without_city) == "45e17e58"
