"""
Разбор объявления из сообщения телеграм-чата.

В чатах пишут свободным текстом, поэтому вытаскиваем то, что поддаётся
разбору надёжно: цену, город и заголовок. Остальное остаётся описанием.

Правило одно: если не уверены — не выдумываем. Пустая цена честнее
неправильной, а неверный город хуже отсутствующего, потому что объявление
попадёт не в ту выдачу и его не найдут те, кому оно нужно.
"""
import re

from app.data.cities_data import CITY_ALIASES, DISTRICT_NAMES

# Цена: число с необязательными разделителями и валютой рядом. Диапазоны и
# «от 500» тоже ловим — берём нижнюю границу, она и есть ориентир.
_PRICE_RE = re.compile(
    # Перед числом может стоять что угодно — эмодзи, скобка, начало строки:
    # требование пробела отбрасывало «💰13 500 евро», и совпадала вторая
    # половина числа, то есть 500 вместо тринадцати с половиной тысяч.
    # Второй запрет не даёт зацепиться за хвост уже начатого числа.
    r"(?<![\w])(?<![\d][ .,\u00a0])(?:от\s*)?(\d{1,3}(?:[ .,\u00a0]\d{3})+|\d{2,7})\s*"
    r"(€|eur|евро|rsd|рсд|din(?:ara?)?|дин\.?|динар\w*|\$|usd)",
    re.I,
)
# «20к динар», «5k евро» — тысячи сокращают буквой, и без этого цена
# читалась как двадцать динаров
_PRICE_K_RE = re.compile(
    r"(?<![\w])(\d{1,4})\s*[кk]\s*(€|eur|евро|rsd|рсд|din\w*|дин\w*)", re.I)

_PRICE_AFTER_RE = re.compile(
    r"(?:цена|price|cena)\s*[:\-—]?\s*(\d{1,3}(?:[ .,\u00a0]\d{3})+|\d{2,7})",
    re.I,
)

CURRENCY_BY_WORD = {
    "€": "EUR", "eur": "EUR", "евро": "EUR",
    "rsd": "RSD", "рсд": "RSD", "din": "RSD", "dinar": "RSD", "dinara": "RSD",
    "дин": "RSD", "дин.": "RSD", "динар": "RSD", "динара": "RSD", "динаров": "RSD",
    "$": "USD", "usd": "USD",
}

# Мусор, из-за которого объявление лучше не переносить вовсе
_SPAM_MARKERS = (
    "подпишись", "подписывайтесь", "реклама", "розыгрыш", "казино",
    "заработок", "инвестиц", "крипт", "ставки", "промокод",
)


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_URL_RE = re.compile(r"https?://\S+|t\.me/\S+|www\.\S+", re.I)
_HASHTAG_RE = re.compile(r"#[\w\u0400-\u04ff]+", re.U)
# разметка Telegram: **жирный**, __курсив__, `моноширинный`
_MD_MARK_RE = re.compile(r"\*\*|__|`")
# Зачёркнутое убираем вместе с содержимым: так помечают старую цену, и от
# «~~500~~ 450€» после снятия одних знаков оставалось «500 450» — то есть
# полмиллиона вместо четырёхсот пятидесяти.
_STRIKE_RE = re.compile(r"~~.*?~~", re.S)
# «Стол 3000 RSD» — цена уже вынесена в поле, в заголовке она лишняя
_TITLE_PRICE_RE = re.compile(
    r"\s*[—-]?\s*\d[\d .,\u00a0]*\s*(?:€|eur|евро|rsd|рсд|din\w*|дин\w*|\$|usd)\.?\s*$", re.I)
_SPEC_RE = re.compile(r"^[\w \u0400-\u04ff]{3,24}\s*[:：]\s*\S")
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u27BF\uFE0F\u2B00-\u2BFF]+"
)


def clean_text(text: str) -> str:
    """
    Приводит сообщение к виду, годному для описания.

    В чатах к тексту прикладывают гроздь хэштегов для поиска внутри
    Telegram и ссылки на карты — у нас и то, и другое бесполезно: поиск
    свой, а ссылка в описании ведёт наружу. Заодно из-за хэштегов слова
    слипались с решёткой, и «#Vozdovac» не опознавался как район.
    """
    # ссылка вида [Bilećka](https://...) — оставляем подпись, адрес убираем
    text = _STRIKE_RE.sub(" ", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    # звёздочки и подчёркивания — разметка Telegram, у нас описание обычным
    # текстом, и «**Стол 3000 RSD**» показывалось со звёздочками
    text = _MD_MARK_RE.sub("", text)

    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        without_tags = _HASHTAG_RE.sub(" ", line)
        # строка из одних хэштегов не несёт ничего, кроме поиска в Telegram
        if line.strip() and not without_tags.strip():
            continue
        lines.append(re.sub(r"[ \t]+", " ", without_tags).strip())

    # схлопываем пустые строки, оставшиеся от вырезанного
    out, blank = [], False
    for line in lines:
        if not line:
            if blank or not out:
                continue
            blank = True
        else:
            blank = False
        out.append(line)
    return "\n".join(out).strip()


def searchable_text(text: str) -> str:
    """
    Текст для распознавания города и категории.

    Отличается от описания тем, что хэштеги здесь не выбрасываются, а
    раскрываются в слова: «#Vozdovac #квартира» — часто единственное место,
    где названы район и предмет, и без них объявление теряет и то, и другое.
    """
    text = _STRIKE_RE.sub(" ", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    text = _MD_MARK_RE.sub(" ", text)
    return re.sub(r"#(?=[\w\u0400-\u04ff])", " ", text)


def _to_number(raw: str) -> float | None:
    """«1 200» и «1.200» — это тысяча двести, а не 1.2. Разделители убираем."""
    cleaned = re.sub(r"[ .,\u00a0]", "", raw)
    try:
        value = float(cleaned)
    except ValueError:
        return None
    # Отсекаем годы и телефоны: цена в 2016 почти всегда год выпуска
    if value < 3 or value > 5_000_000:
        return None
    return value


def extract_price(text: str) -> tuple[float | None, str | None]:
    m = _PRICE_K_RE.search(text)
    if m:
        value = _to_number(m.group(1))
        if value is not None:
            return value * 1000, CURRENCY_BY_WORD.get(
                m.group(2).lower(), "RSD" if m.group(2).lower().startswith(("d", "д")) else None)

    m = _PRICE_RE.search(text)
    if m:
        value = _to_number(m.group(1))
        if value is not None:
            return value, CURRENCY_BY_WORD.get(m.group(2).lower())
    m = _PRICE_AFTER_RE.search(text)
    if m:
        value = _to_number(m.group(1))
        if value is None:
            return None, None
        # Валюта не названа. До тысячи это почти наверняка евро: в динарах
        # такими суммами не оперируют. Выше — не угадываем: 10000 € и
        # 10000 динаров отличаются в сто раз, и промах в любую сторону
        # выглядит обманом. Цену не ставим, сумма остаётся в описании.
        return (value, "EUR") if value <= 1000 else (None, None)
    return None, None


def extract_city(text: str) -> str | None:
    """
    Город по упоминанию в тексте.

    Берём первое совпадение по длинному написанию: «Нови Сад» должен
    выигрывать у «Сад», иначе объявление уедет в другой город.
    """
    # Переводы строк и повторные пробелы схлопываем: город часто стоит
    # последней строкой, и с «\n» перед ним совпадение не находилось.
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    best = None
    for alias, slug in CITY_ALIASES.items():
        if f" {alias} " in low or f" {alias}," in low or f" {alias}." in low:
            if best is None or len(alias) > best[0]:
                best = (len(alias), slug)
    return best[1] if best else None


def make_title(text: str, limit: int = 70) -> str | None:
    """
    Заголовок из первой содержательной строки.

    Отдельного заголовка в чатах нет, поэтому берём начало текста —
    так же, как его читает человек в ленте чата.
    """
    fallback = None
    for raw in text.splitlines():
        line = _EMOJI_RE.sub("", raw).strip(" \t•·—-*#")
        # пропускаем строки из одних эмодзи, решёток и знаков
        if len(re.sub(r"[^\w]", "", line, flags=re.UNICODE)) < 8:
            continue
        line = re.sub(r"\s+", " ", line)
        # «Площадь: 72м2» — характеристика, а не название; заголовком берём
        # только если ничего лучше в тексте не нашлось
        if _SPEC_RE.match(line):
            fallback = fallback or line
            continue
        line = _TITLE_PRICE_RE.sub("", line).strip(" ,.;:-—")
        if not line:
            continue
        if len(line) <= limit:
            return line
        cut = line[:limit].rsplit(" ", 1)[0]
        return (cut or line[:limit]).rstrip(" ,.;:") + "…"
    return fallback


_AREA_RE = re.compile(r"(\d{2,4})\s*(?:м2|м²|кв\.?\s*м|m2|m²)", re.I)
_ROOMS_WORD = {
    "однушк": 1, "гарсоньер": 1, "студи": 1,
    "двушк": 2, "двухкомнат": 2, "трешк": 3, "трёшк": 3, "трехкомнат": 3,
    "четырёхкомнат": 4, "четырехкомнат": 4,
}
_ROOMS_NUM_RE = re.compile(r"(\d)\s*-?\s*(?:комнат|комн\.?|соб[аы])", re.I)
_ROOMS_PLUS_RE = re.compile(r"гостин\w*\s*\+\s*(\d)\s*комнат", re.I)


def extract_rooms(text: str) -> int | None:
    """
    Число комнат. «Гостиная + 2 комнаты» — это трёшка: так считают в
    объявлениях, и покупатель ищет именно по этому числу.
    """
    low = text.lower()
    m = _ROOMS_PLUS_RE.search(low)
    if m:
        return int(m.group(1)) + 1
    for word, count in _ROOMS_WORD.items():
        if word in low:
            return count
    m = _ROOMS_NUM_RE.search(low)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 9 else None
    return None


def extract_district(text: str) -> str | None:
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    best = None
    for alias, name in DISTRICT_NAMES.items():
        if f" {alias} " in low or f" {alias}," in low or f" {alias}." in low or f" {alias}/" in low:
            if best is None or len(alias) > best[0]:
                best = (len(alias), name)
    return best[1] if best else None


def compose_title(category_slug: str | None, text: str) -> str | None:
    """
    Собирает заголовок из фактов, а не из первой строки.

    Для недвижимости строка из текста почти всегда бесполезна: люди
    начинают с хэштегов или с характеристик, и получалось «гостиная + 2
    комнаты». Комнаты, площадь и район — то, по чему квартиру и узнают.
    """
    if category_slug != "real-estate":
        return None

    rooms = extract_rooms(text)
    area = _AREA_RE.search(text)
    district = extract_district(text)

    if rooms:
        head = "Студия" if rooms == 1 and "студи" in text.lower() else f"{rooms}-комнатная квартира"
    elif area:
        head = "Квартира"
    else:
        return None

    parts = [head]
    if area:
        parts.append(f"{area.group(1)} м²")
    if district:
        parts.append(district)
    return ", ".join(parts)


def looks_like_spam(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _SPAM_MARKERS)


def drop_duplicates(description: str, price: float | None, city: str | None) -> str:
    """
    Убирает из описания то, что уже вынесено в поля объявления.

    Цена и город показываются отдельными строками наверху, и повторять их в
    описании незачем — читателю приходится дважды разбирать одно и то же.
    Убираем только строки, которые ничего, кроме этого, не сообщают:
    «Цена 10 000» уходит, а «1100€ (аренда) + депозит» остаётся, потому что
    про депозит больше нигде не сказано.
    """
    if price is None and not city:
        return description

    price_only = re.compile(
        r"^(?:цена|price|cena)?\s*[:\-—]?\s*\d[\d .,\u00a0]*\s*"
        r"(?:€|eur|евро|rsd|рсд|din\w*|дин\w*|\$|usd)?\s*$", re.I)

    kept = []
    for line in description.splitlines():
        bare = _EMOJI_RE.sub("", line).strip(" \t•·—-*📍")
        if not bare:
            kept.append(line)
            continue
        if price is not None and price_only.match(bare):
            continue
        # строка целиком про место: «Белград, Стари Град»
        if city and extract_city(bare) == city and len(bare) <= 40 and not any(
            ch.isdigit() for ch in bare
        ):
            continue
        kept.append(line)

    out, blank = [], False
    for line in kept:
        if not line.strip():
            if blank or not out:
                continue
            blank = True
        else:
            blank = False
        out.append(line)
    return "\n".join(out).strip()


def drop_title_line(description: str, title: str | None) -> str:
    """
    Убирает первую строку, если из неё сделан заголовок.

    Заголовок стоит над описанием, и повторять его сразу под собой —
    только тратить экран.
    """
    if not title:
        return description
    lines = description.splitlines()
    for i, line in enumerate(lines[:3]):
        bare = _EMOJI_RE.sub("", line).strip(" \t•·—-*")
        stripped = _TITLE_PRICE_RE.sub("", bare).strip(" ,.;:-—")
        if stripped and (stripped == title or bare == title or title.startswith(stripped[:40])):
            del lines[i]
            break
    return "\n".join(lines).strip()


def parse(text: str) -> dict:
    """Сводит разбор воедино. Ничего не додумывает: не нашли — оставили пустым."""
    description = clean_text(text)
    price, currency = extract_price(description)
    city = extract_city(searchable_text(text))
    title = make_title(description)
    return {
        "title": title,
        "description": drop_title_line(drop_duplicates(description, price, city), title),
        "price": price,
        "currency": currency or "EUR",
        # город и категорию ищем по тексту с раскрытыми хэштегами
        "city": city,
        "searchable": searchable_text(text),
    }
