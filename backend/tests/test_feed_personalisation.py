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
    # Единственное исключение — возврат на прежнюю вкладку ленты.
    #
    # Общий возврат прокрутки работает по адресу страницы, а вкладки
    # адрес не меняют: для него «Все» и «Даром» — одно и то же место.
    # Поэтому память по вкладкам возвращает прокрутку сама, иначе
    # случайное смахивание сбрасывало бы ленту к началу.
    scrolls = [l for l in home.splitlines() if "window.scrollTo" in l]
    assert len(scrolls) == 1, "прокрутку возвращаем только для вкладок"
    # Возвращаем после отрисовки карточек, а не сразу: иначе человек
    # успевает увидеть верх страницы, а потом прыжок вниз — это и
    # читалось как мелькание.
    assert "useLayoutEffect" in home


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


def test_page_is_hidden_while_it_returns_to_place():
    """Пока страница встаёт на место, её не показывают.

    Мелькание при возврате — это момент, когда человек успевает увидеть
    верх страницы, и только потом она прыгает вниз, на нужное место.
    Спрятать на пару кадров честнее, чем показать заведомо не то место
    и дёрнуть.

    Прячем только когда возвращаться есть куда: на самый верх страница
    и так открывается мгновенно. И держим не дольше полусекунды — что
    бы ни случилось, невидимой она не останется.

    Проверено покадрово: из 94 кадров возврата страница скрыта пять, а
    среди видимых нет ни одного рывка. Прежде рывок был.
    """
    app = (Path(__file__).resolve().parents[2]
           / "frontend" / "src" / "App.jsx").read_text()
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    assert "restoring-scroll" in app
    assert "const hide = saved > 40" in app
    assert "setTimeout(show, 500)" in app
    assert ".restoring-scroll body { opacity: 0; }" in styles


def test_feed_stops_when_nothing_new_arrives():
    """Подгрузка останавливается, если новое не приходит.

    Сломалось на живом сайте: объявления начали переносить в другие
    разделы, порядок в ленте сместился, и сервер стал отдавать уже
    показанное. Показанное повторно мы отсеиваем — список переставал
    расти, а подгрузка просила порцию за порцией без конца. На экране
    «Загружаем», которое дёргается и никогда не кончается.

    Две правки: смещение считаем отдельно от длины списка (иначе просим
    одну и ту же порцию), и останавливаемся, когда после отсева не
    осталось ничего нового.

    Проверено на худшем случае — сервер отдаёт одни и те же карточки:
    было 186 запросов за шесть попыток долистать, стало 2.
    """
    for page in ("Home.jsx", "Search.jsx", "CategoryLanding.jsx"):
        source = (Path(__file__).resolve().parents[2]
                  / "frontend" / "src" / "pages" / page).read_text()
        assert "asked" in source, page
        assert "if (!fresh.length)" in source, page
        # Одна пустая порция — не конец ленты: после переноса
        # объявлений порядок смещается, и порция целиком из уже
        # показанного попадается в середине. Так лента и обрывалась на
        # второй сотне вместо четырёх тысяч. Конец — три подряд.
        assert "empty.current >= 3" in source, page


def test_own_favourites_are_not_pushed_to_the_top():
    """Своё избранное не поднимается в общей ленте.

    Оно попадало наверх через общий счёт популярности: сохранений пока
    мало, и собственные добавления резко поднимали объявление — человек
    видел вверху ленты ровно то, что сам уже отложил.

    У Авито избранное — сигнал об интересах, а не то, что показывают:
    задача ленты, как они пишут сами, показать объявления с наибольшей
    вероятностью обращения к продавцу. Сохранённое человек уже нашёл, и
    лежит оно у него в «Избранном».

    Штраф, а не исключение: вкусы человека эти объявления отражают, и
    вовсе выкидывать их — перебор. И только в общей ленте: в поиске по
    слову прятать найденное было бы издевательством.

    Проверено на живой выдаче: объявление стояло пятым, после
    добавления в избранное ушло из первой десятки.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    assert "own_fav_penalty" in source
    assert "- own_fav_penalty" in source
    # Только общая лента, без поиска и разделов.
    block = source.split("own_fav_penalty = 0.0")[1][:400]
    assert "not q_text and not category_slug" in block


def test_search_survives_typos():
    """Поиск находит вещь, даже если слово набрано с ошибкой.

    Поиск был точным по словам: «каляска» и «диваан» не находили
    ничего. Человек решал, что вещи нет, и уходил — а она лежала в
    ленте. Для площадки с тремя языками и вечной путаницей латиницы с
    кириллицей это потеря на ровном месте.

    Запасной поиск включается, только когда обычный пуст: считать
    похожесть на каждый запрос дорого, а пустых запросов немного.
    Остальные условия — город, цена, раздел — сохраняются: человек
    задал их осознанно.

    Сравниваем слово со словом внутри заголовка, а не с заголовком
    целиком: «каляска» против «Коляска Bugaboo» даёт 0.26 и не проходит
    порог, а по слову — 0.5. Проверил на живых данных.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "listings.py").read_text()

    assert "word_similarity(lower(:w" in source
    assert "if q_text and total == 0" in source
    assert "before_words.filter(Listing.id.in_(found))" in source
    # Короткие слова не ищем по похожести: на трёх буквах она находит
    # что угодно.
    assert "len(w) >= 4" in source


def test_listing_page_has_no_grey_gap_at_the_bottom():
    """Под номером объявления нет серой полосы.

    Место под кнопку «Написать продавцу» держала страница, а не белый
    лист объявления: отступ в сто пикселей лежал за пределами листа и
    красился фоном страницы. Выглядело так, будто страница оборвалась.

    Проверено вживую: белый лист доходит до самого низа, разница ноль
    пикселей.
    """
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    sheet = styles.split(".detail-sheet{")[1].split("}")[0]
    assert "padding:20px 20px 100px" in sheet
    assert ".detail-page{ padding-bottom:0; }" in styles


def test_profile_icons_are_all_different():
    """Значки в профиле не повторяются.

    Три строки подряд — «Правила», «Условия» и «Журнал действий» —
    показывали почти одинаковый документ с полосками, и различить их
    было нельзя. Заметно глазом на снимке профиля.

    Теперь у правил список с галочками, у условий документ с загнутым
    углом, у журнала часы со стрелкой назад.
    """
    import re

    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Profile.jsx").read_text()

    # Берём содержимое каждого значка и сверяем на повторы.
    icons = re.findall(r'<svg viewBox="0 0 24 24".*?</svg>', page, re.S)
    shapes = [re.sub(r"\s+", " ", i) for i in icons]
    assert len(shapes) == len(set(shapes)), "в профиле есть одинаковые значки"


def test_delete_button_always_leads_somewhere():
    """Нажатие на «Удалить» не проваливается молча.

    Жалоба была «иногда не срабатывает, обновишь страницу — работает».
    Причин оказалось две.

    Первая: удаление начиналось со строки «если объявление ещё не
    загружено — выйти», и делало это молча. Кнопка выглядела живой, но
    не делала ничего. Теперь она неактивна, пока данных нет, а нажатие
    объясняет, что объявление ещё грузится.

    Вторая: у объявлений, поданных на сайте, кнопка открывала окно
    «Вернуть на доработку» вместо удаления — человек жал удаление и не
    получал удаления. Возврат остаётся первым: чужое объявление честнее
    вернуть с причиной, чем стереть чужую работу. Но теперь в том же
    окне есть и прямое удаление.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    # Кнопка не активна без данных.
    assert page.count("disabled={deleting || !listing}") == 2
    # И нажатие не молчит.
    assert "t('detail.not_loaded_yet')" in page
    # В окне возврата есть прямое удаление.
    assert 'className="reasons-delete"' in page


def test_saved_feed_survives_for_the_way_back():
    """Сохранённая лента показывается при возврате, даже если устарела.

    Она для того и есть: человек смотрел объявление три минуты и должен
    вернуться на своё место, а не в начало ленты. Я было добавил
    проверку возраста при открытии — и возврат сломался.

    Свежесть при этом не страдает: если память старше минуты, лента
    перезагружается в фоне. Человек видит своё место сразу, данные
    обновляются через мгновение.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    block = page.split("const cached =")[1].split("\n\n")[0]
    assert "FEED_CACHE_TTL" not in block, "возраст здесь проверять нельзя"
    # А фоновая перезагрузка по возрасту — на месте.
    assert "Date.now() - cached.fetchedAt < FEED_CACHE_TTL) return" in page


def test_saved_feed_lives_long_enough_to_read_a_listing():
    """Память ленты живёт дольше, чем человек читает объявление.

    Минуты было мало: он открывает объявление, смотрит фотографии,
    пишет продавцу — и на возврате лента перезагружается, хотя он
    никуда не уходил. В поиске это обиднее вдвойне: запрос он набирал
    руками.

    Пять минут. За это время в ленте всё равно почти ничего не
    меняется: за сутки прибавляется несколько сотен объявлений на
    четыре тысячи. А цена ошибки несимметрична: показать ленту на пару
    минут несвежей — мелочь, потерять место человека — обидно.
    """
    home = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()
    search = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "Search.jsx").read_text()

    assert "FEED_CACHE_TTL = 300_000" in home
    assert "FRESH = 300_000" in search


def test_feed_never_stops_for_good():
    """Подгрузка ленты не может остановиться навсегда.

    Две дыры, обе объясняли «обновил страницу — заработало».

    Первая: подгрузка включается, только если показано меньше, чем
    всего. Если в памяти страницы total оказывался нулём, а карточки
    были, условие сразу ложно — сторож прокрутки не ставился, и лента
    замирала.

    Вторая: после трёх пустых порций мы ставили total равным числу
    показанных, то есть отключали подгрузку до перезагрузки. Если три
    пустых порции попались посреди ленты — а после ночных чисток
    порядок смещается, и это возможно — человек оставался с обрывком
    без всякого способа это исправить.

    Теперь в этом случае показывается кнопка «Показать ещё»: он нажмёт
    и продолжит.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    # Ноль из памяти больше не считается концом ленты.
    assert "cached.items.length + 1" in page
    # Конец ленты не выключает подгрузку насмерть.
    assert "setStalled(true)" in page
    assert "setFeedTotal(prev.length)" not in page
    # И есть кнопка.
    assert "feed-more" in page and "feed.show_more" in page


def test_search_also_never_stops_for_good():
    """В поиске подгрузка тоже не останавливается навсегда.

    Та же ошибка, что была на главной: после трёх пустых порций
    ставился total = показанному, и подгрузка выключалась до
    перезагрузки страницы. Здесь это обиднее — запрос человек набирал
    руками.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Search.jsx").read_text()

    assert "setStalled(true)" in page
    assert "setTotal(prev.length)" not in page
    assert "feed.show_more" in page


def test_images_load_by_one_rule_everywhere():
    """Картинки грузятся по одному правилу на всех страницах.

    Первые четыре карточки — сразу: они видны в тот же миг, и ленивая
    загрузка для них лишняя задержка. Остальные лениво: до них человек
    может и не долистать.

    decoding=async везде, чтобы распаковка картинки не тормозила
    прокрутку. Раньше он стоял только в карточке ленты, а в объявлении,
    похожих и списке продавца его не было.
    """
    root = Path(__file__).resolve().parents[2] / "frontend" / "src"

    card = (root / "components" / "ListingCard.jsx").read_text()
    assert "priority ? 'eager' : 'lazy'" in card
    assert "priority ? 'high' : 'auto'" in card

    for name in ("pages/ListingDetail.jsx", "pages/Moderation.jsx",
                 "components/SimilarListings.jsx",
                 "components/SellerListings.jsx"):
        text = (root / name).read_text()
        if 'loading="lazy"' in text:
            assert 'decoding="async"' in text, name


def test_category_tree_updates_within_an_hour():
    """Новые разделы появляются на сайте в тот же час, а не назавтра.

    Дерево разделов хранилось в браузере сутки, и при устаревании
    показывалось старое, а свежее подтягивалось в фоне: новые разделы
    появлялись только со второго захода на следующий день. Завели
    двадцать три раздела — а на сайте их нет, и непонятно, сломалось
    что-то или нет.

    Теперь срок час, и при устаревании показываем свежее. Если запрос
    не удался — сохранённое: пустое дерево хуже устаревшего.
    """
    client = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "api" / "client.js").read_text()

    assert "FRESH_FOR = 60 * 60 * 1000" in client
    assert "return refresh().catch(() => saved.tree)" in client


def test_pull_indicator_clears_the_notch():
    """Полоса обновления не прячется под «островом» айфона.

    В приложении с домашнего экрана страница занимает весь экран,
    включая место под островом. Шапка это учитывала, а полоса
    обновления начиналась от самого верха — и остров её перегораживал.

    В браузере беды не было: там сверху адресная строка, и полоса
    оказывалась ниже. Оттого и не находилась долго — на компьютере всё
    выглядело правильно.
    """
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    block = styles.split(".ptr-indicator{")[1].split("}")[0]
    # Отступ под вырез не помог: он только увеличил белый разрыв над
    # цветной шапкой. Красим область в цвет шапки — тогда стыка нет
    # вовсе, и остров ложится на тот же цвет, что и всегда.
    assert "background:var(--pull-bg" in block

    home = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()
    assert "setProperty('--pull-bg'" in home


def test_cards_appear_one_after_another():
    """Карточки в ленте появляются по очереди, а не разом.

    Приём подсмотрен в anime.js — там он зовётся stagger, — но без
    самой библиотеки: она весит сотню килобайт, а нужен один эффект,
    который делается парой строк в стилях.

    Сдвиг маленький, по три сотых секунды: лента оживает, но ждать
    никого не заставляет. Только первые восемь карточек — дальше
    человек уже листает, и задержка стала бы помехой.

    Кому движение мешает, тому не показываем вовсе.
    """
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    assert "@keyframes card-in" in styles
    assert ".s-card:nth-child(n+9){ animation:none; }" in styles
    assert "prefers-reduced-motion" in styles


def test_photo_travels_from_card_to_page():
    """Фотография переносится с карточки на страницу объявления.

    Раньше страница просто сменялась рывком. Теперь снимок из карточки
    разворачивается в страницу — так делают приложения, и от этого сайт
    перестаёт ощущаться набором отдельных страниц.

    Имя своё у каждого объявления, иначе браузер не поймёт, какую
    именно карточку переносить.

    Работает через встроенное умение браузера. Кто его не умеет, увидит
    обычный переход: ничего не сломается. Кому движение мешает —
    переходов нет вовсе.
    """
    card = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "components" / "ListingCard.jsx").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    assert "viewTransitionName: `photo-${listing.id}`" in card
    assert "viewTransitionName: `photo-${listing.id}`" in page
    assert "@view-transition" in styles
    assert "prefers-reduced-motion" in styles


def test_home_has_three_feed_tabs():
    """На главной три взгляда на ленту: все, новое, даром.

    Три ленты подряд для четырёх тысяч объявлений выглядели бы жидко, а
    переключатель честнее: одна лента, три взгляда на неё.

    Названия короткие нарочно. С длинным «Рекомендации» третья вкладка
    заезжала под переключатель колонок — увидел на наброске, до того
    как делать.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "listings.py").read_text()

    assert "feed-tabs" in page
    assert "tab === 'new' ? { sort: 'new' }" in page
    assert "tab === 'free' ? { only_free: true }" in page
    # И отбор бесплатных на сервере: признак был, отбирать было нельзя.
    assert "only_free: bool = Query(False)" in api
    assert "q.filter(Listing.is_free.is_(True))" in api


def test_feed_tab_survives_going_back():
    """Выбранная вкладка не сбрасывается при возврате.

    Человек смотрел «Даром», открыл объявление, вернулся свайпом — и
    оказывался на «Все». Работа выбора пропадала.

    Держим выбор в хранилище страницы, а не только в памяти: память
    живёт, пока жива сама страница, а возврат из объявления —
    особенно свайпом в приложении — нередко перезагружает её целиком.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    assert "sessionStorage.getItem('plonk_feed_tab')" in page
    assert "sessionStorage.setItem('plonk_feed_tab', key)" in page
    # И в памяти страницы тоже — для быстрого возврата без перезагрузки.
    assert "tab: tabRef.current" in page


def test_tab_filter_applies_to_further_pages_too():
    """Отбор вкладки действует и на подгружаемые порции.

    Лента замирала на двенадцати карточках во вкладке «Даром», хотя
    всего их сто четыре. Причина: подгрузка про вкладку не знала.
    Первая порция приходила «даром», а следующие — обычной лентой:
    новое в них было чужое, дубли отсеивались, и лента вставала.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    # Отбор задан дважды: в первой загрузке и в подгрузке.
    assert page.count("tab === 'free' ? { only_free: true }") == 2
    assert page.count("tab === 'new' ? { sort: 'new' }") == 2


def test_free_tab_excludes_services():
    """Во вкладке «Даром» нет услуг, работы и жилья.

    «Бесплатно» у них значит другое: массажист без цены — это не
    подарок, а «цена по договорённости». Человек заходит сюда за
    вещами, которые отдают, и объявления мастеров ему только мешают.

    Тот же приём применён при поиске перечней: там эти разделы
    исключены по той же причине.
    """
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "listings.py").read_text()

    block = api.split("if only_free:")[1].split("if with_photo:")[0]
    assert '"services", "jobs", "real-estate"' in block


def test_swipe_changes_the_tab():
    """Смахивание вбок меняет вкладку ленты.

    Влево — следующая, вправо — предыдущая: так листают ленты во всех
    приложениях, и палец сам тянется к этому жесту.

    Жест висит на самой ленте, а не на всей странице: иначе смахивание
    по плиткам разделов, которые и так листаются вбок, меняло бы
    вкладку заодно.

    И не путается с прокруткой: боковым считается только тот жест, где
    по горизонтали прошли заметно дальше, чем по вертикали.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    assert "const TABS = ['all', 'new', 'free']" in page
    assert "Math.abs(dx) < Math.abs(dy) * 1.8" in page
    grid = page.split("cols === 2 ? 'infinite-grid'")[1][:250]
    assert "onTouchStart={onTouchStart}" in grid


def test_tab_change_slides_the_feed():
    """При смене вкладки лента приезжает сбоку, а не сменяется рывком.

    Приезжает с той стороны, откуда пришёл палец: смахнул влево —
    новая лента въезжает справа. Так понятно, что произошло.

    Кнопки двигают ленту так же, по направлению перехода: с «Все» на
    «Даром» — влево, обратно — вправо.

    Коротко, четверть секунды: жест уже сделан, ждать нечего, движение
    лишь объясняет случившееся. И карточки при этом по очереди не
    появляются — два движения разом выглядят суетливо.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    assert "switchTab(TABS[next], dx < 0 ? 'left' : 'right')" in page
    assert "@keyframes slide-from-right" in styles
    assert ".slide-left .s-card, .slide-right .s-card{ animation:none; }" in styles
    # Фотографии тоже не проявляются заново: вместе с движением ленты
    # это читалось как двойное мигание, будто снимок перезагружается.
    assert ".slide-left .s-photo-wrap img" in styles
    # И движение играет один раз: лента пересоздаётся по ключу вкладки,
    # а не снимает метку по таймеру — от этого оно запускалось дважды.
    assert "key={tab}" in page
    assert "setTimeout(() => setTabSlide(null)" not in page


def test_tab_change_shows_skeletons():
    """При смене вкладки показываются серые заготовки.

    Раньше старые карточки висели до последнего и потом резко сменялись
    новыми: выходил рывок, будто фотографии перезагружаются. Заготовки
    честнее — видно, что идёт загрузка.

    Пульсировать они должны и во время движения ленты, иначе выглядят
    как пустые прямоугольники.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()
    styles = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "styles.css").read_text()

    block = page.split("const switchTab =")[1].split("\n  }")[0]
    assert "setListings([])" in block
    assert "setFeedLoaded(false)" in block

    assert ".slide-left .sk-block, .slide-right .sk-block{" in styles


def test_each_tab_remembers_its_place():
    """У каждой вкладки своя память: карточки и место прокрутки.

    Случайное смахивание стоило дорого: вернулся на прежнюю вкладку, а
    лента с начала, и всё, что пролистал, потеряно.

    Теперь при уходе вкладка запоминается целиком, а при возврате
    восстанавливается вместе с местом. Заодно и загрузки нет — карточки
    уже есть.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    assert "let tabCache = {}" in page
    assert "tabCache[tab] = {" in page
    # Восстановленную вкладку не перезагружаем: иначе память
    # бесполезна — карточки сбросятся к двенадцати.
    assert "const saved = tabCache[tab]" in page
    assert "saved?.items?.length && Date.now() - saved.fetchedAt" in page


def test_held_height_is_released_after_cards_arrive():
    """Удержанная высота снимается, когда приехали карточки.

    Высоту держим на время смены вкладки — иначе лента схлопывается и
    браузер подтягивает страницу вверх. Но держали её в ссылке, а
    ссылка не перерисовывает: высота оставалась от прежней, длинной
    ленты, и под парой карточек зияла пустота во весь экран.

    Держим в состоянии: снятие перерисовывает ленту, и пустоты нет.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Home.jsx").read_text()

    assert "const [holdHeight, setHoldHeight] = useState(null)" in page
    assert "setHoldHeight(gridRef.current?.offsetHeight || null)" in page
    assert "if (listings.length && holdHeight !== null) setHoldHeight(null)" in page
    # И высота снимается в том же эффекте, что возвращает прокрутку.
    assert "}, [listings, holdHeight])" in page


def test_whole_card_opens_the_listing():
    """Вся карточка ведёт в объявление, а не только фото с заголовком.

    Палец попадал в цену или в город — и ничего не происходило. Человек
    не разбирается, что тут ссылка, а что нет: он нажимает на карточку.

    Сердечко при этом остаётся кнопкой — оно в своей области и ссылку
    не задевает.
    """
    card = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "components" / "ListingCard.jsx").read_text()

    assert '<Link to={listing.path} className="s-price">' in card
    assert '<Link to={listing.path} className="s-attrs">' in card
    assert '<Link to={listing.path} className="s-meta">' in card
    assert "'s-fav on' : 's-fav'" in card
