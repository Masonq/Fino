"""
Куда публиковать: наш раздел — ветка чата.

Барахолки устроены каждая по-своему, и названия веток у них не совпадают
ни между собой, ни с нашими разделами. Держим соответствие здесь, а не
заставляем человека выбирать ветку самому: он выбирает вещь, а куда её
положить — забота сервиса.

Ветки берутся один раз при подключении чата:

    python tools/peek-chat.py https://t.me/<чат>
"""

# Чат «БАРАХОЛКА Белград» — первый партнёр.
BARAHOLKA_BELGRAD = -1001762485160
# Тестовый чат: на нём проверяем бота, прежде чем пускать к людям.
BARAHOLKA_TEST = -1004385141960

# Наш раздел → номер ветки. Разделы, которых у партнёра нет, отправляем
# в «Прочие товары»: лучше общая ветка, чем чужая.
TOPIC_BY_CATEGORY: dict[int, dict[str, int]] = {
    BARAHOLKA_BELGRAD: {
        "auto": 1399,               # Авто / мото транспорт
        "electronics": 1398,        # Электроника
        "home-garden": 1394,        # МЕБЕЛЬ и всё для ДОМА
        "fashion": 1410,            # Одежда, обувь
        "kids": 1401,               # Детские товары
        "real-estate": 1396,        # Недвижимость продам/сдам
        "jobs": 1393,               # Вакансии / Резюме
        "beauty": 1406,             # Услуги красоты
        "services": 1407,           # Услуги прочее
        "business": 2206,           # Бизнес, услуги для бизнеса
        # Своих веток нет: животные и хобби идут к прочим товарам
        "pets": 2000,
        "hobby-sport": 2000,
    },
}

TOPIC_BY_CATEGORY[BARAHOLKA_TEST] = {
    # Пока в тестовом чате одна ветка кроме правил — остальное туда же.
    "electronics": 2,
}

SPECIAL_TOPICS_TEST = {"fallback": 2}

# Ветки, которые важнее раздела: вещь может быть любой, а место у неё своё.
SPECIAL_TOPICS: dict[int, dict[str, int]] = {
    BARAHOLKA_TEST: SPECIAL_TOPICS_TEST,
    BARAHOLKA_BELGRAD: {
        # Отдают даром — отдельная ветка, и туда смотрят именно за этим
        "free": 2026,
        # Ищут, а не продают
        "wanted": 4460,
        "fallback": 2000,           # Прочие товары
    },
}

# Названия веток — для кнопок в боте: человеку показываем то же слово,
# что он видит в чате, иначе он не поймёт, куда попадёт объявление.
TOPIC_NAMES: dict[int, dict[int, str]] = {
    BARAHOLKA_TEST: {2: "Электроника"},
    BARAHOLKA_BELGRAD: {
        1393: "Вакансии / Резюме",
        1394: "МЕБЕЛЬ и всё для ДОМА",
        1396: "Недвижимость продам/сдам",
        1398: "Электроника",
        1399: "Авто / мото транспорт",
        1401: "Детские товары",
        1406: "Услуги красоты",
        1407: "Услуги прочее",
        1410: "Одежда, обувь",
        2000: "Прочие товары",
        2026: "Отдам даром",
        2206: "Бизнес, услуги для бизнеса",
        4460: "КУПЛЮ / ИЩУ",
    },
}


# Подкатегории со своей веткой: раздел один, а места разные. У партнёра
# услуги красоты отделены от прочих услуг, и стрижке среди сантехников
# не место.
TOPIC_BY_SUBCATEGORY: dict[int, dict[str, int]] = {
    BARAHOLKA_BELGRAD: {
        "beauty-services": 1406,    # Услуги красоты
    },
}


def topic_for(chat_id: int, category: str | None, *,
              sub: str | None = None,
              is_free: bool = False, is_wanted: bool = False) -> int | None:
    """
    В какую ветку класть объявление.

    Особые ветки идут первыми: «отдам даром» и «куплю» — это про то, что
    человек делает, а не про то, что за вещь. Диван в дар ждут в ветке
    подарков, а не среди мебели на продажу.
    """
    special = SPECIAL_TOPICS.get(chat_id, {})
    if is_wanted and "wanted" in special:
        return special["wanted"]
    if is_free and "free" in special:
        return special["free"]

    # Подкатегория точнее раздела, поэтому смотрим её первой.
    by_sub = TOPIC_BY_SUBCATEGORY.get(chat_id, {})
    if sub and sub in by_sub:
        return by_sub[sub]

    by_category = TOPIC_BY_CATEGORY.get(chat_id, {})
    if category and category in by_category:
        return by_category[category]
    # Раздел не определился — лучше общая ветка, чем наугад чужая.
    return special.get("fallback")


def topic_name(chat_id: int, topic_id: int | None) -> str | None:
    return TOPIC_NAMES.get(chat_id, {}).get(topic_id) if topic_id else None


def topics_of(chat_id: int) -> list[tuple[int, str]]:
    """Все ветки чата — для выбора вручную, когда наш подбор не годится."""
    return sorted(TOPIC_NAMES.get(chat_id, {}).items(), key=lambda kv: kv[1])
