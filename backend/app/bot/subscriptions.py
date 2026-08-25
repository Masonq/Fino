"""
Подписка на объявления: «сообщи, когда появится коляска».

Бот получился для продавцов, а покупателю в нём делать нечего. При этом
покупателей всегда больше, и приходят они чаще: продавец заходит раз в
месяц продать диван, а ищущий коляску проверяет чат каждый день.

Подписка эту работу снимает: человек называет вещь и получает сообщение,
когда она появится. Заодно это возвращает его в бота — а там он однажды
и сам что-нибудь продаст.
"""
import logging
import re

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from app.core.morphology import normal_form

log = logging.getLogger(__name__)

# Сколько подписок на человека. Больше — и уведомления превращаются в
# поток, который перестают читать.
MAX_PER_USER = 5

# Короткие слова не годятся: «стол» найдёт «столик» и «столовую», а «бу»
# вообще всё подряд.
MIN_WORD = 3

# Слова, по которым искать бессмысленно: они есть в любом объявлении или
# описывают само действие поиска.
SKIP = frozenset("""
искать ищу куплю нужен нужна нужно хочу найти подписка новые объявления
для про при над под без как что где когда чтобы если или либо
""".split())


def keywords(text: str) -> list[str]:
    """
    Слова подписки в начальной форме.

    Начальная форма нужна, чтобы «коляски» и «коляску» находили друг
    друга: человек пишет как придётся, а объявления пишут по-разному.
    """
    words = []
    for raw in re.findall(r"[\w-]{%d,}" % MIN_WORD, (text or "").lower()):
        base = normal_form(raw) or raw
        if base in SKIP or raw in SKIP:
            continue
        if base not in words:
            words.append(base)
    return words[:6]


def matches(subscription: list[str], title: str, description: str) -> bool:
    """
    Подходит ли объявление под подписку.

    Требуем все слова: «коляска chicco» не должна срабатывать на любую
    коляску — человек назвал марку не просто так.
    """
    if not subscription:
        return False

    haystack = f"{title or ''} {description or ''}".lower()
    found = {normal_form(w) or w
             for w in re.findall(r"[\w-]{%d,}" % MIN_WORD, haystack)}

    return all(
        word in found or any(word in w or w in word for w in found)
        for word in subscription
    )


def add(db: Session, telegram_id: int, text: str) -> list[str] | None:
    """
    Заводит подписку. Возвращает её слова или None, если не вышло.
    """
    from app.models import SavedSearch

    words = keywords(text)
    if not words:
        return None

    existing = (
        db.query(SavedSearch)
        .filter(cast(SavedSearch.filters["telegram_id"], String)
                == str(telegram_id))
        .count()
    )
    if existing >= MAX_PER_USER:
        return None

    db.add(SavedSearch(
        # Подписка живёт без учётной записи: человек пришёл из чата и
        # нигде не регистрировался, а искать хочет уже сейчас.
        user_id=None,
        name=" ".join(words)[:120],
        filters={"telegram_id": telegram_id, "words": words},
    ))
    db.commit()
    return words


def mine(db: Session, telegram_id: int) -> list[tuple[str, list[str]]]:
    """Подписки человека: название и слова."""
    from app.models import SavedSearch

    rows = (
        db.query(SavedSearch)
        .filter(cast(SavedSearch.filters["telegram_id"], String)
                == str(telegram_id))
        .all()
    )
    return [(str(r.id), r.filters.get("words", [])) for r in rows]


def drop(db: Session, telegram_id: int, number: int) -> bool:
    """Убирает подписку по её месту в списке."""
    rows = mine(db, telegram_id)
    if not 1 <= number <= len(rows):
        return False

    from app.models import SavedSearch

    db.query(SavedSearch).filter(SavedSearch.id == rows[number - 1][0]).delete()
    db.commit()
    return True


def waiting_for(db: Session, title: str, description: str) -> list[int]:
    """
    Кому сообщить о новом объявлении.

    Перебираем подписки в памяти: их немного, а искать по словам в базе
    пришлось бы полнотекстовым поиском, который тут избыточен.
    """
    from app.models import SavedSearch

    ready = []
    for row in db.query(SavedSearch).all():
        words = (row.filters or {}).get("words")
        telegram_id = (row.filters or {}).get("telegram_id")
        if not words or not telegram_id:
            continue
        if matches(words, title, description):
            ready.append(int(telegram_id))
    return ready
