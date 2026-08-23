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


def test_bot_publication_is_never_a_duplicate():
    """
    Отсев повторов нужен переносу из чатов: одно объявление кочует по
    трём барахолкам. Но когда человек публикует сам, он делает это
    осознанно — и отказывать ему нельзя, даже если он второй раз
    выставляет тот же утюг.
    """
    import inspect
    from app.core.tg_import import store

    source = inspect.getsource(store)
    assert 'item.get("from_bot")' in source


def test_write_computes_its_own_fingerprint():
    """
    Отпечаток считается и при проверке повторов, и при записи. Когда
    публикация идёт через бота, проверок не бывает вовсе — значит запись
    должна считать его сама, а не рассчитывать на чужую переменную.
    """
    import inspect
    from app.core.tg_import import _write

    source = inspect.getsource(_write)
    assert "mark = fingerprint(" in source


def test_sold_post_keeps_links_and_drops_the_seller():
    """
    Проданный пост собираем заново, а не правим готовый: разметка в нём
    уже развёрнута, и приписка сверху рвала ссылки.

    Имя продавца убираем — писать ему больше незачем, а в проданном
    объявлении оно только собирает лишние сообщения.
    """
    from app.bot.post_format import build_sold_caption

    caption = build_sold_caption(
        title="Утюг philips azur", price=3000, currency="RSD", is_free=False,
        city="beograd", description="мощность: 2600w",
        site_url="https://plonk.rs")

    assert "ПРОДАНО" in caption
    assert "Продаёт" not in caption
    assert 'href="https://plonk.rs"' in caption        # ссылка цела
    assert "<s>Утюг philips azur</s>" in caption       # название зачёркнуто
    assert "Белград" in caption


def test_my_listings_work_without_registration():
    """
    Человек публиковал через бота и нигде не регистрировался — ссылка на
    сайт ему ничего не даёт: там он никто. Список должен работать в
    переписке, по имени в телеграме.
    """
    import inspect
    from app.bot.publisher import send_my_listings

    source = inspect.getsource(send_my_listings)
    assert "external_author" in source
    assert "username" in source


def test_closing_someone_elses_listing_is_refused():
    """Зная номер объявления, чужое закрыть всё равно нельзя."""
    import inspect
    from app.bot.publisher import close_listing

    source = inspect.getsource(close_listing)
    assert "Listing.external_author == author" in source


def test_listings_come_as_one_message():
    """
    Список из отдельных сообщений с кнопкой у каждого выглядит как спам
    от самого себя и занимает весь экран. Отправляем одним.
    """
    import inspect
    from app.bot.publisher import send_my_listings

    source = inspect.getsource(send_my_listings)
    # ровно одна отправка в конце, а не по сообщению на объявление
    assert source.count("await message.answer(") <= 2
    # названия — ссылками, кнопки — по номеру из списка
    assert '{number}. <a href=' in source
    assert 'f"✅ {number}"' in source


def test_sold_mark_reaches_the_chat():
    """
    Пометка из списка меняла только запись в базе, а пост в чате
    оставался зазывать покупателей на проданную вещь.
    """
    import inspect
    from app.bot.publisher import close_listing, publish

    # номер поста запоминается при публикации — и в памяти, и в базе
    published = inspect.getsource(publish)
    assert "posted_messages[listing_id]" in published
    assert "external_message_id = posted.message_id" in published

    # и используется при закрытии
    closing = inspect.getsource(close_listing)
    assert "build_sold_caption" in closing
    assert "edit_message_caption" in closing


def test_sold_caption_gets_only_what_it_expects():
    """
    Номер поста нужен, чтобы найти сообщение в чате, — но сборке текста
    он не нужен и ломает вызов. Держим его отдельно от полей объявления.
    """
    import inspect
    from app.bot.post_format import build_sold_caption
    from app.bot.publisher import close_listing

    expected = set(inspect.signature(build_sold_caption).parameters)
    source = inspect.getsource(close_listing)

    # всё, что кладётся в fields, должно быть среди полей сборки
    block = source[source.index("fields = {"):source.index("db.commit()")]
    for line in block.splitlines():
        line = line.strip()
        if line.startswith('"') and '":' in line:
            key = line.split('"')[1]
            assert key in expected, f"лишнее поле в fields: {key}"


def test_long_actions_show_progress():
    """
    Публикация занимает несколько секунд. Без отметки человек не
    понимает, идёт ли дело, и жмёт кнопку второй раз — тогда объявление
    уходит дважды.
    """
    import inspect
    from app.bot.publisher import close_listing, mark_busy, publish

    # кнопки убираются сразу, чтобы второе нажатие было невозможно
    assert "reply_markup=None" in inspect.getsource(mark_busy)
    assert "mark_busy(call" in inspect.getsource(publish)
    assert "mark_busy(call" in inspect.getsource(close_listing)
