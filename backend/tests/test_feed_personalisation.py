"""
Персональная лента: интересы человека и разбавление разделов.

Два правила, которые легко сломать одной правкой формулы, а заметить
потом только по жалобам: «лента показывает не то» и «лента показывает
одно и то же».
"""
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.interests import (  # noqa: E402
    HALF_LIFE_DAYS, WEIGHT_CONTACT, WEIGHT_FAVORITE, WEIGHT_VIEW,
    _decay, interest_boost,
)


def test_contact_weighs_more_than_a_view():
    """Написал продавцу — усилие, открыл карточку — случайность.

    Если уравнять веса, лента начнёт идти за случайными заходами:
    просмотров на порядок больше, и они перекроют настоящий интерес.
    """
    assert WEIGHT_CONTACT > WEIGHT_FAVORITE > WEIGHT_VIEW


def test_interest_fades_with_time():
    """Вчерашний интерес весит больше недельного.

    Половина запросов на доске живёт недолго: купил коляску — она больше
    не нужна. Без затухания лента месяцами возила бы за человеком его
    прошлые покупки.
    """
    assert _decay(0) == 1.0
    assert _decay(HALF_LIFE_DAYS) == 0.5
    assert _decay(HALF_LIFE_DAYS * 2) == 0.25
    assert _decay(30) < 0.1


def test_boost_is_capped_and_proportional():
    """Сильнейший интерес получает потолок, остальные — свою долю."""
    boosts = interest_boost({"auto": 10.0, "pets": 5.0, "jobs": 1.0})
    assert boosts["auto"] == 0.5
    assert boosts["pets"] == 0.25
    assert boosts["jobs"] == 0.05


def test_subsection_weighs_more_than_section():
    """Подраздел точнее раздела: «наушники» против «электроники».

    Тот, кто всю неделю открывает наушники, хочет видеть наушники, а не
    всю «Электронику» подряд. Раздел тоже поднимаем, но слабее — он
    подсказывает смежное, вроде автокресел к коляскам.
    """
    from app.core.interests import SUB_CAP

    section = max(interest_boost({"electronics": 10.0}).values())
    subsection = max(interest_boost({"headphones": 10.0}, cap=SUB_CAP).values())
    assert subsection > section
    # Вместе не выходят за прежний общий потолок и остаются ниже
    # стартового буста новых объявлений.
    assert section + subsection <= 1.2


def test_boost_never_outweighs_paid_promotion():
    """Персонализация не отбирает место у оплаченного продвижения.

    Платное поднятие даёт до 6.0, стартовый буст нового объявления —
    1.2. Прибавка за интерес должна быть меньше обоих: иначе купленное
    место и первые показы новичка съедает чужая история просмотров.
    """
    from app.core.interests import SUB_CAP

    top = (max(interest_boost({"auto": 10.0}).values())
           + max(interest_boost({"cars": 10.0}, cap=SUB_CAP).values()))
    assert top <= 1.2

    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()
    assert "BUMP_BOOST_MAX = 6.0" in source
    assert "EXPLORE_BOOST_MAX = 1.2" in source


def test_feed_is_diluted_by_section():
    """В ранжировании есть штраф за место внутри своего раздела.

    Без него похожие объявления получают близкие оценки и слипаются в
    блоки, а с персональной прибавкой наверх выходит целый раздел
    разом. Штраф считается оконной функцией — до нарезки на страницы,
    иначе разбивка едет и объявления повторяются между страницами.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()
    assert "DIVERSITY" in source
    assert "row_number().over(" in source
    assert "partition_by=root_category_id" in source


def test_personalisation_stays_out_of_search_and_filters():
    """Поиск по слову и выбранный раздел персонализация не трогает.

    Там человек уже сам сказал, что ему нужно, и подмешивать к этому
    его прошлые интересы — значит спорить с прямым запросом.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()
    assert "if viewer and not q_text and not category_slug:" in source


def test_seen_listings_sink_but_stay():
    """Уже открытое опускается ниже, а не исчезает.

    Лента, которая на каждом заходе крутит одно и то же, надоедает:
    человек эту вещь уже видел. Но и прятать её нельзя — к вещи
    возвращаются: посмотреть ещё раз, показать близким, написать
    продавцу через неделю.

    Штраф ослабевает со временем и меньше платного поднятия, чтобы не
    топить оплаченные места. Проверено на живой выдаче: тому, кто вчера
    смотрел три верхних объявления, лента показала сперва остальные, а
    просмотренные — следом.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    assert "seen_penalty" in source
    assert "SEEN_PENALTY_MAX = 1.2" in source
    # Вычитаем, а не отбрасываем: объявление остаётся в выдаче.
    assert "- seen_penalty" in source
    assert "ListingViewLog.viewer_key == str(viewer.id)" in source
    # В поиске по слову и в выбранном разделе штрафа нет: там человек
    # ищет конкретное, и прятать от него уже открытое — издевательство.
    assert "if viewer and not q_text and not category_slug:" in source
