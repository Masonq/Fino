"""
Автоперевод объявлений.

Трёхъязычность — главное отличие сервиса, но продавец пишет на одном
языке. Без перевода серб не найдёт объявление, написанное по-русски:
поиск идёт по тексту, а текста на его языке просто нет.

Переводим через открытый сервис. Если он недоступен, объявление всё
равно публикуется — просто на одном языке; перевести можно потом.
"""
import json
import logging
from urllib import request as urlrequest, error as urlerror

from app.core.config import settings

log = logging.getLogger(__name__)

LANGS = ("ru", "en", "sr")
TIMEOUT = 8

# В Сербии объявления пишут латиницей (KupujemProdajem, Polovni Automobili),
# поэтому просим у Google именно её. Google периодически всё равно отдаёт
# кириллицу, а LibreTranslate — всегда, так что перекладываем сами:
# соответствие однозначное, ошибиться негде.
GOOGLE_LANG = {"sr": "sr-Latn"}

# Заголовки объявлений начинаются с «Продам…», «Сдам…» — для человека это
# ясно, но переводчик читает их как обращение к читателю и выдаёт
# повелительное наклонение: «Сдам квартиру» превращалось в «Iznajmite stan»
# («снимите квартиру»), то есть смысл переворачивался. Убираем эти глаголы
# перед переводом — на сербских досках заголовок и так начинается с предмета.
# Оригинал продавца не трогаем, правка живёт только внутри перевода.
import re

_SALE = r"(?:прода(?:м|ю|\u0451тся|ется)|продаю\s+срочно|отдам)"
_RENT = r"(?:сда(?:м|ю|\u0451тся|ется))"
_WANT = r"(?:купл[юe]|разыскиваю)"

_NORMALIZERS = [
    # «Отдам даром» — не продажа, смысл нужно сохранить отдельно
    (re.compile(r"^\s*отдам\s+(?:даром|бесплатно)\s*[:,-]?\s*", re.I), "Бесплатно: "),
    (re.compile(r"^\s*" + _RENT + r"\s*[:,-]?\s*", re.I), "В аренду: "),
    (re.compile(r"^\s*" + _SALE + r"\s*[:,-]?\s*", re.I), ""),
    # «Куплю» — это запрос, а не предложение; без глагола смысл теряется
    (re.compile(r"^\s*" + _WANT + r"\s*[:,-]?\s*", re.I), "Ищу "),
    # «Работа» переводчик читает как «работай»: у слова есть глагольный
    # омоним, и «Работа удалённо» приходило как «Radite na daljinu» —
    # приказ вместо названия вакансии. Двоеточие снимает двусмысленность.
    # Соседи по категории («Ремонт недорого», «Уборка быстро») переводятся
    # верно и без него, поэтому правило узкое, только на это слово.
    (re.compile(r"^\s*Работа\s+(?=[а-яё])", re.I), "Работа: "),
    # английские аналоги
    (re.compile(r"^\s*(?:selling|for\s+sale)\s*[:,-]?\s*", re.I), ""),
    (re.compile(r"^\s*(?:renting\s+out|for\s+rent)\s*[:,-]?\s*", re.I), "For rent: "),
    (re.compile(r"^\s*(?:looking\s+for|wanted)\s*[:,-]?\s*", re.I), "Looking for "),
]


def _normalize_for_translation(text: str) -> str:
    """Снимает «Продам/Сдам» — иначе переводчик делает из них приказ."""
    for pattern, replacement in _NORMALIZERS:
        changed = pattern.sub(replacement, text, count=1)
        if changed != text:
            changed = changed.strip()
            if not changed:
                return text
            # После снятия глагола заголовок начинается со строчной буквы.
            # Но первое слово может быть брендом с внутренней заглавной
            # (iPhone, eBay) — такие не трогаем, иначе выйдет «IPhone».
            first = changed.split(" ", 1)[0]
            if first[1:].islower() or first[1:] == "":
                changed = changed[:1].upper() + changed[1:]
            return changed
    return text


_DIGRAPHS = {"\u0409": "Lj", "\u040a": "Nj", "\u040f": "D\u017e",
             "\u0459": "lj", "\u045a": "nj", "\u045f": "d\u017e"}
_SINGLES = str.maketrans(
    "\u0410\u0411\u0412\u0413\u0414\u0402\u0415\u0416\u0417\u0418\u0408\u041a\u041b\u041c\u041d\u041e\u041f\u0420\u0421\u0422\u040b\u0423\u0424\u0425\u0426\u0427\u0428"
    "\u0430\u0431\u0432\u0433\u0434\u0452\u0435\u0436\u0437\u0438\u0458\u043a\u043b\u043c\u043d\u043e\u043f\u0440\u0441\u0442\u045b\u0443\u0444\u0445\u0446\u0447\u0448",
    "ABVGD\u0110E\u017dZIJKLMNOPRST\u0106UFHC\u010c\u0160"
    "abvgd\u0111e\u017ezijklmnoprst\u0107ufhc\u010d\u0161")


def _to_serbian_latin(text: str) -> str:
    for cyr, lat in _DIGRAPHS.items():
        text = text.replace(cyr, lat)
    return text.translate(_SINGLES)


def _restore_latin_tokens(original: str, translated: str) -> str:
    """
    Возвращает на место латинские слова из оригинала.

    Google приспосабливает бренды к сербскому произношению: Volkswagen
    становится Volksvagen (а в другом заголовке Folksvagen), Galaxy —
    Galaki. Для сербского текста это нормально, но по такому названию
    объявление никто не найдёт: ищут «Volkswagen».

    Сопоставляем по огрублённой форме слова, поэтому словарь брендов не
    нужен — работает и с теми, о которых мы не знаем.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9&.-]*", original)
    if not tokens:
        return translated

    def key(word: str) -> str:
        word = word.lower()
        # звуки, которые сербский передаёт иначе: v/f/w, k/x, s/z
        for a, b in (("w", "v"), ("f", "v"), ("x", "k"), ("z", "s"), ("y", "i"), ("j", "i")):
            word = word.replace(a, b)
        # x передаётся то как «k», то как «ks» (Galaxy → Galaki или Galaksi,
        # в зависимости от того, вернул Google латиницу или кириллицу)
        word = word.replace("ks", "k")
        # двойные буквы сербский не пишет
        return re.sub(r"(.)\1+", r"\1", word)

    # Короткие слова не трогаем: сербский союз «a» или предлог «u» совпал бы
    # с одиночной буквой из названия модели и был бы заменён на неё.
    by_key = {key(t): t for t in tokens if len(t) >= 3}
    if not by_key:
        return translated

    def replace(match: "re.Match") -> str:
        word = match.group(0)
        if word in tokens or len(word) < 3:   # уже как в оригинале
            return word
        return by_key.get(key(word), word)

    return re.sub(r"[A-Za-z][A-Za-z0-9&.-]*", replace, translated)


def _fix_script(text: str | None, target: str) -> str | None:
    """Сербский показываем латиницей — на ней пишут все сербские доски."""
    if not text or target != "sr":
        return text
    if any("\u0400" <= ch <= "\u04ff" for ch in text):
        return _to_serbian_latin(text)
    return text


# Публичные сервисы перевода закрываются и вводят ключи, поэтому берём
# список: обходим по очереди, пока какой-нибудь не ответит. Свой адрес,
# указанный в настройках, пробуем первым — на своём сервере нет ограничений.
FALLBACK_ENDPOINTS = [
    "https://libretranslate.de/translate",
    "https://translate.terraprint.co/translate",
    "https://trans.zillyhuhn.com/translate",
]


def _endpoints() -> list[str]:
    own = getattr(settings, "translate_url", None)
    return ([own] if own else []) + FALLBACK_ENDPOINTS


def _translate_google(text: str, source: str, target: str) -> str | None:
    """
    Открытый интерфейс переводчика Google — без ключа и бесплатно.
    Качество для сербского заметно выше, чем у открытых сервисов,
    а они к тому же почти все закрылись.
    """
    from urllib import parse
    params = parse.urlencode({
        "client": "gtx",
        "sl": source,
        "tl": GOOGLE_LANG.get(target, target),
        "dt": "t",
        "q": text[:4000],
    })
    url = f"https://translate.googleapis.com/translate_a/single?{params}"
    req = urlrequest.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            # ответ приходит кусками — собираем их вместе
            parts = [chunk[0] for chunk in data[0] if chunk and chunk[0]]
            result = "".join(parts).strip()
            if not result:
                return None
            # Сначала в латиницу, потом бренды: Google порой отдаёт весь
            # текст кириллицей, и латинских слов, которые надо вернуть,
            # в нём попросту нет.
            return _restore_latin_tokens(text, _fix_script(result, target))
    except Exception as exc:
        log.info("Перевод через Google не вышел: %s", exc)
        return None


def translate(text: str, source: str, target: str) -> str | None:
    """Переводит текст. None — если не получилось."""
    if not text or not text.strip():
        return None
    if source == target:
        return text

    text = _normalize_for_translation(text)

    payload = json.dumps({
        "q": text[:4000],          # длинные описания режем: смысл в начале
        "source": source,
        "target": target,
        "format": "text",
    }).encode()

    # Сначала пробуем Google: остальные публичные сервисы либо закрылись,
    # либо требуют ключ.
    result = _translate_google(text, source, target)
    if result:
        return result

    for endpoint in _endpoints():
        req = urlrequest.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
                result = (data.get("translatedText") or "").strip()
                if result:
                    return _restore_latin_tokens(text, _fix_script(result, target))
        except Exception as exc:
            log.info("Перевод через %s не вышел: %s", endpoint, exc)
            continue

    return None


def translate_listing(db, listing) -> int:
    """
    Дополняет объявление недостающими языками.
    Возвращает, сколько переводов добавлено.
    """
    from app.models import ListingTranslation

    existing = {t.language for t in listing.translations}
    source_lang = listing.source_language or "ru"
    source = next(
        (t for t in listing.translations if t.language == source_lang),
        listing.translations[0] if listing.translations else None,
    )
    if not source:
        return 0

    added = 0
    for lang in LANGS:
        if lang in existing:
            continue

        title = translate(source.title, source_lang, lang)
        if not title:
            continue   # без заголовка перевод бесполезен

        description = translate(source.description, source_lang, lang) if source.description else None

        db.add(ListingTranslation(
            listing_id=listing.id,
            language=lang,
            title=title[:255],
            description=description or "",
            is_auto_translated=True,
        ))
        added += 1

    added += _translate_attributes(listing, source_lang)

    if added:
        db.commit()
        log.info("Объявление %s: добавлено переводов %s", listing.id, added)

    return added


def _translate_attributes(listing, source_lang: str) -> int:
    """
    Переводит атрибуты, которые продавец пишет словами.

    Часть атрибутов — выбор из списка, у них переводы уже лежат в схеме
    категории. А «Вид услуги» и «Район обслуживания» вводятся текстом, и
    без перевода английский интерфейс показывал «Репетитор английского».
    Марку, модель и VIN не трогаем: их пишут одинаково на любом языке.
    """
    schema = (listing.category.attribute_schema or []) if listing.category else []
    keys = [a["key"] for a in schema if a.get("translatable") and listing.attributes.get(a["key"])]
    if not keys:
        return 0

    stored = dict(listing.attributes_i18n or {})
    changed = 0
    for lang in LANGS:
        if lang == source_lang:
            continue
        current = dict(stored.get(lang) or {})
        for key in keys:
            if current.get(key):
                continue
            value = translate(str(listing.attributes[key]), source_lang, lang)
            if value:
                current[key] = value
                changed += 1
        if current:
            stored[lang] = current

    if changed:
        # JSONB меняется целиком — присваиваем новый объект, иначе
        # SQLAlchemy не заметит правку вложенного словаря.
        listing.attributes_i18n = stored

    return 1 if changed else 0


def translate_pending(db, limit: int = 50) -> int:
    """
    Дополняет переводами уже опубликованные объявления — те, что были
    созданы до появления перевода или когда сервис был недоступен.

    Запуск:  python3 -m app.core.translate
    """
    from sqlalchemy import func
    from app.models import Listing, ListingStatus, ListingTranslation

    # Отбираем именно неполные — считаем языки в самой базе. Иначе при
    # росте числа объявлений неполные оказались бы за пределами выборки
    # и до них бы никогда не дошло.
    incomplete = (
        db.query(Listing)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(Listing.status == ListingStatus.active)
        .group_by(Listing.id)
        .having(func.count(func.distinct(ListingTranslation.language)) < len(LANGS))
        .order_by(Listing.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )

    done = 0
    failures = 0
    for listing in incomplete:
        added = translate_listing(db, listing)
        if added:
            done += 1
            failures = 0
        else:
            failures += 1
            # Сервис перевода недоступен — прекращаем, а не перебираем
            # весь список впустую. Следующий запуск через час попробует снова.
            if failures >= 3:
                log.warning("Перевод недоступен, откладываем до следующего запуска")
                break

    return done


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        n = translate_pending(session)
        print(f"Переведено объявлений: {n}")
    finally:
        session.close()
