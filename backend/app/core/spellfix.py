"""
Исправление опечаток в названии объявления.

Опечатка в первом слове стоит дороже всех прочих: «Скорода» не найдут
поиском, не отнесут к разделу и пролистают в ленте. При этом человек её
не видит — он написал и отправил.

Правим только очевидное: слово должно почти совпадать с известной вещью
и отличаться на одну-две буквы. «Скорода» → «Сковорода», «холодилник» →
«холодильник». Незнакомые слова, марки и модели не трогаем: там опечатка
неотличима от названия, а испортить чужой текст хуже, чем оставить его
как есть.

Исправления показываем человеку. Молча менять чужие слова нельзя: он
должен видеть, что получилось, и успеть возразить.
"""
import logging
import re

log = logging.getLogger(__name__)

# Насколько слово должно совпасть с известным, чтобы счесть это опечаткой.
# Ниже — начинаются подмены смысла: «кот» превращается в «код».
SIMILARITY = 78

# Короткие слова не правим: у них одна буква разницы — это уже другое
# слово, а не опечатка.
MIN_LENGTH = 6

def _full_form(root: str, written: str) -> str:
    """
    Достраивает слово из корня.

    Корень «сковород» сам по себе не слово: если поставить его в
    объявление, выйдет обрубок. Словарь форм знает полное написание.
    """
    from app.core.morphology import analyzer

    morph = analyzer()
    if morph is None:
        return root

    # Словарь сам приводит корень к начальной форме: «сковород» он
    # понимает как «сковорода». Это и есть то слово, которое нужно.
    parsed = morph.parse(root)[0]
    if parsed.tag.POS == "NOUN" and parsed.normal_form:
        return parsed.normal_form
    return root


_known: set[str] | None = None


def known_words() -> set[str]:
    """
    Слова, с которыми сверяемся, — названия вещей из наших словарей.

    Берём то, что уже собрано для разбора: отдельный список пришлось бы
    вести параллельно, и он бы разошёлся с этим.
    """
    global _known
    if _known is not None:
        return _known

    from app.core.tg_classify import KEYWORDS, SUB_KEYWORDS
    from app.core.title_rules import OBJECT_ROOTS

    words = set()
    for source in (KEYWORDS.values(),
                   (subs for group in SUB_KEYWORDS.values()
                    for subs in group.values())):
        for group in source:
            for word in group:
                word = word.strip()
                # Составные («трек гараж») и короткие не годятся
                if " " in word or len(word) < MIN_LENGTH:
                    continue
                if word.isascii():               # марки не правим
                    continue
                words.add(word)

    for root in OBJECT_ROOTS:
        root = root.strip()
        if len(root) >= MIN_LENGTH and not root.isascii() and " " not in root:
            words.add(root)

    _known = words
    return _known


def fix(text: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Исправляет опечатки в строке.

    Возвращает исправленный текст и список замен — чтобы показать
    человеку, что именно поправили.
    """
    try:
        from rapidfuzz import process
    except ImportError:                          # noqa: BLE001
        return text, []                          # библиотеки нет — не правим

    words = known_words()
    if not words:
        return text, []

    changes: list[tuple[str, str]] = []
    result = text

    for word in re.findall(r"[А-Яа-яЁё]{%d,}" % MIN_LENGTH, text):
        low = word.lower()
        # Слово известно — править нечего. Сверяем по корню: «кастрюля»
        # и «кастрюлю» начинаются с «кастрюл», значит написаны верно, и
        # окончание у человека своё.
        if any(low.startswith(root) for root in words):
            continue

        match = process.extractOne(low, words, score_cutoff=SIMILARITY)
        if not match:
            continue

        correct = match[0]
        # Словарь хранит корни, а слово в объявлении стоит в падеже.
        # Спрашиваем у морфологии полную форму: «сковород» → «сковорода»,
        # иначе выходит обрубок.
        fixed = _full_form(correct, low)
        if fixed == low or len(fixed) > len(low) + 4:
            continue

        # Регистр сохраняем: «Скорода» → «Сковорода»
        if word[:1].isupper():
            fixed = fixed[:1].upper() + fixed[1:]

        result = re.sub(rf"\b{re.escape(word)}\b", fixed, result, count=1)
        changes.append((word, fixed))
        log.info("поправил опечатку: %r → %r", word, fixed)

    return result, changes
