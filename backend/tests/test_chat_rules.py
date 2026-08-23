"""
Правила чата-партнёра.

Смысл правил в том, что бот подстраивается под барахолку, а не наоборот:
у каждой свои привычки, и переписывать бота под каждого партнёра нельзя.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.chat_rules import ChatRules, RULES, check, rules_for  # noqa: E402
from app.core.partner_chats import BARAHOLKA_TEST  # noqa: E402


def test_unknown_chat_gets_careful_defaults():
    """Незнакомому чату — осторожные значения, а не вседозволенность."""
    rules = rules_for(-999)
    assert rules.daily_limit <= 5
    assert not rules.blocked_categories


def test_price_required_spares_free_and_services():
    """
    «Пишите в личку» вместо цены раздражает больше всего. Но у подарков
    и услуг цены не бывает, и запрет им не годится.
    """
    strict = ChatRules(price_required=True)
    RULES[-1] = strict
    try:
        assert check(-1, price=None, currency=None, is_free=False,
                     category="fashion")
        assert check(-1, price=None, currency=None, is_free=True,
                     category="fashion") is None
        assert check(-1, price=3000, currency="RSD", is_free=False,
                     category="fashion") is None
    finally:
        del RULES[-1]


def test_min_price_counts_in_dinars():
    """
    Порог задан в динарах, а цены бывают в евро — без пересчёта
    пятидесятиевровая вещь считалась бы мелочью.
    """
    RULES[-2] = ChatRules(min_price_rsd=1000)
    try:
        assert check(-2, price=500, currency="RSD", is_free=False,
                     category="fashion")                      # мелочь
        assert check(-2, price=50, currency="EUR", is_free=False,
                     category="fashion") is None              # это 5850 динаров
    finally:
        del RULES[-2]


def test_blocked_categories():
    RULES[-3] = ChatRules(blocked_categories={"services"})
    try:
        assert check(-3, price=None, currency=None, is_free=False,
                     category="services")
        assert check(-3, price=3000, currency="RSD", is_free=False,
                     category="fashion") is None
    finally:
        del RULES[-3]


def test_complaint_is_written_for_a_human():
    """
    Объяснение пишем словами, а не кодом ошибки: человек должен понять,
    что поправить, и опубликовать заново.
    """
    RULES[-4] = ChatRules(price_required=True)
    try:
        complaint = check(-4, price=None, currency=None, is_free=False,
                          category="fashion")
        assert "цену" in complaint.lower()
        assert len(complaint) > 20
    finally:
        del RULES[-4]


def test_test_chat_has_room_to_try():
    assert rules_for(BARAHOLKA_TEST).daily_limit >= 10
