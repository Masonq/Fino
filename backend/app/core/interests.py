"""
Интерес человека к разделам — по его собственной истории.

Зачем. Лента ранжируется одной формулой для всех: свежесть, поведение
других людей, рейтинг продавца. Она не знает, что этот конкретный
человек всю неделю смотрит коляски, а машины ему не нужны, и верх
ленты у всех одинаковый.

Как считаем. Интерес к разделу — сумма событий этого человека с весами
по важности и затуханием по времени. Приём известный (так собрана лента
у Авито, и там простой счётчик с затуханием дал почти весь выигрыш —
переход на нейросеть добавил заметно меньше), но данные наши: смотрим
ровно то, что уже собирается в базе.

Веса. Написать продавцу — самый честный сигнал: человек потратил
усилие. Добавить в избранное — слабее, но это осознанное действие.
Открыть карточку — самый слабый и самый частый сигнал, поэтому весит
мало: иначе случайные заходы перевесят настоящий интерес.

Затухание. Позавчерашний интерес весит меньше вчерашнего: у половины
запросов на доске жизнь короткая — купил коляску и больше она не
нужна. HALF_LIFE_DAYS — за сколько дней вес события падает вдвое.

Раздел берём верхнего уровня (родитель категории): интерес к
«Электронике» полезнее, чем к «Наушникам» — по одной покупке наушников
рано судить, что человеку нужны только они.
"""
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Category, Chat, Favorite, Listing, ListingViewLog

# Сколько истории смотрим. Дальше месяца интерес почти всегда протух:
# вещь либо куплена, либо человек передумал.
HISTORY_DAYS = 30
HALF_LIFE_DAYS = 7.0

WEIGHT_CONTACT = 5.0
WEIGHT_FAVORITE = 3.0
WEIGHT_VIEW = 1.0


def _decay(age_days: float) -> float:
    return 0.5 ** (age_days / HALF_LIFE_DAYS)


def _root_id(category: Category | None):
    if not category:
        return None
    return category.parent_id or category.id


def category_interests(db: Session, user_id, now=None) -> dict:
    """
    {id раздела: вес} по истории человека. Пустой словарь — истории нет.

    Момент отсчёта округляем до часа. Иначе вес каждого события плыл бы
    непрерывно, а вместе с ним и порядок ленты: человек листает,
    подгружается вторая страница — и часть объявлений из неё уже
    побывала на первой. Ровно та же беда, что была у ленты с
    неустойчивой сортировкой; здесь её проще не создавать вовсе.
    """
    if not user_id:
        return {}

    now = (now or utcnow()).replace(minute=0, second=0, microsecond=0)
    since = now - timedelta(days=HISTORY_DAYS)
    scores: dict = {}

    def add(category, when, weight):
        root = _root_id(category)
        if not root or when is None:
            return
        age_days = max((now - when).total_seconds(), 0) / 86400.0
        scores[root] = scores.get(root, 0.0) + weight * _decay(age_days)

    # Написал продавцу.
    contacts = (
        db.query(Chat.created_at, Category)
        .join(Listing, Listing.id == Chat.listing_id)
        .join(Category, Category.id == Listing.category_id)
        .filter(Chat.buyer_id == user_id, Chat.created_at >= since)
        .all()
    )
    for when, category in contacts:
        add(category, when, WEIGHT_CONTACT)

    # Добавил в избранное.
    favorites = (
        db.query(Favorite.created_at, Category)
        .join(Listing, Listing.id == Favorite.listing_id)
        .join(Category, Category.id == Listing.category_id)
        .filter(Favorite.user_id == user_id, Favorite.created_at >= since)
        .all()
    )
    for when, category in favorites:
        add(category, when, WEIGHT_FAVORITE)

    # Открывал карточку. В журнале просмотров одна запись на человека в
    # день (там стоит уникальный индекс), так что десять заходов в одно
    # и то же объявление не перевесят собой всё остальное.
    views = (
        db.query(ListingViewLog.created_at, Category)
        .join(Listing, Listing.id == ListingViewLog.listing_id)
        .join(Category, Category.id == Listing.category_id)
        .filter(
            ListingViewLog.viewer_key == str(user_id),
            ListingViewLog.created_at >= since,
        )
        .limit(500)
        .all()
    )
    for when, category in views:
        add(category, when, WEIGHT_VIEW)

    return scores


def interest_boost(scores: dict, cap: float = 1.0) -> dict:
    """
    Веса разделов, приведённые к прибавке в формуле ранжирования.

    Сильнейший интерес получает cap, остальные — свою долю от него.
    Прибавка намеренно скромная: она поднимает интересный раздел выше
    при прочих равных, но не выносит наверх старое объявление только за
    то, что оно из «нужной» категории. Для сравнения, платное поднятие
    даёт до 6.0 — персонализация не должна перебивать оплаченное место.

    Значение подобрано против штрафа за однообразие в ранжировании
    (DIVERSITY в listings.py): при 1.5 интерес перевешивал штраф, и вся
    первая страница у вошедшего оказывалась одним разделом — проверил
    на выдаче. При 1.0 наверх выходят первые два-три объявления
    интересного раздела, дальше идут остальные.
    """
    if not scores:
        return {}
    top = max(scores.values())
    if top <= 0:
        return {}
    return {cid: cap * (weight / top) for cid, weight in scores.items()}
