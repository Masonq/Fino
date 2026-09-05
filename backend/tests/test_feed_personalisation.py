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
    #
    # Способ с тех пор изменился (см. соседний тест про точный возврат):
    # место берём из ref, а не из location напрямую, и повторяем чаще.
    assert "scrollPositions.current[locationKeyRef.current]" in app
    assert "setTimeout(put, 80)" in app
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


def test_history_stores_the_full_listing_id():
    """В историю просмотров пишется полный номер объявления.

    Он брался из адреса, а в красивом адресе
    (/beograd/mebel/stol-45e17e58) последняя часть — лишь восемь знаков
    от полного номера. В историю попадал обрезок, страница «Вы смотрели»
    запрашивала объявления по нему, сервер отвечал отказом — и список
    оставался пустым, даже сразу после просмотра.

    Такие обрезки уже лежат у людей в браузере, поэтому чиним обе
    стороны: страница их отбрасывает при чтении, а сервер пропускает
    негодные номера вместо отказа всему запросу — один обрезок не должен
    обрушивать список целиком.
    """
    detail = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()
    store = (Path(__file__).resolve().parents[2]
             / "frontend" / "src" / "data" / "history.js").read_text()
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "listings.py").read_text()

    # Номер берётся из загруженного объявления, а не из адреса.
    assert "addToHistory(listing.id)" in detail
    assert "addToHistory(listingId)" not in detail
    # Старые обрезки отбрасываются при чтении.
    assert "FULL_ID.test" in store
    # Сервер не отказывает всему запросу из-за одного негодного номера.
    assert 'raise HTTPException(400, "bad_ids")' not in api


def test_video_has_no_browser_controls_in_the_card():
    """У видео в карточке нет кнопок браузера.

    Браузер рисует поверх видео крупные кружки — пауза, две перемотки,
    раскрытие в углу — и они закрывают и наши кнопки сверху, и само
    видео. Видно на снимке объявления с видео.

    Вместо них своя кнопка звука в углу и тап по видео, открывающий
    полный экран. Там кнопки браузера остаются: на весь экран они
    уместны и никому не мешают.

    Проверено вживую: кнопок браузера нет, звук выключен по умолчанию
    (иначе объявление начинает говорить, едва его открыли), своя кнопка
    не перекрывает кружки сверху.
    """
    detail = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    card = detail.split("photo-main")[1].split(") : (")[0]
    assert "controls" not in card
    assert "muted={videoMuted}" in detail
    assert "photo-sound" in detail
    # А в полноэкранном просмотре — остаются.
    assert "controls playsInline" in detail


def test_city_choice_filters_the_feed():
    """Выбор города на главной действительно фильтрует ленту.

    Город хранился в состоянии, но никуда не уходил: человек выбирал
    Нови-Сад и продолжал видеть объявления отовсюду. Хуже того, по
    умолчанию в списке стоял Белград — то есть выбранный город прямо
    противоречил тому, что показано.

    Теперь по умолчанию «Все города» (честное «везде»), выбор уходит в
    запрос, запоминается между заходами и входит в ключ сохранённой
    ленты — иначе при возврате показалась бы лента чужого города.

    Проверено вживую: Нови-Сад показывает своё, Ниш своё, после
    перезагрузки выбор на месте.
    """
    home = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    assert "city: city || undefined" in home
    assert home.count("city: city || undefined") == 2      # лента и подгрузка
    assert "localStorage.getItem('plonk_city')" in home
    assert "feedCache.city === savedCity" in home
    assert 'value=""' in home                              # пункт «все города»


def test_city_choice_works_on_category_pages_too():
    """Выбор города действует и на страницах разделов.

    Там фильтра по городу не было вовсе: человек выбирал Нови-Сад,
    заходил в «Мебель» и снова видел всю Сербию. Выбор один на весь
    сайт, и странице раздела незачем его переспрашивать.

    В поиске город работал и раньше — проверил, там всё в порядке:
    уходит в запрос, попадает в адрес, показывается меткой.
    """
    landing = (Path(__file__).resolve().parents[2]
               / "frontend" / "src" / "pages" / "CategoryLanding.jsx").read_text()

    assert landing.count("localStorage.getItem('plonk_city')") == 2
    assert "if (city) params.city = city" in landing
    assert "city: savedCity || undefined" in landing


def test_empty_filters_do_not_reach_the_server():
    """Пустые значения не уходят в запрос.

    URLSearchParams превращает undefined в строку «undefined», и сервер
    получал city=undefined как настоящее название города — при выборе
    «Все города» лента становилась пустой.

    Ошибка тихая: запрос выполняется, ответ приходит, просто в нём
    ничего нет. Поэтому чиню не в одном месте, а в сборке запроса — и
    перевожу на неё все запросы с необязательными полями.
    """
    client = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "api" / "client.js").read_text()

    assert "function query(params)" in client
    assert "value === undefined || value === null || value === ''" in client
    assert "searchListings: (params) => request(`/listings?${query(params)}`)" in client
    # Прямая сборка с объектом-переменной больше не используется.
    assert "new URLSearchParams(params)" not in client


def test_listing_can_be_moved_to_another_category():
    """Объявление переносится в другой раздел, не теряя ничего.

    Из чатов объявления приезжают с разделом, угаданным по тексту, и
    ошибается он нередко: коляска попадает в «Хобби», сантехник в
    «Ремонт квартир». Раньше такое можно было только снять с
    публикации — то есть выбросить настоящий товар вместе с ошибкой
    разбора.

    Меняется только раздел: заголовок, описание, фото, цена, автор и
    переписка остаются как были.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "moderation.py").read_text()

    move = source.split("def move_to_category")[1].split("@router.post")[0]
    assert "listing.category_id = target.id" in move
    # Только раздел — ничего больше не трогаем.
    #
    # Смотрим именно присваивания: владелец в коде упоминается, но лишь
    # затем, чтобы попасть в журнал — по нему видно, чьё объявление
    # перенесли. Первая версия проверки этого не различала и падала на
    # собственном же журнале.
    for field in ("status", "price", "owner_id", "title"):
        assert f"listing.{field} =" not in move, field
    # В раздел верхнего уровня класть нельзя: там объявления не ищут.
    assert "pick_subcategory" in move
    # Действие попадает в журнал: видно, кто и куда перенёс.
    assert '"listing.move"' in move


def test_move_window_shows_names_not_slugs():
    """В окне переноса — названия разделов, а не служебные имена.

    Название приходит словарём с тремя языками. Рисовать его как строку
    нельзя — страница падает с «Objects are not valid as a React child»,
    что и случилось при первой проверке.
    """
    detail = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    assert "const catName = (c) =>" in detail
    assert "c.name?.[i18n.language]" in detail
    assert "{catName(root)}" in detail


def test_move_errors_are_explained_on_the_page():
    """Ошибки переноса разбираются на самой странице.

    Сперва я взял для этого errorText — но такая функция живёт только на
    странице входа и знает лишь её ошибки. Линт остановил деплой на
    «errorText is not defined», и верно сделал: на сервер бы уехала
    страница, падающая при первой же неудаче переноса.
    """
    detail = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    # Смотрим строки кода, а не весь файл: прежнее имя осталось в
    # пояснении рядом. За день это четвёртый раз, когда проверка
    # спотыкается о мой же комментарий — беру за правило сразу
    # отбрасывать их.
    code_lines = [ln for ln in detail.split("\n")
                  if not ln.strip().startswith(("//", "*", "/*"))]
    assert not any("errorText" in ln for ln in code_lines)
    for code in ("pick_subcategory", "category_not_found", "not_found"):
        assert code in detail, code


def test_request_body_is_always_sent_as_text():
    """Тело запроса всегда уходит строкой.

    Передал объект как есть — fetch отправил «[object Object]», сервер
    ответил «неверные данные», а человек увидел общее «не получилось
    перенести». Ошибка тихая: ни в консоли, ни в журнале ничего
    внятного, только код 422 в логе сервера.

    Раз уж такое возможно, превращаем в строку в самой отправке, а не
    полагаемся на память в каждом вызове.
    """
    client = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "api" / "client.js").read_text()

    assert "typeof options.body === 'object'" in client
    assert "JSON.stringify(options.body)" in client
    # Файлы (загрузка фото) отправляются как есть, их трогать нельзя.
    assert "instanceof FormData" in client


def test_category_page_keeps_the_spot_after_a_long_look():
    """Возврат в раздел приводит на то же место, даже спустя минуты.

    Сохранённый список раздела считался годным только минуту: человек
    изучал объявление дольше, возвращался — список сбрасывался, страница
    становилась короткой, и возвращать прокрутку было уже некуда. Он
    оказывался наверху.

    Возраст решает, обновлять ли данные, но не показывать ли их: список
    рисуется сразу, а свежие данные подъезжают следом и незаметно.

    Проверено по-настоящему: пролистал раздел, открыл объявление, ждал
    65 секунд, вернулся — та же точка, разница ноль пикселей.
    """
    landing = (Path(__file__).resolve().parents[2]
               / "frontend" / "src" / "pages" / "CategoryLanding.jsx").read_text()

    assert "const cacheFresh = Boolean(cached)" in landing
    assert "cacheStale" in landing
    # Обновляем только первую порцию: если человек долистал далеко,
    # перетряхивать всё под ним нельзя — страница подпрыгнет.
    assert "prev.length > (res.items || []).length ? prev : res.items" in landing


def test_move_window_shows_all_three_levels():
    """В окне переноса виден весь третий уровень дерева.

    Дерево трёхуровневое: раздел → подраздел → вложенный. Окно
    показывало только два, и мультиварка уезжала в «Бытовую технику»
    целиком, хотя внутри есть свои разделы. Проверено вживую: в списке
    33 вложенных — ровно столько их и есть в дереве.
    """
    detail = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    assert "(sub.children || []).map((deep)" in detail
    assert "doMove(deep.id)" in detail
    # С отступом и точкой — иначе не понять, что одно внутри другого.
    assert ".move-deep" in styles


def test_scroll_returns_exactly_on_every_list_page():
    """Возврат приводит на то же место — на главной, в разделе и в поиске.

    Собралось из четырёх причин, каждую нашли замером:

    Замена адреса. Поиск дописывает фильтры в адрес, чтобы результатом
    можно было делиться ссылкой; мы принимали это за новый переход —
    мотали наверх и обрывали восстановление.

    Собственная прокрутка. Наш же вызов порождает событие, и обработчик
    записывал в память обрезанное значение: страница ещё короткая,
    браузер вместо 628 ставит 274 — и это затирало настоящее место.

    Ранний выход. Страница на миг дорастала, мы попадали и переставали
    следить, а высота менялась снова и прокрутку сбивало. Теперь
    попадание засчитывается, только если продержалось три проверки.

    Два механизма. На странице раздела было своё восстановление, оно
    спорило с общим — отсюда дёрганье. Механизм остался один.

    Проверено вживую: главная 4500 → 4500, раздел 628 → 628, поиск
    2000 → 2000.
    """
    app = (Path(__file__).resolve().parents[2]
           / "frontend" / "src" / "App.jsx").read_text()
    landing = (Path(__file__).resolve().parents[2]
               / "frontend" / "src" / "pages" / "CategoryLanding.jsx").read_text()

    # Замена адреса той же страницы ничего не сбрасывает, а замена
    # одного объявления другим — открывает сверху (см. соседний тест).
    assert "if (navTypeRef.current === 'REPLACE') {" in app
    assert "if (navigating.current) return" in app
    assert "if (++held >= 3)" in app
    # На странице раздела своего восстановления быть не должно.
    assert "window.scrollTo" not in landing


def test_search_keeps_its_results_between_visits():
    """Поиск помнит найденное — иначе возвращаться некуда."""
    search = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "Search.jsx").read_text()

    assert "let searchCache" in search
    assert "searchCache.items" in search


def test_navigation_between_listings_is_predictable():
    """Переходы между объявлениями ведут себя предсказуемо.

    Три правила, все проверены живым прогоном:

    Объявление из списка открывается сверху и поверх списка — «назад»
    возвращает в список, на то же место.

    Соседнее объявление из «Похожих» и «Ещё у продавца» открывается
    взамен текущего и тоже сверху. Иначе «назад» уводил не в список, а к
    предыдущей карточке — и так по цепочке: посмотрел пять похожих, жми
    назад пять раз. Открывалось оно при этом там же, где человек листал
    предыдущее, то есть внизу.

    Страницы разделов (/c/...) всегда открываются сверху: там не список,
    а плитки подразделов — возвращать человека в их середину незачем.
    """
    app = (Path(__file__).resolve().parents[2]
           / "frontend" / "src" / "App.jsx").read_text()
    similar = (Path(__file__).resolve().parents[2]
               / "frontend" / "src" / "components" / "SimilarListings.jsx").read_text()
    seller = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "components" / "SellerListings.jsx").read_text()

    assert "pathname.startsWith('/c/')" in app
    assert "pathname !== lastPath.current" in app
    for source in (similar, seller):
        assert "navigate(l.path, { replace: true })" in source
