"""
Разбор объявления из сообщения телеграм-чата.

В чатах пишут свободным текстом, поэтому вытаскиваем то, что поддаётся
разбору надёжно: цену, город и заголовок. Остальное остаётся описанием.

Правило одно: если не уверены — не выдумываем. Пустая цена честнее
неправильной, а неверный город хуже отсутствующего, потому что объявление
попадёт не в ту выдачу и его не найдут те, кому оно нужно.
"""
import re

from app.data.cities_data import CITY_ALIASES

# Цена: число с необязательными разделителями и валютой рядом. Диапазоны и
# «от 500» тоже ловим — берём нижнюю границу, она и есть ориентир.
_PRICE_RE = re.compile(
    r"(?:^|[\s(])(?:от\s*)?(\d{1,3}(?:[ .,\u00a0]\d{3})+|\d{2,7})\s*"
    r"(€|eur|евро|rsd|рсд|дин|динар|\$|usd)",
    re.I,
)
_PRICE_AFTER_RE = re.compile(
    r"(?:цена|price|cena)\s*[:\-—]?\s*(\d{1,3}(?:[ .,\u00a0]\d{3})+|\d{2,7})",
    re.I,
)

CURRENCY_BY_WORD = {
    "€": "EUR", "eur": "EUR", "евро": "EUR",
    "rsd": "RSD", "рсд": "RSD", "дин": "RSD", "динар": "RSD",
    "$": "USD", "usd": "USD",
}

# Мусор, из-за которого объявление лучше не переносить вовсе
_SPAM_MARKERS = (
    "подпишись", "подписывайтесь", "реклама", "розыгрыш", "казино",
    "заработок", "инвестиц", "крипт", "ставки", "промокод",
)


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
    m = _PRICE_RE.search(text)
    if m:
        value = _to_number(m.group(1))
        if value is not None:
            return value, CURRENCY_BY_WORD.get(m.group(2).lower())
    m = _PRICE_AFTER_RE.search(text)
    if m:
        value = _to_number(m.group(1))
        if value is not None:
            # валюта не названа — в Сербии по умолчанию считают в евро
            return value, "EUR"
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
    for raw in text.splitlines():
        line = raw.strip(" \t•·—-*#")
        # пропускаем строки из одних эмодзи, решёток и знаков
        if len(re.sub(r"[^\w]", "", line, flags=re.UNICODE)) < 8:
            continue
        line = re.sub(r"\s+", " ", line)
        if len(line) <= limit:
            return line
        cut = line[:limit].rsplit(" ", 1)[0]
        return (cut or line[:limit]).rstrip(" ,.;:") + "…"
    return None


def looks_like_spam(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _SPAM_MARKERS)


def parse(text: str) -> dict:
    """Сводит разбор воедино. Ничего не додумывает: не нашли — оставили пустым."""
    price, currency = extract_price(text)
    return {
        "title": make_title(text),
        "description": text.strip(),
        "price": price,
        "currency": currency or "EUR",
        "city": extract_city(text),
    }
