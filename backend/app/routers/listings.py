import re
import uuid

from app.core.urls import listing_path
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, case, exists, func, or_
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field, field_validator

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.search_terms import variants as search_variants
from app.models import Listing, ListingStatus, ListingTranslation, ListingPhoto, Category, User, UserRole
from app.core.clock import utcnow

router = APIRouter(prefix="/api/listings", tags=["listings"])


class TranslationIn(BaseModel):
    language: str
    title: str
    description: str


class PhotoIn(BaseModel):
    url: str
    thumbnail_url: str | None = None


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


@router.post("")
def create_listing(
    payload: ListingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создаёт объявление от имени вошедшего пользователя."""
    from app.core.rate_limit import check_listing_limit
    check_listing_limit(db, user.id)

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
    sort: str = Query("new"),
    lang: str = Query("ru"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Listing).options(
        joinedload(Listing.translations), joinedload(Listing.photos)
    ).filter(Listing.status == ListingStatus.active)

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

    if category_slug:
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
    if price_min is not None:
        q = q.filter(Listing.price >= price_min)
    if price_max is not None:
        q = q.filter(Listing.price <= price_max)
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

    total = q.count()

    order = {
        "new": Listing.published_at.desc(),
        "old": Listing.published_at.asc(),
        "cheap": Listing.price.asc().nullslast(),
        "expensive": Listing.price.desc().nullslast(),
    }.get(sort, Listing.published_at.desc())

    # Полные объявления впереди неполных: обрубок без цены и фотографии
    # тоже кому-то нужен, но встречать им человека нельзя.
    #
    # Не прячем совсем — только опускаем: вещь без снимка находится
    # поиском, открывается по ссылке и живёт в своём разделе.
    ordering = [Listing.is_complete.desc()]
    if title_hit is not None:
        # При поиске слово в названии важнее полноты: человек искал
        # конкретную вещь, а не красивую карточку.
        ordering = [title_hit, Listing.is_complete.desc()]
    ordering.append(order)
    items = q.order_by(*ordering).offset(offset).limit(limit).all()

    def serialize(listing: Listing):
        translation = pick_translation(listing, lang)
        if not translation and listing.translations:
            translation = listing.translations[0]
        cover = next((p for p in listing.photos if p.is_cover), listing.photos[0] if listing.photos else None)
        return {
            "id": str(listing.id),
            "title": translation.title if translation else None,
            "price": float(listing.price) if listing.price else None,
            "is_free": bool(listing.is_free),
            "currency": listing.currency,
            "city": listing.city,
            "cover_photo": cover.thumbnail_url if cover else None,
            "delivery_available": listing.delivery_available,
            "is_urgent": listing.is_urgent,
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
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
        .options(joinedload(Listing.translations), joinedload(Listing.photos))
        .filter(Listing.id.in_(wanted), Listing.status == ListingStatus.active)
        .all()
    )
    by_id = {l.id: l for l in rows}

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
            # Понятный адрес: он должен быть одинаков везде — в ленте,
            # в избранном, в своих объявлениях.
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
            "cover_photo": cover.thumbnail_url if cover else None,
            "status": l.status.value,
            "views_count": l.views_count,
            "created_at": l.created_at.isoformat() if l.created_at else None,
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
        .options(joinedload(Listing.translations), joinedload(Listing.photos))
        .filter(
            Listing.id != listing_id,
            Listing.status == ListingStatus.active,
            Listing.category_id == base.category_id,
        )
    )

    price = float(base.price) if base.price else None
    if price:
        # Цену не сужаем жёстко: похожая вещь может стоить вдвое дороже
        # из-за состояния, и отбрасывать её рано.
        q = q.filter(Listing.price.between(price * 0.25, price * 4))

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

        if price and l.price:
            diff = abs(float(l.price) - price) / price
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
            "is_free": bool(l.is_free),
            "currency": l.currency,
            "city": l.city,
            "cover_photo": cover.thumbnail_url if cover else None,
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    return {"total": total, "items": [serialize(l) for l in items]}


@router.get("/{listing_id}")
def get_listing(listing_id: str, db: Session = Depends(get_db)):
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

    listing.views_count += 1
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
        "photos": [{"url": p.url, "is_cover": p.is_cover} for p in listing.photos],
        "views_count": listing.views_count,
        "owner": {
            "id": str(listing.owner.id),
            "display_name": listing.owner.display_name,
            "rating_avg": listing.owner.rating_avg,
            "rating_count": listing.owner.rating_count,
            "phone_verified": listing.owner.phone_verified,
        },
        "delivery_available": listing.delivery_available,
        "safe_deal_available": listing.safe_deal_available,
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
    listing.status = ListingStatus(payload.status)
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
    db.delete(listing)
    db.commit()
    return {"status": "deleted"}

class ListingUpdate(BaseModel):
    price: float | None = None
    currency: str | None = None
    price_negotiable: bool | None = None
    city: str | None = None
    attributes: dict | None = None
    title: str | None = None
    description: str | None = None
    delivery_available: bool | None = None
    safe_deal_available: bool | None = None


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
                  "attributes", "delivery_available", "safe_deal_available"):
        value = getattr(payload, field)
        if value is not None:
            setattr(listing, field, value)
            if field in ("price", "city"):
                content_changed = True

    if payload.title is not None or payload.description is not None:
        tr = next(
            (t for t in listing.translations if t.language == listing.source_language),
            listing.translations[0] if listing.translations else None,
        )
        if tr:
            if payload.title is not None:
                tr.title = payload.title.strip()[:200]
            if payload.description is not None:
                tr.description = payload.description.strip()
            content_changed = True

    if content_changed and listing.status == ListingStatus.active:
        listing.status = ListingStatus.pending_moderation

    # Полнота могла измениться: дописали цену — объявление поднимется в
    # ленте, стёрли название — опустится.
    listing.is_complete = _looks_complete(listing)

    db.commit()
    return {"status": listing.status.value}


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
