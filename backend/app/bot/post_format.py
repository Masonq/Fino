"""
Как выглядит объявление в чате.

Отдельно от самого бота: вид поста обсуждают с владельцем чата, меняют
и переделывают, а работа бота при этом не трогается.

Главное правило вида — человек листает ленту глазами и решает за
секунду. Поэтому первая строка это название вещи, вторая цена и место,
а описание идёт ниже: его читают, только если первые две строки
зацепили.
"""
import re
from html import escape

# Подпись под постом. Одна строка мелким текстом, без картинок и
# восклицаний: навязчивая реклама — первое, за что владелец чата
# попросит убрать бота.
SIGNATURE = 'Опубликовано через <a href="{site}">PLONK</a> — объявления Сербии'

# У сообщения с фотографией подпись не длиннее 1024 знаков — это
# ограничение Telegram, а не наше. Оставляем запас на служебные строки.
MAX_CAPTION = 1024
BODY_LIMIT = 600


# Город хранится ключом («beograd»), а показывать его надо так, как
# люди пишут: латиница в русском объявлении выглядит чужеродно.
CITY_TITLES = {
    "beograd": "Белград",
    "novi-sad": "Нови Сад",
    "nis": "Ниш",
    "kragujevac": "Крагуевац",
    "subotica": "Суботица",
    "zrenjanin": "Зренянин",
    "pancevo": "Панчево",
    "cacak": "Чачак",
    "novi-pazar": "Нови Пазар",
    "kraljevo": "Кралево",
}


def city_title(city: str | None) -> str:
    if not city:
        return ""
    return CITY_TITLES.get(city, city.replace("-", " ").title())


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


# Строки, которым в нашем посте не место.
#
# В перенесённых объявлениях у продавцов свои хвосты: приглашение в свой
# канал, «полная информация тут», ссылка на другой чат, повтор цены,
# которая у нас и так стоит второй строкой. Всё это либо уводит людей из
# нашего чата, либо занимает место впустую.
_PROMO_LINE_RE = re.compile(
    r"(t\.me/|https?://|@[a-z0-9_]{4,}"
    r"|больше\s+(объявлен|в\s+канале|тут|здесь)"
    r"|подпис(ыв|ат|ка|ыв)"
    r"|наш\s+(канал|чат|телеграм)"
    r"|подробн\w*\s+(тут|здесь|в\s+)"
    r"|полн\w*\s+информац\w*"
    r"|все\s+объявлен\w*"
    r"|пишите\s+в\s+(лич|дир)"
    r"|vise\s+na\s+|više\s+na\s+|prati\w*\s+nas)",
    re.I)
# Строка, состоящая только из цены: «Цена 12.200€», «12200 rsd».
_PRICE_LINE_RE = re.compile(
    r"^(цена|cena|price)?\s*[:\-—]?\s*\d[\d\s.,\u00a0]*"
    r"\s*(€|\$|eur|евро|e|rsd|рсд|дин\w*|din\w*)?\s*"
    # Хвост в скобках — «(возможен небольшой торг)», «(fiksno)»: он про
    # цену, а цена у нас и так стоит второй строкой.
    r"(\([^)]*\))?\s*(торг\w*|fiksno)?$", re.I)


def strip_promo(text: str) -> str:
    """
    Убирает из описания чужие приглашения и повтор цены.

    Разбираем по строкам, а не по всему тексту: выбросить надо ровно
    строку с приглашением, а не весь абзац вокруг неё. Двоеточие в конце
    оставшейся строки («Полная информация тут:» ушла, а «Пробег:»
    осталась) не трогаем — это нормальная строка характеристики.
    """
    kept = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if _PROMO_LINE_RE.search(stripped):
            continue
        if _PRICE_LINE_RE.match(stripped):
            continue
        kept.append(stripped)
    # Схлопываем пустые строки, оставшиеся от выброшенных.
    out, blank = [], False
    for line in kept:
        if not line:
            blank = True
            continue
        if out and blank:
            out.append("")
        blank = False
        out.append(line)
    return "\n".join(out).strip()


def _useful_body(title: str, description: str | None) -> str:
    """
    Что из описания стоит показывать под заголовком.

    В посте заголовок и так стоит сверху крупным, а цена — второй
    строкой. Если в описании нет ничего сверх этого — «Рюкзак 500
    динар» под заголовком «Рюкзак» и ценой «500 RSD», — показывать его
    незачем: строка занимает место и выглядит небрежно.
    """
    body = strip_promo(description or "")
    if not body:
        return ""

    # Сравниваем по существу: убираем цену, знаки и регистр. Останется
    # ли что-то, чего нет в заголовке?
    import re

    def bare(text: str) -> set[str]:
        clean = re.sub(r"\d[\d\s.,]*\s*"
                       r"(€|\$|eur|евро|evr[ao]|rsd|рсд|дин\w*|din\w*)?",
                       " ", text.lower().replace("ё", "е"))
        return {w[:5] for w in re.findall(r"[\w-]{3,}", clean)}

    extra = bare(body) - bare(title)
    return body if extra else ""


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
        second += f" · {escape(city_title(city))}"
    lines.append(second)

    body = _shorten(_useful_body(title, description), BODY_LIMIT)
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


def build_sold_caption(*, title: str, price: float | None,
                       currency: str | None, is_free: bool,
                       city: str | None, description: str | None,
                       site_url: str) -> str:
    """
    Пост после пометки «продано».

    Собираем заново, а не правим готовый: разметка в тексте уже
    развёрнута, и попытка приписать строку сверху рвала ссылки.

    Автора убираем: писать ему больше незачем, а имя в проданном
    объявлении только собирает лишние сообщения.
    """
    from app.bot.emoji import emoji

    lines = [
        f"{emoji('done')} <b>ПРОДАНО</b>",
        "",
        f"<s>{escape(title)}</s>",
        f"<s>{escape(money(price, currency, is_free))}</s>"
        + (f" · {escape(city_title(city))}" if city else ""),
    ]
    body = _shorten(_useful_body(title, description), BODY_LIMIT // 2)
    if body:
        lines += ["", escape(body)]
    lines += ["", SIGNATURE.format(site=escape(site_url))]
    return "\n".join(lines)


def build_preview(*, title: str, price: float | None, currency: str | None,
                  is_free: bool, city: str | None, description: str | None,
                  topic_title: str | None, photo_count: int = 0,
                  fixes: list | None = None, to_site: bool = True) -> str:
    """
    Что бот показывает человеку перед публикацией.

    Показываем и ветку: человек должен понимать, куда попадёт объявление,
    до того как нажмёт «Опубликовать», а не после.
    """
    lines = [
        "<b>Вот что получилось:</b>",
        "",
        f"<b>{escape(title)}</b>",
        f"<b>{escape(money(price, currency, is_free))}</b>"
        + (f" · {escape(city_title(city))}" if city else ""),
    ]
    body = _shorten(_useful_body(title, description), BODY_LIMIT)
    if body:
        lines += ["", escape(body)]
    if fixes:
        # Показываем, что поправили: человек должен видеть, что
        # получилось, и успеть возразить.
        shown = ", ".join(f"{was} → <b>{now}</b>" for was, now in fixes[:3])
        lines += ["", f"Поправил опечатку: {shown}"]

    # Куда уйдёт объявление, человек должен знать до нажатия, а не
    # после: он публикует в чат, а оно попадает ещё и на сайт — узнать
    # об этом задним числом неприятно.
    if topic_title and to_site:
        lines += ["", "<b>Опубликую в двух местах:</b>",
                  f"├ чат — ветка «{escape(topic_title)}»",
                  "└ сайт PLONK — там объявление найдут поиском"]
    elif topic_title:
        lines += ["", "<b>Опубликую только в чат</b>",
                  f"└ ветка «{escape(topic_title)}»"]
    # Снимки показываются рядом целиком, поэтому счётчик нужен только
    # чтобы подтвердить: столько и уйдёт.
    if photo_count > 1:
        lines.append(f"\nФотографий: <b>{photo_count}</b> — уйдут все")
    elif photo_count == 0:
        lines.append("\nБез фотографии — такие объявления почти не смотрят")
    return "\n".join(lines)
