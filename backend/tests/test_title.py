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


# ── Правдоподобие цены и мелочи разбора ─────────────────────────────────────
def test_implausible_price_dropped():
    """Дом за 150 динар — это площадь или этаж, попавшие под разбор."""
    from app.core.tg_parse import plausible_price
    assert not plausible_price("houses", 150, "RSD")
    assert not plausible_price("cars", 5000, "RSD")
    # настоящие цены остаются
    assert plausible_price("flats", 380, "EUR")
    assert plausible_price("shoes", 150, "RSD")
    # порог не трогает мелочь, лежащую в том же разделе: «носки
    # автомобильные» за тысячу динар — нормальная цена
    assert plausible_price("car-parts", 1000, "RSD")
    assert plausible_price(None, 1000, "RSD")


def test_city_glued_after_dot():
    """«Учебники по сербскому.Белград» — точку перед городом не отделяют."""
    assert parse("Отдам учебники по сербскому.Белград. Стари Град")["title"] \
        == "Учебники по сербскому"


def test_textbooks_are_school_supplies():
    from app.core.tg_classify import classify, classify_sub
    text = "Отдам учебники по сербскому.Белград"
    assert classify(text)[0] == "kids"
    assert classify_sub("kids", text) == "school"
    # художественные книги остаются в хобби
    assert classify("Продам книги, детективы и фантастика")[0] == "hobby-sport"


# ── Падеж: склоняем только то, с чего сняли глагол ──────────────────────────
def test_first_person_verbs_survive():
    """
    Склонение всегда портило глаголы: «Провожу занятия» → «Провожа»,
    «Живу и ищу работу» → «Жива», «Куплю гарнитуру» → «гарнитура».
    """
    for text in (
        "Провожу занятия с детьми",
        "Живу и ищу работу в Белграде",
        "Куплю гарнитуру Xbox mono",
    ):
        assert parse(text)["title"] == text, text


def test_declension_still_works_where_verb_was_removed():
    assert parse("Отдаю красивую одежду для девочки")["title"] \
        == "Красивая одежда для девочки"
    assert parse("Продам:\n1. вешалку с решетчатым экраном.")["title"] \
        == "Вешалка с решетчатым экраном"


# ── Услуги против товаров ───────────────────────────────────────────────────
def test_repair_of_goods_is_a_service():
    """«Ремонт бойлеров» — услуга, а не бойлер на продажу."""
    from app.core.tg_classify import classify
    for text in ("Ремонт бойлеров в Белграде, выезд",
                 "Установка и ремонт бытовой техники",
                 "Ремонт квартир / домов под ключ"):
        assert classify(text)[0] == "services", text
    # сам товар остаётся товаром
    assert classify("Продам бойлер Ariston 80 л")[0] == "home-garden"


def test_household_machine_is_not_a_car():
    """«Стиральную машину» роднит с автомобилем только слово."""
    from app.core.tg_classify import classify, classify_sub
    assert classify("Продам стиральную машину Bosch, 20000 RSD")[0] == "home-garden"
    assert classify_sub("home-garden", "Продам стиральную машину Bosch") == "appliances"
    assert classify("Продам машину Volkswagen Golf, пробег 200000")[0] == "auto"


def test_small_goods_recognised():
    from app.core.tg_classify import classify
    for text, expected in (
        ("Входной коврик 300 RSD", "home-garden"),
        ("AirPods 4 — только ЛЕВЫЙ наушник + кейс", "electronics"),
        ("Винтажная статуэтка «Спящая девочка»", "home-garden"),
        ("Цветочное темно-серое кашпо", "home-garden"),
    ):
        assert classify(text)[0] == expected, text


# ── Услуга против товара: решает глагол продажи ─────────────────────────────
def test_service_wins_without_selling_verb():
    """
    У мастера по бойлерам в тексте полно названий техники. Отличает его от
    продавца не предмет, а отсутствие «продам».
    """
    from app.core.tg_classify import classify, classify_sub
    for text in (
        "Сантехник. Замена смесителей, подключение посудомоечных машин",
        "🔧 Чистка и обслуживание кондиционеров с разбором",
        "Услуги домашнего мастера в Белграде",
        "Ремонт бойлеров, выезд по городу",
        "Мастер по дому в Белграде",
    ):
        assert classify(text)[0] == "services", text
        assert classify_sub("services", text) == "repair", text


def test_goods_stay_goods():
    from app.core.tg_classify import classify
    for text in ("Продам бойлер Ariston 80 л, 15000 RSD",
                 "Продам стиральную машину Bosch",
                 "Продам кондиционер LG, б/у"):
        assert classify(text)[0] == "home-garden", text


def test_gearbox_only_for_cars():
    """«Коробка» — это и коробка передач, и коробка от наушников."""
    from app.core.tg_classify import classify
    assert classify("AirPods 4 — только ЛЕВЫЙ наушник + кейс + коробка")[0] == "electronics"
    assert classify("Продам Golf 5, коробка передач механика, пробег")[0] == "auto"


def test_dishwasher_hashtag_is_not_a_flat_title():
    """«#посудомойка» из перечня удобств — не название квартиры."""
    text = "#Vracar\n#квартира #лифт #посудомойка #балкон\n1250 €"
    assert build_title("real-estate", "flats", text, {},
                       fallback_title=parse(text).get("title")) == "Квартира"


def test_job_search_beats_service_words():
    """Человек ищет работу — это «Работа», а не услуга, которую он умеет."""
    from app.core.tg_classify import classify
    for text in ("Живу и ищу работу в Белграде",
                 "Опыт работы 5 лет, ищу вакансию клинера",
                 "Также работал слесарем КИПиА, ищу работу"):
        assert classify(text)[0] == "jobs", text


def test_trailer_word_needs_context():
    """«прицеп» ловило «прицепить»."""
    from app.core.tg_classify import classify
    assert classify("Кошелечек, за зажимчик можно прицепить")[0] != "auto"
    assert classify("Продам автоприцеп, состояние хорошее")[0] == "auto"


def test_request_without_question_mark():
    """«Может кто-то отдает диван» — просьба, знак вопроса ставят не все."""
    from app.core.title_rules import looks_like_question
    assert looks_like_question("Может кто-то отдает диван")
    assert looks_like_question("Подскажите хорошего стоматолога")
    assert not looks_like_question("Продам диван IKEA 15000 RSD")


# ── Описание ────────────────────────────────────────────────────────────────
# Заголовок и описание читаются вместе: повтор, обрывки и чужие контакты в
# описании портят карточку не меньше, чем неверный заголовок.
def test_currency_without_price_is_empty():
    """У объявления без цены стоял EUR — оборванный ценник в ленте."""
    parsed = parse("Оззик ищет дом! Сообразительный энергичный парень 2-3 года")
    assert parsed["price"] is None
    assert parsed["currency"] is None


def test_title_line_dropped_even_when_reworded():
    """
    Заголовок мы правим — снимаем глагол и знаки, — и точным совпадением
    строка уже не ловилась: «Оззик ищет дом!» оставался дублем.
    """
    parsed = parse("Оззик ищет дом!\n\nСообразительный энергичный парень 2-3 года.")
    assert parsed["title"] == "Оззик ищет дом"
    assert not parsed["description"].startswith("Оззик ищет дом")


def test_contact_lines_removed_from_description():
    """Связь идёт кнопкой в Telegram; ник в описании уводит мимо неё."""
    text = ("Оззик ищет дом!\nПарень 2-3 года\nКонтакты:\n"
            "Telegram: @foo\n+381 63 733 0218")
    description = parse(text)["description"]
    assert "@foo" not in description
    assert "Контакты" not in description
    assert "381" not in description
    assert "Парень 2-3 года" in description


def test_call_only_line_removed():
    """После снятия ника от строки остаётся один призыв «Пишите»."""
    description = parse("Продам диван IKEA, 15000 RSD\nПишите @masterbg\nЗемун")["description"]
    assert "Пишите" not in description


def test_place_line_removed_only_if_nothing_else():
    """
    «Белград, Стари Град» — только место, убираем. «Состояние отличное,
    самовывоз Земун» сообщает ещё и о состоянии — оставляем.
    """
    assert "Стари Град" not in parse("Продам шкаф\n25000 RSD\nБелград, Стари Град")["description"]
    kept = parse("Продам стол 3000 RSD\nСостояние отличное, самовывоз Земун")["description"]
    assert "Состояние отличное" in kept


def test_description_never_loses_everything():
    """Пустое описание хуже повтора: последнюю содержательную строку держим."""
    for text in ("Продам стол, 3000 RSD\nПишите в личку",
                 "Диван 25000 RSD"):
        assert parse(text)["description"].strip()


# ── Найденное на стресс-наборе ──────────────────────────────────────────────
def test_deal_terms_in_the_tail_do_not_kill_the_listing():
    """«Торг уместен» в конце строки выбрасывал всё объявление целиком."""
    text = ("Продам iPhone 14 Pro 256gb, состояние идеал, батарея 89%. "
            "620 евро, торг уместен. Нови Београд")
    assert parse(text)["title"] == "iPhone 14 Pro 256gb"
    # а строка, которая целиком про условие, заголовком по-прежнему не станет
    assert parse("Торг уместен, пишите в лс")["title"] is None


def test_giving_away_phrases_removed():
    """«Отдам в добрые руки взрослую кошку» → «Взрослая кошка»."""
    assert parse("Отдам в добрые руки взрослую кошку, стерилизована")["title"] \
        == "Взрослая кошка"
    assert parse("Отдам даром детские вещи 74-80 размер")["title"] \
        == "Детские вещи 74-80 размер"


def test_punctuation_does_not_block_declension():
    """«кошку,» со знаком не совпадало ни с одним правилом падежа."""
    from app.core.tg_parse import to_nominative
    assert to_nominative("взрослую кошку, стерилизована") == "взрослая кошка, стерилизована"


def test_animal_plural_declension():
    assert parse("Отдам котят в добрые руки, 2 месяца")["title"] == "Котята в добрые руки"


def test_appliance_beats_the_brand():
    """«Микроволновка Samsung» — техника для дома, хотя Samsung и телефоны."""
    from app.core.tg_classify import classify, classify_sub
    assert classify("Продам микроволновку Samsung, рабочая, 6000 дин")[0] == "home-garden"
    assert classify_sub("home-garden", "Продам микроволновку Samsung") == "appliances"
    assert classify("Продам телефон Samsung Galaxy S21")[0] == "electronics"
    # работа с техникой остаётся услугой
    assert classify("Чиню стиральные машины на дому")[0] == "services"
    assert classify("Ремонт микроволновок на дому")[0] == "services"


def test_wanted_service_is_a_service():
    """«Ищу репетитора», «Нужен электрик» — тот же раздел, что и предложение."""
    from app.core.tg_classify import classify
    assert classify("Ищу репетитора по сербскому для ребёнка 8 лет")[0] == "services"
    assert classify("Нужен хороший электрик в Земуне")[0] == "services"


def test_cleaning_is_a_service_not_property():
    from app.core.tg_classify import classify, classify_sub
    text = "Уборка квартир и офисов, свои средства, от 2000 динар"
    assert classify(text)[0] == "services"
    assert classify_sub("services", text) == "cleaning"


def test_consoles_and_languages_recognised():
    from app.core.tg_classify import classify, classify_sub
    assert classify("Куплю PS5 в хорошем состоянии, до 400 евро")[0] == "electronics"
    assert classify_sub("electronics", "Куплю PS5") == "gaming"
    assert classify("Английский язык для взрослых, онлайн и очно")[0] == "services"


def test_car_traits_pick_the_subcategory():
    from app.core.tg_classify import classify_sub
    assert classify_sub("auto", "Toyota Corolla 2015, автомат, бензин, растаможена") == "cars"


# ── Нейросеть для сухих заголовков ──────────────────────────────────────────
# Модель зовём только там, где правила выдали сухое, и её ответ проверяем
# теми же правилами: хуже стать не должно ни при какой её выдумке.
def test_ai_called_only_when_rules_fall_short():
    from app.core.title_rules import needs_help
    # правила справились — модель не нужна
    for title in ("Диван IKEA", "iPhone 13 Pro", "Письменный стол IKEA MICKE"):
        assert not needs_help(title, "описание объявления"), title
    # сухо или обрезано — нужна
    for title in ("Стол", "Одежда", "Квартира", "Длинное название…", ""):
        assert needs_help(title, "описание объявления"), title
    # заголовок собран из фактов
    assert needs_help("Кошка", "описание", composed=True)
    # описания нет вовсе
    assert needs_help("Хороший диван", "")


def test_ai_answer_is_checked_by_the_same_rules():
    """Модель может выдумать вещь, которой в объявлении нет."""
    from app.core.ai_title import _acceptable
    text = "Продаётся стол письменный IKEA MICKE в прекрасном состоянии"
    assert _acceptable("Письменный стол IKEA MICKE", text)
    assert not _acceptable("Мотоцикл Harley Davidson", text)   # выдумка
    assert not _acceptable("Здравствуйте, вот описание", text)  # болтовня
    assert not _acceptable("", text)
    assert not _acceptable("Стол " * 30, text)                  # длиннее строки


def test_ai_answer_parsed_from_markdown():
    """Модели любят обрамлять JSON пояснениями и ```-блоками."""
    from app.core.ai_title import _parse_answer
    data = _parse_answer('```json\n{"title":"Стол IKEA","summary":"Хороший стол."}\n```')
    assert data["title"] == "Стол IKEA"
    assert _parse_answer("извините, не понял") == {}
    assert _parse_answer(None) == {}


def test_parser_works_without_any_key():
    """Без ключа парсер должен работать как прежде, только на правилах."""
    from app.core.ai_title import improve
    assert improve("Продам стол 3000 RSD") == {}


def test_category_rechecked_after_ai_titled_the_item():
    """
    Сухой заголовок часто означает, что и категорию правила угадали мимо:
    «Держатель для туалетной бумаги» лежал в недвижимости, потому что
    предмет опознан не был. Раз предмет назван — категорию перепроверяем.
    """
    from app.core.tg_import import recategorize
    assert recategorize(
        "Держатель для туалетной бумаги IKEA BROGRUND",
        "Новый держатель из Икеи, не подошел для съемной квартиры",
        "real-estate")[0] == "home-garden"
    assert recategorize(
        "Винтажные немецкие блюда и комплект тарелок",
        "Два винтажных блюда 36 см с ручной росписью",
        "real-estate")[0] == "home-garden"


def test_recategorize_keeps_category_when_title_says_nothing():
    """Если по заголовку не судить, оставляем то, что определили правила."""
    from app.core.tg_import import recategorize
    assert recategorize("Хорошая вещь", "Продам хорошую вещь", "fashion")[0] == "fashion"


# ── Описание по фотографии и раздел от модели ───────────────────────────────
def test_photo_summary_rejects_invented_facts():
    """
    Рассказывая по снимку, модель склонна добавить то, чего знать не
    может: цену, размер, год. Покупатель этому поверит.
    """
    from app.core.ai_title import _PROMISES_RE
    for invented in ("Стол в отличном состоянии, цена 3000 динар",
                     "Куртка, размер 46, тёплая",
                     "Автомобиль 2015 года, ухоженный",
                     "Диван с гарантией на год"):
        assert _PROMISES_RE.search(invented), invented
    assert not _PROMISES_RE.search(
        "Керамическая ваза белого цвета с рельефным узором, без сколов")


def test_photo_description_needs_key_and_photos():
    from app.core.ai_title import describe_by_photo
    assert describe_by_photo("текст", []) == {}


def test_forced_category_is_not_published_at_once():
    """Догадку модели о разделе смотрит человек, как и всякое расхождение."""
    from app.core.tg_import import screen
    from app.core.tg_sources import CHATS

    chat_id = next(iter(CHATS))
    topic_id = next(iter(CHATS[chat_id]["topics"]))
    reason, parsed = screen("Продам штуковину непонятную и полезную в быту",
                            chat_id, topic_id, forced="home-garden")
    assert reason is None
    assert parsed["category_slug"] == "home-garden"
    assert parsed["publish"] is False


def test_guess_category_returns_known_slug_only():
    from app.core.ai_title import guess_category
    assert guess_category("Продам что-то", ["fashion", "auto"]) is None


# ── Повторы объявлений ──────────────────────────────────────────────────────
# Одно объявление кочует по чатам переписанным, часто от разных людей.
def test_same_item_recognised_across_chats():
    from app.core.tg_parse import fingerprint, same_thing
    pairs = (
        (("Диван IKEA раскладной", "Раскладной диван, Земун"),
         ("Продам диван Икеа", "Диван раскладной в Земуне")),
        (("MacBook Pro 16 M5 24 Gb", "Ноутбук MacBook"),
         ("MacBook Pro 16’ M5 Pro 24 Gb / 1 Tb", "MacBook Pro 16")),
        (("Кроссовки мужские Under Armour", "Новые кроссовки 42"),
         ("Кроссовки Under Armour", "Кроссовки мужские 42 размер")),
    )
    for one, two in pairs:
        assert same_thing(fingerprint(*one), fingerprint(*two)), one


def test_different_items_not_merged():
    """
    «Платье» и «жилет» за одну цену в одном городе сходятся по словам
    «женское» и «отличное» — но это разные вещи.
    """
    from app.core.tg_parse import fingerprint, same_thing
    pairs = (
        (("Платье H&M размер S", "Женское платье отличное"),
         ("Женский жилет Gant", "Жилет женский отличное")),
        (("Пиджак Mexx замшевые вставки", "Пиджак мужской"),
         ("Пиджак Barbosa", "Пиджак размер 52")),
        (("Куртка зимняя женская", "Тёплая куртка размер М"),
         ("Куртка мужская кожаная", "Кожаная куртка размер L")),
    )
    for one, two in pairs:
        assert not same_thing(fingerprint(*one), fingerprint(*two)), one


def test_fingerprint_keeps_short_model_tokens():
    """Марка и модель самые приметные, а они короткие: «m5», «16», «gb»."""
    from app.core.tg_parse import fingerprint
    mark = fingerprint("MacBook Pro 16 M5 24 Gb", "")
    assert "16" in mark.split() and "m5" in mark.split()


def test_fingerprint_ignores_common_words():
    from app.core.tg_parse import fingerprint
    mark = fingerprint("Продам диван", "Отличное состояние, самовывоз, торг уместен")
    assert "prodam" not in mark and "torg" not in mark


# ── Найденное переразбором старых объявлений ────────────────────────────────
# Переразбор показал, что строгое требование предметного слова выбрасывало
# настоящие названия и подставляло случайную строку из середины текста.
def test_first_line_trusted_without_dictionary():
    """
    Словарь предметов конечен, а мир вещей — нет. «Каланхоэ», «Антуриум»,
    «Лапушка Софи» в нём не значатся, и заголовком становилось «Цветёт
    долго» — строка из середины объявления.
    """
    assert parse("Каланхоэ\nЦветёт долго, неприхотливо")["title"] == "Каланхоэ"
    assert parse("Антуриум (Мужское счастье)\nЦветёт красными цветами")["title"] == "Антуриум"
    assert parse("Лапушка Софи в поисках семьи\nК собакам интереса нет")["title"] \
        == "Лапушка Софи в поисках семьи"


def test_blacklists_still_work_on_first_line():
    """Доверие к первой строке не отменяет чёрных списков."""
    from app.core.title_rules import rejects_as_title
    for text in ("Мы — компания, специализирующаяся на трансферах",
                 "Если вы хотите научиться играть джаз",
                 "Наша команда работает 5 лет",
                 "Меня зовут Даниил",
                 "Мой Телеграм @masterbg"):
        assert rejects_as_title(text, first_line=True), text


def test_model_number_kept_at_the_end():
    """«Bedside Lamp 2» и «3 в 1» — часть названия, а не остаток разметки."""
    assert parse("Умная лампа Xiaomi Mi Bedside Lamp 2")["title"] \
        == "Умная лампа Xiaomi Mi Bedside Lamp 2"
    assert parse("Коляска Maxi-Cosi VSO 3 в 1")["title"] == "Коляска Maxi-Cosi VSO 3 в 1"
    # а вот это по-прежнему мусор
    assert parse("Два брата-акробата 3\nКотята ищут дом")["title"] == "Два брата-акробата"


def test_colon_line_announces_a_list():
    """«Продаю пакетом:» и «Характеристики:» — не названия."""
    assert parse("Продаю пакетом:\n- ведро ИКЕА 10 л\n- таз 15 л")["title"] \
        == "Ведро ИКЕА 10 л"
    assert parse("Характеристики:\n- CPU AMD Ryzen 7")["title"] == "CPU AMD Ryzen 7"


def test_title_not_judged_twice():
    """
    Заголовок из текста уже прошёл отбор — вторая, строгая проверка
    оставляла объявление вовсе без названия.
    """
    text = "Каланхоэ\nЦветёт долго\n500 RSD"
    assert build_title("home-garden", "garden", text, {},
                       fallback_title=parse(text).get("title")) == "Каланхоэ"


def test_declension_only_for_known_things():
    """
    Общее правило падежа делало из «Почему» — «Почема», из «Хочу» —
    «Хоча». Склоняем только то, что заведомо вещь.
    """
    assert parse("Почему творог — лучший друг продуктивности")["title"] \
        == "Почему творог — лучший друг продуктивности"
    assert parse("Хочу научиться электромонтажу")["title"] == "Хочу научиться электромонтажу"
    # а вещь по-прежнему приводим в именительный
    assert parse("Картину, размер 40х40см, холст, масло")["title"].startswith("Картина")


def test_continuation_line_is_not_a_title():
    """«+ вторая бесплатно» — продолжение мысли, а не название."""
    from app.core.title_rules import rejects_as_title
    assert rejects_as_title("+ вторая бесплатно", first_line=True)
    assert rejects_as_title("— и ещё одна такая же", first_line=True)


def test_serbian_cat_does_not_catch_mac():
    """«mač» — сербское «кот», но так же начинается Mac mini и MacBook."""
    from app.core.tg_classify import classify
    assert classify("Apple Mac mini M2 16/512 GB")[0] == "electronics"
    assert classify("MacBook Pro 16 M5")[0] == "electronics"
    assert classify("Mačka traži dom, sterilisana")[0] == "pets"


def test_required_means_a_person():
    """«Требуется небольшой ремонт» — про вещь, а не про вакансию."""
    from app.core.tg_classify import classify
    assert classify("Мотоцикл Kawasaki 2025, требуется небольшой ремонт")[0] != "jobs"
    assert classify("В квартире требуется ремонт")[0] != "jobs"
    assert classify("Требуется мойщик, зарплата 60000")[0] == "jobs"
    assert classify("Требуется сотрудник на мойку")[0] == "jobs"


def test_greeting_variants_stripped():
    """
    Приветствие сокращают и переставляют: «Добрый всем», «Доброго дня»,
    просто «Добрый». Обрывок «Добрый» обрастал моделью со следующей
    строки — выходило «Добрый earpods 3».
    """
    for greeting in ("Добрый всем", "Добрый", "Доброго дня", "Всем привет",
                     "Добрый день", "Dobar dan"):
        title = parse(f"{greeting}\nКуплю earpods 3 поколения")["title"]
        assert title == "Куплю earpods 3 поколения", greeting


def test_toy_garage_is_not_property():
    """«Трек гараж Hot-Wheels» — игрушка, а не место для машины."""
    from app.core.tg_classify import classify, classify_sub
    text = "Огромный трек гараж Mega Hot-Wheels с винтовым подъемником"
    assert classify(text)[0] == "kids"
    assert classify_sub("kids", text) == "toys"
    # настоящий гараж остаётся недвижимостью
    assert classify("Сдам гараж на Вождовце, 15 м2, охрана")[0] == "real-estate"
    assert classify("Продам гараж в Земуне")[0] == "real-estate"


def test_flat_with_fresh_repair_is_not_a_service():
    """«Сдаю квартиру, ремонт свежий» — жильё, а не услуга мастера."""
    from app.core.tg_classify import classify
    assert classify("Собственник. Сдаю квартиру 60 м2, ремонт свежий")[0] == "real-estate"
    assert classify("Ремонт квартир под ключ, выезд мастера")[0] == "services"


def test_house_plants_recognised():
    from app.core.tg_classify import classify
    for text in ("Ананас декоративный в горшке", "Мускари / мышиный гиацинт",
                 "Каланхоэ цветёт долго"):
        assert classify(text)[0] == "home-garden", text


def test_garage_at_a_flat_is_an_amenity():
    """
    «Квартира 48 м², гараж в подземном паркинге» — это квартира. Гараж
    при жилье удобство, а не предмет продажи. Обратное неверно: у гаража
    квартиры не бывает.
    """
    from app.core.tg_classify import classify_sub
    assert classify_sub("real-estate",
                        "2-комнатная квартира, 48 м², гараж в подземном паркинге") == "flats"
    assert classify_sub("real-estate", "Студия 34 м2, есть паркинг") == "flats"
    assert classify_sub("real-estate", "Продам дом с гаражом в Земуне") == "houses"
    # сам гараж остаётся гаражом
    assert classify_sub("real-estate", "Сдам гараж на Вождовце, 15 м2") == "garages"
    assert classify_sub("real-estate", "Машиноместо в подземном паркинге") == "garages"


def test_subcategory_weight_by_root_not_phrase_length():
    """
    Вес считался по длине всей фразы, и «сдам гараж» тянул сильнее
    «квартир» — квартиры уезжали в раздел гаражей.
    """
    from app.core.tg_classify import classify_sub
    assert classify_sub("real-estate", "3-комнатная квартира 72 м2 Врачар") == "flats"


# ── Обучаемый классификатор ─────────────────────────────────────────────────
# Словарь ключевых слов хрупок: решение принимает одно совпавшее слово, и
# уточнение ради одного случая ломает соседний. Модель складывает
# свидетельства всех слов сразу.
def test_model_separates_by_context_not_single_word():
    """
    «Трек гараж Hot-Wheels» и «Сдам гараж 15 м2» состоят из одинаковых
    слов, но значат разное. Правилами это разводится вручную, моделью —
    само собой.
    """
    from app.core.category_model import Model
    samples = [
        ("Продам 2-комнатную квартиру 48 м2 Врачар, 5 этаж, балкон", "real-estate"),
        ("Сдаю студию 34 м2 Нови Белград, мебель, от сентября", "real-estate"),
        ("3-комнатная квартира 72 м2, гараж в подземном паркинге", "real-estate"),
        ("Сдам гараж на Вождовце 15 м2, охрана, парковочное место", "real-estate"),
        ("Трек гараж Mega Hot-Wheels с винтовым подъемником игрушка", "kids"),
        ("Много Lego duplo за все, конструктор детский", "kids"),
        ("Коляска Chicco 2в1 состояние хорошее", "kids"),
        ("Продам диван IKEA раскладной 25000 динар", "home-garden"),
        ("Стол письменный IKEA MICKE 100х60 см", "home-garden"),
    ]
    model = Model.train(samples)
    assert model.predict("2-комнатная квартира 46 м2, есть гараж и паркинг")[0] == "real-estate"
    assert model.predict("Огромный трек гараж Hot-Wheels для машинок")[0] == "kids"


def test_model_reports_low_confidence():
    """
    Когда два раздела рядом, объявление двусмысленно. Модель отдаёт
    разрыв, а не «сколько процентов»: маленький разрыв — не угадываем, а
    передаём правилам.
    """
    from app.core.category_model import Model
    model = Model.train([
        ("Продам квартиру 48 м2 Врачар этаж балкон", "real-estate"),
        ("Сдаю студию 34 м2 мебель", "real-estate"),
        ("Продам диван IKEA раскладной", "home-garden"),
        ("Стол письменный IKEA MICKE", "home-garden"),
    ])
    _, margin = model.predict("Продам нечто совершенно неизвестное")
    assert margin < 0.8


def test_parser_works_without_trained_model():
    """Модели нет — классификация идёт по правилам, как прежде."""
    from app.core.tg_classify import classify
    assert classify("Продам диван IKEA 25000 RSD")[0] == "home-garden"


# ── Поиск ───────────────────────────────────────────────────────────────────
def test_brand_spellings_for_search():
    """
    Марку пишут и латиницей, и кириллицей. «айфон» должен находить
    «iPhone» — иначе вещь лежит в ленте, а покупатель её не видит.
    """
    from app.core.search_terms import variants
    assert "iphone" in variants("айфон")
    assert "айфон" in [v.lower() for v in variants("iPhone")]
    assert "iphone 13 про" in variants("айфон 13 про")
    assert "samsung" in variants("самсунг")
    assert "ikea стол" in variants("Икеа стол")


def test_search_keeps_original_first():
    """Первым идёт то, что набрал человек: по нему совпадения точнее."""
    from app.core.search_terms import variants
    assert variants("айфон")[0] == "айфон"
    assert variants("диван")[0] == "диван"


def test_search_variants_handle_empty():
    from app.core.search_terms import variants
    assert variants("") == []
    assert variants("   ") == []


# ── Аудит разбора цены ──────────────────────────────────────────────────────
def test_currency_after_amount_wins():
    """
    «Отдам за 500 дин» уходило в евро: правило для суммы без валюты
    срабатывало раньше, чем разбор самой валюты.
    """
    from app.core.tg_parse import extract_price
    assert extract_price("Отдам за 500 дин") == (500, "RSD")
    assert extract_price("Отдам за 500дин") == (500, "RSD")
    assert extract_price("Продам за 100 евро") == (100, "EUR")
    # без валюты правило работает как прежде
    assert extract_price("Продаю за 7500") == (7500, "RSD")


def test_latin_e_means_euro():
    """«250e» — так пишут евро одной латинской буквой."""
    from app.core.tg_parse import extract_price
    assert extract_price("Продам телефон 250e") == (250, "EUR")
    assert extract_price("Продам 250 e") == (250, "EUR")


def test_price_range_takes_lower_bound():
    """По нижней границе покупатель и ориентируется в фильтре «до N»."""
    from app.core.tg_parse import extract_price
    assert extract_price("Стол 1500-2000 дин") == (1500, "RSD")
    assert extract_price("от 1500 до 2000 дин") == (1500, "RSD")


def test_amount_not_truncated():
    """Разбор отступал на меньшее число, и «100 евро» становилось «10»."""
    from app.core.tg_parse import extract_price
    assert extract_price("Продам за 100 евро")[0] == 100
    assert extract_price("Диван 30к динар")[0] == 30000


# ── Аудит города ────────────────────────────────────────────────────────────
def test_city_in_any_case():
    """Город склоняют: «в Белграде», «из Нови Сада» — так пишет половина."""
    from app.core.tg_parse import extract_city
    for text, expected in (
        ("Диван в Новом Саде, 20000", "novi-sad"),
        ("Продам стол в Белграде", "beograd"),
        ("Живу в Нише", "nis"),
        ("Заберите из Нови Сада", "novi-sad"),
        ("Продам в Суботице", "subotica"),
    ):
        assert extract_city(text) == expected, text


def test_city_dropped_from_title():
    """Место показывается отдельной строкой — в названии оно лишнее."""
    assert parse("Стол, Нови-Сад, 3000 дин")["title"] == "Стол"
    assert parse("Продам шкаф, Земун поле")["title"] == "Шкаф"
    # а внутри фразы место остаётся: это часть названия
    assert parse("Диван в Новом Саде, 20000")["title"] == "Диван в Новом Саде"


def test_city_line_dropped_from_description():
    """«Нови Сад» отдельной строкой — это поле города, а не описание."""
    assert "Нови Сад" not in parse("Продам диван\nНови Сад")["description"]


# ── Аудит характеристик ─────────────────────────────────────────────────────
def test_number_before_the_word():
    """
    Этаж и размер пишут с любой стороны слова: «3 этаж» и «этаж 3»,
    «42 размер» и «размер 42». Ловилось только второе.
    """
    from app.core.tg_parse import extract_attributes
    assert extract_attributes("real-estate", "Квартира 65 м2, 3 этаж из 5")["floor"] == 3
    assert extract_attributes("real-estate", "Квартира, этаж 4")["floor"] == 4
    assert extract_attributes("real-estate", "Квартира 2/5 этаж")["floor"] == 2
    assert extract_attributes("fashion", "Кроссовки 42 размер")["size"] == "42"
    assert extract_attributes("fashion", "Джинсы 30 р-р")["size"] == "30"


def test_rooms_in_words_and_serbian():
    """«Однокомнатная», «trosoban», «3 собе» — так пишут не реже цифр."""
    from app.core.tg_parse import extract_rooms
    assert extract_rooms("Однокомнатная квартира") == 1
    assert extract_rooms("Trosoban stan 72 m2") == 3
    assert extract_rooms("Dvosoban stan Vracar") == 2
    assert extract_rooms("Стан од 3 собе") == 3
    assert extract_rooms("Полуторка 35 м2") == 1


def test_area_written_differently():
    """Дробная площадь, «квадраты», «kvadrata», слово впереди числа."""
    from app.core.tg_parse import extract_attributes
    for text in ("Квартира 65.5 м2", "65m2, Vracar"):
        assert extract_attributes("real-estate", text)["area_m2"] == 65, text
    assert extract_attributes("real-estate", "Stan 72 kvadrata")["area_m2"] == 72
    assert extract_attributes("real-estate", "Квартира площадью 80 квадратов")["area_m2"] == 80


def test_mileage_in_words():
    from app.core.tg_parse import extract_attributes
    assert extract_attributes("auto", "Прошёл 200 000 километров")["mileage_km"] == 200000
    assert extract_attributes("auto", "Пробег 145.000 км")["mileage_km"] == 145000


def test_memory_written_as_pair():
    """«16/512» — так пишут оперативную и встроенную память разом."""
    from app.core.tg_parse import extract_attributes
    attrs = extract_attributes("electronics", "Ноутбук 16/512")
    assert attrs["ram_gb"] == 16 and attrs["storage_gb"] == 512
    attrs = extract_attributes("electronics", "iPhone 15 8/256")
    assert attrs["ram_gb"] == 8 and attrs["storage_gb"] == 256


def test_battery_percent_in_words():
    from app.core.tg_parse import extract_attributes
    assert extract_attributes("electronics", "Батарея 89 процентов")["battery_health"] == 89
    assert extract_attributes("electronics", "Аккумулятор 100%")["battery_health"] == 100


# ── Аудит отсева и хвостов заголовка ────────────────────────────────────────
def test_negation_before_sold_mark():
    """
    «Не продано», «ещё актуально» — вещь на месте. Метка рядом ничего не
    меняет, а объявление снималось с публикации.
    """
    from app.core.tg_parse import looks_sold
    assert not looks_sold("Продам стол, не продано")
    assert not looks_sold("Ещё не продано")
    assert not looks_sold("Продаю, ещё актуально")
    assert not looks_sold("Продам диван (актуально)")
    assert not looks_sold("В наличии, пишите")
    # настоящие метки работают
    assert looks_sold("ПРОДАНО")
    assert looks_sold("Товар продан")
    assert looks_sold("Не актуально")
    assert looks_sold("неактуально")
    assert looks_sold("Забрали, спасибо")


def test_weak_spam_words_need_company():
    """
    Спам-фильтр удаляет объявление целиком, поэтому ошибка тут дороже
    всего. «Промокод на доставку» и «ставки не принимаю» — не спам.
    """
    from app.core.tg_parse import looks_like_spam
    assert not looks_like_spam("Продам велосипед, есть промокод на доставку")
    assert not looks_like_spam("Продам билеты на концерт, ставки не принимаю")
    assert not looks_like_spam("Продам стол, акция до конца недели")
    # а вместе — уже спам
    assert looks_like_spam("Заработок в интернете, инвестиции в крипту, бонус")
    assert looks_like_spam("ПОДПИСАТЬСЯ НА КАНАЛ, ваша подписка наша поддержка")


def test_all_tails_stripped_from_title():
    """
    Цена, место и условия сделки идут через запятую после названия — и
    вытесняли его за предел строки.
    """
    assert parse("Продам диван IKEA, 25000 динар, Земун, самовывоз, торг уместен")["title"] \
        == "Диван IKEA"
    assert parse("Продам стол, 3000 дин, недорого")["title"] == "Стол"
    assert parse("Куртка зимняя, размер S, Земун, срочно")["title"] == "Куртка зимняя"
    # то, что относится к вещи, остаётся
    assert parse("Стол письменный IKEA MICKE, отличное состояние")["title"] \
        == "Стол письменный IKEA MICKE"


def test_question_behind_a_greeting():
    """«Привет! Кто-нибудь продаёт диван?» — тот же вопрос в чат."""
    from app.core.title_rules import looks_like_question
    assert looks_like_question("Привет! Кто-нибудь продаёт диван недорого?")
    assert looks_like_question("Кто-нибудь знает хорошего мастера?")
    assert not looks_like_question("Добрый день! Продам стол 3000")


# ── Аудит характеристик и цены в описании ───────────────────────────────────
def test_floor_needs_a_whole_number():
    """
    Без границы слова правило хватало двойку из «65 м2» и объявляло её
    этажом — у квартиры без этажа он всё равно появлялся.
    """
    from app.core.tg_parse import extract_attributes
    assert extract_attributes("real-estate", "Квартира 65 м2\nЭтаж: 3")["floor"] == 3
    assert extract_attributes("real-estate", "Квартира 80 м2, 5-й этаж")["floor"] == 5
    assert "floor" not in extract_attributes("real-estate", "Квартира 100 м2 без этажа")


def test_attribute_lines_dropped_with_units():
    """
    Единицы содержат цифру и считались вторым числом: «Площадь: 65 м2»
    выглядело как два значения, и строка оставалась рядом с тем же полем.
    """
    from app.core.tg_parse import drop_attribute_lines, extract_attributes
    text = "Квартира 65 м2\nПлощадь: 65 м2\nЭтаж: 3\nХорошая планировка"
    out = drop_attribute_lines(text, extract_attributes("real-estate", text))
    assert "Площадь:" not in out and "Этаж:" not in out
    assert "Хорошая планировка" in out


def test_letter_size_line_dropped():
    """«Размер: M» чисел не содержит вовсе, и правило его не трогало."""
    from app.core.tg_parse import drop_attribute_lines, extract_attributes
    text = "Куртка\nРазмер: M\nЦвет чёрный"
    out = drop_attribute_lines(text, extract_attributes("fashion", text))
    assert "Размер:" not in out and "Цвет чёрный" in out
    # а строка с добавкой остаётся: в ней сказано больше
    text = "Куртка\nРазмер: M, но маломерит"
    assert "маломерит" in drop_attribute_lines(
        text, extract_attributes("fashion", text))


def test_delivery_cost_is_not_the_price():
    """«Доставка 500 динар» — цена доставки, а не вещи."""
    from app.core.tg_parse import extract_price
    assert extract_price("Стол\nЦена 3000\nДоставка 500 динар отдельно") == (3000, "RSD")
    assert extract_price("Продам стол 3000 дин, доставка 500 дин") == (3000, "RSD")
    # объявление с бесплатной доставкой свою цену не теряет
    assert extract_price("Диван 25000 динар, доставка бесплатно") == (25000, "RSD")


def test_labelled_price_without_currency():
    """«Цена 3000» без валюты — тоже цена, а не просто число в тексте."""
    from app.core.tg_parse import extract_price
    assert extract_price("Стол\nЦена 3000\nДоставка 500 динар")[0] == 3000


# ── Объявления по-сербски ───────────────────────────────────────────────────
# Половина ленты написана латиницей: сербский для этих чатов такой же
# рабочий язык, как русский.
def test_serbian_currency():
    """«1200 evra» ценой не считалось вовсе."""
    from app.core.tg_parse import extract_price
    assert extract_price("Prodajem stan, 1200 evra") == (1200, "EUR")
    assert extract_price("Golf 5, 3500 evra") == (3500, "EUR")
    assert extract_price("Prodajem sto, 3000 din") == (3000, "RSD")
    assert extract_price("Nov ranac, 2500 rsd") == (2500, "RSD")


def test_serbian_tails_stripped():
    """«hitno», «nikad korišćen», «povoljno» — то же, что «срочно» и «б/у»."""
    assert parse("Prodajem sto, 3000 din, Zemun, hitno")["title"] == "Sto"
    assert parse("Nov ranac, nikad korišćen, 2500 rsd")["title"] == "Nov ranac"
    assert parse("Prodajem Golf 5, 2008, 200000 km, 3500 evra")["title"] == "Golf 5"


def test_serbian_categories():
    from app.core.tg_classify import classify
    for text, expected in (
        ("Prodajem Golf 5, 2008, benzin", "auto"),
        ("Nov ranac Nike, nikad korišćen", "fashion"),
        ("Prodajem majicu, veličina M", "fashion"),
        ("Dajem časove engleskog jezika", "services"),
        ("Frizer, šišanje i farbanje kose", "services"),
        ("Selidbe i transport, kombi", "services"),
        ("Dečja kolica Chicco", "kids"),
        ("Mačka traži dom, sterilisana", "pets"),
        ("Veš mašina Bosch, ispravna", "home-garden"),
    ):
        assert classify(text)[0] == expected, text


def test_memory_stays_in_the_title():
    """«iPhone 11, 128gb» — так вещь и ищут, объём тут не лишний."""
    assert parse("iPhone 11, 128gb")["title"] == "iPhone 11, 128gb"
    # а пробег и площадь показываются полями
    assert parse("Квартира, 72 m2")["title"] == "Квартира"


# ── Объявления со списками ──────────────────────────────────────────────────
# В чатах часто продают несколько вещей разом: перечнем через дефис или
# по номерам. Валюту в таких списках почти никогда не пишут.
def test_phrase_with_colon_is_not_a_spec_line():
    """
    «Продам вещи пакетом: футболки» принималось за характеристику вида
    «поле: значение» и уходило в обход всех чисток — вместе с глаголом.
    """
    assert parse("Отдам даром: книги, посуда, игрушки")["title"] \
        == "Книги, посуда, игрушки"
    # настоящая характеристика по-прежнему заголовком не станет
    assert parse("Площадь: 72м2")["title"] is None


def test_price_from_list_line():
    """«- диван 25000» — сумма в конце строки перечня, валюты нет."""
    from app.core.tg_parse import extract_price
    assert extract_price("Продам:\n- диван 25000\n- стол 3000") == (25000, "RSD")
    assert parse("Продам:\n- диван 25000\n- стол 3000")["title"] == "Диван"


def test_year_is_not_a_price():
    """Год выпуска стоит в конце строки так же, как цена."""
    from app.core.tg_parse import extract_price
    assert extract_price("- Golf 5 2008")[0] is None
    assert parse("- Golf 5 2008")["title"] == "Golf 5 2008"


def test_number_kept_outside_lists():
    """
    Срезать число на конце можно только у строк перечня: в обычном
    названии это объём памяти или модель.
    """
    assert parse("iPhone 11 128")["title"] == "iPhone 11 128"
    assert parse("Умная лампа Xiaomi Mi Bedside Lamp 2")["title"] \
        == "Умная лампа Xiaomi Mi Bedside Lamp 2"


def test_ai_answer_schema_declared():
    """
    Форму ответа задаём на уровне запроса, а не просьбой в тексте: тогда
    модель не может вернуть ни пояснений, ни других полей.
    """
    from app.core.ai_title import CATEGORY_SCHEMA, TITLE_SCHEMA
    assert set(TITLE_SCHEMA["properties"]) == {"title", "summary"}
    assert TITLE_SCHEMA["required"] == ["title", "summary"]
    assert set(CATEGORY_SCHEMA["properties"]) == {"category"}


# ── Ограничения Telegram ────────────────────────────────────────────────────
def test_flood_wait_is_remembered(tmp_path, monkeypatch):
    """
    Пока действует запрет, повторный запрос считается новым нарушением, и
    ожидание растёт: с семи секунд до нескольких часов. Часовой заход по
    расписанию — ровно тот случай, поэтому срок держим на диске.
    """
    import app.core.tg_import as importer

    monkeypatch.setattr(importer, "FLOOD_PATH", tmp_path / "flood")
    assert importer.flood_wait_left() == 0
    importer.remember_flood(120)
    left = importer.flood_wait_left()
    assert 100 <= left <= 120
    importer.FLOOD_PATH.unlink()
    assert importer.flood_wait_left() == 0


def test_flood_file_broken_is_not_fatal(tmp_path, monkeypatch):
    """Испорченный файл не должен останавливать заход."""
    import app.core.tg_import as importer

    path = tmp_path / "flood"
    path.write_text("не число")
    monkeypatch.setattr(importer, "FLOOD_PATH", path)
    assert importer.flood_wait_left() == 0


# ── Водяные знаки и служебные аккаунты ──────────────────────────────────────
def test_watermark_filter_reports_missing_template():
    """
    Без образца отсев пропускает всё подряд, а снаружи выглядит рабочим.
    Молчать об этом нельзя: объявления агентств с чужим знаком идут в ленту.
    """
    from app.core.watermark import ready
    # функция должна отвечать честно, а не падать
    assert isinstance(ready(), bool)


def test_watermark_check_survives_any_image():
    from PIL import Image
    from app.core.watermark import has_watermark
    # маленькая, чёрно-белая, с прозрачностью — не должно падать ни на чём
    for mode, size in (("RGB", (100, 100)), ("L", (10, 10)), ("RGBA", (50, 40))):
        assert isinstance(has_watermark(Image.new(mode, size)), bool)


def test_service_account_cannot_be_logged_into():
    """У служебных аккаунтов чатов пароля нет — войти в них нельзя."""
    from app.core.auth import verify_password
    assert not verify_password("любой", "!")
    assert not verify_password("любой", None)
    assert not verify_password("", "!")
