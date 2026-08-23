"""
Куда публиковать объявление в чате-партнёре.

Смысл этой таблицы в том, что человек выбирает вещь, а не ветку. Значит
подбор должен быть верным без его участия — иначе бот только добавит
работы владельцу чата.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.partner_chats import (  # noqa: E402
    BARAHOLKA_BELGRAD, topic_for, topic_name, topics_of,
)
from app.core.tg_classify import classify, classify_sub  # noqa: E402
from app.core.tg_parse import parse  # noqa: E402

CHAT = BARAHOLKA_BELGRAD


def pick(text: str) -> str | None:
    """Ветка, которую выберет бот для такого объявления."""
    parsed = parse(text)
    category, _ = classify(text)
    topic = topic_for(
        CHAT, category,
        sub=classify_sub(category or "", text),
        is_free=parsed["is_free"],
        is_wanted=text.lower().startswith(("куплю", "ищу")),
    )
    return topic_name(CHAT, topic)


def test_things_go_to_their_topics():
    assert pick("Продам диван IKEA раскладной, 25000 динар") == "МЕБЕЛЬ и всё для ДОМА"
    assert pick("iPhone 13 Pro 256gb, 550 евро") == "Электроника"
    assert pick("Кроссовки Adidas Samba 42 размер") == "Одежда, обувь"
    assert pick("Сдаю квартиру 65 м2 на Врачаре, 450 евро") == "Недвижимость продам/сдам"
    assert pick("Продам Volkswagen Golf 5, пробег 200000") == "Авто / мото транспорт"


def test_what_you_do_beats_what_you_sell():
    """
    «Отдам даром» и «Куплю» — про действие, а не про вещь. Диван в дар
    ждут в ветке подарков, а не среди мебели на продажу.
    """
    assert pick("Отдам даром детские вещи 74-80 размер") == "Отдам даром"
    assert pick("Диван в добрые руки, самовывоз") == "Отдам даром"
    assert pick("Куплю earpods 3 поколения") == "КУПЛЮ / ИЩУ"


def test_subcategory_is_more_precise():
    """У партнёра услуги красоты отделены — стрижке среди сантехников не место."""
    assert pick("Стрижка и окрашивание волос, выезд на дом") == "Услуги красоты"
    assert pick("Маникюр, наращивание ресниц") == "Услуги красоты"
    assert pick("Ремонт бойлеров, выезд мастера") == "Услуги прочее"


def test_unknown_goes_to_the_common_topic():
    """Лучше общая ветка, чем чужая: раздела может не быть у партнёра."""
    assert pick("Велосипед Merida 27.5, рама M") == "Прочие товары"
    assert topic_name(CHAT, topic_for(CHAT, None)) == "Прочие товары"


def test_topics_listed_for_manual_choice():
    """Когда подбор не годится, человек выбирает сам — из настоящих веток."""
    names = dict(topics_of(CHAT))
    assert len(names) >= 10
    assert "Прочие товары" in names.values()
