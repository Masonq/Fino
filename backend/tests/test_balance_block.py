"""
Блок баланса: деньги и бонусы отдельно и красиво.

Данные разделены давно (app.core.wallet): деньги, которые человек внёс сам, и подаренные бонусы. Условия обещают
разное: деньги при необходимости возвращаются, бонус тратится только на продвижение. Поэтому на экране это две
разные вещи: зелёные «Деньги» и оранжевые «Бонусы», между ними полоса-пропорция, ниже — порядок списания.

Здесь закреплено то, что нашла проверка глазами на телефонах шириной 320 и 393 точки:
  - на узком экране крупная сумма не наезжает на кнопку «Пополнить» и на подпись «недоступно» (уходят под неё);
  - сумма в плитке не вылезает за плитку («12 500,50 RSD» на 320 точках);
  - копейки всегда двумя знаками («12 500,50», а не «12 500,5»).
"""
import json
import re
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import wallet  # noqa: E402

FRONT = Path(__file__).resolve().parents[2] / "frontend"
SRC = FRONT / "src"
CSS = (SRC / "styles.css").read_text(encoding="utf-8")
CARD = (SRC / "components" / "BalanceCard.jsx").read_text(encoding="utf-8")
PROMO = (SRC / "components" / "PromoteButton.jsx").read_text(encoding="utf-8")


def rule(selector: str) -> str:
    found = re.findall(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert found, f"нет правила {selector}"
    return found[-1]


@pytest.mark.skipif(shutil.which("node") is None, reason="нужен node")
def test_amounts_are_formatted_per_language_with_two_decimals_when_fractional():
    script = (
        "import { formatAmount } from './src/utils/money.js';"
        "const f = (v, l) => formatAmount(v, l).replace(/\\u00a0|\\u202f/g, ' ');"
        "console.log(JSON.stringify({ int_ru: f(1500, 'ru'), frac_ru: f(12500.5, 'ru'), frac_sr: f(12500.5, 'sr'), frac_en: f(12500.5, 'en'),"
        " zero: f(0, 'ru'), none: f(null, 'ru'), cents: f(150.05, 'ru') }));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=FRONT, capture_output=True, text=True, check=True).stdout
    got = json.loads(out)
    assert got["int_ru"] == "1 500" and got["zero"] == "0" and got["none"] == "0"
    assert got["frac_ru"] == "12 500,50" and got["cents"] == "150,05"
    assert got["frac_sr"] == "12.500,50", "сербский — точка в тысячах и запятая в копейках"
    assert got["frac_en"] == "12,500.50"


def test_the_card_has_two_parts_with_the_colours_that_mean_money_and_gift():
    assert "balance-part money" in CARD and "balance-part bonus" in CARD
    assert 'role="img"' in CARD and "balance.aria" in CARD, "полоса читается скринридером словами"
    assert "balance-hint" in CARD and "balance.spend_order" in CARD, "порядок списания подписан"
    assert "background:var(--primary)" in rule(".balance-seg.money").replace(" ", "")
    assert "background:var(--accent)" in rule(".balance-seg.bonus").replace(" ", "")
    assert "formatAmount" in CARD and "toLocaleString" not in CARD, "суммы форматирует один помощник"


def test_the_bar_fills_by_proportion_and_animates_only_when_motion_is_allowed():
    assert "flexGrow: value" in CARD, "ширина сегмента — доля суммы"
    assert "scaleX(1)" in CSS and "transition:transform" in CSS.replace(" ", "")


def test_the_header_layout_does_not_depend_on_the_data():
    """
    Раньше шапка переносила кнопку под сумму, когда сумма не влезала, — а при загрузке сумма была короткой. Кнопка
    прыгала, и карточка съезжала на 23 точки (замер на 320). Теперь схема одна и та же в загрузке и в готовом виде:
    на широком экране один ряд, на узком (до 360) всегда два.
    """
    assert "flex-wrap" not in rule(".balance-head")
    assert re.search(r"@media \(max-width:359px\)\s*\{\s*\.balance-head\{\s*flex-direction:column", CSS)
    assert "min-height:38px" in rule(".balance-action").replace(" ", "")
    button = rule(".balance-topup-btn").replace(" ", "")
    assert "min-height:38px" in button and "margin-left:auto" in button


def test_the_tile_amount_shrinks_instead_of_overflowing_its_tile():
    assert "clamp(15px,4.9vw,18px)" in rule(".balance-part-amount").replace(" ", "")


def test_loading_keeps_the_layout_so_nothing_jumps():
    """Замер: в загрузке скелет суммы был ниже настоящей строки (26 против 34), и подписи плиток съезжали на 5 точек."""
    assert "balance-topup-ph" in CARD and "visibility:hidden" in rule(".balance-topup-ph").replace(" ", "")
    assert CARD.count("balance-sk-inline") >= 3, "скелет суммы и обеих плиток"
    for holder in ('className="balance-total"', 'className="balance-part-amount"'):
        assert holder in CARD, holder
    total = CARD[CARD.index('className="balance-total"'):]
    assert total.index("balance-sk-inline") < total.index("</div>"), "скелет лежит ВНУТРИ настоящей строки той же высоты"
    assert 'id="balance-foot"' in CARD and "visibility: 'hidden'" in CARD, "строка-подсказка всегда одна и всегда на месте"
    skeleton = (SRC / "components" / "Skeletons.jsx").read_text(encoding="utf-8")
    assert "balance-parts" in skeleton and "balance-bar" in skeleton, "скелет профиля повторяет новую форму блока"


def test_every_new_string_exists_in_all_languages_with_the_same_placeholders():
    keys = ["money", "money_note", "bonus", "bonus_note", "spend_order", "aria", "spend_bonus", "spend_money", "topup_off"]
    holders = {}
    for lang in ("ru", "en", "sr"):
        balance = json.loads((SRC / "i18n" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))["balance"]
        for key in keys:
            assert isinstance(balance.get(key), str) and balance[key], (lang, key)
            holders.setdefault(key, set()).add(frozenset(re.findall(r"\{\{(\w+)\}\}", balance[key])))
    for key, variants in holders.items():
        assert len(variants) == 1, f"{key}: подстановки различаются между языками: {variants}"


@pytest.mark.parametrize("price", [150, 300, 450])
@pytest.mark.parametrize("bonus", [0, 100, 300, 500])
def test_the_promotion_sheet_predicts_exactly_what_the_server_will_charge(price, bonus):
    """Окно продвижения пишет «300 из бонусов + 150 деньгами» до нажатия; сервер должен списать ровно так."""
    assert "Math.min(data?.bonus || 0, price)" in PROMO and "Math.max(0, price - fromBonus)" in PROMO

    class Person:
        balance = Decimal(1000)
        bonus_balance = Decimal(bonus)

    from_bonus, from_money = wallet.charge(Person, price)
    assert from_bonus == Decimal(min(bonus, price)) and from_money == Decimal(max(0, price - min(bonus, price)))
