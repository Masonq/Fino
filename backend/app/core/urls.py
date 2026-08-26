"""
Понятные адреса объявлений.

Было: /listing/45e17e58-e7c8-4f24-9642-6a55b878023a
Стало: /beograd/mebel/stol-pismennyy-ikea-micke-45e17e58

Человек видит адрес в поисковой выдаче под заголовком и по нему решает,
нажимать ли. Набор цифр читается как случайная страница, а название вещи
— как то, что он искал. Поисковики к этому относятся так же: понятный
адрес считается признаком настоящего сайта.

Короткий хвост от внутреннего ключа оставляем: два объявления могут
называться одинаково, а адрес должен вести к одному.
"""
import re
import unicodedata

# Русские буквы латиницей. Берём как в паспортах и на дорожных знаках —
# люди привыкли читать именно так.
CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    # Сербские
    "ђ": "dj", "ј": "j", "љ": "lj", "њ": "nj", "ћ": "c", "џ": "dz",
}

# Слова, которые в адресе ничего не добавляют: они есть в половине
# объявлений и только удлиняют строку.
SKIP = frozenset("""
prodam prodayu prodaetsya otdam novyy novaya novoe sostoyanii sostoyanie
otlichnom horoshem srochno nedorogo cena torg dlya pod iz na v s i
""".split())

# Длина адреса. Слишком длинный обрезается в выдаче и хуже
# запоминается; трёх-пяти слов довольно, чтобы понять, о чём страница.
MAX_WORDS = 6
MAX_LENGTH = 60


def slugify(text: str) -> str:
    """
    Название вещи в виде части адреса.

    Только строчные латинские буквы, цифры и дефисы: всё прочее
    браузеры и поисковики кодируют в нечитаемую кашу.
    """
    body = (text or "").lower()

    # Сербские буквы с надстрочными знаками: «č» → «c».
    body = "".join(
        CYRILLIC.get(letter,
                     unicodedata.normalize("NFKD", letter)
                     .encode("ascii", "ignore").decode())
        for letter in body
    )

    words = [w for w in re.split(r"[^a-z0-9]+", body) if w and w not in SKIP]

    slug = ""
    for word in words[:MAX_WORDS]:
        nxt = f"{slug}-{word}" if slug else word
        if len(nxt) > MAX_LENGTH:
            break
        slug = nxt
    return slug or "obyavlenie"


def listing_path(listing_id: str, title: str,
                 city: str | None = None,
                 category: str | None = None) -> str:
    """
    Адрес объявления целиком.

    Город и раздел впереди: так адрес показывает, где эта вещь и что
    это — а поисковику даёт понять устройство сайта.
    """
    # Хвост ключа для однозначности: два объявления могут называться
    # одинаково, а адрес должен вести к одному.
    tail = str(listing_id).split("-")[0]

    # Город и раздел ставим всегда: адрес из разного числа частей
    # пришлось бы разбирать по-разному, а треть объявлений записана без
    # города. Пусть будет «bez-goroda» — зато устройство одинаковое.
    parts = [
        slugify(city) if city else "srbija",
        slugify(category) if category else "raznoe",
        f"{slugify(title)}-{tail}",
    ]
    return "/" + "/".join(parts)


def listing_id_from(path: str) -> str | None:
    """
    Достаёт хвост ключа из адреса.

    Название могли поправить, и адрес разойдётся с нынешним — но хвост
    остаётся, и объявление найдётся по нему.
    """
    last = path.rstrip("/").rsplit("/", 1)[-1]
    tail = last.rsplit("-", 1)[-1]
    return tail if re.fullmatch(r"[0-9a-f]{8}", tail) else None
