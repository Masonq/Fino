"""
Как выглядит объявление в чате.

Отдельно от самого бота: вид поста обсуждают с владельцем чата, меняют
и переделывают, а работа бота при этом не трогается.

Главное правило вида — человек листает ленту глазами и решает за
секунду. Поэтому первая строка это название вещи, вторая цена и место,
а описание идёт ниже: его читают, только если первые две строки
зацепили.
"""
from html import escape

# Подпись под постом. Одна строка мелким текстом, без картинок и
# восклицаний: навязчивая реклама — первое, за что владелец чата
# попросит убрать бота.
SIGNATURE = 'Опубликовано через <a href="{site}">PLONK</a> — барахолка Сербии'

# У сообщения с фотографией подпись не длиннее 1024 знаков — это
# ограничение Telegram, а не наше. Оставляем запас на служебные строки.
MAX_CAPTION = 1024
BODY_LIMIT = 600


def money(price: float | None, currency: str | None, is_free: bool) -> str:
    """Цена так, как её читают: без копеек и с пробелом между тысячами."""
    if is_free:
        return "Бесплатно"
    if price is None:
        return "Цена не указана"
    whole = f"{int(price):,}".replace(",", " ")
    sign = "€" if (currency or "").upper() == "EUR" else "RSD"
    return f"{whole} {sign}"


def _shorten(text: str, limit: int) -> str:
    """
    Подрезает описание по границе предложения.

    Обрыв на полуслове выглядит небрежно, а полный текст всё равно
    открывается на нашей странице по кнопке.
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in (". ", "! ", "? ", "\n"):
        edge = cut.rfind(mark)
        if edge > limit * 0.5:
            return cut[:edge + 1].strip()
    return cut.rsplit(" ", 1)[0].strip() + "…"


def build_caption(*, title: str, price: float | None, currency: str | None,
                  is_free: bool, city: str | None, description: str | None,
                  author_name: str, author_id: int | None,
                  site_url: str) -> str:
    """
    Собирает подпись к посту.

    Автор — ссылкой на его телеграм: написать ему можно прямо отсюда, не
    разыскивая через профиль бота.
    """
    lines = [f"<b>{escape(title)}</b>"]

    second = f"<b>{escape(money(price, currency, is_free))}</b>"
    if city:
        second += f" · {escape(city)}"
    lines.append(second)

    body = _shorten(description or "", BODY_LIMIT)
    if body:
        lines.append("")
        lines.append(escape(body))

    lines.append("")
    if author_id:
        who = f'<a href="tg://user?id={author_id}">{escape(author_name)}</a>'
    else:
        who = escape(author_name)
    lines.append(f"Продаёт: {who}")
    lines.append(SIGNATURE.format(site=escape(site_url)))

    caption = "\n".join(lines)
    if len(caption) > MAX_CAPTION:
        # Подрезаем ещё раз, уже жёстче: служебные строки важнее описания.
        lines[3] = escape(_shorten(body, BODY_LIMIT // 2))
        caption = "\n".join(lines)
    return caption


def build_preview(*, title: str, price: float | None, currency: str | None,
                  is_free: bool, city: str | None, description: str | None,
                  topic_title: str | None) -> str:
    """
    Что бот показывает человеку перед публикацией.

    Показываем и ветку: человек должен понимать, куда попадёт объявление,
    до того как нажмёт «Опубликовать», а не после.
    """
    lines = [
        "<b>Так это будет выглядеть в чате:</b>",
        "",
        f"<b>{escape(title)}</b>",
        f"<b>{escape(money(price, currency, is_free))}</b>"
        + (f" · {escape(city)}" if city else ""),
    ]
    body = _shorten(description or "", BODY_LIMIT)
    if body:
        lines += ["", escape(body)]
    if topic_title:
        lines += ["", f"Ветка: <b>{escape(topic_title)}</b>"]
    return "\n".join(lines)
