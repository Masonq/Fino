"""
Цена нейросетью — там, где правила путаются.

В описании чего только нет: размер «EUR 36», объём памяти «8 GB», год
выпуска, старая цена «покупал за 12000», цена за сутки аренды. Правила
берут первое подходящее число и промахиваются — куртка становится за
семьдесят динар, а веб-камера за тысячу евро.

Модель видит смысл: она отличит «продаю за 2000» от «размер 37» и
«батарея 99%». Но зовём её не всегда — только когда правила дали
подозрительный ответ или не дали никакого. Так на неё уходит малая
часть объявлений, и бесплатных пределов хватает.

Ответ модели проверяем: цена должна быть в тексте и быть похожей на
цену. Модель может придумать число, и без проверки мы записали бы
выдумку вместо пустоты — а это хуже.
"""
import json
import logging
import re

log = logging.getLogger(__name__)

# Цена, при которой стоит усомниться. Вещь дешевле сотни динар — это
# почти всегда не цена, а размер, объём или год.
TOO_CHEAP_RSD = 100
TOO_CHEAP_EUR = 3

PROMPT = """Найди цену в объявлении с барахолки Белграда.

Ответь строго JSON: {{"price": число или null, "currency": "RSD" | "EUR"}}

Правила:
- Бери цену, за которую продают сейчас. Не бери старую цену
  («покупал за 12000»), цену за сутки аренды, размер, объём памяти,
  год выпуска, ёмкость батареи, проценты.
- Если цена не названа, верни null. Не выдумывай.
- Валюту бери из текста. Если не написана: до тысячи обычно евро,
  выше — динары. Но у одежды, посуды и мелочи наоборот — динары.

Объявление:
{text}"""


def looks_wrong(price: float | None, currency: str | None,
                title: str, body: str) -> bool:
    """
    Стоит ли переспросить у модели.

    Правила ошибаются заметно: цена в сто раз меньше настоящей или
    подозрительно круглая для вещи, которую так не продают.
    """
    if price is None:
        return True                              # цены нет — вдруг найдётся

    eur = str(currency or "").upper() == "EUR"

    # Слишком дёшево: это размер или объём, а не деньги.
    if eur and price < TOO_CHEAP_EUR:
        return True
    if not eur and price < TOO_CHEAP_RSD:
        return True

    # В тексте есть слова-ловушки — те, из-за которых правила и
    # промахиваются.
    traps = re.search(
        r"(разм\w*|\bр\.\s*\d|\bgb\b|\bтб\b|\bмб\b|батаре\w+\s+\d|"
        r"\d+\s*%|год\w*\s+выпуска|купл\w+\s+за|покупал\w*\s+за|"
        r"в\s+сутки|за\s+сутки|в\s+час|за\s+час|в\s+месяц)",
        f"{title} {body}"[:400], re.I)
    return bool(traps)


def ask_model(title: str, body: str) -> tuple[float | None, str | None]:
    """
    Цена по мнению модели.

    Возвращает (цена, валюта) или (None, None), если цены нет или
    ответ не удалось проверить.
    """
    from app.core.ai_title import _ask

    text = f"{title or ''}\n{(body or '')[:700]}"
    answer = _ask(PROMPT.format(text=text), limit=80)
    if not answer:
        return None, None

    try:
        data = json.loads(re.sub(r"```\w*|```", "", answer).strip())
    except Exception:                            # noqa: BLE001
        return None, None

    price = data.get("price")
    if price is None:
        return None, None

    try:
        price = float(price)
    except (TypeError, ValueError):
        return None, None

    # Число должно быть в тексте: модель может его придумать, и без
    # проверки мы записали бы выдумку вместо пустоты — это хуже.
    if not _in_text(price, text):
        log.info("модель придумала цену %s, в тексте её нет", price)
        return None, None

    currency = str(data.get("currency", "RSD")).upper()
    return price, ("EUR" if currency == "EUR" else "RSD")


def _in_text(price: float, text: str) -> bool:
    """Есть ли такое число в объявлении."""
    whole = int(price)
    for written in (str(whole), f"{whole:,}".replace(",", " "),
                    f"{whole:,}".replace(",", "."),
                    f"{whole // 1000}к" if whole >= 1000 else ""):
        if written and written in text:
            return True
    return False
