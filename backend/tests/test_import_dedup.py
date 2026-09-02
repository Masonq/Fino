"""
Отсев повторов при переносе из чатов.

Живой случай: в ленте висело шесть одинаковых «Сантехников» подряд, по
одному за каждый день. Все проверки на повтор мимо: снимок каждый раз
новый (мастер переснимает), заголовок гуляет мелочами («Сантехник ⚡️»,
«САНТЕХНИК Белград»), а проверка по смыслу — единственная, которой эти
мелочи не мешают — включалась только при указанной цене. У услуг цену
не пишут почти никогда.

Тест сторожит обе стороны правила: повтор без цены отсекается, а разные
услуги без цены остаются каждая своим объявлением.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.tg_parse import fingerprint, same_thing  # noqa: E402


SANTEHNIK = (
    "Сантехнические работы в Белграде. Установка, замена труб, "
    "устранение протечек. Выезд по городу."
)


def test_price_is_not_required_for_the_meaning_check():
    """Условие на цену не должно возвращаться в проверку по смыслу.

    Читаем сам исходник: поведение целиком зависит от одной строки, и
    именно её однажды написали так, что объявления без цены проверку
    пропускали. Сравнение с None здесь должно быть частью отбора
    (price IS NULL), а не поводом отказаться от проверки.
    """
    import inspect
    from app.core import tg_import

    source = inspect.getsource(tg_import.store)
    assert 'if mark and item["price"] is not None:' not in source
    assert "Listing.price.is_(None)" in source


def test_same_service_reposted_with_a_different_title_is_one_thing():
    """Тот же текст под другим заголовком — тот же товар."""
    first = fingerprint("Сантехник ⚡️", SANTEHNIK)
    second = fingerprint("САНТЕХНИК Белград", SANTEHNIK)
    third = fingerprint("Сантехник", SANTEHNIK)

    assert same_thing(first, second)
    assert same_thing(first, third)


def test_different_services_are_not_merged():
    """Разные мастера без цены в одном городе — разные объявления.

    Обратная сторона правила: если ослабить сравнение, лента начнёт
    терять живые объявления, а это хуже пары дублей.
    """
    plumber = fingerprint("Сантехник", SANTEHNIK)
    electrician = fingerprint(
        "Электрик",
        "Электромонтаж, розетки, автоматы, щитки. Выезд в любой район Белграда.",
    )
    tutor = fingerprint(
        "Репетитор английского",
        "Занятия английским для взрослых, подготовка к экзаменам, онлайн и очно.",
    )

    assert not same_thing(plumber, electrician)
    assert not same_thing(plumber, tutor)
    assert not same_thing(electrician, tutor)
