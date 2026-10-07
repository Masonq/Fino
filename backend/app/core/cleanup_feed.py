"""
Уборка ленты: заголовки и описания уже опубликованного.

Порядок работы такой.

Сперва правила — там, где гадать не о чем: заголовок пуст, это
название раздела вместо вещи, в нём телефон, ник, ссылка или хэштеги,
он набран капсом. Такие разбираются всегда: ни запаса, ни обращений
наружу это не требует. Там же правилами проверяется и обратное:
заголовок, который явно хорош, дальше не идёт.

Остальное — спорное, и его решает модель. Именно на нём правила и
промахивались: правило про цену съело «Подъёмный столик», правило про
заглавные выбросило «IKEA MELLTORP», правило про длину — «Ноутбук HP
255 G7 / Ryzen 5». Модель видит объявление целиком и отвечает по
строгой схеме: годен, поправить (и как) или снимать (и почему). Её
ответ проверяется правилами — не выдумала ли число, не вставила ли
цену или контакт.

Спорных сотни, а не тысячи, поэтому дневного запаса на них хватает.
Кончился — спорные откладываются до следующего захода, а очевидное
разбирается дальше.

Описания чистятся правилами всегда: строка либо зовёт в чужой канал
(«Больше товаров тут», «Подписывайтесь»), либо нет.

    python3 -m app.core.cleanup_feed --dry-run       посмотреть счёт
    python3 -m app.core.cleanup_feed --limit 300     разобрать первые 300
    python3 -m app.core.cleanup_feed --apply         разобрать всё
"""
import argparse
import logging
import re

from app.core.ai_title import clean_listing_title
from app.core.audit import record
from app.core.contacts import strip_contacts
from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.tg_parse import strip_promo_lines
from app.models import Listing, ListingStatus

log = logging.getLogger(__name__)

REASON = "Непонятный заголовок: по названию не видно, что продают"


# Строгий разбор заголовка.
#
# Прежняя проверка (title_is_clear) ловила совсем мусор: одно слово,
# обрывок фразы, рекламу. Из трёх с половиной тысяч объявлений она
# снимала сто двадцать — то есть почти всё проходило, хотя в ленте
# полно заголовков вроде «ПРОДАМ СРОЧНО!!! 💥💥», «#мебель #белград» и
# «Отличная вещь за копейки». Здесь правила жёстче: лента должна
# читаться с первого взгляда, а не «в среднем быть ничего».
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
# Телефон, а не номер модели. «Clarks Chantry Walk 26155071» — артикул,
# и по прежнему правилу он считался телефоном: восьми цифр подряд для
# этого хватало. Теперь либо явный плюс с кодом страны, либо девять
# цифр подряд и больше — короче номера в Сербии не бывает.
_PHONE_RE = re.compile(r"(\+\d[\d\s().-]{8,}|\b\d{9,}\b)")
_SHOUT_RE = re.compile(r"[!?]{2,}")

# Слова, которые в заголовке ничего не сообщают о вещи.
_EMPTY_WORDS = frozenset("""
срочно дёшево дешево недорого распродажа скидка акция супер топ лучший
отличный отличное отличная новинка выгодно шок хит успей звоните пишите
подробности цена договорная торг обмен всё все разное прочее
продам продаю продается продаётся отдам отдаю куплю сдам сдаю ищу
новый новая новое почти идеальном состоянии состояние
""".split())

# Родовые слова: предмет ими не назван. «Отличная вещь за копейки» —
# формально три слова, а что продают, неизвестно.
_GENERIC = frozenset("""
вещь вещи вещей товар товары товаров штука штуки предмет предметы
набор комплект лот разное всякое мелочь мелочи
""".split())


# Цена в заголовке. У Avito это прямой отказ: цена живёт в своём поле,
# а в названии занимает место и устаревает первой. «Куртка 3000 динар»,
# «- 4000 за все», «2000 rsd».
# Предлог перед ценой съедаем вместе с ней: иначе «по 1000 динар за
# бутылку» превращалось в «по за бутылку», а «все за 2000 дин» — в
# «все за». Дыра в фразе хуже самой цены.
_PRICE_IN_TITLE_RE = re.compile(
    # Обязательно с числом. Прежняя запись разрешала «по», «за» и
    # «цена» без суммы — и вырезала эти слоги внутри слов:
    # «Подъёмный» превращался в «дъёмный», «поднос» в «днос»,
    # «Зарядка» в «рядка». Числа тут не хватало.
    r"[\s\-—,:(]*"
    r"(?:\b(?:по|за|всего|цена|стоимость)\s*[:\-—]?\s*)?"
    r"\d[\d\s.,\u00a0]*\s*"
    r"(?:€|\$|eur|евро|rsd|рсд|дин\w*|din\w*|руб\w*|₽)"
    # Хвост при цене: «за всё», «за штуку», «за растение».
    r"(?:\s*за\s+[\wёЁ]+)?[\s)]*", re.I)

_PRICE_TAIL_RE = re.compile(r"[\s\-—,:(]*\b\d[\d\s.,\u00a0]*\s*за\s+(все|всё)\b[\s)]*", re.I)

# Ник или ссылка в заголовке: «Платье @shopbelgrade», «t.me/...».
_CONTACT_RE = re.compile(r"(@[a-zA-Z0-9_]{3,}|t\.me/\S+|https?://\S+)")


def _is_shouting(body: str) -> bool:
    """
    Кричащий заголовок — только про кириллицу.

    Латиницей заглавными пишутся названия моделей: «IKEA MELLTORP»,
    «ASUS TUF FX506QM», «DeepCool MATREXX ADD-RGB». Считать их криком —
    значит выбрасывать всю мебель и технику, что и случилось на прошлом
    прогоне. По-русски же заглавные в названии вещи не нужны, и «ПРОДАМ
    СРОЧНО» остаётся криком.
    """
    # Порог по длине выше прежнего: «Стул ИКЕА» — восемь кириллических
    # букв, из них пять заглавных, и по старому счёту это был крик,
    # хотя ИКЕА так и пишется. Крик — это когда заглавными набрана
    # целая фраза, а не одно название.
    cyr = [c for c in body if "а" <= c.lower() <= "я" or c.lower() == "ё"]
    return len(cyr) >= 12 and sum(c.isupper() for c in cyr) > len(cyr) * 0.6


def _tidy(title: str | None) -> str:
    """
    Прибирает заголовок, не переписывая его.

    Убирает то, что по правилам досок в названии не место: цену, ник
    продавца, ссылку, задвоенные пробелы и знаки на концах. Часто
    после этого заголовок становится годным — и объявление не надо
    снимать, достаточно поправить. Это и делает Avito: отклоняет с
    причиной, а не выбрасывает.
    """
    body = (title or "").strip()
    body = _CONTACT_RE.sub(" ", body)
    body = _PRICE_IN_TITLE_RE.sub(" ", body)
    body = _PRICE_TAIL_RE.sub(" ", body)
    # Знаки препинания подряд — «Стол,, новый!!» — и хвосты по краям.
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r"([,.!?;:—-])\1+", r"\1", body)
    # Разделители, оставшиеся от вырезанного: «Монитор BenQ — / (Белград».
    body = re.sub(r"[\s]*[—\-/|]{1,}[\s]*(?=[)\s]*$)", " ", body)
    body = re.sub(r"[—\-/|]\s*[—\-/|]+", " ", body)
    body = re.sub(r"\(\s*\)", " ", body)
    # Открытая скобка без закрывающей — тоже след вырезанного.
    if body.count("(") > body.count(")"):
        body = body.replace("(", " ")
    # Осиротевшие запятые: «Босоножки, р.38 , Земун» после вырезания.
    body = re.sub(r"\s+([,.;:])", r"\1", body)
    body = re.sub(r"([,;:])\s*([,;:])", r"\1", body)
    body = re.sub(r"\s{2,}", " ", body)
    return body.strip(" ,.;:-—|/\\").strip()


def _why(title: str | None, sections: set[str]) -> str:
    """
    Коротко, за что сняли. Нужно для отчёта: список из двух сотен
    заголовков без причин проверять невозможно — непонятно, правило
    сработало по делу или промахнулось.
    """
    body = (title or "").strip()
    if _is_section_name(body, sections):
        return "название раздела"
    if "#" in body:
        return "хэштеги"
    if _PHONE_RE.search(body):
        return "телефон"
    if _SHOUT_RE.search(body) or _is_shouting(body):
        return "крик"

    # Строгая планка (решение владельца, окт. 2026): в ленте только объявления с чётким названием ОДНОЙ вещи —
    # «Игровой ноутбук Dell G15 5510 / i5-10200H / RTX 3050 / 16GB / 512GB». Снимаем:
    strict = _strict_reason(body)
    if strict:
        return strict
    if len(_EMOJI_RE.findall(body)) > 1:
        return "значки"

    words = [w.strip(".,!?()«»\"'—-").lower() for w in body.split()]
    words = [w for w in words if w]
    meaningful = [w for w in words if w not in _EMPTY_WORDS]
    if len(meaningful) < 2:
        return "нет названия вещи"
    if all(w in _GENERIC for w in meaningful) or (
            meaningful[0] in _GENERIC and len(meaningful) < 3):
        return "родовое слово"
    if len(words) - len(meaningful) >= len(words) / 2:
        return "одни зазывалки"
    wordy = [w for w in words if len(w) > 2 and not any(c.isdigit() for c in w)
             and w not in {"gb", "tb", "ssd", "hdd"}]
    if len(wordy) > 10 or len(body) > 110:
        return "слишком длинный"
    return "обрывок фразы"


def _is_section_name(title: str, sections: set[str]) -> bool:
    """
    Заголовок — название раздела, а не вещи.

    «Электроника», «Мебель», «Обувь», «Книги»: человек искал телевизор,
    а получил слово из меню. У Avito это отдельная причина отказа —
    «слишком общий термин».
    """
    return title.strip().lower() in sections


def _clear(title: str | None) -> bool:
    from app.routers.listings import title_is_clear

    body = (title or "").strip()
    if not title_is_clear(body):
        return False

    # Хэштеги вместо названия: «#мебель #белград #продам».
    if body.count("#") >= 1:
        return False

    # Телефон в заголовке — это объявление, написанное как листовка.
    if _PHONE_RE.search(body):
        return False

    # Крик: «СРОЧНО!!!», «ПРОДАМ ДЁШЕВО».
    #
    # Заглавные считаем по всей строке, а не по двум словам подряд:
    # «Велосипед CANNONDALE TOPSTONE» и «MSI GeForce RTX VENTUS» — это
    # названия моделей, они пишутся заглавными по делу. Криком считаем
    # строку, где заглавными набрано больше половины букв.
    if _SHOUT_RE.search(body):
        return False
    if _is_shouting(body):
        return False

    # Больше одного значка: «🔥 Диван 🔥 дёшево 🔥».
    if len(_EMOJI_RE.findall(body)) > 1:
        return False

    words = [w.strip(".,!?()«»\"'—-").lower() for w in body.split()]
    words = [w for w in words if w]

    # Одно слово не проходило и раньше, но и два слова, из которых одно
    # пустое («Продам стол»), вещь не называют толком. Требуем, чтобы
    # после выброса пустых слов осталось хотя бы два.
    meaningful = [w for w in words if w not in _EMPTY_WORDS]
    if len(meaningful) < 2:
        # Исключение — узнаваемая модель: «PS5», «iMac», «RTX 4070».
        # Буква с цифрой или заглавная посреди слова означают, что перед
        # нами название вещи, а не общее слово.
        if not re.search(r"[A-Za-z]{2,}\s?\d|\d\s?[A-Za-z]{2,}|[A-Za-z][a-z]*[A-Z]", body):
            return False

    # Родовое слово вместо вещи: «отличная вещь», «набор разное».
    # Годится, только если рядом сказано, чего именно набор.
    if meaningful[0] in _GENERIC and len(meaningful) < 3:
        return False
    if all(w in _GENERIC for w in meaningful):
        return False

    # Заголовок, наполовину состоящий из зазывалок.
    if len(words) - len(meaningful) >= len(words) / 2:
        return False

    # Слишком длинный — это уже не название, а первая строка описания.
    #
    # Считаем только слова: у техники заголовок законно длинный из-за
    # характеристик — «Ноутбук HP 255 G7 / Ryzen 5 / 8 GB / SSD 256 GB»
    # это четырнадцать «слов», но каждое по делу. Поэтому числа,
    # обозначения и разделители в счёт не идут.
    wordy = [w for w in words if len(w) > 2 and not any(c.isdigit() for c in w)
             and w not in {"gb", "tb", "ssd", "hdd"}]
    if len(wordy) > 10 or len(body) > 110:
        return False

    return True


def _ai_available() -> bool:
    """Остался ли хоть один провайдер с запасом на сегодня."""
    from app.core.ai_title import _ready

    return bool(_ready())


def _obvious(title: str, sections: set[str]) -> str:
    """
    Что видно без модели: «good», «unsure» или причина снятия.

    Сюда попадает только бесспорное. Пустой заголовок, название
    раздела вместо вещи, телефон, хэштеги, ссылка — здесь гадать не о
    чем, и правила справляются без обращений наружу. Всё остальное
    помечается «unsure» и уходит к модели: именно там правила и
    промахивались.
    """
    body = (title or "").strip()
    if len(body) < 3:
        return "пустой заголовок"
    # Три-четыре знака — это может быть и мусор («Все»), и модель
    # («PS5», «iMac»). Решать вслепую нельзя, отдаём модели.
    if len(body) < 5 and not body.isalpha():
        return "unsure"
    if len(body) < 4:
        return "пустой заголовок"
    if _is_section_name(body, sections):
        return "название раздела"
    if "#" in body:
        return "хэштеги"
    if _PHONE_RE.search(body) or _CONTACT_RE.search(body):
        return "контакты в заголовке"
    if _SHOUT_RE.search(body) or _is_shouting(body):
        return "крик"

    # Заголовок уже хороший: вещь названа, ничего лишнего. Проверка та
    # же, что на входе в ленту, и она проверена на четырёх отчётах —
    # «Кровать IKEA KURA с матрасом» и «Ноутбук HP 255 G7» проходят.
    from app.routers.listings import title_is_clear

    words = [w for w in body.split() if len(w) > 2]
    if title_is_clear(body) and len(words) >= 2 and not _PRICE_IN_TITLE_RE.search(body):
        return "good"

    return "unsure"


# несколько вещей в одном объявлении: «3 штуки», «3 ноутбука», «несколько», «в ассортименте», «оптом», «лот»
_MULTI_RE = re.compile(
    r"(\b([2-9]|\d{2,})\s*(шт|штук|штуки|единиц|комплект|пар[аы]?|ноутбук|телефон|смартфон|айфон|iphone|монитор|"
    r"стул|кресл|велосипед|самокат|колес|шин|диск)\w*)|\bнескольк\w*|\bв\s+ассортимент\w*|\bоптом\b|\bлот\b|"
    r"\bразн(ые|ое)\b|\bи\s+(другое|другие|т\.?\s?д\.?|прочее)\b|\bмного\b|\bраспродаж\w*", re.I)
# «продающие» слова вместо названия: «в отличном состоянии», «срочно», «недорого», «как новый», «торг»
_FLUFF_RE = re.compile(
    r"\bв\s+(отличн|хорош|идеальн|нормальн|рабоч)\w*\s+состояни\w*|\bсрочно\b|\bнедорого\b|\bдёшево\b|\bдешево\b|"
    r"\bкак\s+нов\w*|\bторг\b|\bвыгодн\w*|\bсупер\b|\bтоп\b|\bбомба\b", re.I)
# множественное число раздела в начале без модели: «Ноутбуки Lenovo», «Телефоны», «Кроссовки разные»
_PLURAL_HEAD_RE = re.compile(r"^(ноутбуки|телефоны|смартфоны|планшеты|мониторы|кроссовки|куртки|платья|вещи|игрушки|"
                             r"книги|стулья|столы|шины|диски|запчасти|инструменты|товары|костюмы|сумки)\b", re.I)


# вещи, которые законно продают комплектом: «Стулья IKEA 4 шт», «Шины 205/55 R16 — 4 шт»
_SET_OK_RE = re.compile(r"стул|кресл|шин|колес|диск|тарел|чаш|кружк|бокал|комплект|набор", re.I)


def _strict_reason(body: str) -> str:
    if _MULTI_RE.search(body) and not _SET_OK_RE.search(body):
        return "несколько вещей в одном объявлении"
    # «Ноутбуки Lenovo» — общее; «Шины Michelin 205/55 R16» — конкретное (есть размер/модель)
    if _PLURAL_HEAD_RE.search(body) and not re.search(r"\d", body):
        return "общее название вместо конкретной вещи"
    if _FLUFF_RE.search(body):
        return "в названии — рекламные слова, а не вещь"
    return ""


def _acceptable(proposed: str, original: str, sections: set[str]) -> bool:
    """
    Проверка того, что предложила модель.

    Схема в ответе гарантирует форму, но не содержание: модель может
    выдумать характеристику, потерять объём памяти или вернуть название
    раздела. Поэтому короткий разбор — он же страховка на случай, когда
    модель ошиблась.
    """
    body = (proposed or "").strip()
    if len(body) < 4 or len(body) > 110:
        return False
    if _is_section_name(body, sections):
        return False
    if _PHONE_RE.search(body) or _CONTACT_RE.search(body) or "#" in body:
        return False
    if _PRICE_IN_TITLE_RE.search(body):
        return False
    # Числа из оригинала — объём памяти, размер, год — должны остаться:
    # «iPhone 13 128gb» не может стать «iPhone, много памяти».
    # Заглавные посреди фразы: «Два Корпуса ПК и Блок Питания». Так
    # пишут заголовки по-английски, по-русски это чужеродно. Марки не в
    # счёт: они пишутся заглавными по делу, но целиком («IKEA», «ПК»),
    # а не первой буквой.
    # Города и районы не в счёт: «Стол письменный, Нови Белград» —
    # имя собственное, оно и пишется с заглавных.
    from app.data.cities_data import _CITIES

    places = {name.lower() for names in _CITIES.values() for name in names}
    places |= {part for name in places for part in name.split()}

    cyr_words = [w.strip(".,()") for w in body.split()[1:]]
    cyr_words = [w for w in cyr_words if w and "а" <= w[0].lower() <= "я"]
    capped = [w for w in cyr_words
              if w[0].isupper() and not w.isupper() and w.lower() not in places]
    if len(capped) >= 3:
        return False

    if not set(re.findall(r"\d+", original or "")) >= set(re.findall(r"\d+", body)):
        # В новом заголовке появилось число, которого не было в старом.
        # Оно могло прийти из описания — это допустимо, но выдуманное
        # число хуже отсутствующего, поэтому такие правки не берём.
        return False
    return _clear(body)


# Сколько раз за заход можно позвать модель. Запас общий с переводом
# объявлений и переносом из чатов; выбрать его весь одной уборкой
# значит оставить ленту одноязычной.
AI_BUDGET = 120


def run(limit: int | None, apply: bool, use_ai: bool = True,
        show: int = 0, report_path: str | None = None) -> dict:
    # Показ ничего не меняет, поэтому и нейросеть в нём не зовём: она
    # тратит суточный запас, общий с переводом и переносом из чатов, и
    # тянет по несколько секунд на объявление. Для счёта хватает правил.
    if not apply:
        use_ai = False

    # Запас кончился ещё до начала — предупреждаем и идём по правилам.
    # Раньше проход в этом случае зависал: на каждое объявление он шёл
    # к четырём провайдерам подряд, ждал отказа и выдерживал паузу.
    # Двадцать секунд на ответ плюс пауза между обращениями: если
    # запас кончился, каждое спорное объявление стоит этой паузы. При
    # трёх с половиной тысячах это часы ожидания впустую, поэтому
    # ниже мы выключаем модель после трёх молчаний подряд.
    if use_ai and not _ai_available():
        log.warning("у нейросети кончился дневной запас — работаем по правилам")
        use_ai = False

    db = SessionLocal()
    counts = {"проверено": 0, "описаний почищено": 0,
              "заголовков переписано": 0, "снято": 0, "отложено": 0}
    # Что именно тронули — построчно. Смотреть в базе, кого сняли,
    # неудобно: адрес объявления, старый и новый заголовок рядом дают
    # проверить решение глазами и вернуть лишнее.
    report: list[dict] = []
    # Сколько раз подряд модель промолчала.
    silent = 0
    asked = 0
    try:
        from app.core.retitle import _section_names

        sections = _section_names(db)

        query = (db.query(Listing)
                 .filter(Listing.status == ListingStatus.active)
                 .order_by(Listing.published_at.desc().nullslast()))
        if limit:
            query = query.limit(limit)

        for listing in query.all():
            counts["проверено"] += 1
            if counts["проверено"] % 250 == 0:
                # В консоль, а не только в лог: иначе долгий проход
                # выглядит зависшим.
                print(f"  разобрано {counts['проверено']}…", flush=True)
            translations = list(listing.translations)
            if not translations:
                continue

            source_lang = listing.source_language or "ru"
            tr = next((t for t in translations if t.language == source_lang),
                      translations[0])

            # 1. Описание
            cleaned = strip_promo_lines(tr.description)
            if listing.external_source:
                # Только у перенесённых: своего продавца мы просим
                # убрать номер сами, а не правим за него.
                cleaned = strip_contacts(cleaned)
            if cleaned != (tr.description or "").strip():
                counts["описаний почищено"] += 1
                report.append({
                    "действие": "описание почищено",
                    "id": str(listing.id),
                    "заголовок": tr.title,
                    "было": (tr.description or "").strip(),
                    "стало": cleaned,
                })
                if apply:
                    tr.description = cleaned

            # 2. Заголовок: очевидное решают правила, спорное — модель.
            #
            # Правила хороши там, где гадать не о чем: заголовок пуст,
            # это название раздела, в нём телефон или хэштеги. Такие
            # случаи разбираются всегда, без обращений наружу и без
            # дневного запаса.
            #
            # А вот «годится ли этот заголовок» в общем случае правилами
            # не решается: каждое новое правило ломало прежнее — правило
            # про цену съело «Подъёмный столик», правило про заглавные
            # выбросило «IKEA MELLTORP». Здесь зовём модель, и только
            # здесь: таких объявлений сотни, а не тысячи, и запаса на
            # них хватает.
            title = (tr.title or "").strip()
            verdict_name = _obvious(title, sections)

            if verdict_name == "good":
                continue

            if verdict_name == "unsure" and use_ai and asked >= AI_BUDGET:
                # Запас на этот заход исчерпан: спорное ждёт следующей
                # ночи, а не съедает то, что нужно переводу.
                counts["отложено"] += 1
                continue

            if verdict_name == "unsure" and use_ai:
                asked += 1
                answer = clean_listing_title(
                    title, tr.description,
                    listing.category.name.get("ru")
                    if listing.category and listing.category.name else None,
                )
                if answer is None:
                    # Запас кончился или сеть отказала. Спорное
                    # откладываем, а после трёх отказов подряд
                    # перестаём звать модель вовсе: иначе каждый
                    # следующий заход к ней — это ожидание ответа,
                    # которого не будет, и проход выглядит зависшим.
                    counts["отложено"] += 1
                    silent += 1
                    if silent >= 3:
                        log.warning("нейросеть не отвечает — дальше только правила")
                        print("нейросеть не отвечает — спорные откладываем, "
                              "разбираем очевидное")
                        use_ai = False
                    continue
                silent = 0
                if answer["verdict"] == "keep":
                    continue
                if answer["verdict"] == "fix" and _acceptable(answer["title"], title, sections):
                    counts["заголовков переписано"] += 1
                    report.append({
                        "действие": "заголовок переписан",
                        "id": str(listing.id),
                        "было": title,
                        "стало": answer["title"],
                        "почему": answer["reason"],
                    })
                    if apply:
                        tr.title = answer["title"][:255]
                        for other in list(listing.translations):
                            if other is not tr and other.is_auto_translated:
                                listing.translations.remove(other)
                        record(db, None, "listing_retitled", target_type="listing",
                               target_id=listing.id,
                               details={"was": title, "now": answer["title"]})
                    continue
                reason = answer["reason"] or "непонятно, что продают"
            elif verdict_name == "unsure":
                # Модель выключена: спорное не трогаем.
                # Спорное без запаса — не трогаем вовсе.
                counts["отложено"] += 1
                continue
            else:
                reason = verdict_name

            # 3. Снимаем с ленты
            counts["снято"] += 1
            report.append({
                "действие": "снято",
                "id": str(listing.id),
                "заголовок": title,
                "почему": reason,
                "раздел": listing.category.slug if listing.category else None,
                "источник": listing.external_source or "сайт",
            })
            if show and counts["снято"] <= show:
                print(f"  снимаем: {title}")
            if apply:
                if listing.owner_id and not listing.external_source:
                    listing.status = ListingStatus.rejected
                    listing.rejection_reason = REASON
                else:
                    listing.status = ListingStatus.archived
                record(db, None, "listing.unclear_title", target_type="listing",
                       target_id=listing.id, reason=REASON)

            if apply and counts["проверено"] % 50 == 0:
                db.commit()

        if apply:
            db.commit()
    finally:
        db.close()

    if report_path:
        _write_report(report_path, counts, report, apply)
    return counts


def _write_report(path: str, counts: dict, rows: list[dict], apply: bool) -> None:
    """
    Отчёт файлом рядом с кодом: его видно в репозитории и можно
    посмотреть глазами, не заходя в базу. Пишем Markdown, а не CSV:
    заголовки объявлений читают, а не считают, и в таблице они видны
    сразу.
    """
    from pathlib import Path

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Уборка ленты — {utcnow():%d.%m.%Y %H:%M} UTC",
        "",
        "Показ, ничего не изменено." if not apply else "Изменения применены.",
        "",
        "| что | сколько |",
        "| --- | --- |",
    ]
    lines += [f"| {key} | {value} |" for key, value in counts.items()]

    for action, title in (("снято", "Сняты с публикации"),
                          ("заголовок переписан", "Заголовки переписаны"),
                          ("описание почищено", "Описания почищены")):
        chosen = [r for r in rows if r["действие"] == action]
        if not chosen:
            continue
        lines += ["", f"## {title} ({len(chosen)})", ""]
        if action == "снято":
            lines += ["| заголовок | почему сняли | раздел | источник |",
                      "| --- | --- | --- | --- |"]
            lines += [f"| {_cell(r['заголовок'])} | {r.get('почему', '')} | "
                      f"{r['раздел'] or ''} | {r['источник']} |" for r in chosen]
        elif action == "заголовок переписан":
            lines += ["| было | стало | id |", "| --- | --- | --- |"]
            lines += [f"| {_cell(r['было'])} | {_cell(r['стало'])} | {r['id'][:8]} |"
                      for r in chosen]
        else:
            lines += ["| заголовок | убрали | id |", "| --- | --- | --- |"]
            for r in chosen:
                # Считаем убранные знаки, а не строки: телефон вырезают
                # посреди строки, и счёт по строкам показывал ноль —
                # отчёт врал, будто ничего не изменилось.
                dropped_lines = len(r["было"].splitlines()) - len(r["стало"].splitlines())
                dropped_chars = len(r["было"]) - len(r["стало"])
                what = (f"{dropped_lines} строк" if dropped_lines
                        else f"{dropped_chars} знаков")
                lines.append(f"| {_cell(r['заголовок'])} | {what} | {r['id'][:8]} |")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("отчёт: %s", out)


def _cell(text: str | None) -> str:
    """Ячейка таблицы: переносы и палки ломают разметку."""
    return (text or "").replace("|", "¦").replace("\n", " ").strip()[:120]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-ai", action="store_true",
                        help="только правила, без обращений к нейросети")
    parser.add_argument("--show", type=int, default=0,
                        help="напечатать N заголовков, которые будут сняты")
    parser.add_argument("--report", default="reports/cleanup-feed.md",
                        help="куда положить отчёт (по умолчанию reports/cleanup-feed.md)")
    args = parser.parse_args()

    result = run(args.limit, apply=args.apply and not args.dry_run,
                 use_ai=not args.no_ai, show=args.show,
                 report_path=args.report)

    if args.apply and not args.dry_run:
        from app.core.job_report import report as job_report

        job_report("уборка ленты",
                   done=result["снято"] + result["заголовков переписано"],
                   skipped=None if (result["снято"] or result["заголовков переписано"])
                   else "все заголовки и описания в порядке",
                   проверено=result["проверено"],
                   снято=result["снято"],
                   переписано=result["заголовков переписано"],
                   отложено=result.get("отложено", 0))
    print()
    for key, value in result.items():
        print(f"{key}: {value}")
    if not args.apply or args.dry_run:
        print("\nэто был показ. Чтобы применить, добавьте --apply")
