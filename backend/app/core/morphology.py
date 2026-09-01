"""
Морфология: падежи и части речи по словарю, а не по окончаниям.

Своими правилами падеж не выправить. Окончание -у бывает у существительного
в винительном («вешалку»), у глагола первого лица («хочу») и у наречия
(«почему») — на вид они неотличимы, и правило по окончанию раз за разом
делало «Почема» и «Хоча». Мы латали это списком глаголов, но список
конечен, а язык нет.

Словарь знает про слово всё: часть речи, падеж, начальную форму. Это та
задача, где готовая библиотека надёжнее любых регулярок, и держать своё
решение незачем.

Библиотека загружается один раз и живёт в памяти процесса: разбор слова
после этого занимает микросекунды. Если её нет — работают прежние правила,
парсер не останавливается.
"""
import logging

log = logging.getLogger(__name__)

# Винительный падеж множественного числа совпадает с родительным, и
# словарь оставляет слово как есть: «отдам котят» так и висит.
_ACC_PLURAL = {
    "котят": "котята", "щенят": "щенята", "утят": "утята",
    "крольчат": "крольчата", "цыплят": "цыплята", "поросят": "поросята",
}

_analyzer = None
_tried = False


def analyzer():
    """Морфологический словарь. None, если библиотека не установлена."""
    global _analyzer, _tried
    if _tried:
        return _analyzer
    _tried = True
    try:
        import pymorphy3
        _analyzer = pymorphy3.MorphAnalyzer()
    except Exception as exc:
        log.warning("морфология недоступна (%s) — падеж правится по "
                    "окончаниям, как раньше", exc)
    return _analyzer


def available() -> bool:
    return analyzer() is not None


def is_noun(word: str) -> bool:
    """Существительное ли это слово."""
    morph = analyzer()
    if morph is None:
        return False
    return morph.parse(word)[0].tag.POS in ("NOUN", "ADJF", "PRTF")


def normal_form(word: str) -> str:
    """Начальная форма слова: «котят» → «котёнок», «хочу» → «хотеть»."""
    morph = analyzer()
    if morph is None:
        return word
    return morph.parse(word)[0].normal_form


def to_nominative(text: str, words: int = 2) -> str | None:
    """
    Переводит начало строки в именительный падеж.

    Правим только существительные и согласованные с ними прилагательные в
    винительном падеже: «красивую одежду» → «красивая одежда». Глагол,
    наречие и слово в другом падеже остаются как есть — словарь их
    отличает, а окончание нет.

    Возвращает None, если словаря нет: тогда работает прежнее правило.
    """
    morph = analyzer()
    if morph is None:
        return None

    parts = text.split()
    if not parts:
        return text

    changed = False
    for i in range(min(words, len(parts))):
        # Множественное число детёнышей словарь не правит: винительный
        # падеж там совпадает с родительным, и «котят» остаётся «котят».
        plural = _ACC_PLURAL.get(parts[i].strip(" ,.;:!?").lower())
        if plural:
            word = parts[i]
            fixed = plural.capitalize() if word[:1].isupper() else plural
            parts[i] = word.replace(word.strip(" ,.;:!?"), fixed, 1)
            changed = True
            continue

        raw = parts[i]
        core = raw.strip(" ,.;:!?—–-«»\"'()")
        if not core or not core[0].isalpha():
            continue

        best = morph.parse(core)[0]
        # Винительный падеж существительного или прилагательного — то, что
        # осталось от снятого глагола: «продаю вешалку».
        if best.tag.POS not in ("NOUN", "ADJF"):
            break
        if "accs" not in str(best.tag):
            # Слово уже в именительном — дальше по строке идут уточнения,
            # их падеж законный.
            break

        nominative = best.inflect({"nomn"})
        if nominative is None:
            continue
        fixed = nominative.word
        # Регистр сохраняем: «Вешалку» → «Вешалка», «iPhone» не трогаем.
        if core[:1].isupper():
            fixed = fixed[:1].upper() + fixed[1:]
        parts[i] = raw.replace(core, fixed, 1)
        changed = True

    return " ".join(parts) if changed else text


def to_instrumental(name: str) -> str:
    """
    «Иван» -> «Иваном» — для «сделка с {name}». Склоняем только слова,
    которые словарь уверенно считает именем или фамилией (грамема
    Name/Surn) — не любое слово подряд: ник вроде 'Petrov_92' или
    название компании 'ООО Ромашка' словарь не отмечает так, и они
    остаются как есть, а не превращаются во что-то беспорядочное.

    Возвращает исходную строку без изменений, если словаря нет или
    распознать по этим грамемам нечего — тогда «с {name}» просто
    остаётся без падежа, как было до этой функции, не хуже.
    """
    morph = analyzer()
    if morph is None:
        return name

    words = name.split()
    changed = False
    for i, raw in enumerate(words):
        core = raw.strip(" ,.;:!?—–-«»\"'()")
        if not core or not core[0].isalpha():
            continue
        best = morph.parse(core)[0]
        tag = str(best.tag)
        if "Name" not in tag and "Surn" not in tag and "Patr" not in tag:
            continue
        inst = best.inflect({"ablt"})
        if inst is None:
            continue
        fixed = inst.word
        if core[:1].isupper():
            fixed = fixed[:1].upper() + fixed[1:]
        words[i] = raw.replace(core, fixed, 1)
        changed = True

    return " ".join(words) if changed else name


def sentences(text: str) -> list[str]:
    """
    Делит текст на предложения.

    Своё правило рвало «1. вешалку» на «1» и «вешалку», а «100 руб. штука»
    считало двумя предложениями. Библиотека знает про сокращения и числа.
    """
    try:
        from razdel import sentenize
        return [s.text for s in sentenize(text)]
    except Exception:
        import re
        return re.split(r"(?<=[.!?])\s+", text)
