"""
Чистка отображаемого имени.

Имя человека попадает в заголовок страницы, в карточку объявления, в
переписку и в письма. Пока в нём буквы — всё хорошо; но там оказываются
ряды «зарисованных» символов (zalgo), нити эмодзи во всю строку,
невидимые пробелы и управляющие знаки. Такое имя не читается, ломает
вёрстку (заголовок уезжает за экран — видели у одного продавца) и
служит прикрытием для тех, кому не нужно, чтобы их узнавали.

Поэтому имя чистится на входе, а не только показывается покороче:
обрезка в интерфейсе спасла бы вёрстку, но не письма, не уведомления и
не поиск.
"""
import re
import unicodedata

MAX_LEN = 40
# Сколько значков (эмодзи, символов, знаков) допустимо в имени. Один-два
# рядом с именем — обычное дело; десять — уже не имя.
MAX_SYMBOLS = 3

# Невидимое: нулевой ширины, управляющие, метки направления письма.
_INVISIBLE = re.compile(r"[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
_SPACES = re.compile(r"\s+")


def clean_display_name(raw: str | None) -> str:
    """Приводит имя к пригодному виду: без невидимого и без нагромождений."""
    if not raw:
        return ""
    # NFKC разворачивает «математические» и «широкие» подделки букв: ту же
    # латиницу, записанную другим блоком Юникода, иначе не отличить.
    name = unicodedata.normalize("NFKC", raw)
    name = _INVISIBLE.sub("", name)
    # Комбинирующие метки — то, из чего собирают «зарисованные» надписи.
    # Оставляем не больше одной подряд: в настоящих языках (сербском,
    # вьетнамском) двух подряд над буквой не бывает.
    out, combining = [], 0
    for ch in name:
        if unicodedata.combining(ch):
            combining += 1
            if combining > 1:
                continue
        else:
            combining = 0
        out.append(ch)
    name = _SPACES.sub(" ", "".join(out)).strip()
    return name[:MAX_LEN]


def is_unusable_name(name: str) -> bool:
    """
    Годится ли имя к показу.

    Не про красоту и не про язык: сербское, русское, арабское имя
    одинаково годятся. Плохо, когда букв нет вовсе или их меньше, чем
    значков.
    """
    if not name:
        return True
    letters = sum(1 for ch in name if ch.isalnum())
    symbols = sum(
        1 for ch in name
        if not ch.isalnum() and not ch.isspace() and unicodedata.category(ch)[0] in "SCP"
    )
    if letters == 0:
        return True
    return symbols > MAX_SYMBOLS and symbols >= letters
