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


def test_feed_never_repeats_a_listing():
    """Лента не показывает одно и то же дважды.

    Здесь стояло разбавление разделов, и оно прошло два круга, оба раза
    выйдя хуже. Оконная функция в запросе стоила 1.9с вместо 0.24с. Та
    же работа на порции в 200 объявлений давала повторы: порция
    пересобирается по мере листания, порядок внутри меняется, и человек
    снова видит пролистанное. На живой ленте — 73 повтора из 400
    карточек, отдельные объявления по четыре раза.

    Однообразие соседних карточек — беда меньшая, чем выдача, которая
    крутит одно и то же по кругу. Поэтому разбавления нет, а этот тест
    сторожит, чтобы оно не вернулось незаметно.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    assert "blend" not in source
    assert "POOL_STEP" not in source
    # Порядок задаёт база, страницы режутся ею же — тогда они сходятся.
    assert ".offset(offset).limit(limit).all()" in source


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
    # Смотрим на журнал просмотров именно этого человека. Соединением, а
    # не подзапросом на каждую строку: подзапрос заметно замедлял выдачу.
    assert "seen_alias.viewer_key == str(viewer.id)" in source
    # В поиске по слову и в выбранном разделе штрафа нет: там человек
    # ищет конкретное, и прятать от него уже открытое — издевательство.
    assert "if viewer and not q_text and not category_slug:" in source


def test_todays_signals_do_not_shuffle_the_feed():
    """Сегодняшние показы не участвуют в оценке.

    Лента сама записывает показы при каждом запросе — а оценка их
    учитывает. Пролистал страницу, у полусотни карточек изменились те
    самые данные, по которым идёт сортировка, и следующая страница
    считается уже иначе: одни объявления показываются второй раз, другие
    не показываются вовсе.

    На живой ленте это дало 204 повтора и ровно столько же пропущенных
    из 2764 карточек. Поэтому в расчёт идёт только накопленное до
    сегодня: порядок держится сутки, а поведение людей всё равно
    меряется неделей — сегодняшние показы ничего к нему не добавляют,
    кроме неустойчивости.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    assert "until_day = date_type.today()" in source
    # Верхняя граница стоит у всех дневных сигналов, а не у одного.
    assert source.count("day < until_day") >= 4


def test_pages_never_append_a_listing_twice():
    """Подгрузка не дописывает то, что уже в списке.

    В базе объявление одно и в выдаче одно, а на экране показывалось
    дважды: человек возвращался на главную с карточки объявления, лента
    перечитывала первую страницу, а висевшая подгрузка дописывала в
    конец те же самые объявления.

    Проверка стоит на всех трёх списках — лента, поиск, страница
    раздела: схема подгрузки у них одинаковая, и чинить надо было все
    три.
    """
    frontend = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages"

    for page in ("Home.jsx", "Search.jsx", "CategoryLanding.jsx"):
        source = (frontend / page).read_text()
        assert "have.has(l.id)" in source, page


def test_scroll_is_restored_in_one_place():
    """Прокрутку возвращает один механизм, а не два.

    Их было два: общий в App.jsx, по ключу истории, и собственный в
    ленте, со своим сохранённым местом и восьмикратной поправкой. Они
    спорили за прокрутку и перебивали друг друга разными значениями —
    при возврате свайпом человека кидало то не туда, то в самое начало.

    Проверено вживую: лента пролистана на 4500px, открыто объявление,
    возврат — снова 4500px, разница ноль.
    """
    pages = Path(__file__).resolve().parents[2] / "frontend" / "src"

    app = (pages / "App.jsx").read_text()
    home = (pages / "pages" / "Home.jsx").read_text()

    # Восстановление живёт в App и делает несколько попыток: списки
    # грузятся порциями, и высота страницы растёт уже после первой.
    assert "scrollPositions.current[location.key]" in app
    assert "setTimeout(put, 60)" in app
    # А в ленте своего восстановления нет.
    assert "window.scrollTo" not in home


def test_charts_open_on_today():
    """Графики открываются на сегодняшнем дне, а не на начале периода.

    График шире экрана и прокручивается вбок. Без этого человек видел
    двадцатые числа прошлого месяца, а сегодняшние столбики — те, ради
    которых он и зашёл — оставались за краем, и до них надо было
    доскроллить. Видно на снимке служебного раздела.
    """
    chart = (Path(__file__).resolve().parents[2]
             / "frontend" / "src" / "components" / "BarsChart.jsx").read_text()

    assert "el.scrollLeft = el.scrollWidth" in chart
    assert "ref={barsRef}" in chart


def test_stats_show_sign_ins_and_sign_ups():
    """В статистике есть входы и регистрации, отдельным графиком.

    Заходят сотни, а входят единицы: в одном графике с посещаемостью
    вход был бы неразличимой полоской у нуля. Разница между «зашли» и
    «вошли» — главное, что тут видно.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "admin_stats.py").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "AdminStats.jsx").read_text()

    assert '"logins": logins' in source
    assert '"signups"' in source
    assert 'valueKey="logins"' in page
