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
