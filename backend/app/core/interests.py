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
    # До самого верха: на третьем уровне parent_id — это подраздел.
    from app.core.category_tree import root_of

    return root_of(category).id


def category_interests(db: Session, user_id, now=None) -> tuple[dict, dict]:
    """
    Веса разделов и подразделов по истории человека.

    Возвращает две пары {id: вес}: по разделам верхнего уровня и по
    подразделам. Пустые словари — истории нет.

    Два уровня, а не один: раздел говорит, куда человек смотрит вообще,
    подраздел — что именно он ищет. Тот, кто всю неделю открывает
    наушники, хочет видеть наушники, а не всю «Электронику» подряд.
    Раздел при этом тоже нужен — он подсказывает смежное: у смотревшего
    коляски уместны и автокресла.

    Момент отсчёта округляем до часа. Иначе вес каждого события плыл бы
    непрерывно, а вместе с ним и порядок ленты: человек листает,
    подгружается вторая страница — и часть объявлений из неё уже
    побывала на первой. Ровно та же беда, что была у ленты с
    неустойчивой сортировкой; здесь её проще не создавать вовсе.
    """
    if not user_id:
        return {}, {}

    now = (now or utcnow()).replace(minute=0, second=0, microsecond=0)
    since = now - timedelta(days=HISTORY_DAYS)
    roots: dict = {}
    subs: dict = {}

    def add(category, when, weight):
        if not category or when is None:
            return
        age_days = max((now - when).total_seconds(), 0) / 86400.0
        value = weight * _decay(age_days)
        root = _root_id(category)
        if root:
            roots[root] = roots.get(root, 0.0) + value
        # Подраздел — только если он и правда подраздел: у объявления
        # прямо в разделе верхнего уровня второго уровня нет.
        if category.parent_id:
            subs[category.id] = subs.get(category.id, 0.0) + value

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

    return roots, subs


def interest_boost(scores: dict, cap: float = 0.5) -> dict:
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
    на выдаче.

    Разделу достаётся половина прежней прибавки: вторую половину теперь
    даёт подраздел (SUB_CAP ниже), и вместе они не должны выходить за
    прежний потолок. Иначе интерес снова начнёт перевешивать
    разнообразие.
    """
    if not scores:
        return {}
    top = max(scores.values())
    if top <= 0:
        return {}
    return {cid: cap * (weight / top) for cid, weight in scores.items()}


# Потолок прибавки за подраздел. Он весомее раздела: «наушники» точнее
# говорят о том, что человек ищет, чем «электроника». Вместе с разделом
# даёт не больше прежней общей прибавки — чтобы не перевесить штраф за
# однообразие и не отобрать место у оплаченного продвижения.
SUB_CAP = 0.7


def blend(items, key, max_run: int = 3):
    """
    Разбавляет подряд идущие объявления одного раздела.

    Ранжирование оценивает объявления поодиночке, поэтому похожие
    получают близкие оценки и слипаются в блоки: сначала десять машин,
    потом десять квартир. Человеку от второй одинаковой карточки пользы
    почти нет, а остальное к нему не пробивается — тем более когда
    сверху ещё и персональная прибавка тянет вверх целый раздел.

    Считаем здесь, а не оконной функцией в самом запросе: там формула
    вычислялась для каждого объявления базы и дважды за строку — 1.9
    секунды против 0.24 на живом объёме. База отдаёт порцию лучших,
    чередование раскладываем на ней.

    Правило простое: больше max_run подряд из одного раздела не идёт —
    следующим встаёт лучший из другого. Порядок внутри раздела не
    трогаем, он задан ранжированием.
    """
    if len(items) < 3:
        return items

    order = {id(item): i for i, item in enumerate(items)}
    groups: dict = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)

    out = []
    run_key, run_len = None, 0
    while groups:
        # Кандидаты в порядке ранжирования: первый в каждой группе.
        choices = sorted(groups.items(), key=lambda kv: order[id(kv[1][0])])
        pick = None
        for gkey, group in choices:
            if gkey == run_key and run_len >= max_run and len(groups) > 1:
                continue
            pick = gkey
            break
        if pick is None:
            pick = choices[0][0]
        out.append(groups[pick].pop(0))
        if not groups[pick]:
            del groups[pick]
        run_len = run_len + 1 if pick == run_key else 1
        run_key = pick
    return out
