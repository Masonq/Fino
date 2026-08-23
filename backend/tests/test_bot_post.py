"""
Вид объявления в чате.

Человек листает ленту глазами и решает за секунду — поэтому проверяем не
красоту, а порядок: название сверху, цена следом, служебное внизу.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bot.post_format import (  # noqa: E402
    BODY_LIMIT, MAX_CAPTION, build_caption, build_preview, money,
)


def test_price_reads_like_people_write_it():
    assert money(550, "EUR", False) == "550 €"
    assert money(25000, "RSD", False) == "25 000 RSD"
    assert money(None, None, True) == "Бесплатно"
    assert money(None, None, False) == "Цена не указана"
    # даром — даже если цена случайно осталась
    assert money(800, "RSD", True) == "Бесплатно"


def test_caption_order():
    """Название, цена, описание, автор, подпись — именно в таком порядке."""
    caption = build_caption(
        title="iPhone 13 Pro", price=550, currency="EUR", is_free=False,
        city="Земун", description="Состояние идеальное.",
        author_name="Максим", author_id=7, site_url="https://plonk.rs")

    lines = [l for l in caption.splitlines() if l.strip()]
    assert "iPhone 13 Pro" in lines[0]
    assert "550 €" in lines[1] and "Земун" in lines[1]
    assert "Состояние идеальное." in lines[2]
    assert "Продаёт" in lines[3]
    assert "PLONK" in lines[4]


def test_author_is_a_link():
    """Написать продавцу можно прямо из поста, не разыскивая через бота."""
    caption = build_caption(
        title="Стол", price=3000, currency="RSD", is_free=False, city=None,
        description="", author_name="Анна", author_id=42,
        site_url="https://plonk.rs")
    assert 'tg://user?id=42' in caption


def test_caption_fits_telegram_limit():
    """
    У поста с фотографией подпись не длиннее 1024 знаков — это правило
    Telegram, и превысить его значит не опубликовать вовсе.
    """
    caption = build_caption(
        title="Стол письменный IKEA MICKE", price=6000, currency="RSD",
        is_free=False, city="Земун", description="Очень длинно. " * 300,
        author_name="Максим", author_id=1, site_url="https://plonk.rs")
    assert len(caption) <= MAX_CAPTION


def test_long_text_cut_at_a_sentence():
    """Обрыв на полуслове выглядит небрежно."""
    body = ("Первое предложение здесь. Второе предложение тоже здесь. "
            + "Ещё немного текста. " * 60)
    caption = build_caption(
        title="Стол", price=None, currency=None, is_free=False, city=None,
        description=body, author_name="А", author_id=1,
        site_url="https://plonk.rs")
    shown = caption.splitlines()[3]
    assert shown.endswith((".", "…"))


def test_html_is_escaped():
    """В описании попадаются угловые скобки — пост не должен ломаться."""
    caption = build_caption(
        title="Стол <b>", price=None, currency=None, is_free=False, city=None,
        description="цена < 5000 & торг", author_name="А", author_id=1,
        site_url="https://plonk.rs")
    assert "&lt;" in caption and "&amp;" in caption


def test_preview_shows_the_topic():
    """
    Человек должен понимать, куда попадёт объявление, до того как нажмёт
    «Опубликовать», а не после.
    """
    preview = build_preview(
        title="Диван IKEA", price=25000, currency="RSD", is_free=False,
        city="Земун", description="Раскладной.", topic_title="МЕБЕЛЬ и всё для ДОМА")
    assert "МЕБЕЛЬ и всё для ДОМА" in preview


def test_body_dropped_when_it_repeats_the_title():
    """
    «Рюкзак 500 динар» под заголовком «Рюкзак» и ценой «500 RSD» —
    третья строка ничего не добавляет и выглядит небрежно.
    """
    caption = build_caption(
        title="Рюкзак", price=500, currency="RSD", is_free=False, city=None,
        description="Рюкзак 500 динар", author_name="А", author_id=1,
        site_url="https://plonk.rs")
    assert caption.count("Рюкзак") == 1

    # а описание с подробностями остаётся
    caption = build_caption(
        title="Рюкзак", price=500, currency="RSD", is_free=False, city="Земун",
        description="Бежевый, много карманов, почти новый",
        author_name="А", author_id=1, site_url="https://plonk.rs")
    assert "много карманов" in caption


def test_preview_tells_about_photos():
    """
    Показываем первый снимок, а прислать могли пять: без счётчика человек
    не поймёт, ушли ли остальные.
    """
    many = build_preview(
        title="Рюкзак", price=500, currency="RSD", is_free=False, city=None,
        description="", topic_title="Одежда • Обувь", photo_count=3)
    assert "Фотографий" in many and "3" in many

    none = build_preview(
        title="Стол", price=3000, currency="RSD", is_free=False, city=None,
        description="", topic_title="Мебель", photo_count=0)
    assert "Без фотографии" in none

    one = build_preview(
        title="Стол", price=3000, currency="RSD", is_free=False, city=None,
        description="", topic_title="Мебель", photo_count=1)
    assert "Фотографий" not in one and "Без фотографии" not in one


def test_city_shown_in_words():
    """
    Город хранится ключом «beograd», а в объявлении латиница выглядит
    чужеродно: людям показываем «Белград».
    """
    from app.bot.post_format import city_title

    assert city_title("beograd") == "Белград"
    assert city_title("novi-sad") == "Нови Сад"
    assert city_title(None) == ""
    # незнакомый ключ хотя бы приводим в приличный вид
    assert city_title("some-place") == "Some Place"
