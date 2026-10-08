import logging
import json
import re
import uuid

from app.core.urls import listing_path
from datetime import datetime, timedelta, date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, and_, cast, case, exists, func, or_, Float
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, joinedload
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_current_user, require_named_user, get_current_user_optional
from app.core.database import get_db
from app.core.search_terms import variants as search_variants
from app.models import Listing, ListingStatus, ListingTranslation, ListingPhoto, Category, Currency, User, UserRole, PromotionType
from app.core.clock import utcnow


# Подразделы недвижимости, которые по сути — тип сделки в общем разделе
REAL_ESTATE_DEAL_ALIASES = {
    "flats-rent": ("flats", "rent"),
    "flats-sale": ("flats", "sale"),
    "daily-rent": ("real-estate", "daily"),
    "flats-studio": ("flats", "studio"),
}

router = APIRouter(prefix="/api/listings", tags=["listings"])


# Пороги длины. Нижняя граница — против заголовков вроде «Продам» и
# описаний в одно слово: по такому объявлению нельзя понять, что
# продают, и оно засоряет ленту. Верхняя — против полотен, вставленных
# из чужого поста: в базе поле заголовка 255 знаков, а описания 4000, и
# всё, что длиннее, молча обрезалось на середине слова.
#
# 10 знаков для заголовка — это «Стол Ikea» с запасом, но уже не
# «Продам». 200 — предел читаемого в карточке: длиннее человек всё
# равно не дочитает, а в ленте заголовок обрежется многоточием.
TITLE_MIN, TITLE_MAX = 10, 200
# Описание короче двадцати знаков не описывает ничего («Пишите в лс»),
# но требовать больше нельзя: у половины вещей и правда нечего
# добавить к названию и фотографии.
DESCRIPTION_MIN, DESCRIPTION_MAX = 20, 4000


class TranslationIn(BaseModel):
    language: str
    title: str
    description: str


class PhotoIn(BaseModel):
    url: str
    thumbnail_url: str | None = None
    is_video: bool = False


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

    @field_validator("photos")
    @classmethod
    def check_single_video(cls, v):
        # Одно видео на объявление — не карусель роликов, второе
        # только раздуло бы хранилище без реальной пользы.
        if sum(1 for p in v if p.is_video) > 1:
            raise ValueError("only_one_video_allowed")
        return v

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
        # Долларов в модели нет (Currency — только RSD и EUR): раньше
        # «USD» проходил проверку и падал уже на записи в базу.
        if v not in ("EUR", "RSD"):
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


def _category_path(category) -> list[dict]:
    """
    Цепочка от верхнего раздела к самой категории объявления — для
    «хлебных крошек» («Главная › Животные › Кролики»).

    Идём вверх по parent циклом, а не двумя жёстко прописанными
    обращениями (сейчас уровней всегда два — раздел и подраздел): если
    когда-нибудь появится третий, тут ничего править не придётся.
    Ограничение на 5 шагов — страховка от зацикливания, если в базе
    вдруг окажется категория, ссылающаяся сама на себя через цепочку.
    """
    chain = []
    node = category
    while node is not None and len(chain) < 5:
        chain.append({"slug": node.slug, "name": node.name})
        node = node.parent
    return list(reversed(chain))


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
    user: User = Depends(require_named_user),
    db: Session = Depends(get_db),
):
    """Создаёт объявление от имени вошедшего пользователя."""
    from app.core.rate_limit import check_listing_limit
    from app.models import UserRole
    check_listing_limit(db, user.id, is_business=user.role == UserRole.seller_business)

    # Длину проверяем здесь, а не валидатором схемы: ошибка схемы
    # уходит ответом 422 со списком внутри, а фронт читает код строкой —
    # человек видел бы общее «не получилось» вместо причины.
    for t in payload.translations:
        title, description = (t.title or "").strip(), (t.description or "").strip()
        if len(title) < TITLE_MIN:
            raise HTTPException(400, "title_too_short")
        if len(title) > TITLE_MAX:
            raise HTTPException(400, "title_too_long")
        if len(description) < DESCRIPTION_MIN:
            raise HTTPException(400, "description_too_short")
        if len(description) > DESCRIPTION_MAX:
            raise HTTPException(400, "description_too_long")

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
            is_video=photo.is_video,
        ))

    # Публикуем сразу, если и текст, и продавец не вызывают вопросов.
    # Иначе — в очередь модератору, как было всегда.
    db.flush()
    # Полнота — от неё зависит место в ленте. Раньше считалась только
    # при правке, и свежее объявление всегда числилось неполным.
    listing.is_complete = _looks_complete(listing)

    from app.core.autopublish import apply as maybe_publish

    published_now = maybe_publish(db, listing, user)
    if published_now:
        # Опубликовано сразу, без модерации (проверенный или знакомый продавец) — подарок за первое объявление и
        # награда пригласившему начислялись только при одобрении модератором, и такие люди их не получали.
        db.commit()
        try:
            from app.core.referrals import reward_referral_if_first_listing
            from app.core.welcome_bonus import reward_first_listing
            reward_referral_if_first_listing(db, listing)
            reward_first_listing(db, listing)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("бонус за первое объявление не начислен: %s", exc)

    db.commit()
    db.refresh(listing)
    return {"id": str(listing.id), "status": listing.status}


from app.core.category_tree import branch_ids as _branch_ids  # noqa: E402



CARD_PHOTOS = 5


def _map_point(listing) -> tuple[float | None, float | None]:
    """
    Точка для поиска на карте. Точный адрес — только если продавец его не скрыл; скрыт — округляем до ~1 км
    (видно район, но не дом). Координат нет вовсе — None: карта поставит объявление в центр его города.
    """
    lat, lng = getattr(listing, "location_lat", None), getattr(listing, "location_lng", None)
    if lat is None or lng is None:
        # адреса нет — центр города объявления, устойчиво разнесённый (~до 1,5 км) по номеру объявления, чтобы
        # объявления одного города не ложились в одну точку
        from app.data.city_coords import CITY_COORDS
        raw = (getattr(listing, "city", None) or "").strip()
        c = CITY_COORDS.get(raw)
        if not c:   # город записан названием («Белград», «Novi Sad») — ищем по подписям городов
            from app.data.cities_data import CITY_LABELS
            low = raw.lower()
            slug = next((s for s, names in CITY_LABELS.items() if low in {n.lower() for n in names.values()}), None)
            c = CITY_COORDS.get(slug or "")
        if not c:
            return None, None
        import hashlib, math
        h = int(hashlib.md5(str(listing.id).encode()).hexdigest()[:8], 16)
        a, r = (h % 360) * math.pi / 180, ((h >> 9) % 1000) / 1000 * 0.012
        return round(c[0] + math.cos(a) * r, 5), round(c[1] + math.sin(a) * r, 5)
    if getattr(listing, "hide_exact_address", False):
        return round(float(lat), 2), round(float(lng), 2)
    return float(lat), float(lng)


def _owner_storefront(db, owner_id):
    try:
        from app.routers.storefronts import by_owner
        return by_owner(owner_id, db).get("storefront")
    except Exception:  # noqa: BLE001
        return None


def card_photos(photos, cover) -> list[str]:
    """
    Превью для листания фото прямо в карточке ленты: обложка первой, дальше по порядку, видео не берём.
    Не больше пяти: дальше листать в ленте никто не станет, а каждая лишняя ссылка — лишние байты на карточку.
    Картинки браузер грузит, только когда до них долистали.
    """
    if not cover or cover.is_video:
        return []
    rest = sorted((p for p in photos if p is not cover and not p.is_video), key=lambda p: p.sort_order or 0)
    return [x.thumbnail_url or x.url for x in [cover, *rest][:CARD_PHOTOS]]

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
    # Только то, что отдают даром.
    #
    # Признак у объявлений был, а отбирать по нему было нельзя. Нужен
    # для вкладки «Даром» на главной: люди листают её из любопытства и
    # остаются.
    only_free: bool = Query(False),
    lang: str = Query("sr"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    # Кто смотрит — нужно для персональной прибавки за интересные
    # разделы. Необязательный: лента открыта и без входа, просто без
    # персонализации.
    viewer: User | None = Depends(get_current_user_optional),
    # Сам запрос — нужен, чтобы посчитать заход: из него берём адрес и
    # браузер для ключа посетителя (см. visit_daily.py).
    request: Request = None,
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
    sem_rank = None
    # Запрос без фильтра по словам — понадобится, если поиск ничего не
    # найдёт и мы будем пробовать с опечатками.
    before_words = None

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
        # Запоминаем запрос без фильтра по словам: если поиск ничего не
        # найдёт, повторим по похожести, сохранив остальные условия —
        # город, цену, раздел человек задал осознанно.
        before_words = q

        matches = []
        for spelling in spellings:
            # Поиск по словам через полнотекстовый индекс. Дополнительно
            # ищем по началу слова, чтобы «дива» находило «диван» — люди
            # часто не дописывают.
            matches.append(haystack.op("@@")(func.plainto_tsquery("simple", spelling)))
            matches.append(ListingTranslation.title.ilike(f"{spelling}%"))
        word_filter = Listing.translations.any(or_(*matches))

        # Поиск по смыслу (служба plonk-embed): «софа» находит «диван», «sofa» и «kauč» — тоже. Добавляем
        # к совпадениям по словам, когда их мало (< 40): точные совпадения остаются первыми (title_hit ниже),
        # близкие по смыслу идут следом по степени близости. Служба недоступна — поиск как раньше, по словам.
        sem_ids = []
        if q.filter(word_filter).limit(40).count() < 40:
            from app.core.semantic import similar_ids
            sem_ids = similar_ids(db, words)
        if sem_ids:
            q = q.filter(or_(word_filter, Listing.id.in_(sem_ids)))
            sem_rank = case({lid: i for i, lid in enumerate(sem_ids)}, value=Listing.id, else_=len(sem_ids))
        else:
            q = q.filter(word_filter)

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
            deal_alias = REAL_ESTATE_DEAL_ALIASES.get(category_slug)
            if cat and deal_alias:
                # «Аренда квартир», «Продажа квартир», «Посуточная аренда»: большинство квартир лежит в общем разделе
                # «Квартиры» с отметкой типа сделки (attributes.deal_type) — без этого подраздел показывал «ничего не
                # нашлось», хотя сдаваемых квартир десятки.
                parent_slug, deal = deal_alias
                parent = db.query(Category).filter(Category.slug == parent_slug).first()
                cond = Listing.category_id.in_(_branch_ids(cat))
                if parent and deal == "studio":
                    # «Гарсоньеры и студии» — по числу комнат, а не по сделке
                    cond = or_(cond, and_(Listing.category_id.in_(_branch_ids(parent)), Listing.attributes["rooms"].astext.in_(["studio", "0.5"])))
                elif parent:
                    cond = or_(cond, and_(Listing.category_id.in_(_branch_ids(parent)), Listing.attributes["deal_type"].astext == deal))
                q = q.filter(cond)
            elif cat:
                # Все уровни вниз, а не только прямые дети: появился третий
                # уровень («Оборудование» → «Пищевое»), и объявления из него
                # выпадали — счётчик обещал три, список показывал одно.
                q = q.filter(Listing.category_id.in_(_branch_ids(cat)))
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
    if only_free:
        q = q.filter(Listing.is_free.is_(True))

        # Услуги, работу и жильё сюда не пускаем.
        #
        # «Бесплатно» у них значит другое: массажист без цены — это не
        # подарок, а «цена по договорённости». Человек заходит во
        # вкладку «Даром» за вещами, которые отдают, и объявления
        # мастеров ему только мешают.
        #
        # Тот же приём применён при поиске перечней (см.
        # app/core/find_bundles.py): там эти разделы исключены по той же
        # причине.
        # По всей ветке, а не «родитель или сам»: с третьим уровнем
        # («Услуги» → «Мастера» → «Сантехник») родитель — уже не корень,
        # и мастера возвращались во вкладку.
        from app.core.category_tree import ids_under_roots

        q = q.filter(Listing.category_id.notin_(
            ids_under_roots(db, ("services", "jobs", "real-estate"))))

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
                # Список — «любое из»: «1 комната» на входе в раздел — это и 1, и 1,5 комнаты
                if isinstance(value, list):
                    vals = [str(v).lower() for v in value if v not in (None, "")]
                    if vals:
                        q = q.filter(func.lower(Listing.attributes[key].astext).in_(vals))
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

    # Ничего не нашлось — пробуем с опечатками.
    #
    # Поиск у нас точный по словам, и «каляска» или «диваан» не находят
    # ничего. Человек при этом решает, что вещи нет, и уходит — а она
    # лежит в ленте. Для площадки с тремя языками и вечной путаницей
    # латиницы с кириллицей это потеря на ровном месте.
    #
    # Включаем только когда обычный поиск пуст: на каждый запрос такое
    # сравнение считать дорого, а пустых запросов немного.
    corrected = None
    if q_text and total == 0 and before_words is not None:
        words = [w for w in q_text.strip().split() if len(w) >= 4]
        if words:
            from sqlalchemy import text as sql_text

            # Если расширения нет (база другая, деплой не прошёл) —
            # молча остаёмся без запасного поиска: пустая выдача хуже
            # ошибки, но ошибка хуже пустой выдачи.
            similar = []
            try:
                similar = db.execute(sql_text("""
                select distinct t.listing_id
                from listing_translations t
                where """ + " or ".join(
                    # Сравниваем слово со словом внутри заголовка, а не с
                    # заголовком целиком: «каляска» против «Коляска
                    # Bugaboo» даёт 0.26 и не проходит порог, а по слову
                    # — 0.5. Проверил на живых данных.
                    f"word_similarity(lower(:w{i}), lower(t.title)) > 0.45"
                    for i in range(len(words))
                ) + " limit 200"), {f"w{i}": w for i, w in enumerate(words)}).fetchall()
            except Exception:                              # noqa: BLE001
                db.rollback()

            found = [row[0] for row in similar]
            if found:
                corrected = did_you_mean(db, q_text)
                # Пересобираем запрос: прежний фильтр по словам ничего не
                # дал, а остальные условия (город, цена, раздел) должны
                # остаться — человек их задал осознанно.
                q = before_words.filter(Listing.id.in_(found))
                total = q.count()
                # Прежде здесь ставился флаг fuzzy — им никто не
                # пользовался ни дальше в запросе, ни в ответе.

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
    # Момент отсчёта для всех «возрастов» в формуле — начало текущего
    # часа, а не сейчас.
    #
    # Иначе оценка каждого объявления плывёт непрерывно: пока человек
    # листает, объявления с близкими оценками могут поменяться местами,
    # и одна карточка попадёт на обе страницы, а другая пропадёт.
    #
    # Оговорка о честности: повторы в ленте (3 на 80 карточек) этим не
    # объясняются — воспроизвести их подменой времени не удалось. В тот
    # момент шёл перенос из чатов и добавлял объявления, то есть состав
    # ленты менялся прямо во время листания. Округление времени —
    # страховка, снимающая один из источников сдвига, а не лечение той
    # находки.
    NOW = func.date_trunc("hour", func.now())

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
        age_days = func.extract("epoch", NOW - Listing.published_at) / 86400.0
        freshness = 1.0 / (1.0 + age_days / 7.0)

        from app.models import ListingViewDaily, ListingSignalDaily, Favorite, Chat

        WINDOW_DAYS = 7
        since_day = date_type.today() - timedelta(days=WINDOW_DAYS)
        # Питоновский datetime как параметр, не SQL-литерал вида "interval
        # '7 days'" — тот работает только в Postgres, а тесты гоняются на
        # SQLite (см. tests/).
        since_ts = utcnow() - timedelta(days=WINDOW_DAYS)

        # Верхняя граница окна — начало сегодняшнего дня, и это главное
        # здесь.
        #
        # Оценка учитывает показы в ленте, а лента сама их записывает при
        # каждом запросе: пролистал страницу — у полусотни карточек
        # изменились те самые данные, по которым идёт сортировка, и
        # следующая страница считается уже иначе. Одни объявления
        # сдвигаются назад и показываются второй раз, другие вперёд и не
        # показываются вовсе. На живой ленте: 2764 карточки, 204 повтора
        # и ровно столько же пропущенных.
        #
        # Поэтому считаем только то, что накопилось до сегодня. Порядок
        # держится сутки, а поведение людей всё равно измеряется неделей
        # — сегодняшние показы ничего к нему не добавляют, кроме
        # неустойчивости.
        until_day = date_type.today()

        recent_views = (
            db.query(func.coalesce(func.sum(ListingViewDaily.count), 0))
            .filter(ListingViewDaily.listing_id == Listing.id,
                    ListingViewDaily.day >= since_day, ListingViewDaily.day < until_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_impressions = (
            db.query(func.coalesce(func.sum(ListingSignalDaily.impressions), 0))
            .filter(ListingSignalDaily.listing_id == Listing.id,
                    ListingSignalDaily.day >= since_day, ListingSignalDaily.day < until_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_gallery = (
            db.query(func.coalesce(func.sum(ListingSignalDaily.gallery_views), 0))
            .filter(ListingSignalDaily.listing_id == Listing.id,
                    ListingSignalDaily.day >= since_day, ListingSignalDaily.day < until_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_desc = (
            db.query(func.coalesce(func.sum(ListingSignalDaily.desc_expands), 0))
            .filter(ListingSignalDaily.listing_id == Listing.id,
                    ListingSignalDaily.day >= since_day, ListingSignalDaily.day < until_day)
            .correlate(Listing).scalar_subquery()
        )
        recent_favorites = (
            db.query(func.count(Favorite.id))
            .filter(Favorite.listing_id == Listing.id,
                    Favorite.created_at >= since_ts, Favorite.created_at < NOW)
            .correlate(Listing).scalar_subquery()
        )
        recent_chats = (
            db.query(func.count(Chat.id))
            .filter(Chat.listing_id == Listing.id,
                    Chat.created_at >= since_ts, Chat.created_at < NOW)
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
        age_hours = func.extract("epoch", NOW - Listing.published_at) / 3600.0
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
        bump_hours = func.extract("epoch", NOW - bump_started) / 3600.0
        bump_boost = case(
            (bump_started.isnot(None), BUMP_BOOST_MAX * func.exp(-bump_hours / BUMP_DECAY_HOURS)),
            else_=0.0,
        )

        # Персональная прибавка за раздел, который человеку интересен по
        # его собственной истории (см. app/core/interests.py).
        #
        # Прибавка небольшая — 1.5 против 6.0 у платного поднятия и 1.2 у
        # стартового буста новых объявлений. Она поднимает интересный
        # раздел при прочих равных, но не выносит наверх что попало
        # только за категорию и не отбирает место у оплаченного
        # продвижения и у новичков, которым нужны первые показы.
        #
        # Сперва хотел оставить первый экран общим для всех и включать
        # персонализацию со второй страницы — ради тех же новичков. Так
        # делать нельзя: у страниц одной ленты получается разный
        # порядок, и часть объявлений либо показывается дважды, либо не
        # показывается вовсе. Тот же класс беды, что и с неустойчивой
        # сортировкой, только источник другой. Порядок в ленте должен
        # быть один, поэтому прибавка действует с первой карточки.
        #
        # К поиску по слову и к выдаче с фильтром по разделу прибавка не
        # применяется: там человек уже сам сказал, что ему нужно, и
        # подмешивать к этому прошлые интересы — значит спорить с прямым
        # запросом.

        personal_boost = 0.0
        if viewer and not q_text and not category_slug:
            from app.core.interests import (
                SUB_CAP, category_interests, interest_boost,
            )

            roots, subs = category_interests(db, viewer.id)
            # Раздел — куда человек смотрит вообще, подраздел — что
            # именно ищет. Смотревшему наушники поднимаем наушники, а не
            # всю «Электронику»; сам раздел тоже поднимаем, но слабее —
            # он подсказывает смежное, вроде автокресел к коляскам.
            root_boosts = interest_boost(roots)
            sub_boosts = interest_boost(subs, cap=SUB_CAP)
            if root_boosts:
                # Корень ищем подъёмом до конца: «родитель или сам» на
                # третьем уровне давал подраздел вместо раздела, и его
                # объявления оставались без буста.
                from app.core.category_tree import root_ids

                under: dict = {}
                for cid, rid in root_ids(db).items():
                    under.setdefault(rid, []).append(cid)
                personal_boost = case(
                    *[
                        (Listing.category_id.in_(under.get(cid, [cid])), weight)
                        for cid, weight in root_boosts.items()
                    ],
                    else_=0.0,
                )
            if sub_boosts:
                personal_boost = personal_boost + case(
                    *[
                        (Listing.category_id == cid, weight)
                        for cid, weight in sub_boosts.items()
                    ],
                    else_=0.0,
                )

        # Уже открывал — опускаем ниже. Лента, которая на каждом заходе
        # крутит одно и то же, быстро надоедает: человек уже видел эту
        # вещь и решение по ней принял.
        #
        # Опускаем, а не прячем: к вещи возвращаются — посмотреть ещё
        # раз, показать близким, написать продавцу через неделю. Совсем
        # убрать её из ленты значит отнять эту возможность.
        #
        # Штраф ослабевает со временем: вчерашний просмотр говорит о
        # том, что вещь уже смотрели, куда увереннее, чем просмотр
        # двухнедельной давности. И действует он только в общей ленте —
        # в поиске по слову человек ищет конкретное, и прятать от него
        # уже открытое было бы издевательством.
        seen_penalty = 0.0
        if viewer and not q_text and not category_slug:
            from app.models import ListingViewLog

            SEEN_PENALTY_MAX = 1.2
            SEEN_FADE_DAYS = 10.0
            # Что человек уже открывал — одним соединением с журналом
            # просмотров, а не подзапросом на каждую строку. Записей
            # немного: журнал хранит одну строку на человека в день,
            # и берём только его собственные.
            seen_alias = aliased(ListingViewLog)
            q = q.outerjoin(
                seen_alias,
                (seen_alias.listing_id == Listing.id)
                & (seen_alias.viewer_key == str(viewer.id)),
            )
            last_seen = func.max(seen_alias.created_at).over(
                partition_by=Listing.id)
            seen_days = func.extract("epoch", NOW - last_seen) / 86400.0
            seen_penalty = case(
                (last_seen.isnot(None),
                 SEEN_PENALTY_MAX * func.exp(-seen_days / SEEN_FADE_DAYS)),
                else_=0.0,
            )

        # Своё избранное в общей ленте не показываем наверху.
        #
        # Оно попадало туда через общий счёт популярности: сохранений
        # мало, и собственные добавления резко поднимали объявление —
        # человек видел вверху ленты ровно то, что сам уже отложил.
        #
        # У Авито избранное — сигнал об интересах, а не то, что
        # показывают: задача ленты, как они сами пишут, показать
        # объявления с наибольшей вероятностью обращения к продавцу.
        # А сохранённое человек уже нашёл, оно лежит у него в
        # «Избранном» — второй раз подсовывать его незачем.
        #
        # Штраф, а не полное исключение: вкусы человека эти объявления
        # всё же отражают, и вовсе выкидывать их из ленты — перебор.
        # И только в общей ленте: в поиске по слову прятать найденное
        # было бы издевательством.
        own_fav_penalty = 0.0
        if viewer and not q_text and not category_slug:
            fav_alias = aliased(Favorite)
            q = q.outerjoin(
                fav_alias,
                (fav_alias.listing_id == Listing.id)
                & (fav_alias.user_id == viewer.id),
            )
            OWN_FAV_PENALTY = 2.5
            # Считаем строки, а не берём максимум от номера: номер у нас
            # не число, и база такого максимума не умеет — поймал сразу
            # на запросе.
            own_fav_penalty = case(
                (func.count(fav_alias.id).over(partition_by=Listing.id) > 0,
                 OWN_FAV_PENALTY),
                else_=0.0,
            )

        relevance = (
            behavior_score * 2.0
            + freshness * 1.5
            + seller_score * 1.0
            + case((Listing.is_complete.is_(True), 0.8), else_=0)
            + bump_boost
            + explore_boost
            + personal_boost
            - seen_penalty
            - own_fav_penalty
        )

        # Штраф за место внутри своего раздела: первое объявление раздела
        # идёт как есть, второе чуть ниже, десятое — заметно ниже.
        #
        # Без него лента слипается в блоки: ранжирование оценивает
        # объявления поодиночке, похожие получают близкие оценки и встают
        # подряд. С персональной прибавкой становится ещё хуже — целый
        # раздел поднимается разом. Проверил на своей выдаче: со входом
        # вся первая страница оказалась из одного раздела.
        #
        # Считаем здесь, а не перестановкой готовой страницы: страница
        # может целиком состоять из одного раздела, и тогда переставлять
        # уже нечего. А оконная функция работает до нарезки на страницы,
        # порядок остаётся единым для всей ленты — разбивка не едет.
        #
        # Логарифм, а не линейный штраф: разница между первым и вторым
        # объявлением раздела должна быть заметной, между двадцатым и
        # двадцать первым — почти никакой, иначе большие разделы
        # проваливались бы в конец целиком.
        # Разбавления разделов здесь больше нет.
        #
        # Оно прошло два круга и оба раза вышло хуже. Первый заход —
        # оконная функция в самом запросе: формула считалась для каждого
        # объявления базы и дважды за строку, лента отвечала 1.9с вместо
        # 0.24с. Второй — та же работа на порции в 200 объявлений: порция
        # пересобирается по мере листания, порядок внутри неё меняется, и
        # человек снова видит то, что уже пролистал. На живой ленте это
        # 73 повтора из 400 карточек, отдельные объявления по четыре
        # раза — видно и на экране, и в замере.
        #
        # Лента должна быть предсказуемой: один порядок, никаких
        # повторов. Однообразие соседних карточек — беда меньшая, чем
        # выдача, которая крутит одно и то же по кругу.
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
        if sem_rank is not None:
            # близкие по смыслу (без слова из запроса) — по степени близости, а не по свежести
            ordering = [title_hit, early_desc_hit, sem_rank, Listing.is_complete.desc()]
    ordering.append(order)
    # Последний ключ — id, и он не про смысл выдачи, а про её
    # устойчивость. При равных значениях всех ключей выше (а так бывает
    # сплошь и рядом: пачка объявлений из одного импорта — одна дата,
    # одинаковая полнота, близкая релевантность) база вправе вернуть
    # такие строки в любом порядке, и порядок этот от запроса к запросу
    # не обязан совпадать. Лента же читается страницами через OFFSET:
    # одно и то же объявление попадало и в первую порцию, и во вторую, а
    # другое пропадало вовсе. В браузере это видно как повторяющиеся
    # карточки и жалоба React на одинаковые ключи.
    ordering.append(Listing.id)
    items = q.order_by(*ordering).offset(offset).limit(limit).all()

    promo = _active_promo_ids(db, [l.id for l in items])

    # Показ в выдаче — отдельный сигнал от открытия карточки, нужен для
    # CTR (просмотры/показы) в формуле релевантности. Считаем и на
    # relevance, и на других сортировках — иначе на "новые"/"дешёвые"
    # показы вообще не копились бы, а объявление могло сортироваться
    # по CTR из одной пустой выдачи.
    from app.core.signals import bump_impressions
    bump_impressions(db, [l.id for l in items])

    # Заход на сайт — считаем здесь, а не отдельным запросом с браузера.
    #
    # Лента открывается на главной, в поиске и в разделах, то есть на
    # любом входе в сайт, а лишний запрос ради счётчика — это лишняя
    # задержка на телефоне и лишний повод для блокировщиков. Считаем на
    # первой странице выдачи: подгрузка следующих — это тот же человек,
    # и второй раз его записывать незачем.
    if offset == 0:
        from app.models import record_visit
        record_visit(db, request, viewer.id if viewer else None)

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
            "price_mark": listing.price_mark,
            "is_free": bool(listing.is_free),
            "currency": listing.currency,
            "city": listing.city,
            "cover_photo": cover.thumbnail_url if cover else None,
            "map_point": _map_point(listing),
            "photos": card_photos(listing.photos, cover),
            "cover_is_video": bool(cover.is_video) if cover else False,
            "is_reserved": bool(listing.reserved_until and listing.reserved_until > utcnow()),
            "cover_video_url": cover.url if (cover and cover.is_video) else None,
            "delivery_available": listing.delivery_available,
            "is_xl": listing.id in promo[PromotionType.xl_card],
            "is_highlighted": listing.id in promo[PromotionType.highlight],
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
            "attributes": listing.attributes,
            "category_slug": listing.category.slug if listing.category else None,
            "is_company": bool(listing.owner and listing.owner.role == UserRole.seller_business),
            "owner_id": str(listing.owner_id) if listing.owner_id else None,  # «Скрыть продавца» долгим нажатием
            # Понятный адрес собираем здесь: он должен быть одинаков
            # везде — в ленте, в боте, в письме и в карте сайта.
            "path": listing_path(
                listing.id, translation.title if translation else "",
                listing.city,
                listing.category.slug if listing.category else None),
        }

    # журнал запросов — только первая страница обычного поиска (без «ещё»), для «Популярного» и отчёта
    if q_text and not offset:
        log_search(db, q_text, lang, total, corrected)
    out = {"total": total, "items": [serialize(l) for l in items]}
    if corrected:
        out["corrected"] = corrected  # показали результаты по исправленному запросу — интерфейс сообщит об этом
    return out


# «Только что» — полоска свежих объявлений в шапке главной.
#
# Берём последние объявления с фото за сутки, по одному на живого
# продавца (иначе один человек, выложивший десять вещей, займёт всю
# полоску); импортированные из чатов не ограничиваем — у них общий
# служебный владелец.
# Если за сутки в городе мало — добираем более старыми, чтобы полоска
# не пустела: пустая шапка выглядит как сломанная площадка. Каждое
# помечено fresh, чтобы кольцо у совсем свежих было ярче.
_FRESH_LIMIT = 14


@router.get("/fresh")
def fresh_listings(
    city: str | None = None,
    lang: str = Query("sr"),
    db: Session = Depends(get_db),
):
    now = utcnow()
    q = (
        db.query(Listing)
        .options(joinedload(Listing.photos), joinedload(Listing.translations), joinedload(Listing.category))
        .filter(Listing.status == ListingStatus.active, Listing.published_at.isnot(None))
        .filter(exists().where(ListingPhoto.listing_id == Listing.id))
    )
    if city:
        q = q.filter(Listing.city == city)
    rows = q.order_by(Listing.published_at.desc()).limit(_FRESH_LIMIT * 4).all()

    seen_owners: set = set()
    out = []
    for l in rows:
        # Импортированные из чатов висят на одном служебном владельце —
        # для них отбор «один на продавца» оставил бы одно объявление
        # из тысяч. Ограничиваем только живых продавцов.
        if not l.external_source:
            if l.owner_id in seen_owners:
                continue
        cover = next((p for p in l.photos if p.is_cover), l.photos[0] if l.photos else None)
        if not cover or cover.is_video or not (cover.thumbnail_url or cover.url):
            continue
        if not l.external_source:
            seen_owners.add(l.owner_id)
        tr = pick_translation(l, lang) or (l.translations[0] if l.translations else None)
        out.append({
            "id": str(l.id),
            "title": tr.title if tr else "",
            "price": float(l.price) if l.price else None,
            "currency": l.currency,
            "is_free": bool(l.is_free),
            "cover_photo": cover.thumbnail_url or cover.url,
            "published_at": l.published_at.isoformat(),
            "fresh": (now - l.published_at) < timedelta(hours=24),
            "path": listing_path(l.id, tr.title if tr else "", l.city, l.category.slug if l.category else None),
        })
        if len(out) >= _FRESH_LIMIT:
            break
    return {"items": out}


@router.get("/by-ids")
def listings_by_ids(
    ids: str = Query(..., description="идентификаторы через запятую"),
    lang: str = Query("sr"),
    db: Session = Depends(get_db),
):
    """
    Несколько объявлений одним запросом — для истории просмотров.
    Порядок сохраняем тот, что передали: он означает недавность.
    """
    # Негодные номера просто пропускаем, а не отказываем всему запросу.
    #
    # В историю просмотров однажды писался обрезок из красивого адреса —
    # восемь знаков вместо полного номера. Такие записи остались у людей
    # в браузере, и один обрезок в списке обрушивал страницу «Вы
    # смотрели» целиком, вместе с правильными записями.
    wanted = []
    for part in ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            wanted.append(uuid.UUID(part))
        except ValueError:
            continue
    wanted = wanted[:40]

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
            "price_mark": l.price_mark,
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
            "map_point": _map_point(l),
            "photos": card_photos(l.photos, cover),
            "cover_is_video": bool(cover.is_video) if cover else False,
            "is_reserved": bool(l.reserved_until and l.reserved_until > utcnow()),
            "cover_video_url": cover.url if (cover and cover.is_video) else None,
        }

    # снятые с публикации просто выпадают из списка
    return {"items": [serialize(by_id[i]) for i in wanted if i in by_id]}


@router.get("/my/list")
def my_listings(
    status: str | None = None,
    lang: str = Query("sr"),
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
            "map_point": _map_point(l),
            "cover_is_video": bool(cover.is_video) if cover else False,
            "is_reserved": bool(l.reserved_until and l.reserved_until > utcnow()),
            "cover_video_url": cover.url if (cover and cover.is_video) else None,
            # Когда объявление снимут само: показываем предупреждение и
            # кнопку продления, пока не поздно.
            "expires_at": l.expires_at.isoformat() if l.expires_at else None,
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


def _seller_key(listing) -> str:
    """
    Кто на самом деле продаёт. Объявления из чатов Telegram принадлежат
    служебному аккаунту — один на чат, а настоящий человек записан в
    external_author. Считать «продавцом» аккаунт нельзя: тысяча объявлений
    одного чата оказалась бы одним торговцем, и «не больше трёх от
    продавца» оставляло в выборке три штуки — оценки не стало ни у кого.
    """
    if listing.external_source and listing.external_author:
        return f"{listing.external_source}:{listing.external_author}"
    if listing.external_source:
        return f"{listing.external_source}-msg:{listing.id}"   # автор не назван — считаем разными
    return str(listing.owner_id)


def _condition_group(value) -> str | None:
    """'new' — новое; 'used' — как новое и б/у; иначе не сравниваем по состоянию."""
    if value == "new":
        return "new"
    if value in ("like_new", "used"):
        return "used"
    return None


_root_cache: dict = {"at": None, "map": {}}


def _root_slug(db, category_id) -> str | None:
    """Раздел верхнего уровня; словарь всех разделов держим десять минут."""
    from app.core.category_tree import root_slugs

    now = utcnow()
    stale = not _root_cache["at"] or (now - _root_cache["at"]).total_seconds() > 600
    if stale or category_id not in _root_cache["map"]:
        # Незнакомый раздел (только что заведённый) — тоже повод пересобрать.
        _root_cache["map"] = root_slugs(db)
        _root_cache["at"] = now
    return _root_cache["map"].get(category_id)


def _model_tokens(listing, lang: str) -> set[str]:
    """
    Числа и модели из названия: «15», «s23», «fx2», «256gb».

    Слова названия (_title_words) короче трёх букв отбрасывают, а именно
    «15» отличает iPhone 15 от iPhone 11 — и цену вдвое. Совпасть должен
    хотя бы один такой знак, если он есть у самого объявления.
    """
    translation = pick_translation(listing, lang)
    title = ((translation.title if translation else "") or "").lower()
    return {tok for tok in re.findall(r"[a-z]*\d+[a-z]*", title) if len(tok) <= 12}


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


# Тот же курс, что в поиске и сортировке по цене: сравнивать RSD с EUR
# напрямую нельзя, а точный курс дня тут не нужен — оценка грубая по
# своей природе.
RSD_PER_EUR = 117


# Оценка считается по сотням похожих объявлений и разбору их названий —
# на каждое открытие карточки это дорого. Держим готовый ответ в памяти
# процесса десять минут: цены на доске за это время не двигаются, а
# ключ включает саму цену, так что правка цены обнуляет оценку сразу.
_price_cache: dict = {}
_PRICE_TTL = 600


def compute_price_check(db, listing, lang: str) -> dict:
    """
    Оценка цены: дорого, дёшево или в рынке.

    Покупатель с доски объявлений всё равно делает это сам — открывает
    десяток похожих и смотрит, из чего выбирать. Считаем за него, и
    честно показываем, на чём считали: без этого любая оценка выглядит
    гаданием, и доверия к ней нет.

    Сравниваем с похожими по названию из того же раздела и города:
    раздела мало («Мебель» — это и табурет, и кухня), а название
    отличает стол от шкафа. Города — потому что одна и та же вещь в
    Белграде и в Нише стоит по-разному. Если в городе набралось меньше
    пяти похожих, смотрим по всей стране: лучше сравнение пошире, чем
    оценка по двум объявлениям.

    Границы «в рынке» — от четверти до трёх четвертей выборки: внутри
    них цена обычная, ниже — дёшево, выше — дорого. Проценты не
    показываем: точность тут кажущаяся.
    """
    base = listing
    if not base or not base.price or base.is_free:
        return {"verdict": None}

    key = (str(base.id), str(base.price), base.currency, lang)
    hit = _price_cache.get(key)
    if hit and (utcnow() - hit["at"]).total_seconds() < _PRICE_TTL:
        return hit["data"]

    base_things, _ = _title_words(base, lang)
    if not base_things:
        return {"verdict": None, "why": "no_words"}

    # Что берём за рынок. Всё, что тут написано, — ответ на один вопрос:
    # «а если цены на сайте занижены?». На своих же объявлениях честно
    # сравнивать можно, только защитившись от перекосов:
    #  - проданные — тоже в выборке. Заявленная цена, по которой вещь
    #    реально ушла, весит больше, чем цена, что месяцами висит;
    #  - объявления самого продавца не в счёт, и от каждого другого
    #    берём не больше двух: один торговец с тридцатью объявлениями
    #    иначе сам определил бы «рынок»;
    #  - состояние сравниваем с тем же: новое с б/у смешивать нельзя;
    #  - модель — с той же: «iPhone 11» и «iPhone 15» делят слово, но не
    #    цену.
    #
    # Строгость подобрана так, чтобы выборки не выродились в пустые:
    #  - «модель» проверяем только в электронике. Число в названии одежды
    #    или мебели — размер, год, габарит, а не модель; по нему сравнивать
    #    нельзя, иначе «Куртка 48» никогда не найдёт «Куртка 50» и оценки
    #    не будет вовсе;
    #  - состояние делим на две группы, а не на четыре: новое отдельно,
    #    остальное (как новое, б/у) вместе. Четыре группы дробили выборку
    #    настолько, что похожих не набиралось;
    #  - от одного продавца берём до трёх объявлений.
    # Свои объявления продавца в выборку не входят. Для перенесённых из чата
    # «свои» — того же external_author, а не того же служебного аккаунта.
    if base.external_source and base.external_author:
        not_mine = or_(Listing.external_author.is_(None), Listing.external_author != base.external_author)
    elif base.external_source:
        not_mine = Listing.id != base.id
    else:
        not_mine = Listing.owner_id != base.owner_id
    base_condition = _condition_group((base.attributes or {}).get("condition"))
    base_models = _model_tokens(base, lang) if _root_slug(db, base.category_id) == "electronics" else set()
    PER_SELLER = 3

    def prices_for(city: str | None) -> list[float]:
        q = (db.query(Listing)
             .options(joinedload(Listing.translations))
             .filter(Listing.id != base.id,
                     not_mine,
                     Listing.status.in_((ListingStatus.active, ListingStatus.sold)),
                     Listing.category_id == base.category_id,
                     Listing.price.isnot(None),
                     Listing.is_free.is_(False),
                     Listing.created_at >= utcnow() - timedelta(days=180)))
        if city:
            q = q.filter(Listing.city == city)
        if base_condition == "new":
            q = q.filter(Listing.attributes["condition"].astext == "new")
        elif base_condition == "used":
            q = q.filter(Listing.attributes["condition"].astext.in_(("like_new", "used")))
        out, per_owner = [], {}
        for other in q.order_by(Listing.created_at.desc()).limit(400).all():
            things, _ = _title_words(other, lang)
            # Совпасть должен сам предмет, а не признак: «стол» и
            # «стол письменный» — одно, «стол» и «стул» — разное.
            if not (things & base_things):
                continue
            if base_models and not (_model_tokens(other, lang) & base_models):
                continue
            seller = _seller_key(other)
            if per_owner.get(seller, 0) >= PER_SELLER:
                continue
            per_owner[seller] = per_owner.get(seller, 0) + 1
            price = float(other.price)
            if other.currency != Currency.eur:
                price /= RSD_PER_EUR
            out.append(price)
        return out

    prices = prices_for(base.city)
    scope = "city"
    if len(prices) < 5:
        wider = prices_for(None)
        if len(wider) > len(prices):
            prices, scope = wider, "country"
    if len(prices) < 5:
        few = {"verdict": None, "why": "few", "found": len(prices)}
        _price_cache[key] = {"at": utcnow(), "data": few}
        return few

    prices.sort()
    def at(share: float) -> float:
        return prices[min(len(prices) - 1, int(len(prices) * share))]

    low, mid, high = at(0.25), at(0.5), at(0.75)
    mine = float(base.price)
    if base.currency != Currency.eur:
        mine /= RSD_PER_EUR

    if mine < low:
        verdict = "cheap"
    elif mine > high:
        verdict = "expensive"
    else:
        verdict = "fair"

    data = {
        "verdict": verdict,
        "scope": scope,
        "based_on": len(prices),
        # Отдаём в евро: клиент показывает в валюте объявления сам.
        # mine_eur — цена самого объявления: по ней клиент ставит метку на шкале «дешевле / обычно / дороже».
        "mine_eur": round(mine, 2),
        "low_eur": round(low, 2),
        "median_eur": round(mid, 2),
        "high_eur": round(high, 2),
    }
    _price_cache[key] = {"at": utcnow(), "data": data}
    return data


@router.get("/for-you")
def for_you(
    lang: str = Query("sr"),
    limit: int = Query(12, le=30),
    user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    «Может быть интересно» — подборка под конкретного человека.

    Лента на главной уже учитывает его интересы, но там их перебивает
    свежесть: наверху то, что выложили час назад, а не то, что человеку
    нужно. Здесь наоборот — сначала совпадение с интересами, свежесть
    только как поправка.

    Истории нет — отдаём пусто, а не «популярное»: подборка «для вас»,
    собранная из случайного, обесценивает сам приём.
    """
    from app.core.interests import category_interests

    if not user:
        return {"items": []}

    roots, subs = category_interests(db, user.id)
    if not roots and not subs:
        return {"items": []}

    # Берём объявления из интересных разделов, свежие первыми, и уже
    # среди них расставляем по весу интереса. Ограничение по времени —
    # чтобы не показывать позапрошлогоднее: подборка должна быть про
    # то, что можно купить сейчас.
    wanted = list(subs.keys()) or list(roots.keys())
    rows = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos),
                 joinedload(Listing.category))
        .filter(Listing.status == ListingStatus.active,
                Listing.category_id.in_(wanted),
                Listing.published_at >= utcnow() - timedelta(days=60))
        .order_by(Listing.published_at.desc())
        .limit(limit * 6)
        .all()
    )
    if user:
        # Своё в подборке «может быть интересно» — насмешка.
        rows = [l for l in rows if l.owner_id != user.id]

    def weight(listing) -> float:
        return float(subs.get(listing.category_id, 0) or roots.get(listing.category_id, 0) or 0)

    rows.sort(key=weight, reverse=True)

    def card(l: Listing) -> dict:
        tr = pick_translation(l, lang)
        cover = next((p for p in l.photos if p.is_cover and not p.is_video),
                     next((p for p in l.photos if not p.is_video), None))
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "price": float(l.price) if l.price else None,
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
            "cover_photo": cover.thumbnail_url if cover else None,
            "map_point": _map_point(l),
        }

    return {"items": [card(l) for l in rows[:limit]]}


@router.get("/{listing_id}/price-check")
def price_check(
    listing_id: uuid.UUID,
    lang: str = Query("sr"),
    db: Session = Depends(get_db),
):
    """Та же оценка отдельным запросом — на случай внешних обращений."""
    base = (db.query(Listing)
            .options(joinedload(Listing.translations))
            .filter(Listing.id == listing_id).first())
    if not base:
        raise HTTPException(404, "not_found")
    return compute_price_check(db, base, lang)


@router.get("/{listing_id}/similar")
def similar_listings(
    listing_id: uuid.UUID,
    lang: str = Query("sr"),
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
            "price_mark": l.price_mark,
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "attributes": l.attributes,
            "category_slug": l.category.slug if l.category else None,
            "is_company": bool(l.owner and l.owner.role == UserRole.seller_business),
            "is_xl": l.id in promo[PromotionType.xl_card],
            "is_highlighted": l.id in promo[PromotionType.highlight],
            "cover_photo": cover.thumbnail_url if cover else None,
            "map_point": _map_point(l),
            "photos": card_photos(l.photos, cover),
            "cover_is_video": bool(cover.is_video) if cover else False,
            "is_reserved": bool(l.reserved_until and l.reserved_until > utcnow()),
            "cover_video_url": cover.url if (cover and cover.is_video) else None,
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    return {"items": [serialize(l) for l in picked]}


@router.get("/by-seller/{seller_id}")
def seller_listings(
    seller_id: uuid.UUID,
    lang: str = Query("sr"),
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
            "price_mark": l.price_mark,
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "attributes": l.attributes,
            "category_slug": l.category.slug if l.category else None,
            "cover_photo": cover.thumbnail_url if cover else None,
            "map_point": _map_point(l),
            "photos": card_photos(l.photos, cover),
            "cover_is_video": bool(cover.is_video) if cover else False,
            "is_reserved": bool(l.reserved_until and l.reserved_until > utcnow()),
            "cover_video_url": cover.url if (cover and cover.is_video) else None,
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    return {"total": total, "items": [serialize(l) for l in items]}


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
    # Координата приходит из базы как Decimal, а смещение — float;
    # складывать их напрямую Python отказывается, и страница объявления
    # со скрытым адресом падала целиком.
    return round(float(value) + offset, 5)


@router.get("/{listing_id}")
def get_listing(listing_id: str, request: Request, db: Session = Depends(get_db),
                viewer: User | None = Depends(get_current_user_optional)):
    from app.models import Favorite

    query = db.query(Listing).options(
        joinedload(Listing.translations), joinedload(Listing.photos),
        joinedload(Listing.owner),
        # Категория с родителем — для «хлебных крошек» (_category_path
        # ниже идёт вверх по parent). Без этого на каждое открытие
        # объявления уходило бы два лишних запроса в базу: сама
        # категория и её родитель, по одному на каждое обращение.
        joinedload(Listing.category).joinedload(Category.parent),
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
        # Название раздела словарём — чтобы показать его на языке
        # человека, не переспрашивая сервер отдельным запросом. Нужно
        # для служебного переноса объявления в другой раздел.
        "category_name": listing.category.name or {},
        # Цепочка категорий для «хлебных крошек» — от верхнего раздела
        # к самому объявлению.
        "category_path": _category_path(listing.category),
        "source_language": listing.source_language,
        "translations": {t.language: {"title": t.title, "description": t.description, "is_auto_translated": t.is_auto_translated} for t in listing.translations},
        "price": float(listing.price) if listing.price else None,
        # Последняя цена до правки — показываем перечёркнутой рядом с
        # новой, как у Авито. Только последнюю запись, не всю историю:
        # для одной строки на странице больше не нужно.
        "previous_price": previous_price_of(listing),
            "price_mark": listing.price_mark,
        "is_free": bool(listing.is_free),
        "currency": listing.currency,
        # Оценка цены приходит вместе с карточкой, а не отдельным
        # запросом: иначе блок появлялся через секунду после загрузки и
        # сдвигал вниз всё, что под ним. Расчёт кэширован, так что
        # лишним запросом в базу это не становится.
        "price_check": compute_price_check(db, listing, request.query_params.get("lang", "ru")),
        "price_negotiable": listing.price_negotiable,
        # Для объявлений из Telegram: связь идёт с автором напрямую, поэтому
        # отдаём его ник. Название чата-источника наружу не выносим — оно
        # нужно нам для дублей и жалоб, а покупателю ничего не даёт.
        "external_source": listing.external_source,
        # Ник автора — только вошедшему.
        #
        # Прятать кнопку на странице мало: ник приходил в ответе, и
        # ссылку на человека в Telegram можно было собрать руками. Раз
        # заблокированному закрыт доступ к переписке, значит закрыт и
        # обходной путь — иначе блокировка ничего не значит.
        #
        # Заблокированный для сервера тоже гость (см. auth.py), так что
        # одной проверки на «вошёл» хватает для обоих случаев.
        "external_author": listing.external_author if viewer else None,
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
        # Бронь видно всем как факт (не выдаём чужую, но и не скрываем,
        # что вещь занята — это важно знать любому смотрящему), а вот
        # «забронировано ИМЕННО ДЛЯ ТЕБЯ» — только тому самому покупателю.
        "is_reserved": bool(listing.reserved_until and listing.reserved_until > utcnow()),
        "reserved_for_me": bool(
            listing.reserved_until and listing.reserved_until > utcnow()
            and viewer and listing.reserved_for == viewer.id
        ),
        "photos": [
            {
                "id": str(p.id), "url": p.url, "thumbnail_url": p.thumbnail_url,
                "is_cover": p.is_cover, "is_video": p.is_video,
            }
            for p in listing.photos
        ],
        "views_count": listing.views_count,
        # Публичный счётчик избранного — раньше видел только владелец
        # в своей отдельной статистике (listing_dashboard). Только
        # число, не список имён — кто именно добавил, не публикуем.
        "favorites_count": db.query(Favorite).filter(Favorite.listing_id == listing.id).count(),
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
        # витрина продавца — сразу в ответе: блок «Ещё N товаров у продавца» приходил вторым запросом и толкал
        # объявление вниз на 76 px у человека на глазах
        "owner_storefront": _owner_storefront(db, listing.owner_id),
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
            "official": listing.owner.role in (UserRole.admin, UserRole.moderator),
            # Сам номер тут не отдаём — только флаг, есть ли он вообще.
            # Иконка звонка на этой странице ведёт в чат, где и решается,
            # раскрывать номер или нет; если его нет в профиле у
            # продавца совсем, показывать саму иконку незачем.
            "has_phone": bool(listing.owner.phone),
            # Факты, по которым человек решает, верить ли продавцу.
            #
            # Не выдуманный «рейтинг доверия» из формулы, которую никто
            # не проверит, а то, что проверяется само: сколько он
            # здесь, сколько у него объявлений, как быстро отвечает.
            # Выводы человек делает сам — это честнее любой оценки,
            # выставленной нами.
            "since": listing.owner.created_at.isoformat() if listing.owner.created_at else None,
            "listings_count": (
                db.query(func.count(Listing.id))
                .filter(Listing.owner_id == listing.owner.id,
                        Listing.status == ListingStatus.active)
                .scalar() or 0),
            "reply_speed": _reply_speed_label(db, listing.owner.id),
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


@router.post("/{listing_id}/renew")
def renew_listing(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Продлить объявление ещё на срок жизни, одним нажатием.

    Напоминание о скором снятии приходило, а сделать по нему было
    нечего: чтобы продлить, человек открывал объявление, правил что-то
    наугад и сохранял. Объявления тихо умирали не потому, что вещь
    продана, а потому, что продлить было неочевидно.

    Продлеваем от сегодняшнего дня, а не от прежнего срока: иначе у
    того, кто вспомнил за день до снятия, и у того, кто нажал сразу
    после напоминания, вышло бы по-разному.
    """
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")
    if listing.status not in (ListingStatus.active, ListingStatus.archived):
        raise HTTPException(409, "bad_status")

    listing.status = ListingStatus.active
    listing.expires_at = utcnow() + timedelta(days=LISTING_TTL_DAYS)
    listing.expiry_warned = False
    db.commit()
    return {
        "status": "active",
        "expires_at": listing.expires_at.isoformat(),
        "days": LISTING_TTL_DAYS,
    }


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

    # Периоды платного продвижения — накладываем на график просмотров,
    # чтобы было видно, помогает ли оно на самом деле, а не гадать.
    # Только оплаченные и только те, что хоть немного пересекаются с
    # показанным диапазоном дат — прошлогоднее поднятие на графике за
    # последний месяц не нужно.
    from app.models import Promotion, PromotionStatus, PromotionType
    since_dt = datetime.combine(since, datetime.min.time())
    promos = (
        db.query(Promotion)
        .filter(
            Promotion.listing_id == listing_id,
            Promotion.status == PromotionStatus.paid,
            Promotion.starts_at.isnot(None),
            Promotion.expires_at.isnot(None),
            Promotion.expires_at >= since_dt,
        )
        .order_by(Promotion.starts_at)
        .all()
    )
    promo_periods = [
        {
            "type": p.type.value if isinstance(p.type, PromotionType) else p.type,
            "starts_at": p.starts_at.isoformat(),
            "expires_at": p.expires_at.isoformat(),
        }
        for p in promos
    ]

    # Что не так с объявлением.
    #
    # Цифры сами по себе ничего не говорят: «42 просмотра» — это много
    # или мало? Человеку нужен вывод, что поправить. Считаем по тому,
    # что видно из данных, и не выдумываем того, чего не знаем: про
    # тёмное фото или плохой ракурс сказать нечем, а про число снимков,
    # длину описания, цену выше рынка и просмотры без единого отклика —
    # есть.
    week_views = sum(d["views"] for d in daily[-7:])
    photos = [p for p in listing.photos if not p.is_video]
    tr = next((t for t in listing.translations), None)
    description = (tr.description if tr else "") or ""

    tips: list[dict] = []
    if len(photos) < 3:
        tips.append({"code": "few_photos", "level": "warn", "count": len(photos)})
    if len(description.strip()) < 60:
        tips.append({"code": "short_description", "level": "warn"})

    price_check = compute_price_check(db, listing, "ru")
    if price_check.get("verdict") == "expensive":
        tips.append({"code": "price_high", "level": "warn"})

    # Смотрят, но не пишут: с самим объявлением всё в порядке, дело в
    # цене или в том, чего не видно на снимках.
    if week_views >= 30 and chats_count == 0:
        tips.append({"code": "views_no_contacts", "level": "warn", "count": week_views})
    # Не смотрят вовсе: объявление не находят — дело в заголовке или в
    # разделе, а не в цене.
    if listing.published_at and (utcnow() - listing.published_at).days >= 7 and week_views < 10:
        tips.append({"code": "few_views", "level": "warn", "count": week_views})
    if not tips:
        tips.append({"code": "all_good", "level": "ok"})

    return {
        "views_total": listing.views_count,
        "views_week": week_views,
        "favorites_count": favorites_count,
        "chats_count": chats_count,
        "tips": tips,
        "status": listing.status.value,
        "is_complete": listing.is_complete,
        "published_at": listing.published_at.isoformat() if listing.published_at else None,
        "expires_at": listing.expires_at.isoformat() if listing.expires_at else None,
        "daily": daily,
        "promotions": promo_periods,
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


class ReserveIn(BaseModel):
    buyer_id: uuid.UUID
    # Часов, на сколько бронируем — сутки-двое, как обычно и
    # договариваются «придержи, я заберу завтра». Не даём бронировать
    # на произвольный долгий срок — вещь всё равно должна продаваться,
    # не висеть в подвешенном состоянии неделями.
    hours: int = 48


@router.post("/{listing_id}/reserve")
def reserve_listing(
    listing_id: uuid.UUID,
    payload: ReserveIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Продавец бронирует объявление за конкретным покупателем — из
    чата, не отдельной формой: он и так там, договариваясь. Статус
    объявления не меняется — оно остаётся active, просто с меткой."""
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")
    if listing.status != ListingStatus.active:
        raise HTTPException(400, "listing_not_active")
    if not (1 <= payload.hours <= 168):   # неделя — разумный потолок
        raise HTTPException(400, "bad_duration")

    listing.reserved_for = payload.buyer_id
    listing.reserved_until = utcnow() + timedelta(hours=payload.hours)
    db.commit()

    try:
        from app.core.notifications import notify
        notify(db, payload.buyer_id,
              f"Продавец забронировал для вас объявление на {payload.hours} ч.",
              link=f"/go/{listing.id}", force=True)
    except Exception:
        pass

    return {"reserved_until": listing.reserved_until.isoformat()}


@router.post("/{listing_id}/reserve/cancel")
def cancel_reservation(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")

    listing.reserved_for = None
    listing.reserved_until = None
    db.commit()
    return {"status": "cancelled"}


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: uuid.UUID,
    force: bool = Query(False),
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

    # force — только у модератора/админа: снести объявление вместе с
    # настоящей историей (переписка, жалобы, отзывы), не просто с
    # техническими данными выше. Обычному человеку это недоступно даже
    # на своё же объявление — если по нему уже реально общались,
    # решение стирать эту историю не должно быть в одних руках с
    # тем, кто в этой истории участвовал.
    if force:
        if not is_staff:
            raise HTTPException(403, "force_delete_staff_only")
        from app.models import Chat, Message, Review, Report, ReviewInvite, Ticket, TicketMessage
        chat_ids = [c[0] for c in db.query(Chat.id).filter(Chat.listing_id == listing_id).all()]
        db.query(Message).filter(Message.chat_id.in_(chat_ids)).delete(synchronize_session=False)
        db.query(Chat).filter(Chat.listing_id == listing_id).delete()
        db.query(Review).filter(Review.listing_id == listing_id).delete()
        db.query(Report).filter(Report.listing_id == listing_id).delete()
        db.query(ReviewInvite).filter(ReviewInvite.listing_id == listing_id).delete()
        ticket_ids = [t[0] for t in db.query(Ticket.id).filter(Ticket.listing_id == listing_id).all()]
        db.query(TicketMessage).filter(TicketMessage.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        db.query(Ticket).filter(Ticket.listing_id == listing_id).delete()

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
    # раздел можно поменять при правке (раньше нельзя — ошибся при размещении, исправить было никак)
    category_slug: str | None = None
    attributes: dict | None = None
    title: str | None = None
    description: str | None = None
    delivery_available: bool | None = None
    safe_deal_available: bool | None = None

    @field_validator("attributes")
    @classmethod
    def check_attributes_size(cls, v):
        return _check_attributes_size(v) if v is not None else v

    # Та же проверка, что при создании: без неё правка принимала любую
    # строку и падала уже на записи в базу.
    @field_validator("currency")
    @classmethod
    def check_currency(cls, v):
        if v is not None and v not in ("EUR", "RSD"):
            raise ValueError("bad_currency")
        return v


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
    history_written = False
    if payload.category_slug and (not listing.category or payload.category_slug != listing.category.slug):
        new_cat = db.query(Category).filter(Category.slug == payload.category_slug).first()
        if not new_cat:
            raise HTTPException(400, "category_not_found")
        if db.query(Category.id).filter(Category.parent_id == new_cat.id).first() is not None:
            raise HTTPException(400, "category_not_leaf")   # только конечный раздел, как при размещении
        listing.category_id = new_cat.id
        content_changed = True                             # смена раздела — на проверку, как правка текста
    # Цена до правки: цикл ниже перезапишет её раньше, чем дойдёт до валюты.
    old_price = float(listing.price) if listing.price is not None else None

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
        elif field == "currency":
            # В базе перечисление, в запросе строка — сравниваем строки.
            current_cmp = getattr(current, "value", current)
        else:
            current_cmp = current
        # Старую цену — в историю, до того как перезаписали. Только на
        # реальное изменение, не на каждое сохранение формы: иначе одна
        # и та же цена копилась бы записью на каждое нажатие «Сохранить».
        # Смена валюты — та же смена цены: 9000 динаров и 9000 евро это
        # разные деньги. В историю уходит старая пара «цена + валюта»,
        # один раз за сохранение: цена в цикле идёт первой и валюта в
        # этот момент ещё старая, а если поменяли только валюту —
        # запись делает её собственный проход.
        price_changed = field == "price" and value != current_cmp and current_cmp is not None
        currency_changed = (field == "currency" and value != current_cmp
                            and old_price is not None and not history_written)
        if price_changed or currency_changed:
            history = list(listing.price_history or [])
            history.append({
                "price": old_price,
                "currency": getattr(listing.currency, "value", listing.currency),
                "changed_at": utcnow().isoformat(),
            })
            listing.price_history = history
            history_written = True
            # (снижение цены проверяется заново по price_history в
            # момент, когда объявление снова станет активным после
            # модерации — см. notify_price_drop в search_alerts.py —
            # а не прямо тут: до одобрения объявление всё равно не
            # показывается никому)
        setattr(listing, field, value)
        if field in ("price", "city") and value != current_cmp:
            content_changed = True
        # Валюта без цены ничего не значит — на проверку только с ценой.
        if field == "currency" and value != current_cmp and listing.price is not None:
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
    if payload.is_video and any(p.is_video for p in listing.photos):
        raise HTTPException(400, "only_one_video_allowed")

    next_order = max((p.sort_order for p in listing.photos), default=-1) + 1
    photo = ListingPhoto(
        listing_id=listing.id,
        url=payload.url,
        thumbnail_url=payload.thumbnail_url or payload.url,
        sort_order=next_order,
        is_cover=not listing.photos,   # первое фото у объявления — сразу обложка
        is_video=payload.is_video,
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
    return {"id": str(photo.id), "url": photo.url, "is_cover": photo.is_cover, "is_video": photo.is_video}


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


class PhotoOrderIn(BaseModel):
    # Полный список id фото объявления в новом порядке — первый в
    # списке автоматически становится обложкой. Не присылаем «новую
    # позицию одного фото», а весь порядок разом: перетаскивание на
    # телефоне и так пересчитывает весь список у себя в состоянии,
    # отправить его целиком проще и надёжнее частичного патча.
    photo_ids: list[uuid.UUID]


@router.patch("/{listing_id}/photos/order")
def reorder_photos(
    listing_id: uuid.UUID,
    payload: PhotoOrderIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Порядок фото при редактировании — раньше первое загруженное
    навсегда оставалось обложкой, ни перетащить, ни выбрать другое
    было нельзя.
    """
    listing = db.query(Listing).options(joinedload(Listing.photos)).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")

    by_id = {p.id: p for p in listing.photos}
    # Список должен содержать ровно те же фото, что уже есть у
    # объявления — ни больше, ни меньше: иначе кто-то мог бы шепнуть
    # чужой id фото и обложка объявления стала бы указывать не на
    # свою же фотографию.
    if set(payload.photo_ids) != set(by_id.keys()):
        raise HTTPException(400, "photo_set_mismatch")

    for i, photo_id in enumerate(payload.photo_ids):
        photo = by_id[photo_id]
        photo.sort_order = i
        photo.is_cover = (i == 0)

    db.commit()
    return {"status": "reordered"}


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

# Глаголы самой доски объявлений. «Куплю набор гантелей», «Кошка
# Монеточка ищет дом», «Нашлась собака» — это обычные и понятные
# названия, а не рекламные фразы: сказано, что за вещь и что с ней
# делают. Правило ниже бракует заголовки с глаголами (иначе в ленту
# лезет «уже более 4 лет помогаем клиентам»), и эти его законные
# исключения — проверил на живой базе: из 173 забракованных заголовков
# заметная часть оказалась именно такими, и переписывать их нейросетью
# значило бы портить хорошее.
# Рекламные обороты. Глагол в них стоит где угодно («уже более 4 лет
# помогаем клиентам»), поэтому ловим по самим словам, а не по месту в
# строке: вещь такая фраза не называет, и в ленте ей не место.
_AD_WORDS = frozenset("""
помогаем работаем предлагаем гарантируем обращайтесь звоните пишите
доверьтесь выполним оказываем предоставляем сотрудничаем
""".split())

_TRADE_VERBS = frozenset("""
продам продаю продаётся продается куплю покупаю
сдам сдаю сдаётся сдается сниму снимаю
отдам отдаю подарю обменяю меняю
ищет ищу ищем ищется потерялся потерялась потерян потеряна
нашёлся нашелся нашлась найден найдена
""".split())

_MID_SENTENCE_RE = re.compile(
    r"^(и|а|но|или|да|же|ведь|вот|это|эта|этот|эти|тут|там|"
    r"я|мы|вы|он|она|они|мне|нам|вам|его|её|их|"
    r"чем|что|как|где|когда|почему|зачем|который|которая|"
    r"вроде|кстати|также|тоже|ещё|еще|потом|затем|поэтому|уже|"
    r"наш|наша|наше|наши|нашего|нашей|моя|мой|моё|мои|"
    r"если|чтобы|пока|хотя|причём|причем)\b", re.I)


def _reply_speed_label(db, user_id) -> str | None:
    """
    Как быстро продавец отвечает — словами, а не минутами.

    «Отвечает за час» человек понимает сразу, «медиана 47 минут» — нет.
    Считаем по его же перепискам; если отвечал меньше трёх раз, молчим:
    по двум ответам вывода не сделать.
    """
    try:
        from app.core.reply_speed import reply_speed, speed_label

        speed = reply_speed(db, user_id)
        if not speed or speed.get("answered", 0) < 3:
            return None
        return speed_label(speed["median_minutes"])
    except Exception:                                   # noqa: BLE001
        return None


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

    words = body.lower().split()
    if any(w.strip(".,!—-") in _AD_WORDS for w in words):
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
    # Глагол смотрим только в первых двух словах. Там он превращает
    # заголовок в фразу: «Чикнула свой фикус», «Завалялись книги». А
    # дальше по строке глагол безобиден — «Штатив, новый, ни разу не
    # использовался» вещь называет в первом же слове, и браковать его
    # не за что. Прежнее правило смотрело всю строку и выбрасывало
    # такие заголовки целиком.
    for raw in re.findall(r"[а-яё]{4,}", " ".join(body.lower().split()[:2])):
        # Названия услуг и новые слова глаголами не считаем: «худи»
        # словарь разбирает как глагол, а это вещь.
        if raw in _SERVICE_VERBS or raw in _NEW_WORDS or raw in _TRADE_VERBS:
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

    # Словарь не знает новых вещей: «беговел», «уги», «свитшот». Раньше
    # такой заголовок уходил в мусор целиком — проверил на живой базе,
    # там оказались «Детский беговел» и «Уги совершенно новые». Раз
    # заголовок из нескольких слов, не начинается ни с глагола, ни с
    # вводного оборота и не содержит рекламных слов — вещь в нём
    # названа, пусть словарю она и незнакома.
    return len(body.split()) >= 2



def log_search(db: Session, q_text: str, lang: str | None, total: int, corrected: str | None = None) -> None:
    """Запрос — в журнал поиска (нормализованный). Ошибка журнала не должна ломать поиск."""
    import re as _re
    from app.models.search_log import SearchLog
    norm = _re.sub(r"\s+", " ", (q_text or "").strip().lower())[:80]
    if len(norm) < 2:
        return
    try:
        db.add(SearchLog(query=norm, lang=(lang or "sr")[:4], results=int(total or 0), corrected=corrected))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


def did_you_mean(db: Session, q_text: str) -> str | None:
    """Исправление опечаток: каждое слово запроса (от 4 букв) заменяем ближайшим словом из названий живых
    объявлений (pg_trgm similarity). «каляска» → «коляска», «халадильник» → «холодильник»."""
    from sqlalchemy import text as sql_text
    words = (q_text or "").strip().lower().split()
    if not words:
        return None
    out, changed = [], False
    for w in words:
        if len(w) < 4:
            out.append(w)
            continue
        try:
            rows = db.execute(sql_text("""
                select word from (
                  select distinct lower(unnest(regexp_split_to_array(t.title, '[^[:alnum:]]+'))) as word
                  from listing_translations t join listings l on l.id = t.listing_id
                  where l.status = 'active'
                ) x where length(word) >= 3 and word % :w
                order by similarity(word, :w) desc limit 6"""), {"w": w}).fetchall()
        except Exception:  # noqa: BLE001
            db.rollback()
            return None
        # у коротких слов триграммная похожесть низкая («дивон»/«диван» — 0,33), поэтому кандидатов из базы
        # проверяем ещё и посимвольно: берём лучшее совпадение не ниже 0,7
        from difflib import SequenceMatcher
        best = max(((SequenceMatcher(None, w, r[0]).ratio(), r[0]) for r in rows), default=(0, None))
        if best[1] and best[1] != w and best[0] >= 0.7:
            out.append(best[1]); changed = True
        else:
            out.append(w)
    return " ".join(out) if changed else None
