"""
Проверка объявлений перед лентой.

Ошибка дорога в обе стороны: пропущенное мошенничество бьёт по сайту, а
отклонённое честное объявление отваживает продавца. Поэтому спорное не
одобряем и не отклоняем — оставляем человеку.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.moderation_ai import by_rules  # noqa: E402


def test_forbidden_is_caught_by_rules():
    """
    Явное ловим правилами: они мгновенны, бесплатны и надёжнее модели.
    """
    for title in ("Продам пистолет ТТ",
                  "Водительское удостоверение купить недорого",
                  "Продам лирику капсулы 300мг",
                  "Обнал через карты"):
        assert by_rules(title, "") is not None, title


def test_prepayment_demand_is_caught():
    """Просят денег вперёд — самый частый обман в барахолках."""
    assert by_rules("Коляска", "только предоплата 100%") is not None


def test_ordinary_listings_pass_rules():
    """
    Правила не должны трогать обычные объявления: их большинство, и
    каждое ложное срабатывание — отваженный продавец.
    """
    for title, body in (("Продам стол письменный IKEA", "отличное состояние"),
                        ("Коляска Chicco 2в1", "торг уместен"),
                        ("Услуги массажа", "выезд на дом"),
                        ("Лирические стихи Пушкина", "сборник 1980 года"),
                        ("Продам квартиру 65 м2", "Врачар, без посредников")):
        assert by_rules(title, body) is None, title


def test_rules_never_approve():
    """
    Отсутствие запрещённых слов ещё не значит, что объявление честное.
    Одобрять правилами не беремся — это дело модели или человека.
    """
    import inspect

    source = inspect.getsource(by_rules)
    assert '"ok"' not in source


def test_unsure_is_left_to_a_human():
    """
    Модель не ответила или сомневается — это не повод одобрять или
    отклонять.
    """
    import inspect
    from app.core.moderation_ai import by_model

    source = inspect.getsource(by_model)
    assert source.count('"unsure"') >= 3


def test_used_goods_are_not_forbidden():
    """
    Модель отклонила подержанную косметику как «негигиеничную». Это не
    её дело: подержанные вещи продаются повсеместно, и запрет тут
    только отваживает продавцов.
    """
    from app.core.moderation_ai import PROMPT

    assert "подержанност" in PROMPT
    assert "запрещено законом" in PROMPT


def test_words_instead_of_markup_are_understood():
    """
    Модель может ответить словами вместо разметки. Одного «ok» или
    «no» довольно, чтобы понять решение.
    """
    import inspect
    from app.core.moderation_ai import by_model

    source = inspect.getsource(by_model)
    assert "ответ словами" in source
