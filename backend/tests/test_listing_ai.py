"""
Разбор объявления одним вызовом.

Раньше спрашивали по частям, и каждая часть промахивалась своим
способом: в цене всплывало разрешение экрана, в заголовке первая
строка, в описании оставалось «подробнее на моём канале».
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.listing_ai import (  # noqa: E402
    _body_ok, _in_text, _title_ok, looks_absurd,
)


def test_absurd_prices_are_refused():
    """
    Модель берёт число из названия модели — «Odyssey G5 2560», «iPad
    10» — и выдаёт за цену. Автомобиль за 23 евро выглядит обманом.
    """
    assert looks_absurd(23, "EUR", "Audi A4 Avant (Рестайлинг)")
    assert looks_absurd(92, "EUR", "Apple MacBook Pro 13 (2020)")
    assert looks_absurd(64, "EUR", "Apple iPad 10-ого поколения")


def test_the_thing_is_read_from_the_start():
    """
    «Память для ноутбука DDR3» за 500 динар — нормальная цена. Слово
    «ноутбук» тут не про саму вещь, и правило по всему тексту
    выбрасывало верные цены.
    """
    assert not looks_absurd(500, "RSD", "Память для ноутбука DDR3")
    assert not looks_absurd(1000, "RSD", "Клининг в Белграде")
    assert not looks_absurd(400, "RSD", "Новый чехол для iPhone 16")
    assert not looks_absurd(3000, "RSD", "Графический планшет Wacom")


def test_invented_price_is_refused():
    """
    Модель может придумать число. Записать выдумку хуже, чем оставить
    пустоту.
    """
    assert _in_text(2000, "продам за 2000 динар")
    assert _in_text(2000, "цена 2 000 динар")
    assert _in_text(20000, "цена 20к")
    assert not _in_text(5000, "продам за 2000 динар")


def test_description_may_only_shrink():
    """
    Модель должна была только вычёркивать. Если текст вырос, она его
    придумала — а выдумка в объявлении хуже рекламного хвоста.
    """
    old = "Продам стол. Подробнее на моём канале @shop"

    assert _body_ok("Продам стол.", old)
    assert not _body_ok(old + " Отличное состояние, доставка!", old)
    assert not _body_ok("", old)


def test_several_things_are_not_duplicates():
    """
    В одном объявлении часто продают несколько вещей, и модель
    принимает их за повторы: «сумка 1300, рюкзак 2800, сумка Zara
    1300» превращалось в «абсолютно новая».
    """
    old = ("Сумка с temy. Абсолютно новая. 1300 динар. "
           "Рюкзак Guess. Следы носки. 2800 rsd. "
           "Сумка мешок Zara. Отличное состояние. 1300 динар.")

    assert not _body_ok("Абсолютно новая.", old)

    # а убрать одну вещь целиком тоже нельзя: пропала сумма
    without_zara = old.replace("Сумка мешок Zara. Отличное состояние. "
                               "1300 динар.", "").strip()
    assert _body_ok(without_zara, old)         # 1300 осталось у первой


def test_short_descriptions_may_shrink_a_lot():
    """
    В коротком описании мусор занимает половину, и сильное сокращение
    там законно.
    """
    assert _body_ok("Стол IKEA.", "Стол IKEA. Подробнее в канале @shop")


def test_title_is_checked_by_the_same_rules():
    """
    Модель могла вернуть болтовню или ту же первую строку. Проверяем
    теми же правилами, что и заголовки из текста.
    """
    assert _title_ok("Стол письменный IKEA MICKE")
    assert not _title_ok("Продам")
    assert not _title_ok("И я могу взять на себя уборку вашего дома")


def test_one_call_instead_of_three():
    """
    Модель видит объявление целиком: цену ищет, уже понимая, что за
    вещь, а заголовок пишет, зная цену. Плюс втрое меньше обращений.
    """
    from app.core.listing_ai import PROMPT, SCHEMA

    assert set(SCHEMA["required"]) == {"title", "price", "currency",
                                       "description"}
    assert "моём канале" in PROMPT              # что вычёркивать
    assert "за одну штуку" in PROMPT            # цена
    assert "Начинай с предмета" in PROMPT       # заголовок


def test_title_words_come_from_the_listing():
    """
    Сочинённое название — «Стильная сумка для деловой женщины» —
    читается красиво, но описывает не ту вещь, и покупатель приходит
    зря. Извлечение надёжнее сочинения втрое.
    """
    from app.core.listing_ai import _words_from_source

    source = "Продам коляску Chicco 2в1, состояние отличное, Земун"

    assert _words_from_source("Коляска Chicco 2в1", source)
    assert not _words_from_source("Стильная детская повозка для малыша", source)
    assert not _words_from_source("Прогулочная коляска премиум класса", source)


def test_description_is_cut_not_rewritten():
    """
    Модель, которой велели вычёркивать, иногда пересказывает своими
    словами — выходит гладко, но это уже не то, что писал продавец.
    """
    from app.core.listing_ai import _mostly_from

    old = ("Продам стол письменный IKEA MICKE. Состояние отличное. "
           "Самовывоз Земун. Подробнее в моём канале @shop")

    assert _mostly_from("Продам стол письменный IKEA MICKE. "
                        "Состояние отличное. Самовывоз Земун.", old)
    assert not _mostly_from("Продаётся письменный стол ИКЕА в прекрасном "
                            "состоянии, забрать можно в Земуне.", old)


def test_refusals_are_counted_by_kind():
    """
    Одно общее число не покажет, где модель промахивается чаще — а
    значит, что уточнять в наставлении.
    """
    from app.core.listing_ai import refused

    assert "цена придумана" in refused
    assert "описание переписано" in refused
    assert "заголовок сочинён" in refused
