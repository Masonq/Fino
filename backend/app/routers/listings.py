import json
import re
import uuid

from app.core.urls import listing_path
from datetime import datetime, timedelta, date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, cast, case, exists, func, or_, Float
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.core.search_terms import variants as search_variants
from app.models import Listing, ListingStatus, ListingTranslation, ListingPhoto, Category, User, UserRole, PromotionType
from app.core.clock import utcnow

router = APIRouter(prefix="/api/listings", tags=["listings"])


class TranslationIn(BaseModel):
    language: str
    title: str
    description: str


class PhotoIn(BaseModel):
    url: str
    thumbnail_url: str | None = None


MAX_ATTRIBUTES_JSON_BYTES = 8000
# С запасом на настоящие объявления (обычно 5-20 коротких полей вроде
# площади/состояния/этажа — см. extract_attributes в tg_parse.py), но
# не мегабайты: без границы attributes принимал что угодно, вплоть до
# всего тела запроса (сдерживал только общий лимит nginx на 25 МБ) —
# впустую раздувало бы JSONB-колонку одним объявлением.
def _check_attributes_size(v: dict) -> dict:
    size = len(json.dumps(v, ensure_ascii=False))
    if size > MAX_ATTRIBUTES_JSON_BYTES:
        raise ValueError("attributes_too_large")
    return v


class ListingCreate(BaseModel):
    category_id: uuid.UUID
    source_language: str = "ru"
    # Верхняя граница отсекает опечатки вроде лишних нулей, нижняя — минус.
    # Без них в ленту попадают объявления, ломающие сортировку по цене.
    price: float | None = Field(None, ge=0, le=100_000_000)
    currency: str = "EUR"
    price_negotiable: bool = False
    attributes: dict = {}
    city: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    hide_exact_address: bool = False
    translations: list[TranslationIn]
    photos: list[PhotoIn] = Field(default_factory=list, max_length=10)

    @field_validator("attributes")
    @classmethod
    def check_attributes_size(cls, v):
        return _check_attributes_size(v)

    @field_validator("translations")
    @classmethod
    def check_translations(cls, v):
        if not v:
            raise ValueError("no_translations")
        for t in v:
            if not (t.title or "").strip():
                raise ValueError("empty_title")
            if len((t.title or "").strip()) < 3:
                raise ValueError("title_too_short")
        return v

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v):
        if v not in ("EUR", "RSD", "USD"):
            raise ValueError("bad_currency")
        return v


LISTING_TTL_DAYS = 45


# Порядок запасных языков. Английский понятен почти всем, поэтому он идёт
# сразу после родного; дальше — язык оригинала объявления.
FALLBACK_ORDER = {
    "ru": ["ru", "en", "sr"],
    "en": ["en", "ru", "sr"],
    "sr": ["sr", "en", "ru"],
}


def pick_translation(listing, lang: str):
    """
    Выбирает перевод осмысленно: сначала нужный язык, потом английский
    как наиболее понятный, потом остальные. Раньше при отсутствии перевода
    брался первый попавшийся — англичанину мог достаться сербский текст,
    хотя рядом лежал русский.
    """
    by_lang = {t.language: t for t in listing.translations}
    for candidate in FALLBACK_ORDER.get(lang, [lang, "en", "ru", "sr"]):
        if candidate in by_lang:
            return by_lang[candidate]
    return listing.translations[0] if listing.translations else None


def previous_price_of(listing) -> dict | None:
    """
    Цена до последней правки — для стрелки/перечёркнутой цены на
    карточке и странице объявления. Только последняя запись: для
    индикатора вся история не нужна, важно лишь «было дороже/дешевле».
    """
    if not listing.price_history:
        return None
    last = listing.price_history[-1]
    return {"price": last["price"], "currency": last["currency"]}


def _active_promo_ids(db: Session, listing_ids) -> dict:
    """
    Какие из перечисленных объявлений сейчас куплены как крупная
    карточка (XL) или выделены цветом — один запрос на всю партию
    карточек и сразу на оба типа, не по одному на каждую карточку и
    не по отдельному запросу на каждый тип: их могут быть десятки на
    одной странице ленты.

    Возвращает {PromotionType.xl_card: {id, id, ...}, PromotionType.highlight: {...}}.
    """
    from app.models import Promotion, PromotionStatus

    ids = [i for i in listing_ids if i]
    result = {PromotionType.xl_card: set(), PromotionType.highlight: set()}
    if not ids:
        return result
    rows = (
        db.query(Promotion.listing_id, Promotion.type)
        .filter(
            Promotion.listing_id.in_(ids),
            Promotion.type.in_(list(result.keys())),
            Promotion.status == PromotionStatus.paid,
            or_(Promotion.expires_at.is_(None), Promotion.expires_at > utcnow()),
        )
        .all()
    )
    for listing_id, promo_type in rows:
        result[promo_type].add(listing_id)
    return result


@router.post("")
def create_listing(
    payload: ListingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создаёт объявление от имени вошедшего пользователя."""
    from app.core.rate_limit import check_listing_limit
    from app.models import UserRole
    check_listing_limit(db, user.id, is_business=user.role == UserRole.seller_business)

    owner_id = user.id
    category = db.query(Category).get(payload.category_id)
    if not category:
        raise HTTPException(404, "category_not_found")

    listing = Listing(
        owner_id=owner_id,
        category_id=payload.category_id,
        source_language=payload.source_language,
        price=payload.price,
        currency=payload.currency,
        price_negotiable=payload.price_negotiable,
        attributes=payload.attributes,
        city=payload.city,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
        hide_exact_address=payload.hide_exact_address,
        status=ListingStatus.pending_moderation,
        expires_at=utcnow() + timedelta(days=LISTING_TTL_DAYS),
    )
    db.add(listing)
    db.flush()

    for t in payload.translations:
        db.add(ListingTranslation(
            listing_id=listing.id,
            language=t.language,
            title=t.title,
            description=t.description,
            is_auto_translated=False,
        ))

    for idx, photo in enumerate(payload.photos):
        db.add(ListingPhoto(
            listing_id=listing.id,
            url=photo.url,
            thumbnail_url=photo.thumbnail_url or photo.url,
            sort_order=idx,
            is_cover=(idx == 0),
        ))

    db.commit()
    db.refresh(listing)
    return {"id": str(listing.id), "status": listing.status}


@router.get("")
def search_listings(
    q_text: str | None = Query(None, alias="q"),
    category_slug: str | None = None,
    city: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    currency: str | None = None,
    with_photo: bool | None = None,
    delivery: bool | None = None,
    safe_deal: bool | None = None,
    # Ответы на вопросы раздела, для которых нет структурного поля
    # («1 комната» и т.п.) — отдельными группами синонимов, а не
    # приклеенное к q слово. Группы разделены ";;", синонимы внутри
    # группы — "|". Каждая группа обязательна (AND), внутри группы
    # достаточно любого слова (OR).
    extra_terms: str | None = Query(None),
    # «Купить/Снять/Посуточно», «Ищу работу/Ищу сотрудника» — структурный
    # атрибут (attributes.deal_type), а не угадывание по словам в тексте.
    # Раньше это тоже шло через extra_terms поиском слова «аренда» и
    # находило чужие объявления с этим словом («ищу квартиру в аренду»
    # вместо «сдаю квартиру»), а не только те, что реально сдают.
    deal_type: str | None = Query(None),
    # Марка — тоже структурный атрибут (attributes.brand), выбор из
    # списка на лендинге «Авто», а не текстовый поиск.
    brand: str | None = Query(None),
    model: str | None = Query(None),
    # Общий механизм для остальных структурных полей раздела (год
    # выпуска, пробег, коробка передач, тип кузова и подобное) — раньше
    # под каждое такое поле заводили отдельный именованный параметр
    # (deal_type/brand/model) или не заводили вовсе, и оно просто
    # показывалось на лендинге, ничего не фильтруя по-настоящему (так
    # обнаружился «Год выпуска» у авто — поле было, а бэкенд его не
    # принимал совсем). Теперь один параметр на всё разом, не JSON-
    # объект под каждое новое поле в будущем. attr_eq — точное
    # совпадение атрибута («автомат», «внедорожник»), attr_range —
    # диапазон числового атрибута (пробег, год). Оба — JSON-строкой в
    # query, а не отдельными полями: FastAPI не умеет заранее знать
    # список ключей объекта.
    attr_eq: str | None = Query(None),
    attr_range: str | None = Query(None),
    sort: str = Query("relevance"),
    lang: str = Query("ru"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Listing).options(
        joinedload(Listing.translations), joinedload(Listing.photos),
        joinedload(Listing.owner),
    ).filter(Listing.status == ListingStatus.active)

    # Цена в фильтре и в сортировке — всегда в евро (фронт не даёт
    # выбрать валюту), а в базе объявление хранит цену в своей исходной
    # валюте — часть объявлений (в основном перенесённые из телеграм-
    # чатов) в RSD. Без пересчёта «от 100 до 1000€» находило бы и
    # объявления в 1000 RSD (≈8.5€), а «сначала дешёвые» — путало бы
    # порядок. Курс тот же, что уже используется в tg_import.py.
    price_in_eur = case(
        (Listing.currency == "EUR", Listing.price),
        else_=Listing.price / 117,
    )

    for group in (extra_terms.split(";;") if extra_terms else []):
        synonyms = [s.strip() for s in group.split("|") if s.strip()]
        if not synonyms:
            continue
        group_matches = []
        for syn in synonyms:
            syn_haystack = func.to_tsvector(
                "simple",
                func.coalesce(ListingTranslation.title, "") + " " +
                func.coalesce(ListingTranslation.description, ""),
            )
            group_matches.append(syn_haystack.op("@@")(func.plainto_tsquery("simple", syn)))
            group_matches.append(ListingTranslation.title.ilike(f"%{syn}%"))
            group_matches.append(ListingTranslation.description.ilike(f"%{syn}%"))
        q = q.filter(Listing.translations.any(or_(*group_matches)))

    # текстовый поиск по заголовку и описанию на любом из языков
    title_hit = None
    early_desc_hit = None
    if q_text:
        words = q_text.strip()
        # Марку пишут и латиницей, и кириллицей: «айфон» должен находить
        # «iPhone», иначе вещь лежит в ленте, а покупатель её не видит.
        spellings = search_variants(words) or [words]

        haystack = func.to_tsvector(
            "simple",
            func.coalesce(ListingTranslation.title, "") + " " +
            func.coalesce(ListingTranslation.description, ""),
        )
        matches = []
        for spelling in spellings:
            # Поиск по словам через полнотекстовый индекс. Дополнительно
            # ищем по началу слова, чтобы «дива» находило «диван» — люди
            # часто не дописывают.
            matches.append(haystack.op("@@")(func.plainto_tsquery("simple", spelling)))
            matches.append(ListingTranslation.title.ilike(f"{spelling}%"))
        q = q.filter(Listing.translations.any(or_(*matches)))

        # Название важнее описания: «стол» в заголовке — это стол, а в
        # описании дивана — соседняя вещь, о которой упомянули вскользь.
        # Такие объявления показываем, но ниже.
        title_hit = case(
            (
                exists().where(
                    (ListingTranslation.listing_id == Listing.id)
                    & or_(*[
                        ListingTranslation.title.ilike(f"%{spelling}%")
                        for spelling in spellings
                    ])
                ),
                0,
            ),
            else_=1,
        )

        # Промежуточный уровень между «в заголовке» и «где-то в описании»:
        # слово рядом с началом описания — ещё в тему («…для взрослых и
        # детей. ✅Детские и подростковые массажи» — услуга детского
        # массажа реально среди предложенного), а глубоко в длинном
        # перечне чужих вещей одного объявления-охапки («Платье, топы…
        # Тапочки детские… Карабурма») — уже нет, это соседняя вещь в
        # том же посте, не то, что человек ищет. Первые 150 символов —
        # там, где называют сам предмет/услугу, не весь текст целиком.
        early_desc_hit = case(
            (
                exists().where(
                    (ListingTranslation.listing_id == Listing.id)
                    & or_(*[
                        func.left(ListingTranslation.description, 150).ilike(f"%{spelling}%")
                        for spelling in spellings
                    ])
                ),
                0,
            ),
            else_=1,
        )

    if category_slug:
        # «Работа»: Вакансии/Резюме существуют как категории только для
        # классификации при импорте из Telegram-чатов (tg_parse.py) —
        # реальные объявления, размещённые через саму форму публикации,
        # остаются в родительской jobs, различие живёт в
        # attributes.listing_kind, не в category_id. Без этого псевдонима
        # плитка подраздела всегда находила бы ноль объявлений — ни один
        # человек, размещающий вакансию через форму, не попадал в
        # category_id именно «Вакансии».
        JOBS_KIND_ALIASES = {"vacancies": "vacancy", "resumes": "resume"}
        if category_slug in JOBS_KIND_ALIASES:
            jobs_cat = db.query(Category).filter(Category.slug == "jobs").first()
            if jobs_cat:
                q = q.filter(
                    Listing.category_id == jobs_cat.id,
                    Listing.attributes["listing_kind"].astext == JOBS_KIND_ALIASES[category_slug],
                )
        else:
            # По родительской категории показываем и её подкатегории — иначе
            # «Электроника» была бы пустой, ведь объявления лежат в «Телефонах».
            cat = db.query(Category).filter(Category.slug == category_slug).first()
            if cat:
                ids = [cat.id] + [c.id for c in cat.children]
                q = q.filter(Listing.category_id.in_(ids))
            else:
                q = q.join(Category).filter(Category.slug == category_slug)
    if city:
        # Точное совпадение вместо поиска подстроки: город теперь хранится
        # кодом, а не текстом, поэтому ilike с процентом впереди только
        # мешал — он не даёт использовать индекс.
        q = q.filter(Listing.city == city)
    if price_min is not None or price_max is not None:
        if price_min is not None:
            q = q.filter(price_in_eur >= price_min)
        if price_max is not None:
            q = q.filter(price_in_eur <= price_max)
    if currency:
        q = q.filter(Listing.currency == currency)
    if with_photo:
        q = q.filter(Listing.photos.any())
    if delivery:
        q = q.filter(Listing.delivery_available.is_(True))
    if safe_deal:
        q = q.filter(Listing.safe_deal_available.is_(True))
    if deal_type:
        # Недвижимость хранит это под attributes.deal_type, работа — под
        # attributes.listing_kind (уже так было устроено при переносе
        # объявлений из Telegram) — фильтр общий для обоих, чтобы
        # фронту не нужно было знать про разницу ключей по категориям.
        q = q.filter(or_(
            Listing.attributes["deal_type"].astext == deal_type,
            Listing.attributes["listing_kind"].astext == deal_type,
        ))
    if brand:
        q = q.filter(func.lower(Listing.attributes["brand"].astext) == brand.lower())
    if model:
        q = q.filter(func.lower(Listing.attributes["model"].astext) == model.lower())

    # Точное совпадение атрибута — {"transmission": "automatic"}. Битый
    # JSON или пустое значение внутри просто пропускаем, а не роняем
    # весь поиск: лучше отдать выдачу без этого одного фильтра, чем
    # ошибку на всю страницу из-за одного неверного символа в адресе.
    if attr_eq:
        try:
            filters = json.loads(attr_eq)
        except (ValueError, TypeError):
            filters = {}
        if isinstance(filters, dict):
            for key, value in filters.items():
                if value in (None, ""):
                    continue
                q = q.filter(func.lower(Listing.attributes[key].astext) == str(value).lower())

    # Диапазон числового атрибута — {"mileage_km": [0, 50000], "year":
    # [2015, null]}. Атрибуты — свободный JSONB, у части объявлений
    # значение может быть текстом, пустой строкой или вовсе
    # отсутствовать — приведение к числу прямо в SQL на такой строке
    # уронило бы весь запрос. Проверяем регулярным выражением, что
    # значение вообще похоже на число, прежде чем приводить и сравнивать
    # — непохожие строки просто не участвуют в фильтре, как если бы
    # атрибута не было вовсе.
    if attr_range:
        try:
            ranges = json.loads(attr_range)
        except (ValueError, TypeError):
            ranges = {}
        if isinstance(ranges, dict):
            for key, bounds in ranges.items():
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    continue
                lo, hi = bounds
                if lo is None and hi is None:
                    continue
                looks_numeric = Listing.attributes[key].astext.op("~")(r"^-?\d+(\.\d+)?$")
                numeric_value = cast(Listing.attributes[key].astext, Float)
                if lo is not None:
                    q = q.filter(looks_numeric, numeric_value >= float(lo))
                if hi is not None:
                    q = q.filter(looks_numeric, numeric_value <= float(hi))

    total = q.count()

    # Формула релевантности — свой аналог того же принципа, что у
    # крупных досок объявлений (Avito Ranker и подобные): не просто
    # «сначала новые», а взвешенная сумма из нескольких сигналов.
    # Не нейросеть на сотню признаков — прозрачная, читаемая формула,
    # уместная для нашего масштаба, но того же духа: свежесть — это
    # один из факторов, а не единственный.
    #
    #   поведение   — просмотры/избранное/переписки ЗА ПОСЛЕДНИЕ 7 ДНЕЙ,
    #                 не за весь срок жизни объявления. Раньше это было
    #                 «на день с публикации» (сумма / возраст) — то есть
    #                 фактически СРЕДНЯЯ скорость за всё время, а не
    #                 текущая. Объявление, которое было наверху месяц
    #                 назад и с тех пор только собирает просмотры просто
    #                 потому что наверху, держит эту среднюю скорость
    #                 вечно — замкнутый круг, из-за которого одни и те
    #                 же карточки не сходят с первых мест. Окно в 7 дней
    #                 его размыкает: то, что не смотрели всю неделю,
    #                 больше не считается «активным», сколько бы у него
    #                 ни было просмотров за прошлые месяцы.
    #   CTR         — просмотры / показы в ленте за то же окно. Без
    #                 знаменателя объявление наверху получает больше
    #                 просмотров просто потому что его чаще показывают,
    #                 а не потому что оно интереснее — CTR отличает
    #                 действительно кликабельную карточку от той, что
    #                 просто была на виду.
    #   свежесть    — плавно затухает со временем, не обрыв по дате
    #   продавец    — рейтинг, подтверждённый документ, бизнес-статус
    #   полнота     — как и раньше, is_complete
    #   старт       — гарантированный буст первые часы после публикации,
    #                 пока у объявления физически не было времени набрать
    #                 собственную статистику (см. ниже)
    #
    # Платное продвижение (bump/highlight/xl) эту формулу не подменяет,
    # а работает поверх нее — так же, как у Авито.
    # Тяжёлая часть — JOIN на продавца и шесть скоррелированных
    # подзапросов (просмотры/показы/избранное/чаты/галерея/описание
    # за 7 дней) — нужна только если реально сортируем по релевантности.
    # На странице поиска можно выбрать «сначала дешёвые»/«сначала
    # новые»: считать всю эту машинерию ради результата, который
    # потом не используется, значит гонять лишний JOIN и подзапросы
    # по каждой строке впустую.
    PRICE_DATE_SORTS = {"new", "old", "cheap", "expensive"}
    if sort in PRICE_DATE_SORTS:
        order = {
            "new": Listing.published_at.desc(),
            "old": Listing.published_at.asc(),
            "cheap": price_in_eur.asc().nullslast(),
            "expensive": price_in_eur.desc().nullslast(),
        }[sort]
    else:
        q = q.join(User, Listing.owner_id == User.id)
        age_days = func.extract("epoch", func.now() - Listing.published_at) / 86400.0
        freshness = 1.0 / (1.0 + age_days / 7.0)

        from app.models import ListingViewDaily, ListingSignalDaily, Favorite, Chat

        WINDOW_DAYS = 7
        since_day = date_type.today() - timedelta(days=WINDOW_DAYS)
        # Питоновский datetime как параметр, не SQL-литерал вида "interval
        # '7 days'" — тот работает только в Postgres, а тесты гоняются на
        # SQLite (см. tests/).
        since_ts = utcnow() - timedelta(days=WINDOW_DAYS)

        recent_views = (
            db.query(func.coalesce(func.sum(ListingViewDaily.count), 0))
            .filter(ListingViewDaily.listing_id == Listing.id, ListingViewDaily.day >= since_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_impressions = (
            db.query(func.coalesce(func.sum(ListingSignalDaily.impressions), 0))
            .filter(ListingSignalDaily.listing_id == Listing.id, ListingSignalDaily.day >= since_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_gallery = (
            db.query(func.coalesce(func.sum(ListingSignalDaily.gallery_views), 0))
            .filter(ListingSignalDaily.listing_id == Listing.id, ListingSignalDaily.day >= since_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_desc = (
            db.query(func.coalesce(func.sum(ListingSignalDaily.desc_expands), 0))
            .filter(ListingSignalDaily.listing_id == Listing.id, ListingSignalDaily.day >= since_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_favorites = (
            db.query(func.count(Favorite.id))
            .filter(Favorite.listing_id == Listing.id, Favorite.created_at >= since_ts)
            .correlate(Listing).scalar_subquery()
        )
        recent_chats = (
            db.query(func.count(Chat.id))
            .filter(Chat.listing_id == Listing.id, Chat.created_at >= since_ts)
            .correlate(Listing).scalar_subquery()
        )

        # Знаменатель — не весь возраст, а сколько дней из окна объявление
        # реально прожило: у вчерашнего объявления окно ещё не заполнилось,
        # делить сумму на 7 занизило бы его скорость впятеро.
        window_lived_days = func.greatest(func.least(age_days, float(WINDOW_DAYS)), 0.5)
        engagement = (
            recent_views + recent_favorites * 3 + recent_chats * 5
            + recent_gallery * 0.5 + recent_desc * 0.5
        ) / window_lived_days
        # +20 к знаменателю, не голый максимум с 1 — это ровно та проблема,
        # из-за которой всё вчера скакало местами: пока показов у
        # объявления одна-две штуки, каждый следующий показ (то есть
        # каждая перезагрузка ленты кем угодно) РЕЗКО дёргает CTR —
        # 15/1=15, 15/2=7.5 после одного-единственного лишнего показа.
        # Кто был наверху, того тут же обрезает следующий же показ, наверх
        # лезет кто-то другой — с тем происходит то же самое. Плавающий
        # базовый вес (лапласовское сглаживание) вместо жёсткого пола:
        # при малом числе показов CTR тяготеет к нейтральному нулю, а не
        # прыгает между произвольными числами, и становится осмысленным
        # только когда показов накопится сравнимо с этим весом.
        CTR_PRIOR_IMPRESSIONS = 20
        ctr = recent_views / (recent_impressions + CTR_PRIOR_IMPRESSIONS)
        behavior_score = func.ln(1 + engagement) + ctr * 2.0

        seller_score = (
            func.coalesce(User.rating_avg, 0) / 5.0
            + case((User.document_verified.is_(True), 0.5), else_=0)
            + case((User.role == UserRole.seller_business, 0.3), else_=0)
        )

        # Старт — гарантированная видимость первые часы после публикации,
        # вне зависимости от того, что покажет формула выше: у только что
        # опубликованного объявления просмотров и показов ещё физически не
        # может быть, и без явного буста ему неоткуда взять свои первые
        # просмотры, чтобы формула вообще начала его замечать. Тот же
        # экспоненциальный спад, что и у платного bump, но слабее и короче —
        # это не замена продвижению, а гарантия точки старта для всех.
        EXPLORE_BOOST_MAX = 1.2
        EXPLORE_DECAY_HOURS = 4.0
        age_hours = func.extract("epoch", func.now() - Listing.published_at) / 3600.0
        explore_boost = case(
            (Listing.published_at.isnot(None), EXPLORE_BOOST_MAX * func.exp(-age_hours / EXPLORE_DECAY_HOURS)),
            else_=0.0,
        )

        # Разовое поднятие (bump) — раньше подделывало published_at, теперь
        # свой явный бонус здесь: сильный сразу после покупки, гладко
        # затухающий по экспоненте, а не бессрочный обрубок по дате
        # публикации. BUMP_BOOST_MAX подобран так, чтобы в первые часы
        # перебивать почти любую органическую активность (максимум
        # остальных слагаемых для типичного объявления — единицы, не
        # десятки), BUMP_DECAY_HOURS — за сколько часов бонус спадает
        # вдвое: на 2*BUMP_DECAY_HOURS от покупки уже около четверти
        # исходной силы, дальше объявление конкурирует на общих основаниях.
        from app.models import Promotion, PromotionStatus

        BUMP_BOOST_MAX = 6.0
        BUMP_DECAY_HOURS = 10.0

        bump_started = (
            db.query(func.max(Promotion.starts_at))
            .filter(
                Promotion.listing_id == Listing.id,
                Promotion.type == PromotionType.bump,
                Promotion.status == PromotionStatus.paid,
                Promotion.starts_at.isnot(None),
            )
            .correlate(Listing)
            .scalar_subquery()
        )
        bump_hours = func.extract("epoch", func.now() - bump_started) / 3600.0
        bump_boost = case(
            (bump_started.isnot(None), BUMP_BOOST_MAX * func.exp(-bump_hours / BUMP_DECAY_HOURS)),
            else_=0.0,
        )

        relevance = (
            behavior_score * 2.0
            + freshness * 1.5
            + seller_score * 1.0
            + case((Listing.is_complete.is_(True), 0.8), else_=0)
            + bump_boost
            + explore_boost
        )

        order = relevance.desc()

    # Полные объявления впереди неполных: обрубок без цены и фотографии
    # тоже кому-то нужен, но встречать им человека нельзя.
    #
    # Не прячем совсем — только опускаем: вещь без снимка находится
    # поиском, открывается по ссылке и живёт в своём разделе.
    ordering = [Listing.is_complete.desc()]
    if title_hit is not None:
        # При поиске слово в названии важнее полноты: человек искал
        # конкретную вещь, а не красивую карточку. early_desc_hit —
        # промежуточный уровень между «в заголовке» и «просто где-то
        # в описании»: рано в тексте — ещё в тему, глубоко в длинном
        # перечне чужих вещей одного поста — уже нет.
        ordering = [title_hit, early_desc_hit, Listing.is_complete.desc()]
    ordering.append(order)
    items = q.order_by(*ordering).offset(offset).limit(limit).all()
    promo = _active_promo_ids(db, [l.id for l in items])

    # Показ в выдаче — отдельный сигнал от открытия карточки, нужен для
    # CTR (просмотры/показы) в формуле релевантности. Считаем и на
    # relevance, и на других сортировках — иначе на "новые"/"дешёвые"
    # показы вообще не копились бы, а объявление могло сортироваться
    # по CTR из одной пустой выдачи.
    from app.core.signals import bump_impressions
    bump_impressions(db, [l.id for l in items])

    def serialize(listing: Listing):
        translation = pick_translation(listing, lang)
        if not translation and listing.translations:
            translation = listing.translations[0]
        cover = next((p for p in listing.photos if p.is_cover), listing.photos[0] if listing.photos else None)
        return {
            "id": str(listing.id),
            "title": translation.title if translation else None,
            "price": float(listing.price) if listing.price else None,
            "previous_price": previous_price_of(listing),
            "is_free": bool(listing.is_free),
            "currency": listing.currency,
            "city": listing.city,
            "cover_photo": cover.thumbnail_url if cover else None,
            "delivery_available": listing.delivery_available,
            "is_xl": listing.id in promo[PromotionType.xl_card],
            "is_highlighted": listing.id in promo[PromotionType.highlight],
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
            "attributes": listing.attributes,
            "category_slug": listing.category.slug if listing.category else None,
            "is_company": bool(listing.owner and listing.owner.role == UserRole.seller_business),
            # Понятный адрес собираем здесь: он должен быть одинаков
            # везде — в ленте, в боте, в письме и в карте сайта.
            "path": listing_path(
                listing.id, translation.title if translation else "",
                listing.city,
                listing.category.slug if listing.category else None),
        }

    return {"total": total, "items": [serialize(l) for l in items]}


@router.get("/by-ids")
def listings_by_ids(
    ids: str = Query(..., description="идентификаторы через запятую"),
    lang: str = Query("ru"),
    db: Session = Depends(get_db),
):
    """
    Несколько объявлений одним запросом — для истории просмотров.
    Порядок сохраняем тот, что передали: он означает недавность.
    """
    try:
        wanted = [uuid.UUID(x) for x in ids.split(",") if x.strip()][:40]
    except ValueError:
        raise HTTPException(400, "bad_ids")

    if not wanted:
        return {"items": []}

    rows = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos), joinedload(Listing.owner))
        .filter(Listing.id.in_(wanted), Listing.status == ListingStatus.active)
        .all()
    )
    by_id = {l.id: l for l in rows}
    promo = _active_promo_ids(db, list(by_id.keys()))

    def serialize(l: Listing):
        tr = pick_translation(l, lang)
        cover = next((p for p in l.photos if p.is_cover), l.photos[0] if l.photos else None)
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "price": float(l.price) if l.price else None,
            "previous_price": previous_price_of(l),
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "attributes": l.attributes,
            "category_slug": l.category.slug if l.category else None,
            "is_company": bool(l.owner and l.owner.role == UserRole.seller_business),
            "is_xl": l.id in promo[PromotionType.xl_card],
            "is_highlighted": l.id in promo[PromotionType.highlight],
            # Понятный адрес: он должен быть одинаков везде — в ленте,
            # в избранном, в своих объявлениях.
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
            "cover_photo": cover.thumbnail_url if cover else None,
        }

    # снятые с публикации просто выпадают из списка
    return {"items": [serialize(by_id[i]) for i in wanted if i in by_id]}


@router.get("/my/list")
def my_listings(
    status: str | None = None,
    lang: str = Query("ru"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Объявления текущего пользователя — все статусы, включая скрытые."""
    q = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos))
        .filter(Listing.owner_id == user.id)
    )
    if status:
        q = q.filter(Listing.status == status)

    items = q.order_by(Listing.created_at.desc()).all()

    # Активные продвижения разом на все объявления — без этого
    # человек, купивший highlight/XL/поднятие, никак не мог убедиться
    # в самом «Моих объявлениях», что оно вообще подействовало и
    # сколько ему осталось: кнопка называлась одинаково что до, что
    # после покупки. bump тоже сюда попадает — его expires_at теперь
    # тоже выставляется (окно затухания, см. promotions.py), даже
    # хотя сам бонус в релевантности спадает плавно, а не обрывается
    # ровно в этот момент — для отображения статуса упрощение уместно.
    from app.models import Promotion, PromotionStatus
    listing_ids = [l.id for l in items]
    active_promos: dict = {}
    if listing_ids:
        rows = (
            db.query(Promotion.listing_id, Promotion.type, Promotion.expires_at)
            .filter(
                Promotion.listing_id.in_(listing_ids),
                Promotion.status == PromotionStatus.paid,
                or_(Promotion.expires_at.is_(None), Promotion.expires_at > utcnow()),
            )
            .all()
        )
        for listing_id, promo_type, expires_at in rows:
            active_promos.setdefault(listing_id, []).append({
                "type": promo_type.value,
                "expires_at": expires_at.isoformat() if expires_at else None,
            })

    def serialize(l: Listing):
        tr = pick_translation(l, lang)
        cover = next((p for p in l.photos if p.is_cover), l.photos[0] if l.photos else None)
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "price": float(l.price) if l.price else None,
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "attributes": l.attributes,
            "category_slug": l.category.slug if l.category else None,
            # Понятный адрес: он должен быть одинаков везде — в ленте,
            # в избранном, в своих объявлениях.
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
            "cover_photo": cover.thumbnail_url if cover else None,
            "status": l.status.value,
            # Автор должен видеть, почему объявление отклонили — без
            # этого оно просто пропадало из виду без объяснений.
            "rejection_reason": l.rejection_reason if l.status == ListingStatus.rejected else None,
            "views_count": l.views_count,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "active_promotions": active_promos.get(l.id, []),
        }

    # сводка по статусам — для вкладок на экране
    counts = {}
    for l in items:
        counts[l.status.value] = counts.get(l.status.value, 0) + 1

    return {"total": len(items), "counts": counts, "items": [serialize(l) for l in items]}


# Слова, по которым сравнивать бессмысленно: они есть в половине
# объявлений и роднят стол с диваном.
_EMPTY_WORDS = frozenset("""
продам продаю продается отдам новый новая новое новые бу состоянии
состояние отличном хорошем идеальном срочно недорого дёшево дешево
цена торг размер белград земун врачар почти как для под из
""".split())


def _title_words(listing, lang: str) -> tuple[set[str], set[str]]:
    """
    Слова названия: сама вещь и её признаки.

    Различать их важно: «велосипедный шлем» и «велосипедное кресло»
    делят определение, но вещи разные. Совпадение по предмету весит
    несравнимо больше, чем по признаку.

    Сравниваем по корням: «коляска» и «коляски» — одно слово, а человек
    пишет как придётся.
    """
    from app.core.morphology import analyzer, normal_form

    translation = pick_translation(listing, lang)
    title = (translation.title if translation else "") or ""
    morph = analyzer()

    things, traits = set(), set()
    for raw in re.findall(r"[\w-]{3,}", title.lower()):
        if raw in _EMPTY_WORDS:
            continue
        base = normal_form(raw) or raw
        if base in _EMPTY_WORDS:
            continue

        # Марки и модели латиницей — тоже предмет: «Chicco» отличает
        # коляску от коляски вернее любого прилагательного.
        if raw.isascii() or not morph:
            things.add(base)
            continue

        part = morph.parse(base)[0].tag.POS
        (traits if part in ("ADJF", "ADJS", "PRTF") else things).add(base)

    return things, traits


@router.get("/{listing_id}/similar")
def similar_listings(
    listing_id: uuid.UUID,
    lang: str = Query("ru"),
    limit: int = Query(8, le=20),
    db: Session = Depends(get_db),
):
    """
    Похожие объявления.

    Главное — сходство по словам названия. Раздел и цена слишком грубы:
    в «Мебели» тысяча вещей, и рядом со столом оказывался шкаф за те же
    деньги. Человек, открывший коляску, хочет посмотреть другие коляски,
    а не всё детское в одном бюджете.

    Подкатегория, цена и город идут следом — они уточняют, но не решают.
    Объявления того же продавца показываем в последнюю очередь: человеку
    интереснее альтернативы, а не витрина одного магазина.
    """
    base = db.query(Listing).get(listing_id)
    if not base:
        raise HTTPException(404, "not_found")

    base_things, base_traits = _title_words(base, lang)

    q = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos), joinedload(Listing.owner))
        .filter(
            Listing.id != listing_id,
            Listing.status == ListingStatus.active,
            Listing.category_id == base.category_id,
        )
    )

    price = float(base.price) if base.price else None
    # Цена самого объявления — тоже в исходной валюте, пересчитываем в
    # евро для честного сравнения (та же причина, что и в search_listings
    # чуть выше по файлу: RSD и EUR — разные по величине числа).
    price_eur = (price if (price is None or base.currency == "EUR") else price / 117)
    if price_eur:
        # Цену не сужаем жёстко: похожая вещь может стоить вдвое дороже
        # из-за состояния, и отбрасывать её рано.
        price_in_eur = case(
            (Listing.currency == "EUR", Listing.price),
            else_=Listing.price / 117,
        )
        q = q.filter(price_in_eur.between(price_eur * 0.25, price_eur * 4))

    # Берём с запасом: отбор по словам идёт в памяти, и чем шире выборка,
    # тем больше шансов найти настоящее совпадение.
    candidates = q.limit(200).all()

    def score(l: Listing) -> tuple:
        things, traits = _title_words(l, lang)

        # Совпал сам предмет — это близко. Совпало только определение
        # («велосипедный шлем» и «велосипедное кресло») — это разные
        # вещи, и ставить их рядом нельзя.
        same_thing = bool(base_things & things)

        shared = len(base_things & things) * 3 + len(base_traits & traits)
        total = max(len(base_things | things) * 3 + len(base_traits | traits), 1)
        overlap = shared / total if base_things else 0

        same_city = 0 if (base.city and l.city == base.city) else 1
        own = 1 if l.owner_id == base.owner_id else 0

        if price_eur and l.price:
            l_price_eur = float(l.price) if l.currency == "EUR" else float(l.price) / 117
            diff = abs(l_price_eur - price_eur) / price_eur
        else:
            diff = 1.0

        # Сходство названий решает, остальное уточняет. Полные
        # объявления впереди: обрубок без фотографии в подборке
        # бесполезен — по нему не поймёшь, та ли это вещь.
        # Предмет решает: без совпадения по нему объявление уходит в
        # конец, каким бы близким ни было по прочему.
        return (own, 0 if same_thing else 1, -round(overlap, 2),
                0 if l.is_complete else 1, same_city, diff)

    candidates.sort(key=score)

    # Совсем непохожее не показываем: пустая полка честнее, чем полка
    # случайных вещей — человек решит, что подбор сломан.
    if base_things:
        # Показываем только то, где совпал сам предмет. Пустая полка
        # честнее полки случайных вещей: человек решит, что подбор
        # сломан, и перестанет ему верить.
        candidates = [
            l for l in candidates if _title_words(l, lang)[0] & base_things
        ]

    picked = candidates[:limit]
    promo = _active_promo_ids(db, [l.id for l in picked])

    def serialize(l: Listing):
        tr = pick_translation(l, lang)
        cover = next((p for p in l.photos if p.is_cover), l.photos[0] if l.photos else None)
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "price": float(l.price) if l.price else None,
            "previous_price": previous_price_of(l),
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "attributes": l.attributes,
            "category_slug": l.category.slug if l.category else None,
            "is_company": bool(l.owner and l.owner.role == UserRole.seller_business),
            "is_xl": l.id in promo[PromotionType.xl_card],
            "is_highlighted": l.id in promo[PromotionType.highlight],
            "cover_photo": cover.thumbnail_url if cover else None,
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    return {"items": [serialize(l) for l in picked]}


@router.get("/by-seller/{seller_id}")
def seller_listings(
    seller_id: uuid.UUID,
    lang: str = Query("ru"),
    limit: int = Query(20, le=60),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Активные объявления продавца для его открытой страницы.

    Только активные: черновики и снятые с публикации — его дело, а не
    покупателя. Путь отдельный от «моих объявлений», где статусы видны все.

    Отдаём порциями: у магазина их могут быть тысячи, и без счётчика с
    отступом страница показывала бы первые двадцать, а остальные оставались
    бы недостижимы.
    """
    q = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos))
        .filter(Listing.owner_id == seller_id, Listing.status == ListingStatus.active)
    )
    total = q.count()
    items = (
        q.order_by(Listing.published_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def serialize(l: Listing):
        tr = pick_translation(l, lang)
        cover = next((p for p in l.photos if p.is_cover), l.photos[0] if l.photos else None)
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "price": float(l.price) if l.price else None,
            "previous_price": previous_price_of(l),
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "attributes": l.attributes,
            "category_slug": l.category.slug if l.category else None,
            "cover_photo": cover.thumbnail_url if cover else None,
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    return {"total": total, "items": [serialize(l) for l in items]}


@router.get("/{listing_id}")
def _fuzz_coord(value: float, listing_id) -> float:
    """
    Размывает координату в пределах ~350 метров — детерминированно
    (тот же listing_id всегда даёт то же смещение, а не новое при
    каждой перезагрузке страницы, иначе точка на карте прыгала бы
    туда-сюда). Смещение зависит от того, широта это или долгота
    (используем сам факт вызова + значение как часть затравки), чтобы
    оба смещения по одному объявлению не совпадали.
    """
    import hashlib
    seed = f"{listing_id}:{value}".encode()
    h = int(hashlib.sha256(seed).hexdigest()[:8], 16)
    # ~350 метров в градусах — грубо, но fuzz и не претендует на точность
    offset = ((h % 1000) / 1000 - 0.5) * 0.006
    return round(value + offset, 5)


def get_listing(listing_id: str, request: Request, db: Session = Depends(get_db),
                viewer: User | None = Depends(get_current_user_optional)):
    query = db.query(Listing).options(
        joinedload(Listing.translations), joinedload(Listing.photos),
        joinedload(Listing.owner),
    )

    try:
        listing = query.get(uuid.UUID(listing_id))
    except ValueError:
        # Короткий хвост из понятного адреса: «45e17e58» вместо ключа
        # целиком. Название могли поправить, и адрес разойдётся с
        # нынешним — но хвост остаётся, и объявление найдётся по нему.
        if not re.fullmatch(r"[0-9a-f]{8}", listing_id):
            raise HTTPException(404, "not_found")
        listing = query.filter(
            cast(Listing.id, String).like(f"{listing_id}-%")
        ).first()

    if not listing:
        raise HTTPException(404, "not_found")

    # Не считаем просмотры владельца — иначе продавец, проверяющий своё
    # же объявление (например, из «Моих объявлений»), искусственно
    # завышает себе счётчик и делает вывод о несуществующем интересе.
    #
    # Один и тот же посетитель — не чаще раза в день на одно
    # объявление: раньше здесь считался каждый заход без всякого
    # предела, и обычное обновление страницы (F5) уже накручивало
    # счётчик до бесконечности, без всякого продвижения. viewer_key —
    # id вошедшего, иначе X-Device-Id с браузера, иначе IP как
    # последний запасной вариант.
    if not viewer or viewer.id != listing.owner_id:
        from app.core.login_events import _client_ip
        from app.models import ListingViewLog
        from datetime import date as date_type

        viewer_key = (
            str(viewer.id) if viewer
            else request.headers.get("x-device-id") or _client_ip(request) or "unknown"
        )

        from sqlalchemy.dialects.postgresql import insert as pg_insert
        dedup_stmt = pg_insert(ListingViewLog).values(
            id=uuid.uuid4(), listing_id=listing.id, viewer_key=viewer_key, day=date_type.today(),
        ).on_conflict_do_nothing(index_elements=["listing_id", "viewer_key", "day"])
        result = db.execute(dedup_stmt)

        # rowcount > 0 — запись реально появилась, этот посетитель
        # сегодня тут ещё не был. rowcount == 0 — ON CONFLICT сработал,
        # заход уже был засчитан, просмотр не считаем повторно.
        if result.rowcount > 0:
            listing.views_count += 1
            # И в дневную статистику — без неё дашборд продавца показывал
            # бы только одно растущее число, без единой возможности увидеть,
            # вырос интерес на этой неделе или упал.
            from app.models import ListingViewDaily
            stmt = pg_insert(ListingViewDaily).values(
                id=uuid.uuid4(), listing_id=listing.id, day=date_type.today(), count=1,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["listing_id", "day"],
                set_={"count": ListingViewDaily.count + 1},
            )
            db.execute(stmt)
        db.commit()

    from app.core.urls import listing_path

    return {
        "id": str(listing.id),
        # Понятный адрес: собираем здесь, чтобы он был одинаков везде —
        # в ленте, в боте, в письме и в карте сайта.
        "path": listing_path(listing.id, _own_title(listing),
                             listing.city,
                             listing.category.slug if listing.category else None),
        # Состояние: снятое объявление не исчезает — по нему смотрят, за
        # сколько ушла похожая вещь, и на него уже стоят ссылки. Но
        # человек должен видеть, что вещи больше нет, а не писать
        # продавцу впустую.
        "status": listing.status.value,
        "category_slug": listing.category.slug,
        "source_language": listing.source_language,
        "translations": {t.language: {"title": t.title, "description": t.description, "is_auto_translated": t.is_auto_translated} for t in listing.translations},
        "price": float(listing.price) if listing.price else None,
        # Последняя цена до правки — показываем перечёркнутой рядом с
        # новой, как у Авито. Только последнюю запись, не всю историю:
        # для одной строки на странице больше не нужно.
        "previous_price": previous_price_of(listing),
        "is_free": bool(listing.is_free),
        "currency": listing.currency,
        "price_negotiable": listing.price_negotiable,
        # Для объявлений из Telegram: связь идёт с автором напрямую, поэтому
        # отдаём его ник. Название чата-источника наружу не выносим — оно
        # нужно нам для дублей и жалоб, а покупателю ничего не даёт.
        "external_source": listing.external_source,
        "external_author": listing.external_author,
        "attributes": listing.attributes,
        # Переводы свободных атрибутов; язык выбирает клиент — так же,
        # как он уже делает с переводами заголовка и описания.
        "attributes_i18n": listing.attributes_i18n or {},
        "city": listing.city,
        # Точка на карте — необязательная: у большинства объявлений её
        # никогда не задавали (только текст города). hide_exact_address
        # решает не сам факт наличия координат, а то, показывать ли их
        # ТОЧНО чужим — размытие делаем тут, а не на фронте, чтобы точные
        # координаты вообще не покидали сервер для чужого просмотра.
        # Владельцу (когда редактирует своё же объявление) отдаём как
        # есть, без размытия — иначе, включив скрытие один раз, он бы
        # больше никогда не увидел, куда сам поставил метку, и не смог
        # бы её поправить осмысленно.
        "location_lat": (
            listing.location_lat
            if (viewer and viewer.id == listing.owner_id) or not listing.hide_exact_address
            or listing.location_lat is None
            else _fuzz_coord(listing.location_lat, listing.id)
        ),
        "location_lng": (
            listing.location_lng
            if (viewer and viewer.id == listing.owner_id) or not listing.hide_exact_address
            or listing.location_lng is None
            else _fuzz_coord(listing.location_lng, listing.id)
        ),
        "location_approximate": bool(
            listing.hide_exact_address and listing.location_lat is not None
            and not (viewer and viewer.id == listing.owner_id)
        ),
        "hide_exact_address": bool(listing.hide_exact_address),
        "photos": [{"id": str(p.id), "url": p.url, "is_cover": p.is_cover} for p in listing.photos],
        "views_count": listing.views_count,
        # Дата публикации и номер — номер сначала был первыми 8
        # символами UUID (…-f7642d6b), но это буквы вперемешку с
        # цифрами — «Объявление № f7642d6b» не читается и не
        # произносится вслух. number — настоящий автоинкремент в базе
        # (см. модель Listing), только для этой строки на странице.
        # Дату берём именно published_at, а не created_at — момент,
        # когда объявление реально появилось в выдаче, важнее момента
        # черновика.
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "number": listing.number,
        "owner": {
            "id": str(listing.owner.id),
            "display_name": listing.owner.display_name,
            "avatar_url": listing.owner.avatar_url,
            "is_company": listing.owner.role == UserRole.seller_business,
            "company_name": listing.owner.company_name if listing.owner.role == UserRole.seller_business else None,
            "rating_avg": listing.owner.rating_avg,
            "rating_count": listing.owner.rating_count,
            "document_verified": listing.owner.document_verified,
            "company_verified": listing.owner.company_verified,
            # Сам номер тут не отдаём — только флаг, есть ли он вообще.
            # Иконка звонка на этой странице ведёт в чат, где и решается,
            # раскрывать номер или нет; если его нет в профиле у
            # продавца совсем, показывать саму иконку незачем.
            "has_phone": bool(listing.owner.phone),
        },
        "delivery_available": listing.delivery_available,
        "safe_deal_available": listing.safe_deal_available,
    }


@router.post("/{listing_id}/signal")
def send_signal(listing_id: uuid.UUID, payload: dict, db: Session = Depends(get_db)):
    """Глубина взаимодействия с уже открытой карточкой — пролистал ли
    фото дальше первой, развернул ли полное описание. Тихий сигнал: не
    падает, если объявления уже нет, не требует авторизации, не
    возвращает ничего, что могло бы использоваться для накрутки счётом
    в ответе."""
    kind = payload.get("type")
    field = {"gallery_view": "gallery_views", "desc_expand": "desc_expands"}.get(kind)
    if not field:
        raise HTTPException(400, "bad_signal_type")
    from app.core.signals import bump_signal
    bump_signal(db, listing_id, field)
    return {"ok": True}


@router.get("/{listing_id}/dashboard")
def listing_dashboard(
    listing_id: uuid.UUID,
    days: int = Query(30, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Показатели одного объявления для владельца: просмотры по дням,
    избранное, начатые переписки. Тот самый фундамент, на котором
    потом будет видно, помогает ли платное продвижение — сравнить
    дни с поднятием и без.
    """
    from app.models import ListingViewDaily, Favorite, Chat

    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id and user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_owner")

    since = utcnow().date() - timedelta(days=days - 1)
    daily_rows = (
        db.query(ListingViewDaily)
        .filter(ListingViewDaily.listing_id == listing_id, ListingViewDaily.day >= since)
        .all()
    )
    by_day = {r.day.isoformat(): r.count for r in daily_rows}
    # Дни без единого просмотра в базе не хранятся вовсе — достраиваем
    # нулями, иначе график показывал бы только те дни, где что-то было.
    daily = []
    for i in range(days):
        day = (since + timedelta(days=i)).isoformat()
        daily.append({"day": day, "views": by_day.get(day, 0)})

    favorites_count = db.query(Favorite).filter(Favorite.listing_id == listing_id).count()
    chats_count = db.query(Chat).filter(Chat.listing_id == listing_id).count()

    return {
        "views_total": listing.views_count,
        "favorites_count": favorites_count,
        "chats_count": chats_count,
        "status": listing.status.value,
        "is_complete": listing.is_complete,
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "expires_at": listing.expires_at.isoformat() if listing.expires_at else None,
        "daily": daily,
    }


class StatusIn(BaseModel):
    status: str


@router.patch("/{listing_id}/status")
def change_status(
    listing_id: uuid.UUID,
    payload: StatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Снять с продажи, вернуть в продажу или отметить проданным."""
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")

    allowed = {"active", "sold", "archived"}
    if payload.status not in allowed:
        raise HTTPException(400, "bad_status")

    was_sold = listing.status == ListingStatus.sold
    was_active = listing.status == ListingStatus.active
    listing.status = ListingStatus(payload.status)
    # Вернули в продажу — это по сути повторная публикация, продлеваем
    # срок заново. Без этого объявление, восстановленное после
    # архивации по сроку, тут же попало бы под неё снова при следующем
    # ночном проходе.
    if payload.status == "active" and not was_active:
        listing.expires_at = utcnow() + timedelta(days=LISTING_TTL_DAYS)
        listing.expiry_warned = False
    db.commit()

    # Отметили проданным — самый надёжный момент спросить об отзыве.
    # Приглашение уйдёт только тому, чья переписка похожа на сделку.
    if payload.status == "sold" and not was_sold:
        try:
            from app.core.review_invites import process_listing_sold
            process_listing_sold(db, listing.id)
        except Exception:
            pass   # приглашение не должно ломать смену статуса

    return {"status": listing.status.value}


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    # Модератор и админ удаляют любое объявление — например, мусорную
    # запись, которую парсер по ошибке принял за объявление (обрывок
    # обсуждения из чата). Обычный человек — только своё.
    is_staff = user.role in (UserRole.moderator, UserRole.admin)
    if listing.owner_id != user.id and not is_staff:
        raise HTTPException(403, "not_owner")

    # Просмотры по дням, избранное и продвижение — технические данные
    # без ценности как «история» (в отличие от переписки/жалобы/отзыва):
    # избранное — просто закладка, не след настоящего взаимодействия
    # между людьми, а просмотры и продвижение никто и не читает —
    # задача, которую они решают, умирает вместе с самим объявлением.
    # Раньше их не убирали при добавлении дашборда просмотров
    # (ListingViewDaily) — без этой очистки delete падал так же, как и
    # с чатом/отзывом, но фраза «есть переписка» вводила в заблуждение,
    # когда реальная причина — накопленная статистика просмотров или
    # чья-то закладка.
    from app.models import ListingViewDaily, ListingSignalDaily, ListingViewLog, Promotion, Favorite
    db.query(ListingViewDaily).filter(ListingViewDaily.listing_id == listing_id).delete()
    db.query(ListingSignalDaily).filter(ListingSignalDaily.listing_id == listing_id).delete()
    db.query(ListingViewLog).filter(ListingViewLog.listing_id == listing_id).delete()
    db.query(Promotion).filter(Promotion.listing_id == listing_id).delete()
    db.query(Favorite).filter(Favorite.listing_id == listing_id).delete()

    try:
        db.delete(listing)
        db.commit()
    except IntegrityError:
        # Ни у чатов, ни у жалоб, ни у отзывов, ни у приглашений
        # оставить отзыв, ни у обращений в поддержку нет
        # ondelete=CASCADE на listing_id — без этой обработки запрос
        # падал 500-й ошибкой на любом объявлении, у которого уже
        # накопился хоть один из них, а фронт эту ошибку молча
        # проглатывал («оставляем как было»), не показывая ничего.
        # Каскадом их не удаляем: это настоящая история, которую не
        # стоит стирать заодно с мусорной карточкой.
        db.rollback()
        raise HTTPException(409, "listing_has_history")
    return {"status": "deleted"}

class ListingUpdate(BaseModel):
    # Те же границы, что и при создании (см. ListingCreate выше) — их
    # тут не было вовсе: правка через PATCH принимала любое число,
    # включая отрицательное, огромное или NaN/бесконечность (Pydantic
    # по умолчанию не отклоняет ни то ни другое для float). Отрицательная
    # цена спокойно писалась бы в базу — Numeric(10,2) её не отклоняет
    # без явного CHECK; NaN Postgres принимает как обычное значение
    # numeric, и дальше оно тихо портит сравнения цены везде, где они
    # есть (сортировка «дешевле», формула релевантности ленты) — не
    # ошибкой, а молча неверным результатом. ge=0 заодно отсеивает и
    # NaN — сравнение NaN >= 0 в Python всегда False, так что граница
    # ловит его тем же путём, что и обычное отрицательное число.
    price: float | None = Field(None, ge=0, le=100_000_000)
    currency: str | None = None
    price_negotiable: bool | None = None
    city: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    hide_exact_address: bool | None = None
    attributes: dict | None = None
    title: str | None = None
    description: str | None = None
    delivery_available: bool | None = None
    safe_deal_available: bool | None = None

    @field_validator("attributes")
    @classmethod
    def check_attributes_size(cls, v):
        return _check_attributes_size(v) if v is not None else v


@router.patch("/{listing_id}")
def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Правка своего объявления. Изменение текста или цены возвращает его
    на проверку — иначе можно было бы опубликовать безобидное объявление,
    дождаться одобрения и подменить содержимое.
    """
    listing = db.query(Listing).options(joinedload(Listing.translations)).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")

    content_changed = False

    for field in ("price", "currency", "price_negotiable", "city",
                  "hide_exact_address",
                  "attributes", "delivery_available", "safe_deal_available"):
        value = getattr(payload, field)
        if value is None:
            continue
        # На повторную проверку отправляем только настоящую правку —
        # раньше поле считалось «изменённым», если оно вообще пришло
        # в запросе, а форма редактирования всегда шлёт все поля,
        # даже нетронутые: любое сохранение, включая нажатие «Сохранить»
        # без единой правки, гнало объявление на модерацию заново.
        current = getattr(listing, field)
        if field == "price":
            current_cmp = float(current) if current is not None else None
        else:
            current_cmp = current
        # Старую цену — в историю, до того как перезаписали. Только на
        # реальное изменение, не на каждое сохранение формы: иначе одна
        # и та же цена копилась бы записью на каждое нажатие «Сохранить».
        if field == "price" and value != current_cmp and current_cmp is not None:
            history = list(listing.price_history or [])
            history.append({
                "price": current_cmp,
                "currency": listing.currency,
                "changed_at": utcnow().isoformat(),
            })
            listing.price_history = history
        setattr(listing, field, value)
        if field in ("price", "city") and value != current_cmp:
            content_changed = True

    # Координаты — отдельно от общего цикла выше: там None означает
    # «поле не прислали, не трогаем», а тут null нужно уметь прислать
    # НАРОЧНО — кнопка «Убрать точку» на карте шлёт именно
    # location_lat: null, чтобы стереть ранее поставленную метку. Общий
    # цикл такое молча проигнорировал бы (value is None -> continue),
    # и метка оставалась бы в базе навсегда, что бы ни нажимали.
    # model_fields_set — какие поля реально пришли в теле запроса,
    # включая присланные как null, в отличие от вовсе отсутствующих.
    if "location_lat" in payload.model_fields_set:
        listing.location_lat = payload.location_lat
    if "location_lng" in payload.model_fields_set:
        listing.location_lng = payload.location_lng

    if payload.title is not None or payload.description is not None:
        tr = next(
            (t for t in listing.translations if t.language == listing.source_language),
            listing.translations[0] if listing.translations else None,
        )
        if tr:
            new_title = payload.title.strip()[:200] if payload.title is not None else tr.title
            new_description = payload.description.strip() if payload.description is not None else tr.description
            text_changed = new_title != (tr.title or "") or new_description != (tr.description or "")
            tr.title = new_title
            tr.description = new_description

            if text_changed:
                content_changed = True

                # Автопереводы на другие языки теперь не соответствуют
                # исходнику — translate_listing() (запускается при
                # одобрении) пополняет только недостающие языки и не
                # трогает уже существующие, так что без удаления старый
                # перевод остался бы навсегда рассинхронизирован с
                # правкой. Написанный вручную (is_auto_translated=False)
                # перевод не трогаем — его мог оставить сам продавец на
                # другом языке.
                for other in list(listing.translations):
                    if other is not tr and other.is_auto_translated:
                        listing.translations.remove(other)

    # Обратно на проверку — и если объявление было активным (тогда
    # правка временно снимает его с публикации до одобрения), и если
    # оно было отклонено: это тот самый случай, ради которого правку
    # вообще открывают после отказа — поправили и хотят, чтобы
    # объявление снова дошло до модератора, а не осталось «отклонено»
    # навсегда.
    if content_changed and listing.status in (ListingStatus.active, ListingStatus.rejected):
        listing.status = ListingStatus.pending_moderation

    # Полнота могла измениться: дописали цену — объявление поднимется в
    # ленте, стёрли название — опустится.
    listing.is_complete = _looks_complete(listing)

    db.commit()
    return {"status": listing.status.value}


@router.post("/{listing_id}/photos")
def add_photo(
    listing_id: uuid.UUID,
    payload: PhotoIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Добавляет фото к уже существующему объявлению.

    Раньше фотографии задавались только при первой публикации —
    отклонённое именно за фото объявление («Плохие или чужие фото»)
    нечем было починить: поправить текст можно, а заменить снимки
    негде. Тот же смысл, что и правка текста: реальное изменение
    отправляет объявление на повторную проверку.
    """
    listing = db.query(Listing).options(joinedload(Listing.photos)).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")
    if len(listing.photos) >= 10:
        raise HTTPException(400, "too_many_photos")

    next_order = max((p.sort_order for p in listing.photos), default=-1) + 1
    photo = ListingPhoto(
        listing_id=listing.id,
        url=payload.url,
        thumbnail_url=payload.thumbnail_url or payload.url,
        sort_order=next_order,
        is_cover=not listing.photos,   # первое фото у объявления — сразу обложка
    )
    db.add(photo)

    # Тот же смысл, что и в update_listing() — добавление фото после
    # отказа именно за фото должно возвращать на проверку, а не
    # оставлять «отклонено» навсегда.
    if listing.status in (ListingStatus.active, ListingStatus.rejected):
        listing.status = ListingStatus.pending_moderation
    listing.is_complete = _looks_complete(listing)
    db.commit()
    db.refresh(photo)
    return {"id": str(photo.id), "url": photo.url, "is_cover": photo.is_cover}


@router.delete("/{listing_id}/photos/{photo_id}")
def delete_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).options(joinedload(Listing.photos)).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")

    photo = next((p for p in listing.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(404, "photo_not_found")

    was_cover = photo.is_cover
    listing.photos.remove(photo)   # cascade="all, delete-orphan" удалит саму запись

    # Убрали обложку — назначаем следующую по порядку, иначе карточка
    # осталась бы без превью, хотя другие фото ещё есть.
    if was_cover and listing.photos:
        next_cover = sorted(listing.photos, key=lambda p: p.sort_order)[0]
        next_cover.is_cover = True

    if listing.status in (ListingStatus.active, ListingStatus.rejected):
        listing.status = ListingStatus.pending_moderation
    listing.is_complete = _looks_complete(listing)
    db.commit()
    return {"status": "deleted"}


def _own_title(listing) -> str:
    """Название на языке оригинала."""
    return next(
        (t.title for t in listing.translations
         if t.language == listing.source_language),
        listing.translations[0].title if listing.translations else "",
    )


def _looks_complete(listing) -> bool:
    """
    Полное объявление: понятное название, цена и фотография.

    Это тот минимум, при котором вещь можно рассмотреть и купить. Всё
    прочее — описание, город, доставка — желательно, но без них ещё
    можно обойтись.
    """
    title = next(
        (t.title for t in listing.translations
         if t.language == listing.source_language),
        listing.translations[0].title if listing.translations else "",
    )
    return bool(
        title_is_clear(title)
        and (listing.price is not None or listing.is_free)
        and listing.photos
    )


# Слова, с которых название вещи не начинается: союзы, местоимения,
# вводные обороты. Фраза, начатая с них, вырвана из середины.
# Слова, похожие на глаголы, но называющие услугу.
# Вещи, которых нет в словаре: слова новые, а объявления с ними живые.
_NEW_WORDS = frozenset("""
худи свитшот лонгслив бомбер тайтсы леггинсы кроксы слипоны
худак парка анорак шоппер кроссбоди клатч
эйрподсы аирподсы повербанк наушники-вкладыши
самокат гироскутер моноколесо электросамокат
""".split())

_SERVICE_VERBS = frozenset("""
поможем помощь помогу сделаем сделать делаем шьём шью починим ремонт
""".split())

_MID_SENTENCE_RE = re.compile(
    r"^(и|а|но|или|да|же|ведь|вот|это|эта|этот|эти|тут|там|"
    r"я|мы|вы|он|она|они|мне|нам|вам|его|её|их|"
    r"чем|что|как|где|когда|почему|зачем|который|которая|"
    r"вроде|кстати|также|тоже|ещё|еще|потом|затем|поэтому|"
    r"если|чтобы|пока|хотя|причём|причем)\b", re.I)


def title_is_clear(title: str | None) -> bool:
    """
    По названию понятно, что продают.

    «Hutschenreuther» — марка без вещи, «Чем занимался» — обрывок
    фразы: человек не поймёт, что там, пока не откроет. В ленте таким
    не место, хотя само объявление остаётся.

    Требуем существительное на кириллице: марка вещь не называет, а
    «iPhone» и «MacBook» — исключения, которые знают все.
    """
    from app.core.morphology import analyzer

    body = (title or "").strip()
    if len(body) < 4:
        return False

    # Одно слово без уточнений: «Обувь», «Тест», «Компьютер». Вещь
    # названа, но что именно продают — непонятно: размер, марка,
    # состояние не сказаны. Такое объявление всё равно откроют вслепую.
    #
    # Марку в одно слово это не задевает: «Skechers» узнаваем сам по
    # себе, а «обувь» — это раздел, а не вещь.
    # Латиницу это задевает так же: «Hutschenreuther» — марка без вещи,
    # и понять по ней, ваза там или сервиз, нельзя.
    if len(body.split()) == 1 and body.isalpha():
        return False

    # Заголовок, начатый с середины фразы: «И я могу взять на себя
    # уборку», «Чем занимался», «Вроде бы размер XS». Существительное в
    # таком есть, но названием вещи это не является.
    if _MID_SENTENCE_RE.match(body):
        return False

    # Название техники целиком на латинице — обычное дело: «Honor Magic
    # V3», «Canon RF 28mm», «Synology DS420j». Требовать от них русского
    # слова значит выбросить половину электроники.
    #
    # Признак настоящего названия — марка с моделью: два и более слова,
    # где есть цифры или заглавные посреди строки.
    # «AirPods 4», «Зимние Skechers» — марки узнаваемы и в одно слово.
    # Требовать двух значит выбрасывать половину обуви и техники.
    latin = re.findall(r"[A-Za-z][A-Za-z0-9./-]*", body)
    if len(latin) >= 2 or (latin and len(latin[0]) >= 4):
        return True

    morph = analyzer()
    if not morph:
        return True                              # словаря нет — не судим

    # Название вещи глагола не содержит: «Комод антикварный», «Монитор
    # Philips». Глагол превращает заголовок в рекламную фразу — «наш
    # капитан поможет», «уже более 4 лет помогаем клиентам».
    #
    # Отглагольные существительные не в счёт: «уборка», «доставка»,
    # «хранение» — это названия услуг, и они здесь уместны.
    for raw in re.findall(r"[а-яё]{4,}", body.lower()):
        # Названия услуг и новые слова глаголами не считаем: «худи»
        # словарь разбирает как глагол, а это вещь.
        if raw in _SERVICE_VERBS or raw in _NEW_WORDS:
            continue
        parsed = morph.parse(raw)[0]
        # Незнакомое слово словарь нередко принимает за глагол
        # («юникло»). Судим только по уверенным разборам.
        if parsed.tag.POS in ("VERB", "INFN") and parsed.score >= 0.5:
            return False

    # «2 велосипедных шлема», «3 стула» — после числа вещь стоит в
    # родительном, и это верная форма, а не обрывок.
    if re.match(r"^\d+\s", body):
        return True

    # Название вещи стоит в именительном падеже: «Комод антикварный»,
    # «Монитор Philips». Косвенный падеж выдаёт обрывок: «Времени
    # суток» — хвост от «Доброго времени суток».
    for raw in re.findall(r"[а-яё]{3,}", body.lower()):
        if raw in _EMPTY_WORDS:
            continue
        # Словарь не знает новых слов: «худи», «свитшот», «лонгслив».
        # Они уже вошли в обиход, и выбрасывать из-за них объявление
        # незачем.
        if raw in _NEW_WORDS:
            return True
        # Падеж не требуем: «Три мяча», «Два матраса», «Худи оверсайз» —
        # верные названия, а словарь видит в них родительный. Строгость
        # тут выбрасывает больше хорошего, чем ловит плохого.
        if any(p.tag.POS == "NOUN" for p in morph.parse(raw)[:4]):
            return True
    return False
