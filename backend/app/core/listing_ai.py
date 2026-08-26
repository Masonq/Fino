"""
Разбор объявления целиком — один вызов вместо трёх.

Раньше мы спрашивали модель по частям: отдельно цену, отдельно
заголовок, отдельно проверку. Каждый вопрос — свой промах: в цене
всплывало разрешение экрана, в заголовке первая строка объявления, в
описании оставалось «подробнее на моём канале».

Модель видит объявление целиком, и одним вопросом отвечает лучше, чем
тремя по частям: цену она ищет, уже понимая, что за вещь, а заголовок
пишет, зная цену. Плюс втрое меньше обращений — при тысяче объявлений
это часы.

Ответ приходит по строгой схеме, а не свободным текстом: так модель не
припишет пояснений, и разбирать её многословие не нужно.

Всё, что она вернула, проверяется. Цена должна быть в тексте и быть
похожей на цену для такой вещи; заголовок — называть предмет;
описание — не длиннее исходного. Модель ошибается, и без проверки мы
записали бы выдумку.
"""
import json
import logging
import re

log = logging.getLogger(__name__)

# Форма ответа. Пустая строка вместо пропуска поля: модели проще
# вернуть её, чем решать, включать ли поле вообще.
SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "price": {"type": "number"},
        "currency": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["title", "price", "currency", "description"],
}

PROMPT = """Разбери объявление с барахолки Белграда.

Верни JSON: {{"title": "...", "price": число или 0,
"currency": "RSD" | "EUR", "description": "..."}}

title — название вещи, 3-7 слов.
  Начинай с предмета: «Стол письменный IKEA MICKE», «Коляска Chicco 2в1».
  Не бери первую строку объявления как есть.
  Не пиши «продам», «срочно», «в отличном состоянии», цену, район.

price — сколько просят сейчас, числом.
  0, если цена не названа. Не выдумывай.
  Не бери: старую цену («покупал за 12000»), цену за сутки аренды,
  размер, объём памяти, разрешение экрана, год, поколение, диагональ,
  проценты, номер модели.
  Цена за одну штуку: «4000 за 1 шт, за оба 7000» — это 4000.
  Две цены в разных валютах — одна сумма, бери первую.

currency — из текста. Если не написана: техника и мебель дороже
  тысячи — RSD, дешевле — EUR; одежда, посуда, книги — всегда RSD.

description — то же описание, но без мусора.
  Убери только: «подробнее в моём канале», ссылки, «пишите в личку»,
  приглашения подписаться, рекламные хвосты про другие товары
  продавца.
  Оставь всё остальное: состояние, размеры, комплектацию, район,
  условия, и особенно другие вещи из этого же объявления с их
  ценами — в одном объявлении часто продают несколько вещей, и
  выбросить их значит выбросить половину товара.
  Ничего не придумывай и не пересказывай — только вычёркивай.

Объявление:
{text}"""

# Нижняя граница цены для вещей, которые за бесценок не продают. В евро.
#
# Смотрим только на название: слово «ноутбук» встречается в «памяти для
# ноутбука», и по всему тексту правило выбрасывало верные цены.
# «Продам», «Apple», цифры в начале — приставки, за которыми стоит
# сама вещь. Пропускаем их, но не больше: дальше идут уточнения, где те
# же слова значат другое («память для ноутбука»).
_LEAD = r"^(?:[\d\u20e3\ufe0f\s]*)(?:прода\w+\s+)?(?:apple\s+|samsung\s+)?"

FLOORS = (
    (_LEAD + r"(автомобил|авто\b|машина\b|audi|bmw|mercedes|"
     r"volkswagen|skoda|renault|peugeot|citroen|fiat|opel|toyota|"
     r"mini\s+cooper)", 300),
    (_LEAD + r"(macbook|ноутбук|laptop|imac)\b", 150),
    (_LEAD + r"(iphone|ipad)\b", 80),
)


def looks_absurd(price: float, currency: str, title: str) -> bool:
    """
    Цена нелепа для такой вещи.

    Модель берёт число из названия модели — «Odyssey G5 2560» — и
    выдаёт его за цену. Проверить это она сама не может, а мы можем.

    Смотрим только на начало названия: там стоит сама вещь, а дальше
    идут уточнения, где те же слова значат другое.
    """
    in_euro = price if str(currency).upper() == "EUR" else price / 117
    head = (title or "").strip().lower()[:60]

    return any(re.search(pattern, head, re.I) and in_euro < floor
               for pattern, floor in FLOORS)


def parse(title: str, body: str) -> dict | None:
    """
    Разбирает объявление.

    Возвращает {title, price, currency, description} — только те поля,
    которые прошли проверку. None, если модель не ответила.
    """
    from app.core.ai_title import _ask

    text = f"{title or ''}\n{(body or '')[:900]}"
    answer = _ask(PROMPT.format(text=text), limit=400, schema=SCHEMA)
    if not answer:
        return None

    try:
        data = json.loads(re.sub(r"```\w*|```", "", answer).strip())
    except Exception:                            # noqa: BLE001
        log.info("непонятный ответ модели: %r", (answer or "")[:80])
        return None

    out = {}

    new_title = str(data.get("title", "")).strip()
    if _title_ok(new_title):
        out["title"] = new_title[:120]

    price, currency = _price_ok(data, text, new_title or title)
    if price is not None:
        out["price"] = price
        out["currency"] = currency

    new_body = str(data.get("description", "")).strip()
    if _body_ok(new_body, body):
        out["description"] = new_body

    return out or None


def _title_ok(title: str) -> bool:
    """
    Заголовок годится.

    Модель могла вернуть болтовню, пустоту или ту же первую строку.
    Проверяем теми же правилами, что и заголовки из текста.
    """
    if not 8 <= len(title) <= 120:
        return False

    from app.routers.listings import title_is_clear

    return title_is_clear(title)


def _price_ok(data: dict, text: str, title: str) -> tuple[float | None, str]:
    """Цена годится."""
    try:
        price = float(data.get("price") or 0)
    except (TypeError, ValueError):
        return None, "RSD"

    if price <= 0:
        return None, "RSD"

    currency = str(data.get("currency", "RSD")).upper()
    currency = "EUR" if currency == "EUR" else "RSD"

    # Число должно быть в тексте: модель может его придумать, и
    # записать выдумку хуже, чем оставить пустоту.
    if not _in_text(price, text):
        log.info("модель придумала цену %s для %r", price, title[:40])
        return None, currency

    if looks_absurd(price, currency, title):
        log.info("нелепая цена %s %s для %r", price, currency, title[:40])
        return None, currency

    return price, currency


def _body_ok(new_body: str, old_body: str) -> bool:
    """
    Описание годится.

    Модель должна была только вычёркивать. Если текст вырос, она его
    придумала — а выдумка в объявлении хуже рекламного хвоста.

    Если ужался больше чем вдвое — она выбросила нужное. В одном
    объявлении часто продают несколько вещей, и модель принимает их за
    повторы: «сумка 1300, рюкзак 2800, сумка Zara 1300» превращалось в
    «абсолютно новая».
    """
    old = old_body or ""
    if not new_body or len(new_body) < 10:
        return False
    if len(new_body) > len(old):
        return False

    # Короткое описание может ужаться сильно и законно: там мусор и
    # занимает половину. Смотрим только на заметные.
    if len(old) >= 80 and len(new_body) < len(old) * 0.45:
        log.info("описание ужалось с %d до %d — оставляем прежнее",
                 len(old), len(new_body))
        return False

    # Цены из описания не теряются: если в старом было три числа, а в
    # новом одно — выброшены вещи, а не реклама.
    was = set(re.findall(r"\b\d{3,6}\b", old))
    now = set(re.findall(r"\b\d{3,6}\b", new_body))
    if len(was) >= 2 and len(now) < len(was):
        log.info("из описания пропали суммы: было %s, стало %s", was, now)
        return False

    return True


def _in_text(price: float, text: str) -> bool:
    """Есть ли такое число в объявлении."""
    whole = int(price)
    written = (
        str(whole),
        f"{whole:,}".replace(",", " "),
        f"{whole:,}".replace(",", "."),
        f"{whole // 1000}к" if whole >= 1000 else "",
        f"{whole // 1000}k" if whole >= 1000 else "",
    )
    return any(w and w in text for w in written)
