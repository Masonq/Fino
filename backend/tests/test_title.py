"""
Проверка правила заголовка на живых объявлениях из чатов.

Каждый случай здесь — реальный пост, по которому заголовок в ленте
получался неверным. Тест сторожит именно их: правило легко ослабить одной
неудачной правкой регулярки, и тогда в ленту вернутся «Меня зовут Даниил» и
«Дом — это место».
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.tg_parse import build_title, make_title, parse  # noqa: E402
from app.core.title_rules import rejects_as_title  # noqa: E402


# ── Заголовком быть не может ────────────────────────────────────────────────
# Строка ничего не говорит о предмете: узнать по ней объявление нельзя.
def test_rejects_self_introduction():
    assert rejects_as_title("Меня зовут Даниил")
    assert rejects_as_title("Мы — компания")
    assert rejects_as_title("Занимаюсь климатическими системами")
    assert rejects_as_title("Имею 10 лет опыта инженером")


def test_rejects_rhetoric():
    assert rejects_as_title("Мечтаете о цвете волос")
    assert rejects_as_title("А кому здесь бесплатный")
    assert rejects_as_title("Мечтаете о цвете волос, который выглядит дорого?")


def test_rejects_definition():
    assert rejects_as_title("Дом — это место")


def test_rejects_detail_without_subject():
    assert rejects_as_title("Спереди есть пятно")
    assert rejects_as_title("В остальном отличная")


# ── Заголовком быть должно ──────────────────────────────────────────────────
# Предмет назван — правило не должно мешать хорошим заголовкам.
def test_accepts_real_titles():
    assert not rejects_as_title("Apple Mac mini M2 16/512 GB")
    assert not rejects_as_title("Стильные летние шлепанцы через палец")
    assert not rejects_as_title("Куртка зимняя, размер S")
    assert not rejects_as_title("Двухкамерный холодильник Beko")


# ── Заголовок из текста ─────────────────────────────────────────────────────
def test_takes_sentence_that_names_the_thing():
    """Знакомство пропускаем, берём предложение с предметом."""
    text = (
        "Добрый день!\n"
        "Меня зовут Даниил.\n"
        "Чистка внешнего и внутреннего блока кондиционера с разбором"
    )
    assert make_title(text) == "Чистка внешнего и внутреннего блока кондиционера с разбором"


def test_drops_trailing_number():
    """«Два брата-акробата 3» — тройка осталась от разметки поста."""
    assert make_title("Два брата-акробата 3\nКотята ищут дом") is None or \
        not make_title("Два брата-акробата 3\nКотята ищут дом").endswith("3")


def test_keeps_number_with_unit():
    """«16 ГБ» — характеристика, а не мусор: её оставляем."""
    assert make_title("Apple Mac mini M2 16/512 GB") == "Apple Mac mini M2 16/512 GB"


def test_no_title_when_nothing_names_the_thing():
    assert make_title("Дом — это место, где живёт кошка!") is None


# ── Заголовок из фактов ─────────────────────────────────────────────────────
def test_falls_back_to_facts_for_pets():
    title = build_title("pets", "pets-cats", "Дом — это место, где живёт кошка!", {})
    assert title == "Кошка"


def test_falls_back_to_facts_with_attributes():
    title = build_title(
        "fashion", "women", "Спереди есть пятно, в остальном отличная",
        {"size": "S"},
    )
    assert title == "Женская одежда, размер S"


def test_service_named_by_the_work_not_the_section():
    title = build_title(
        "services", "repair",
        "Меня зовут Даниил. Занимаюсь климатическими системами. "
        "Чистка кондиционера с разбором",
        {},
    )
    assert "кондиционер" in title.lower()


def test_hairdresser_service():
    title = build_title(
        "services", "beauty-services",
        "Мечтаете о цвете волос? Я парикмахер-колорист и мастер стрижек",
        {},
    )
    assert title == "Стрижка и окрашивание волос"


def test_transfers_company():
    title = build_title(
        "services", "transport",
        "Мы — компания, специализирующаяся на трансферах и туристических услугах",
        {},
    )
    assert title == "Трансферы и перевозки"


# ── Хорошие заголовки не портим ─────────────────────────────────────────────
def test_good_title_survives_the_pipeline():
    title = build_title(
        "electronics", "laptops",
        "Apple Mac mini M2 16/512 GB – идеальное состояние",
        {"ram": 16},
        fallback_title="Apple Mac mini M2 16/512 GB – идеальное состояние",
    )
    assert title == "Apple Mac mini M2 16/512 GB – идеальное состояние"


def test_every_listing_gets_a_title():
    """
    Объявление без заголовка — дыра в ленте. Правило обязано выдать хоть
    что-то для любой известной категории.
    """
    for category, sub in (
        ("pets", "pets-dogs"), ("fashion", "shoes"), ("auto", "cars"),
        ("electronics", "phones"), ("jobs", "resumes"), ("business", "equipment"),
    ):
        assert build_title(category, sub, "текст без предмета вовсе", {})


# ── Полный проход по объявлениям со скриншотов ──────────────────────────────
# Один тест на все известные поломки: если правило ослабнет, видно сразу,
# какое объявление вернулось к прежнему заголовку.
def test_real_listings_from_chats():
    cases = [
        (
            "Продаю стильные летние шлепанцы через палец с элегантными ремешками.",
            "fashion", "shoes", {},
            "Стильные летние шлепанцы через палец с элегантными ремешками",
        ),
        (
            "Куртка\nРазмер s\nСпереди есть пятно, в остальном отличная\nЗемун",
            "fashion", "women", {"size": "S"},
            "Женская одежда, размер S, Земун",
        ),
        (
            "Дом — это место, где живёт кошка!\nХанна в свои 1-1,5 года дама.",
            "pets", "pets-cats", {}, "Кошка",
        ),
        (
            "А кому здесь бесплатный котик? Ищет дом",
            "pets", "pets-cats", {}, "Кошка",
        ),
        (
            "Здравствуйте! Меня зовут Алексей. Имею 10 лет опыта инженером.",
            "jobs", "resumes", {}, "Резюме: инженер",
        ),
        (
            "Мы — компания, специализирующаяся на трансферах в Сербии.",
            "services", "transport", {}, "Трансферы и перевозки",
        ),
    ]
    for text, category, sub, attrs, expected in cases:
        # Так же, как в импортёре: заголовок из текста идёт кандидатом,
        # и правило решает, годится он или собирать из фактов.
        candidate = parse(text).get("title")
        got = build_title(category, sub, text, attrs, fallback_title=candidate)
        assert got == expected, text


# ── Падеж и мусор вокруг названия ───────────────────────────────────────────
def test_pronoun_removed_with_the_verb():
    """«Продаю свою видеокарту» — без снятия местоимения выходило
    «Свою видеокарта»: глагол ушёл, а падеж правился только у второго слова."""
    title = build_title(
        "electronics", "computers",
        "Продаю свою видеокарту Palit rtx 5070ti 16gb gaming pro-s "
        "в отличном состоянии.",
        {}, fallback_title=parse(
            "Продаю свою видеокарту Palit rtx 5070ti 16gb gaming pro-s "
            "в отличном состоянии."
        ).get("title"),
    )
    assert title == "Видеокарта Palit rtx 5070ti 16gb gaming pro-s"


def test_numbered_list_item_gets_nominative():
    """Глагол стоит строкой выше («Продам:»), падеж всё равно именительный."""
    text = "Продам:\n1. вешалку с решетчатым экраном в отличном состояние.\nЦена: 1500 динар."
    title = build_title("home-garden", "furniture", text, {},
                        fallback_title=parse(text).get("title"))
    assert title == "Вешалка с решетчатым экраном"


def test_condition_tail_dropped():
    """Оценка состояния вытесняет само название и обрезает его многоточием."""
    text = "Продаю свою видеокарту Palit rtx 5070ti в отличном состоянии"
    assert "состоя" not in (parse(text).get("title") or "")


def test_brand_case_untouched():
    """Правка падежа не должна ломать марку: «iPhone», а не «IPhone»."""
    assert parse("Продам iPhone 13 Pro 256 ГБ").get("title") == "iPhone 13 Pro 256 ГБ"


def test_first_person_self_description_rejected():
    """«Я мастер массажа» — про автора, а не про услугу."""
    assert rejects_as_title("Я мастер массажа")
    text = "Всем привет!\nМеня зовут Анастасия. Я мастер массажа."
    assert build_title("services", "beauty-services", text, {},
                       fallback_title=parse(text).get("title")) == "Массаж"


# ── Разбор объявления целиком ───────────────────────────────────────────────
def test_ikea_desk_listing():
    """
    Стол IKEA: заголовок без оценки состояния, цена продажи вместо цены
    покупки, описание без обрубка со ссылкой.
    """
    text = (
        "Продаётся стол письменный IKEA MICKE в прекрасном состоянии. "
        "Куплен за 25 000 rds, продаю за 15000 rds. Самовывоз. "
        "Белград, Вождовац. При необходимости можем помочь разобрать. "
        "Другие вещи для продажи можно посмотреть тут:"
    )
    parsed = parse(text)
    assert parsed["title"] == "Стол письменный IKEA MICKE"
    # «rds» — как в чатах пишут RSD; без этого цена не находилась вовсе
    assert parsed["price"] == 15000
    assert parsed["currency"] == "RSD"
    assert parsed["description"].endswith("помочь разобрать.")
    assert "посмотреть тут" not in parsed["description"]


def test_purchase_price_not_taken_as_sale_price():
    """«Куплен за 25 000, продаю за 15000» — наша цена вторая."""
    assert parse("Куплен за 25 000 rds, продаю за 15000 rds").get("price") == 15000


# ── КАПС, живая строка против сборки, характеристики ────────────────────────
def test_caps_lock_title_normalised():
    """КАПС кричит на всю ленту; марки при этом не трогаем."""
    text = "✨ ПРОСТОРНАЯ ТРЁХКОМНАТНАЯ КВАРТИРА НА НОВОМ НАСЕЛЬЕ – 80 м² ✨ улица Браће Дроняк."
    title = build_title("real-estate", "flats", text, {"area": 80},
                        fallback_title=parse(text).get("title"))
    assert title == "Просторная трёхкомнатная квартира на Новом Населье – 80 м²"


def test_brand_survives_caps_normalisation():
    assert parse("СРОЧНО ПРОДАМ ДИВАН IKEA").get("title") == "Диван IKEA"


def test_live_line_beats_composed_title():
    """
    Автор сам назвал квартиру — эта строка лучше сухой сборки «Квартира,
    80 м²», в которой теряются комнаты и район.
    """
    text = "Просторная трёхкомнатная квартира на Новом Населье – 80 м²"
    title = build_title("real-estate", "flats", text, {"area": 80},
                        fallback_title=parse(text).get("title"))
    assert title.startswith("Просторная трёхкомнатная")


def test_spec_line_is_not_a_title():
    """«70 м², 2 комнаты» — обрывок таблицы; собираем заголовок сами."""
    text = "#stan\n70 м², 2 комнаты, Вождовац\n120000 €"
    title = build_title("real-estate", "flats", text, {},
                        fallback_title=parse(text).get("title"))
    assert title == "2-комнатная квартира, 70 м², Вождовац"


def test_rooms_with_yo():
    """«ТРЁХКОМНАТНАЯ» через ё раньше не опознавалась вовсе."""
    from app.core.tg_parse import extract_rooms
    assert extract_rooms("ПРОСТОРНАЯ ТРЁХКОМНАТНАЯ КВАРТИРА") == 3


def test_address_tail_dropped():
    """Улица в заголовке лишняя: она есть в описании."""
    text = "Квартира на Новом Населье – 80 м², улица Браће Дроняк."
    assert "улица" not in (parse(text).get("title") or "")


# ── Дыры парсера, найденные на живой ленте ──────────────────────────────────
from app.core.tg_parse import looks_like_ad, looks_like_spam  # noqa: E402


def test_parts_price_is_not_the_item_price():
    """
    «Продается целиком или по деталям… Возможна замена. От 10 евро» —
    десять евро стоит деталь, а не телефон. Пустая цена честнее.
    """
    text = (
        "iPhone 11, 128gb\n"
        "В идеальном состоянии, здоровье аккумулятора 91%.\n"
        "Продается целиком или по деталям:\n"
        "Оригинальный аккумулятор 91%\n"
        "Возможна замена\n"
        "От 10 евро"
    )
    parsed = parse(text)
    assert parsed["price"] is None
    assert parsed["title"] == "iPhone 11, 128gb"


def test_channel_promo_is_spam():
    """Пост ради подписчиков: товара нет, есть приглашение в чужой канал."""
    text = (
        "РАБОТА В БЕЛГРАДЕ — ПОДДЕРЖИТЕ НАШ ПРОЕКТ\n"
        "Ваша подписка — наша поддержка!\n"
        "ПОДПИСАТЬСЯ НА КАНАЛ\n"
        "Чем нас больше — тем больше вакансий!!!"
    )
    assert looks_like_spam(text)


def test_salon_promotion_is_an_ad():
    """Акция салона — повод прийти, а не вещь на продажу."""
    text = (
        "«ЩЕДРЫЕ ВЫХОДНЫЕ» ПРОДОЛЖАЮТСЯ!\n"
        "22 и 23 августа для новых клиентов\n"
        "60 минут массажа 2000 RSD\n"
        "ПРОДЛЕВАЮ АКЦИЮ! только для новых клиентов"
    )
    assert looks_like_ad(text)


def test_generic_title_completed_with_model():
    """«В продаже ноутбук» — род без модели; модель стоит строкой ниже."""
    text = (
        "В продаже ноутбук\n"
        "HP Omen 16-xf0xxx\n"
        "(2023 г. производства)\n"
        "1399 €"
    )
    assert parse(text)["title"] == "Ноутбук HP Omen 16-xf0xxx"


def test_normal_listing_not_flagged():
    """Обычное объявление не должно попасть под фильтры рекламы."""
    text = "Продам диван IKEA, 15000 RSD, самовывоз Земун"
    assert not looks_like_spam(text)
    assert not looks_like_ad(text)


# ── Сито импорта ────────────────────────────────────────────────────────────
# Прогон и настоящий заход судят одной функцией — иначе прогон показывал бы
# одно, а в ленту попадало другое.
def test_screen_matches_the_pipeline():
    from app.core.tg_import import screen
    from app.core.tg_sources import CHATS

    chat_id = next(iter(CHATS))
    topic_id = next(iter(CHATS[chat_id]["topics"]))

    reason, parsed = screen(
        "Продам диван IKEA в хорошем состоянии, 15000 RSD, самовывоз Земун",
        chat_id, topic_id)
    assert reason is None
    assert parsed["title"] == "Диван IKEA"
    assert parsed["price"] == 15000
    assert parsed["category_slug"] and parsed["sub_slug"]


def test_screen_rejects_channel_promo():
    from app.core.tg_import import screen
    from app.core.tg_sources import CHATS

    chat_id = next(iter(CHATS))
    topic_id = next(iter(CHATS[chat_id]["topics"]))
    reason, _ = screen(
        "ПОДПИСАТЬСЯ НА КАНАЛ! Ваша подписка — наша поддержка, "
        "чем нас больше тем лучше!!!", chat_id, topic_id)
    assert reason == "спам"


def test_screen_rejects_short_message():
    from app.core.tg_import import screen
    from app.core.tg_sources import CHATS

    chat_id = next(iter(CHATS))
    topic_id = next(iter(CHATS[chat_id]["topics"]))
    assert screen("Привет", chat_id, topic_id)[0] == "слишком короткое"


# ── Категории ───────────────────────────────────────────────────────────────
# Ключевое слово должно начинать слово, а не сидеть в его середине.
def test_keyword_matches_word_start_only():
    from app.core.tg_classify import classify
    # «шин» внутри «машин» отправляло прокат машин в «Шины и диски».
    # Сам прокат — услуга: продажу автомобилей ищет другой человек.
    assert classify("компания ANTEL Прокат машин в Сербии")[0] == "services"
    assert classify("Продам зимние шины Michelin 205/55")[0] == "auto"


def test_handmade_is_not_a_job():
    """«Ручная работа» у вязаных сумочек — не вакансия."""
    from app.core.tg_classify import classify, classify_sub
    category = classify("Сумочки вязаные, ручная работа, 1200 динар")[0]
    assert category == "fashion"
    assert classify_sub(category, "Сумочки вязаные, ручная работа") == "bags"


def test_real_vacancy_still_found():
    from app.core.tg_classify import classify
    assert classify("Работа в Белграде, требуется официант, зарплата")[0] == "jobs"
    assert classify("Ищу работу барменом, опыт 3 года")[0] == "jobs"


def test_everyday_clothing_recognised():
    """Юбки, боди, бельё, кулоны — в ленте каждый день, в словаре не было."""
    from app.core.tg_classify import classify, classify_sub
    for text, expected_sub in (
        ("Юбки по 500 RSD, тянутся, подойдут на размер m-l", "women"),
        ("Сетчатое боди, подойдет на размер s-m", "women"),
        ("Продам нижнее белье, кружевные комплекты", "women"),
        ("Кулон Бездна, материалы металл и стекло", "watches"),
        ("Сумочки вязаные, ручная работа", "bags"),
    ):
        category = classify(text)[0]
        assert category == "fashion", text
        assert classify_sub(category, text) == expected_sub, text


def test_object_root_matches_word_start():
    """«тен» внутри «толстостенная» делало прилагательное названием вещи."""
    from app.core.title_rules import has_object_word
    assert not has_object_word("Толстостенная")
    assert not has_object_word("Пакетом")
    assert has_object_word("Латунная форма с фруктовым мотивом")


def test_head_of_text_weighs_more():
    """
    «Доставка по Белграду» в конце есть у половины постов — из-за неё
    куртки уезжали в «Перевозки». Предмет назван в начале.
    """
    from app.core.tg_classify import classify
    text = ("Женские куртки\n1) Осенне-весенняя куртка, размер XS -- 1500 rsd\n"
            "Доставка по Белграду, возможна перевозка")
    assert classify(text)[0] == "fashion"


def test_list_first_item_becomes_title():
    """«Продаю пакетом:» — предмет назван первым пунктом списка."""
    text = "Продаю пакетом:\n- ведро ИКЕА, как новое, 10 л\n- таз 15 л\n1300 RSD"
    assert parse(text)["title"].startswith("Ведро")


def test_rental_is_a_service():
    from app.core.tg_classify import classify, classify_sub
    text = "компания ANTEL\nПрокат машин в Сербии\nот 490 евро"
    assert classify(text)[0] == "services"
    assert classify_sub("services", text) == "transport"


# ── Падеж не должен трогать глаголы ─────────────────────────────────────────
def test_verbs_are_not_declined():
    """«Куплю учебники» превращалось в «Купля», «Перевожу» — в «Перевожа»."""
    assert parse("Куплю учебники 8 разред. Elementary Zmaj Jova")["title"] \
        == "Куплю учебники 8 разред"


def test_giving_away_is_a_normal_listing():
    """«Отдаю красивую одежду» — обычное объявление, глагол просто снимается."""
    text = "Отдаю красивую одежду для девочки, на возраст от рождения до 1 года"
    assert parse(text)["title"] == "Красивая одежда для девочки"


# ── Цена без валюты ─────────────────────────────────────────────────────────
def test_bare_price_after_selling_verb():
    """«Покупала за 16к, продаю за 7500» — валюту не написали вовсе."""
    parsed = parse("Продается сумка Victoria Secret, покупала за 16к, продаю за 7500")
    assert parsed["price"] == 7500
    assert parsed["currency"] == "RSD"


# ── Слова, которые тянули объявления не туда ────────────────────────────────
def test_house_word_needs_context():
    """«Возле дома нашли котёнка», «живут у себя дома» — не недвижимость."""
    from app.core.tg_classify import classify
    assert classify("Возле дома нашли маленького котёнка")[0] == "pets"
    assert classify("Продам дом в Земуне, 120 м², участок")[0] == "real-estate"


def test_rubber_word_needs_context():
    """«Обувь на резинке» уезжала в «Шины и диски»."""
    from app.core.tg_classify import classify
    assert classify("Женская обувь на резинке, 40 р-н (26 см)")[0] == "fashion"
    assert classify("Продам зимние шины Michelin 205/55 R16")[0] == "auto"


def test_long_term_rental_is_a_service():
    """«Kia Stonic — долгосрочная аренда» — не продажа автомобиля."""
    from app.core.tg_classify import classify
    assert classify("Kia Stonic — долгосрочная аренда, кроссовер")[0] == "services"
    assert classify("Продам Volkswagen Golf 5, пробег 200000")[0] == "auto"


def test_master_and_movers_are_services():
    from app.core.tg_classify import classify
    assert classify("МАСТЕР В БЕЛГРАДЕ. Мастер на час, два или день")[0] == "services"
    assert classify("Перевожу людей (до 7 чел.) и грузы на автомобиле")[0] == "services"


def test_delivery_note_does_not_make_a_service():
    """«Доставка по Белграду» стоит в половине обычных объявлений."""
    from app.core.tg_classify import classify
    text = "Женские куртки, размер XS -- 1500 rsd\nДоставка по Белграду"
    assert classify(text)[0] == "fashion"


# ── Обрезанные заголовки ────────────────────────────────────────────────────
def test_list_number_without_space():
    """«1.Старинные ножницы» — точку не всегда отделяют пробелом."""
    text = "1.Старинные портновские ножницы немецкого бренда 3Plus Solingen из кованой стали."
    assert parse(text)["title"] == "Старинные портновские ножницы немецкого бренда 3Plus Solingen"


def test_bracket_detail_dropped():
    """Скобка с комплектацией вытесняла название за предел строки."""
    text = ("квадрокоптер DJI Mini 3 Pro (с камерой на 48 МП и датчиками "
            "препятствий) в расширенной комплектации")
    assert parse(text)["title"] == "Квадрокоптер DJI Mini 3 Pro"


def test_vacancy_title_from_first_line():
    """«Требуется мойщик» — готовый заголовок, профессия и есть предмет."""
    text = "Требуется мойщик\n\nМы ищем ответственного сотрудника для работы на мойке"
    assert parse(text)["title"] == "Требуется мойщик"


def test_handyman_pitch_becomes_the_work():
    """«Готов приехать и помочь» — про автора; заголовок — само дело."""
    text = ("Готов оперативно приехать и помочь в ремонте по дому.\n"
            "Много лет работал в сфере ремонта стиральных машин.")
    assert build_title("services", "repair", text, {},
                       fallback_title=parse(text).get("title")) == "Ремонт стиральных машин"


def test_question_post_is_not_a_listing():
    """Вопрос в чат — не объявление."""
    from app.core.title_rules import looks_like_question
    assert looks_like_question(
        "Скажите, есть ли трансфер или визаран до Станишичей (Босния) "
        "из Белграда? Может кто-то возит?")
    assert not looks_like_question("Продам диван IKEA, 15000 RSD")


# ── Живая строка вместо сборки из фактов ────────────────────────────────────
def test_short_object_name_is_a_title():
    """«Стол 3000 RSD» — после снятия цены остаётся четыре буквы."""
    assert parse("**Стол 3000 RSD**\n100х60см, ножки откручиваются")["title"] == "Стол"


def test_counted_goods_are_not_a_spec_line():
    """«4шт бокалы» — товар со счётом, а не обрывок таблицы."""
    assert parse("Продам 4шт бокалы для коньяка. 700 динар")["title"] \
        == "4шт бокалы для коньяка"
    # а вот это по-прежнему характеристики
    assert parse("#stan\n70 м², 2 комнаты, Вождовац\n120000 €")["title"] is None


def test_word_root_with_space_is_exact():
    """Корень «топ » — слово целиком: он не должен ловить «топор»."""
    from app.core.title_rules import has_object_word
    assert has_object_word("Спортивный топ в хорошем состоянии")
    assert not has_object_word("Наточил топор вчера")


def test_tableware_and_boxes_recognised():
    for text, expected in (
        ("Шкатулка с магнитной крышкой 7х5 см. Материал дерево", "Шкатулка с магнитной крышкой 7х5 см"),
        ("Сумочки вязаные, ручная работа\nЛюбая 1200 динар", "Сумочки вязаные"),
    ):
        assert parse(text)["title"] == expected


def test_music_lessons_are_tutoring():
    from app.core.tg_classify import classify, classify_sub
    text = ("Меня зовут Константин, я - джазовый пианист, педагог по ф-но. "
            "Если вы хотите научиться играть джаз")
    assert classify(text)[0] == "services"
    assert classify_sub("services", text) == "tutoring"
    assert build_title("services", "tutoring", text, {},
                       fallback_title=parse(text).get("title")) == "Уроки фортепиано"


def test_contact_line_is_not_a_title():
    """«Мой Телеграм @masterSrbija» — контакт, а не название услуги."""
    from app.core.title_rules import rejects_as_title
    assert rejects_as_title("Мой Телеграм @masterSrbija")
    assert rejects_as_title("@masterSrbija")


def test_plural_giving_verb_removed():
    """«Отдаем добавку» — глагол снимается, падеж выправляется."""
    assert parse("Отдаем добавку Лососевое масло для кошек/собак, за шоколад")["title"] \
        == "Добавка Лососевое масло для кошек/собак"


# ── Корень-слово в классификаторе ───────────────────────────────────────────
def test_classifier_root_with_space_is_exact():
    """
    «кот » ловило «которая» и «котлета»: объявление об одежде для девочки
    уезжало в «Кошек», потому что дальше в тексте стояло «которая».
    """
    from app.core.tg_classify import classify
    assert classify("Отдаю одежду для девочки, которая ждала вторую дочку")[0] != "pets"
    assert classify("Возле дома нашли маленького кот, есть блохи")[0] == "pets"


def test_watches_do_not_catch_часто_и_серебристый():
    from app.core.tg_classify import classify_sub
    # «час» ловило «часто», «серебр» — «серебристые колготки»
    assert classify_sub("fashion", "Женская обувь на резинке, часто носила") == "shoes"
    assert classify_sub(
        "fashion", "Нижнее белье и серебристые капроновые колготки") == "women"


def test_flat_title_must_name_the_object():
    """Хэштеги «Гостиная + 2 комнаты» — не название квартиры."""
    text = ("#Vozdovac\n#квартира #до1000 #лифт #новыйдом #посудомойка "
            "#балкон #трешка #арендабелград\n1100 €")
    assert build_title("real-estate", "flats", text, {},
                       fallback_title=parse(text).get("title")) == "3-комнатная квартира"
    # а живое название по-прежнему в приоритете
    live = "Трёхкомнатная квартира в Beograd na vodi"
    assert build_title("real-estate", "flats", live, {},
                       fallback_title=parse(live).get("title")).startswith("Трёхкомнатная")


def test_service_verb_beats_the_noun():
    """«Перевожу людей на автомобиле» — услуга, хотя «авто» тоже в тексте."""
    from app.core.tg_classify import classify
    assert classify("Перевожу людей (до 7 чел.) и грузы на автомобиле")[0] == "services"
    assert classify("Чиню стиральные машины на дому")[0] == "services"
    assert classify("Продам Volkswagen Golf 5, пробег 200000")[0] == "auto"
