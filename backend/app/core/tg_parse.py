"""
Разбор объявления из сообщения телеграм-чата.

В чатах пишут свободным текстом, поэтому вытаскиваем то, что поддаётся
разбору надёжно: цену, город и заголовок. Остальное остаётся описанием.

Правило одно: если не уверены — не выдумываем. Пустая цена честнее
неправильной, а неверный город хуже отсутствующего, потому что объявление
попадёт не в ту выдачу и его не найдут те, кому оно нужно.
"""
import re

from app.core.title_rules import (
    ATTR_LABELS, SUBJECT_BY_CATEGORY, SUBJECT_BY_SUB, TITLE_ATTRS,
    profession, rejects_as_title, service_subject, strip_trailing_number,
)
from app.data.cities_data import CITY_ALIASES, DISTRICT_NAMES

# Цена: число с необязательными разделителями и валютой рядом. Диапазоны и
# «от 500» тоже ловим — берём нижнюю границу, она и есть ориентир.
_PRICE_RE = re.compile(
    # Перед числом может стоять что угодно — эмодзи, скобка, начало строки:
    # требование пробела отбрасывало «💰13 500 евро», и совпадала вторая
    # половина числа, то есть 500 вместо тринадцати с половиной тысяч.
    # Второй запрет не даёт зацепиться за хвост уже начатого числа.
    r"(?<![\w])(?<![\d][ .,\u00a0])(?:от\s*)?(\d{1,3}(?:[ .,\u00a0]\d{3})+|\d{2,7})\s*"
    r"(€|\$|(?:eur|евро|е|rsd|рсд|rs|din(?:ara?)?|дин\.?|динар\w*|usd)\b)",
    re.I,
)
# «20к динар», «5k евро» — тысячи сокращают буквой, и без этого цена
# читалась как двадцать динаров
_PRICE_K_RE = re.compile(
    r"(?<![\w])(\d{1,4})\s*(?:к|k|т|тыс\.?)\s*"
    r"(€|(?:eur|евро|е|rsd|рсд|rs|din\w*|дин\w*)\b)", re.I)

_PRICE_AFTER_RE = re.compile(
    r"(?:цена|price|cena)\s*[:\-—]?\s*(\d{1,3}(?:[ .,\u00a0]\d{3})+|\d{2,7})",
    re.I,
)

CURRENCY_BY_WORD = {
    "€": "EUR", "eur": "EUR", "евро": "EUR",
    # «250 е» — так пишут евро одной буквой; «RS» — динары
    "е": "EUR", "e": "EUR",
    "rsd": "RSD", "рсд": "RSD", "rs": "RSD",
    "din": "RSD", "dinar": "RSD", "dinara": "RSD",
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
# Телефон человека, который у нас не регистрировался. Связь идёт через
# кнопку в Telegram, а номер в описании — это чужие личные данные на нашей
# витрине, чего мы условились не делать.
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,17}\d)")
_CONTACT_LINE_RE = re.compile(
    r"(для записи|пишите (по|на) номер|звоните по|номер телефона|"
    r"вайбер|viber|whatsapp|вотсап)", re.I)
# «Стол 3000 RSD» — цена уже вынесена в поле, в заголовке она лишняя
# «Растения по 2500 динар каждое» — хвост с ценой в конце заголовка
# «... (б/у)Цена: 15» — слово «цена» и всё после него в заголовке лишнее
_TITLE_PRICE_WORD_RE = re.compile(r"\s*[(\[]?\s*цена\b.*$", re.I)

_TITLE_PRICE_TAIL_RE = re.compile(
    r"\s*(?:по|за)\s+\d[\d .,\u00a0]*\s*"
    r"(?:€|eur|евро|rsd|рсд|din\w*|дин\w*)"
    r"(?:\s*(?:кажд\w*|штук\w*|шт\.?))?\s*$", re.I)

# Предлог захватываем вместе с ценой: без него «Продам стол за 3000 дин»
# превращалось в «Стол за».
_TITLE_PRICE_RE = re.compile(
    r"\s*[—-]?\s*(?:за|по)?\s*\d[\d .,\u00a0]*\s*"
    r"(?:€|eur|евро|rsd|рсд|din\w*|дин\w*|\$|usd)\.?\s*$", re.I)
_SPEC_RE = re.compile(r"^[\w \u0400-\u04ff]{3,24}\s*[:：]\s*\S")
# Глагол в начале ничего не добавляет: в ленте и так всё продаётся
_SELLING_VERB_RE = re.compile(r"^(продам|продаю|продается|продаётся|prodajem|na prodaju)\s+", re.I)

# Сняв «продам», остаёмся с винительным падежом: «Плёночную камеру».
# Названием это быть не может, нужен именительный. Полного решения без
# словаря словоформ нет, но эти окончания покрывают почти все случаи:
# женский род на -у/-ю и прилагательное перед ним на -ую/-юю.
_ACC_ADJ = (
    (re.compile(r"(\w+)ую\b", re.I), "ая"),
    (re.compile(r"(\w+)юю\b", re.I), "яя"),
)
# Существительные женского рода: в винительном оканчиваются на -у/-ю.
# Согласная перед окончанием отсекает несклоняемые слова вроде «кенгуру»
# и «меню», где перед -у стоит гласная.
_ACC_NOUN = re.compile(r"(\w{2,}[бвгджзклмнпрстфхцчшщ])у\b", re.I)
_ACC_NOUN_SOFT = re.compile(r"(\w{2,}[бвгджзклмнпрстфхцчшщ])ю\b", re.I)
# Слова, которые и в именительном кончаются на -у: их не трогаем
_INDECLINABLE = {"кенгуру", "какаду", "меню", "рагу", "интервью", "шоу", "жалюзи"}


def to_nominative(text: str) -> str:
    """
    Переводит первые слова заголовка из винительного падежа в именительный.

    Трогаем только начало: дальше идут уточнения, где падеж уже верный,
    а слова вроде «камеру» встречаются и в них.
    """
    words = text.split()
    if not words:
        return text
    # прилагательное и существительное — не больше двух слов
    for i in range(min(2, len(words))):
        word = words[i]
        if word.lower() in _INDECLINABLE:
            continue
        changed = False
        for pattern, ending in _ACC_ADJ:
            m = pattern.fullmatch(word)
            if m:
                words[i] = m.group(1) + ending
                changed = True
                break
        if changed:
            continue
        m = _ACC_NOUN.fullmatch(word)
        if m:
            words[i] = m.group(1) + "а"
            continue
        m = _ACC_NOUN_SOFT.fullmatch(word)
        if m:
            words[i] = m.group(1) + "я"
    return " ".join(words)
# «Срочно!», «Внимание!» — привлекают взгляд в чате, но вещь не называют
_SHOUT_RE = re.compile(
    r"^(срочно|очень срочно|внимание|важно|только сегодня|акция|hitno|pažnja)"
    r"[\s!.,:—-]*", re.I)
# Строки, которые к названию вещи отношения не имеют: сроки, призывы
# написать, причина продажи. Заголовком становиться не должны.
_SERVICE_LINE_RE = re.compile(
    r"(только до|в продаже до|действует до|по причине переезда|пишите в лс|"
    r"пишите в личку|для записи|запись на просмотр|доп информаци|"
    r"рассмотрю обмен|самовывоз только|торг уместен|цена окончательная|"
    r"^все вещи по|^продам всё|"
    r"^актуально|^забронировано|^продано)", re.I)
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
        # строка, существующая ради телефона, целиком не нужна
        if _CONTACT_LINE_RE.search(line) and _PHONE_RE.search(line):
            continue
        line = _PHONE_RE.sub("", line)
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


# «Новый в магазине стоит 25 000, цена: 17 000» — берём ту, что названа
# ценой, а не первую попавшуюся сумму.
_PRICE_LABELLED_RE = re.compile(
    r"(?:цена|price|cena)\s*[:\-—]?\s*"
    # «15. 000 RS» — точку от разделителя тысяч иногда отделяют пробелом
    r"(\d{1,3}(?:[ .,\u00a0]\s?\d{3})+|\d{2,7})\s*"
    r"(€|\$|(?:eur|евро|е|rsd|рсд|rs|din\w*|дин\w*|usd)\b)?", re.I)


# Про какую сумму идёт речь, видно по словам перед ней.
# «Брал за 18000 рублей», «в магазине стоит 25 000» — это не наша цена.
_PAST_PRICE_RE = re.compile(
    r"(брал\w*|покупал\w*|купил\w*|стоит\w*|стоил\w*|"
    r"в магазин\w*|новый стоит|отдавал\w*|платил\w*|"
    r"было|раньше|изначально|при покупке)", re.I)
# «Продаю за», «отдам за», «цена» — а вот это она
_SELL_PRICE_RE = re.compile(
    r"(цена|price|cena|прода[юмё]\w*|отда[юм]\w*|уступлю|заберите за)", re.I)
# Чужая валюта: рубли и прочее к нашим ценам отношения не имеют
_FOREIGN_RE = re.compile(r"(руб\w*|₽|грн|тенге|злот\w*)", re.I)


def _price_candidates(text: str) -> list[tuple[int, float, str | None]]:
    """Все суммы текста: позиция, значение, валюта."""
    out = []
    for m in _PRICE_RE.finditer(text):
        value = _to_number(m.group(1))
        if value is not None:
            out.append((m.start(), value, CURRENCY_BY_WORD.get(m.group(2).lower())))
    return out


def extract_price(text: str) -> tuple[float | None, str | None]:
    # Сначала разбираем суммы с валютой, глядя на слова перед каждой:
    # в объявлении их бывает несколько, и первая попавшаяся — часто та,
    # за которую вещь когда-то купили.
    candidates = _price_candidates(text)
    if len(candidates) > 1:
        scored = []
        for pos, value, currency in candidates:
            # Смотрим только ближайшие слова: окно пошире захватывало начало
            # фразы, и в «Покупал за 16000, продаю за 10000» обе суммы
            # выглядели как прошлая цена.
            before = text[max(0, pos - 40):pos]
            before = re.split(r"[.,;!?\n]", before)[-1] or before[-18:]
            after = text[pos:pos + 24]
            if _FOREIGN_RE.search(after) or _FOREIGN_RE.search(before[-12:]):
                continue          # цена в рублях — не наша
            if _PAST_PRICE_RE.search(before):
                continue          # столько отдали за неё раньше
            weight = 1 if _SELL_PRICE_RE.search(before) else 0
            scored.append((weight, -pos, value, currency))
        if scored:
            scored.sort(reverse=True)
            _, _, value, currency = scored[0]
            return value, currency

    m = _PRICE_LABELLED_RE.search(text)
    if m:
        value = _to_number(m.group(1))
        if value is not None:
            currency = CURRENCY_BY_WORD.get((m.group(2) or "").lower())
            if currency:
                return value, currency
            # валюта не названа: до тысячи это почти наверняка евро
            if value <= 1000:
                return value, "EUR"

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


_GREETING_RE = re.compile(
    r"^(всем\s+)?(привет\w*|здравствуйте|добрый\s+день|добрый\s+вечер|доброе\s+утро|"
    r"здравствуй|zdravo|pozdrav)[\s,!.—-]*", re.I)


def strip_greeting(text: str) -> str:
    """
    Снимает приветствие в начале.

    «Всем привет. Меня зовут Кирилл, 19 лет...» — так пишут резюме в чатах,
    но заголовком это быть не может: в ленте у всех оказывается одно и то
    же «Всем привет», и объявления неразличимы.
    """
    out = _GREETING_RE.sub("", text.strip())
    # «Меня зовут X, 19 лет», «Мне 28 лет» — знакомство, а не суть
    # объявления. Снимаем в любом порядке: имя бывает и без возраста, и
    # возраст без имени.
    rest = out
    for _ in range(3):
        before = rest
        rest = re.sub(r"^меня\s+зовут\s+[\w-]+[\s,.—-]*", "", rest, flags=re.I)
        rest = re.sub(r"^мне\s+\d{1,2}\s*(?:лет|года?)[\s,.—-]*", "", rest, flags=re.I)
        rest = re.sub(r"^\d{1,2}\s*(?:лет|года?)[\s,.—-]*", "", rest, flags=re.I)
        if rest == before:
            break
    # Порог только чтобы не остаться с обрывком: «Мне 28 лет, ищу работу
    # барменом» давало 19 символов и откатывалось целиком.
    return (rest if len(rest) >= 8 else out).strip(" ,.;:—-")


def make_title(text: str, limit: int = 70) -> str | None:
    """
    Заголовок из первой содержательной строки.

    Отдельного заголовка в чатах нет, поэтому берём начало текста —
    так же, как его читает человек в ленте чата.
    """
    fallback = None
    for raw in text.splitlines():
        line = _EMOJI_RE.sub("", raw).strip(" \t•·—-*#")
        # «Всем привет!» и «Срочно!» как заголовок делают ленту неразличимой
        line = _SHOUT_RE.sub("", strip_greeting(line))
        # пропускаем строки из одних эмодзи, решёток и знаков
        if len(re.sub(r"[^\w]", "", line, flags=re.UNICODE)) < 8:
            continue
        line = re.sub(r"\s+", " ", line)
        # «Площадь: 72м2» — характеристика, а не название; заголовком берём
        # только если ничего лучше в тексте не нашлось
        if _SPEC_RE.match(line):
            fallback = fallback or line
            continue
        # «В продаже только до 24 августа» — условие сделки, не предмет
        if _SERVICE_LINE_RE.search(line):
            continue
        # Цена и в начале, и в конце заголовка лишняя: она стоит строкой
        # выше. В середине не трогаем — вырежется кусок фразы.
        line = _TITLE_PRICE_RE.sub("", line).strip(" ,.;:-—")
        line = _TITLE_PRICE_TAIL_RE.sub("", line).strip(" ,.;:-—")
        if not line:
            continue

        # Заголовок — это что продают, а не рассказ о вещи. «Велосипед. На
        # правом шатуне сорвана резьба...» — название здесь первое слово,
        # остальное относится к описанию.
        # Берём первое предложение, в котором есть что-то кроме восклицания:
        # «Срочно! Продаю растения по 2500 динар» начинается не с названия.
        # Берём первое предложение, которое называет предмет. Раньше брали
        # первое подходящее по длине — так в заголовок попадали «Меня зовут
        # Даниил» и «Мечтаете о цвете волос», после которых в том же посте
        # шло название вещи.
        chosen = None
        for part in re.split(r"(?<=[.!?])\s+", line):
            candidate = _SHOUT_RE.sub("", part).strip(" .!?,;:-—")
            if len(candidate) < 6:
                continue
            if rejects_as_title(candidate):
                continue
            chosen = candidate
            break
        if chosen is None:
            continue
        line = chosen
        # «Белград | Peugeot 308 | » — город и разделители в заголовке лишние:
        # город стоит отдельной строкой, а палки остаются от разметки поста
        parts = [p.strip() for p in re.split(r"\s*[|•]\s*", line) if p.strip()]
        if len(parts) > 1:
            meaningful = [p for p in parts if not extract_city(p) or len(p.split()) > 2]
            if meaningful:
                line = meaningful[0]
        line = line.strip(" |•—-")

        # «Продаю женские вещи» — название здесь есть, лишний только глагол
        without_verb = _SELLING_VERB_RE.sub("", line).strip(" ,.;:-—")
        if not without_verb:
            continue
        # Заглавную ставим, только если сняли глагол и слово начиналось со
        # строчной: иначе «iPhone» становился «IPhone».
        if without_verb != line:
            # падеж правим только там, где сняли глагол — он его и задавал
            without_verb = to_nominative(without_verb)
        line = without_verb

        # Обрываем по первой запятой: до неё называют предмет, после —
        # состояние, город и условия, которым место в описании.
        head = line.split(",", 1)[0].strip()
        if 12 <= len(head) <= limit:
            line = head

        # Цену снимаем после обрезки: до неё «2500 динар каждое» стояло в
        # середине строки, и правило для хвоста его не находило.
        line = _TITLE_PRICE_WORD_RE.sub("", line)
        line = _TITLE_PRICE_TAIL_RE.sub("", line)
        line = _TITLE_PRICE_RE.sub("", line).strip(" ,.;:-—")
        if not line:
            continue

        # Заглавная — только если строку правили: после снятия приветствия
        # или глагола она начиналась со строчной. Нетронутое название не
        # трогаем, иначе «iPhone» становится «IPhone».
        if line != raw.strip() and line[:1].islower() and not line[:2].isupper():
            head = line.split()[0]
            if head.islower():
                line = line[0].upper() + line[1:]

        # «Два брата-акробата 3» — тройка осталась от разметки поста
        line = strip_trailing_number(line)
        # Чистка могла отрезать как раз то слово, ради которого строка
        # прошла отбор, — проверяем итог, а не только кандидата.
        if rejects_as_title(line):
            continue

        if len(line) <= limit:
            return line
        cut = line[:limit].rsplit(" ", 1)[0]
        return (cut or line[:limit]).rstrip(" ,.;:") + "…"
    return fallback if fallback and not rejects_as_title(fallback) else None


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


def title_from_facts(
    category_slug: str | None,
    sub_slug: str | None,
    text: str,
    attrs: dict | None = None,
) -> str | None:
    """
    Заголовок из того, что об объявлении известно наверняка.

    Нужен там, где автор о предмете не написал вовсе: рассказал о себе,
    задал вопрос читателю, начал с настроения. Такой заголовок сухой, зато
    в ленте по нему видно, что это кошка из Нови-Сада, а не «Дом — это
    место».
    """
    # У услуг предмет — это дело, а не раздел: «Услуги красоты» ничего не
    # говорит, «Стрижка и окрашивание волос» говорит всё.
    if category_slug in ("services", "beauty"):
        subject = service_subject(text)
        if subject:
            return subject

    # В резюме и вакансии предмет — профессия: по ней и ищут.
    if category_slug == "jobs":
        job = profession(text)
        if job:
            kind = "Резюме" if sub_slug == "resumes" else "Вакансия"
            return f"{kind}: {job.lower()}"

    subject = SUBJECT_BY_SUB.get(sub_slug or "")
    if not subject:
        subject = SUBJECT_BY_CATEGORY.get(category_slug or "")
    if not subject:
        return None

    parts = [subject]
    if attrs:
        for key in TITLE_ATTRS:
            if len(parts) >= 3:
                break
            value = attrs.get(key)
            if value in (None, "", []):
                continue
            label = ATTR_LABELS.get(key)
            parts.append(label.format(value) if label else str(value))

    district = extract_district(text)
    if district and len(parts) < 3:
        parts.append(district)
    return ", ".join(parts)


def build_title(
    category_slug: str | None,
    sub_slug: str | None,
    text: str,
    attrs: dict | None = None,
    fallback_title: str | None = None,
) -> str | None:
    """
    Единая точка: один заголовок по одному правилу для всех объявлений.

    Порядок жёсткий и одинаковый для любой категории: заголовок из фактов
    для недвижимости (там текст почти всегда начинается хэштегами), затем
    строка из текста, назвавшая предмет, и лишь потом — сборка из фактов.
    """
    composed = compose_title(category_slug, text)
    if composed:
        return composed
    if fallback_title and not rejects_as_title(fallback_title):
        return fallback_title
    return title_from_facts(category_slug, sub_slug, text, attrs)


# Обороты рекламных постов: обращение к читателю и предложение услуг
# вообще, без конкретной вещи и цены.
_PITCH_MARKERS = (
    "вам нужна", "вам нужен", "вам необходим", "нужна надежная", "нужен надежный",
    "мы предлагаем", "мы оказываем", "наша компания", "наши услуги",
    "работаем без выходных", "звоните", "обращайтесь", "ждем ваших заявок",
    "ждём ваших заявок", "оставьте заявку", "гарантия качества",
    "быстро и качественно", "индивидуальный подход", "лучшие цены",
    "широкий выбор", "большой опыт работы", "профессиональная команда",
)


# Пометки, которыми закрывают объявление. Ставят и в самом сообщении
# (правкой), и ответом в ветке.
_SOLD_RE = re.compile(
    r"(^|[\s\[(*_])(продано|прода[нl]а|продал\w*|ушло|ушла|забрали|забрано|"
    r"не\s*актуально|неактуально|снято с продажи|закрыто|"
    r"prodato|prodata|nije aktuelno|rezervisano|"
    r"sold|reserved)([\s\])*_!.,]|$)", re.I)


def looks_sold(text: str) -> bool:
    """
    Объявление закрыто: вещь продали или сняли с продажи.

    Ищем пометку целым словом: «продано» внутри «непроданное» или в
    «продано будет завтра» — не то же самое, а вот «ПРОДАНО» отдельной
    строкой или в скобках у заголовка означает ровно это.
    """
    m = _SOLD_RE.search(text or "")
    if not m:
        return False
    # «продано будет только целиком» — не пометка, а часть фразы. Пометка
    # стоит особняком: в конце, в скобках или отдельной строкой.
    tail = (text[m.end():] or "").strip()
    if tail[:6].lower() in ("будет ", "тольк", "если ", "при "):
        return False
    return True


def looks_like_ad(text: str) -> bool:
    """
    Отличает рекламу услуги от объявления о продаже.

    Объявление говорит о конкретной вещи: что это, сколько стоит, где
    забрать. Реклама обращается к читателю и обещает качество: «Вам нужна
    надёжная доставка?» — здесь нет ни предмета, ни цены, и покупателю с
    такого объявления взять нечего.

    Судим по совокупности, а не по одному обороту: «звоните» в конце
    нормального объявления встречается сплошь и рядом.
    """
    low = text.lower()
    hits = sum(1 for marker in _PITCH_MARKERS if marker in low)
    if not hits:
        return False
    has_price, _ = extract_price(text)
    # два оборота и больше — реклама почти наверняка, даже с ценой
    if hits >= 2:
        return True
    # один оборот тянет на рекламу, только когда цены нет вовсе
    return has_price is None


def looks_like_spam(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _SPAM_MARKERS)


# Раз характеристика вынесена в поле, повторять её в описании незачем:
# «Площадь: 79 м²» стоит строкой выше в своей рамке.
_ATTR_LINE_RE = {
    "area_m2": re.compile(r"^(площадь|kvadratura|povrsina)\b", re.I),
    "floor": re.compile(r"^(этаж|sprat)\b", re.I),
    "rooms": re.compile(r"^(комнат\w*|планировка|struktura)\b", re.I),
    "mileage_km": re.compile(r"^(пробег|kilometraza)\b", re.I),
    "year": re.compile(r"^(год выпуска|godiste)\b", re.I),
}


def drop_attribute_lines(description: str, attrs: dict) -> str:
    """
    Убирает строки, содержимое которых уже разложено по полям.

    Строку убираем, только если в ней стоит ровно то значение, что мы
    забрали: «Этаж: 2» уходит, а «Этаж 2, окна во двор» остаётся — во
    второй половине сказано то, чего в полях нет.
    """
    if not attrs:
        return description

    kept = []
    for line in description.splitlines():
        bare = _EMOJI_RE.sub("", line).strip(" \t•·—-*")
        drop = False
        for key, pattern in _ATTR_LINE_RE.items():
            if key not in attrs or not pattern.match(bare):
                continue
            # «Планировка: 3.0» — это одно число, а не два: дробную запись
            # приводим к целому, иначе строка оставалась в описании
            numbers = re.findall(r"\d+(?:[.,]\d+)?", bare)
            if len(numbers) != 1:
                continue
            value = float(numbers[0].replace(",", "."))
            if abs(value - float(attrs[key])) >= 0.01:
                continue
            # В строке не должно остаться ничего, кроме названия признака,
            # числа и единиц: «Этаж 2, окна во двор» сообщает больше, чем
            # поле, и убирать его нельзя.
            rest = pattern.sub("", bare)
            rest = re.sub(r"\d+(?:[.,]\d+)?", "", rest)
            rest = re.sub(r"(м2|м²|кв\.?\s*м|m2|кв|km|км)", "", rest, flags=re.I)
            if len(re.sub(r"[^\w]", "", rest, flags=re.UNICODE)) <= 2:
                drop = True
                break
        if not drop:
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
    # Заголовок с многоточием — это обрезанная строка, а не она целиком.
    # Убирать её нельзя: у объявления, написанного одним абзацем, вместе с
    # ней уходит весь текст, и в описании остаётся одна подпись.
    if title.endswith("…"):
        return description
    lines = description.splitlines()
    for i, line in enumerate(lines[:3]):
        bare = _EMOJI_RE.sub("", line).strip(" \t•·—-*")
        stripped = _TITLE_PRICE_RE.sub("", bare).strip(" ,.;:-—")
        if stripped and (stripped == title or bare == title or title.startswith(stripped[:40])):
            without = "\n".join(lines[:i] + lines[i+1:]).strip()
            # Если кроме этой строки в описании ничего нет, оставляем её:
            # пустое описание хуже повтора заголовка.
            return without if without else description
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


_FLOOR_RE = re.compile(r"этаж\w*\s*[:\-—]?\s*(\d{1,2})", re.I)
_FLOOR_OF_RE = re.compile(r"(\d{1,2})\s*/\s*\d{1,2}\s*этаж", re.I)
# Пробег пишут и «145 000 км», и «170к пробег» — слово может стоять с любой
# стороны числа, поэтому ловим оба порядка
_MILEAGE_RE = re.compile(
    r"(?:(\d{1,3}(?:[ .,\u00a0]?\d{3})|\d{1,3})\s*(тыс\.?|к|k)?\s*км"
    r"|(\d{1,3}(?:[ .,\u00a0]?\d{3})|\d{1,3})\s*(тыс\.?|к|k)\s*(?=пробег))", re.I)
_YEAR_RE = re.compile(r"(?<!\d)(19[89]\d|20[0-3]\d)(?!\d)\s*(?:год\w*|г\.?|\.|,|$)", re.I)


# Категории, где спрашивают состояние вещи. У авто своя мера — год и
# пробег, у жилья и услуг состояния не бывает вовсе.
WITH_CONDITION = {
    "electronics", "fashion", "home-garden", "kids",
    "hobby-sport", "beauty", "business",
}


def extract_attributes(category_slug: str, text: str) -> dict:
    """
    Раскладывает то, что в тексте написано словами, по полям категории.

    Без этого у перенесённого объявления заполнено одно описание, и человек
    не может ни отфильтровать по площади, ни сравнить два варианта — а ради
    этого поля и заводились. Берём только то, что распознаётся уверенно:
    пустое поле лучше выдуманного.
    """
    low = text.lower()
    attrs: dict = {}

    # Состояние определяем только там, где под него есть поле: у авто,
    # недвижимости, услуг и работы его нет, и ключ выводился на страницу
    # сырым, без названия.
    #
    # И только рядом со словом о самой вещи. В объявлении о машине
    # перечисляют, что заменили при обслуживании — «новое моторное масло», —
    # и машина 2014 года с пробегом 183 тысячи оказывалась новой.
    if category_slug in WITH_CONDITION:
        if any(w in low for w in ("на запчасти", "za delove", "не работает")):
            attrs["condition"] = "for_parts"
        elif re.search(r"как\s+нов\w+|kao\s+nov", low):
            attrs["condition"] = "like_new"
        elif re.search(r"(состояние|state)\W{0,12}нов\w+|нов\w+,?\s*(в\s+)?упаковке"
                       r"|новый\s+в\s+коробке|не\s+использовал\w*", low):
            attrs["condition"] = "new"
        elif any(w in low for w in ("б/у", "б.у", "polovn", "ношен", "поношен")):
            attrs["condition"] = "used"

    if category_slug == "real-estate":
        rooms = extract_rooms(text)
        if rooms:
            attrs["rooms"] = rooms
        area = _AREA_RE.search(text)
        if area:
            attrs["area_m2"] = int(area.group(1))
        floor = _FLOOR_OF_RE.search(low) or _FLOOR_RE.search(low)
        if floor:
            value = int(floor.group(1))
            if 0 < value <= 40:
                attrs["floor"] = value
        # «сдам» и «аренда» — это найм, «продам» — продажа. Если сказано и
        # то, и другое, не выбираем: в таком тексте обычно два объявления.
        rent = any(w in low for w in ("сдам", "сдаю", "сдается", "сдаётся", "аренда", "izdaje", "iznajm"))
        sale = any(w in low for w in ("продам", "продаю", "продается", "продаётся", "prodaje", "na prodaju"))
        if rent != sale:
            attrs["deal_type"] = "rent" if rent else "sale"
        if any(w in low for w in ("без посредник", "без комисси", "bez provizije")):
            attrs["no_commission"] = True

    elif category_slug == "auto":
        year = _YEAR_RE.search(text)
        if year:
            attrs["year"] = int(year.group(1))
        m = _MILEAGE_RE.search(low)
        if m:
            number = m.group(1) or m.group(3)
            multiplier = m.group(2) or m.group(4)
            km = int(re.sub(r"[ .,\u00a0]", "", number))
            if multiplier:
                km *= 1000
            if 100 <= km <= 1_000_000:
                attrs["mileage_km"] = km
        if any(w in low for w in ("автомат", "акпп", "automatik", "automatic")):
            attrs["transmission"] = "automatic"
        elif any(w in low for w in ("механик", "мкпп", "ручная коробка", "manuelni")):
            attrs["transmission"] = "manual"

    elif category_slug == "electronics":
        # Оперативная память и встроенная пишутся одинаково — «16 гб».
        # Различает их соседнее слово, поэтому сначала забираем ту, что
        # названа явно, и только остальное считаем встроенной.
        m = re.search(r"(\d{1,3})\s*(?:гб|gb)\s*(?:озу|оперативн\w*|ram)"
                      r"|(?:озу|оперативн\w*|ram)\D{0,6}(\d{1,3})\s*(?:гб|gb)", low)
        ram = None
        if m:
            ram = int(m.group(1) or m.group(2))
            if ram in (2, 4, 6, 8, 12, 16, 24, 32, 64):
                attrs["ram_gb"] = ram

        for m in re.finditer(r"(\d{2,4})\s*(гб|gb|тб|tb)\b", low):
            value = int(m.group(1))
            if m.group(2) in ("тб", "tb"):
                value *= 1024
            if value == ram and "ram_gb" in attrs:
                continue
            if value in (16, 32, 64, 128, 256, 512, 1024, 2048):
                attrs["storage_gb"] = value
                break
        m = re.search(r"(?:аккумулятор|акб|батаре\w*|battery)\D{0,12}(\d{2,3})\s*%", low)
        if m and 1 <= int(m.group(1)) <= 100:
            attrs["battery_health"] = int(m.group(1))
        m = re.search(r'(\d{1,2}(?:[.,]\d)?)\s*(?:дюйм\w*|inch|")', low)
        if m:
            attrs["screen_inch"] = float(m.group(1).replace(",", "."))
        if any(w in low for w in ("гарантия", "garancij", "чек есть")):
            attrs["warranty"] = True

    elif category_slug == "fashion":
        # «р. 46», «размер 46», «размер M» — пишут и так, и так
        m = re.search(r"(?:размер|р\.|разм\.?|size|vel\.?)\s*[:\-]?\s*"
                      r"(\d{2}(?:[-–/]\d{2})?|x{0,2}[sml]|xl|xxl)\b", low)
        if m:
            attrs["size"] = m.group(1).upper() if m.group(1).isalpha() else m.group(1)
        m = re.search(r"стельк\w*\D{0,8}(\d{2}(?:[.,]\d)?)", low)
        if m:
            attrs["insole_cm"] = float(m.group(1).replace(",", "."))
        if any(w in low for w in ("женск", "zensk", "žensk")):
            attrs["gender"] = "women"
        elif any(w in low for w in ("мужск", "musk", "muška", "muski")):
            attrs["gender"] = "men"

    elif category_slug == "beauty":
        m = re.search(r"(\d{2,4})\s*(?:мл|ml)\b", low)
        if m:
            attrs["volume_ml"] = int(m.group(1))

    elif category_slug == "jobs":
        if any(w in low for w in ("полная занятость", "полный день", "full time", "puno radno")):
            attrs["employment_type"] = "full_time"
        elif any(w in low for w in ("частичная занятость", "подработк", "part time", "skraceno")):
            attrs["employment_type"] = "part_time"

    return attrs
