import enum
import uuid
from datetime import datetime

from sqlalchemy import Index, text, String, ForeignKey, DateTime, Numeric, Boolean, Enum, Integer, Text, BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base
from app.core.clock import utcnow


class ListingStatus(str, enum.Enum):
    draft = "draft"
    pending_moderation = "pending_moderation"
    active = "active"
    sold = "sold"
    archived = "archived"
    rejected = "rejected"


class Currency(str, enum.Enum):
    rsd = "RSD"
    eur = "EUR"


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        # Главный запрос ленты: активные, сначала новые. Отдельные индексы
        # тут не помогают — база сначала отберёт все активные, а их со
        # временем будут десятки тысяч, и только потом отсортирует.
        Index("ix_listings_feed", "status", "published_at"),
        # То же для ленты внутри категории
        Index("ix_listings_category_feed", "category_id", "status", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Чисто витринный номер — для человека на странице, не для связей
    # в базе (те остаются на UUID выше, ничего не переписываем).
    # Настоящий автоинкремент, не первые символы UUID вперемешку из
    # букв и цифр — «Объявление № 100047» читается и произносится
    # вслух, «№ f7642d6b» нет. Стартуем не с единицы — свежий сайт с
    # «Объявление № 3» выглядит подозрительно пустым.
    number: Mapped[int] = mapped_column(BigInteger, Identity(start=100000), unique=True, nullable=False)

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), index=True)

    # Оригинальный язык, на котором продавец создал объявление
    source_language: Mapped[str] = mapped_column(String(8), default="ru")

    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True, index=True)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), default=Currency.eur)
    price_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)

    # Динамические атрибуты по схеме категории: {"brand": "BMW", "year": 2018, ...}
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Переводы тех атрибутов, что заполняются свободным текстом:
    # {"en": {"service_type": "English tutor"}, "sr": {...}}.
    # Марка, модель и VIN сюда не попадают — их не переводят.
    attributes_i18n: Mapped[dict] = mapped_column(JSONB, default=dict)

    # ——— объявления, перенесённые из телеграм-чатов ———
    # Владелец у них — служебный аккаунт чата, поэтому писать и звонить
    # через сайт нельзя: связь только с автором в Telegram по его нику.
    external_source: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    # ник автора без @; без ника объявление не переносим — иначе покупателю
    # некуда обратиться, а это хуже, чем отсутствие объявления
    external_author: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # откуда взято — для поиска дублей и разбора жалоб, покупателю не показываем
    external_chat: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Отпечаток смысла: основы значимых слов заголовка и описания. Одно и
    # то же объявление кочует по чатам переписанным, и по точному тексту
    # его не поймать — а по набору основ видно, что это тот же товар.
    external_fingerprint: Mapped[str | None] = mapped_column(
        String(500), nullable=True)
    # Хеш первого снимка (SHA-256 от исходных байт до пережатия в JPEG).
    # Тот же товар, перевыставленный с другой ценой или переписанным
    # текстом, чаще всего снят на тот же телефон теми же кадрами —
    # текстовый fingerprint такое не всегда ловит (переписанное описание
    # меняет набор слов), а те же самые байты фото — редко совпадение.
    external_photo_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True)

    # Вещь отдают даром. Отдельно от пустой цены: «цена не указана» и
    # «бесплатно» — разные вещи, и читатель проходит мимо первого, хотя
    # второе ему бы подошло.
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Объявление полное: есть внятное название, цена и фотография.
    # Первое впечатление важнее числа — человек, попавший на обрубки,
    # второй раз не придёт. Считаем при записи, а не при каждом запросе:
    # лента открывается тысячи раз, а объявление пишется однажды.
    is_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True)

    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    location_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    hide_exact_address: Mapped[bool] = mapped_column(Boolean, default=False)

    # Бронирование — «придержать для конкретного покупателя», не новый
    # статус объявления (оно остаётся active, ищется и покупается как
    # обычно — просто с меткой). Ставит продавец из чата на
    # определённый срок; reserved_for — кто именно, чтобы отличить
    # «забронировано для тебя» от «забронировано для кого-то другого»
    # на экране у разных людей.
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reserved_for: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), default=ListingStatus.draft, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_available: Mapped[bool] = mapped_column(Boolean, default=False)
    safe_deal_available: Mapped[bool] = mapped_column(Boolean, default=False)

    views_count: Mapped[int] = mapped_column(Integer, default=0)
    favorites_count: Mapped[int] = mapped_column(Integer, default=0)
    # Число начатых переписок — сигнал интереса не слабее избранного,
    # для формулы релевантности в поиске (see search_listings()).
    chats_count: Mapped[int] = mapped_column(Integer, default=0)

    # Кому и о какой цене уже сообщали, что подешевело.
    #
    # Продавец правит цену несколько раз, а сообщение об одном и том же
    # человек должен получить один. Держим по человеку: у каждого свой
    # момент, когда он отложил объявление.
    # server_default обязателен: без него миграция падает на объявлениях,
    # которые уже есть — им нечего подставить в обязательную колонку.
    # Ровно на этом деплой споткнулся с last_hit_at, и я повторил ту же
    # ошибку здесь.
    notified_price_drop: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"))

    price_history: Mapped[list] = mapped_column(JSONB, default=list)  # [{"price": 1000, "changed_at": "..."}]

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Чтобы предупреждение об истечении не уходило по кругу каждый день,
    # пока владелец не отреагирует — шлём его один раз на объявление.
    expiry_warned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="listings", foreign_keys=[owner_id])
    category = relationship("Category", back_populates="listings")
    translations = relationship("ListingTranslation", back_populates="listing", cascade="all, delete-orphan")
    photos = relationship("ListingPhoto", back_populates="listing", cascade="all, delete-orphan", order_by="ListingPhoto.sort_order")


class ListingTranslation(Base):
    """Заголовок/описание на каждом языке — ручной перевод продавца или авто-перевод."""
    __tablename__ = "listing_translations"
    __table_args__ = (
        # Поиск по словам вместо перебора всех описаний подряд. Без этого
        # каждый запрос читает всю таблицу — при тысячах объявлений заметно.
        Index(
            "ix_translations_search",
            text("to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)

    language: Mapped[str] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    is_auto_translated: Mapped[bool] = mapped_column(Boolean, default=False)

    listing = relationship("Listing", back_populates="translations")


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)

    url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    # Видео живёт в этой же коллекции, не отдельным полем на Listing —
    # так оно бесплатно получает то же самое, что уже есть у фото:
    # порядок, возможность стать обложкой, показ в общей карусели.
    # url для видео — уже перекодированный H.264/AAC файл (см.
    # upload_video в media.py), thumbnail_url — вырезанный кадр-превью,
    # используется и как постер видео, и как обложка в карточке ленты.
    is_video: Mapped[bool] = mapped_column(Boolean, default=False)

    listing = relationship("Listing", back_populates="photos")
