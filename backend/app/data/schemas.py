"""
Поля объявлений по категориям.

Блок характеристик — то, по чему вещь выбирают и сравнивают, не читая
описание: память у телефона, размер у обуви, состояние у всего подряд.

Схема — на подраздел, не на раздел целиком. Раньше одна схема
покрывала весь раздел: «Приборы для красоты» получали «Объём, мл» —
поле для духов, не для фена. «Шины» получали «Коробка передач» — поле
для машины целиком, не для одной детали. Подразделы внутри раздела
слишком разные, чтобы описываться одними полями.

SUB_SCHEMAS — по слагу подраздела, это то, что реально уходит в базу.
SCHEMAS (по разделу) остаётся как запасной вариант — для подраздела,
которого нет в SUB_SCHEMAS, и как схема самого раздела на странице
верхнего уровня.
"""


def _label(ru: str, en: str, sr: str) -> dict:
    return {"ru": ru, "en": en, "sr": sr}


def _options(*items: tuple[str, str, str, str]) -> list[dict]:
    return [{"value": v, "label": _label(ru, en, sr)} for v, ru, en, sr in items]


# ——— общие поля ———

CONDITION = {
    "key": "condition", "type": "select", "required": False,
    "label": _label("Состояние", "Condition", "Stanje"),
    "options": _options(
        ("new", "Новое", "New", "Novo"),
        ("like_new", "Как новое", "Like new", "Kao novo"),
        ("used", "Б/у", "Used", "Polovno"),
        ("for_parts", "На запчасти", "For parts", "Za delove"),
    ),
}

BRAND = {
    "key": "brand", "type": "text", "required": False,
    "label": _label("Бренд", "Brand", "Brend"),
}

MODEL = {
    "key": "model", "type": "text", "required": False,
    "label": _label("Модель", "Model", "Model"),
}

WARRANTY = {
    "key": "warranty", "type": "boolean", "required": False,
    "label": _label("Есть гарантия", "Under warranty", "Ima garanciju"),
}

MATERIAL = {
    "key": "material", "type": "text", "required": False,
    "label": _label("Материал", "Material", "Materijal"),
}

DIMENSIONS = {
    "key": "dimensions", "type": "text", "required": False,
    "label": _label("Размеры", "Dimensions", "Dimenzije"),
}

GENDER = {
    "key": "gender", "type": "select", "required": False,
    "label": _label("Кому", "For", "Za"),
    "options": _options(
        ("women", "Женское", "Women's", "Žensko"),
        ("men", "Мужское", "Men's", "Muško"),
        ("unisex", "Унисекс", "Unisex", "Uniseks"),
    ),
}

SIZE_TEXT = {
    "key": "size", "type": "text", "required": False,
    "label": _label("Размер", "Size", "Veličina"),
}

AGE_GROUP = {
    "key": "age_group", "type": "select", "required": False,
    "label": _label("Возраст", "Age", "Uzrast"),
    "options": _options(
        ("baby", "0-1 год", "0-1 year", "0-1 godina"),
        ("toddler", "1-3 года", "1-3 years", "1-3 godine"),
        ("preschool", "3-7 лет", "3-7 years", "3-7 godina"),
        ("school", "7+ лет", "7+ years", "7+ godina"),
    ),
}

YEAR = {
    "key": "year", "type": "number", "required": False,
    "label": _label("Год выпуска", "Year", "Godište"),
}

POWER_WATTS = {
    "key": "power_watts", "type": "number", "required": False,
    "label": _label("Мощность, Вт", "Power, W", "Snaga, W"),
}


# ——— авто: одна схема на весь раздел не годится — у детали и шины нет
# ни года, ни пробега, ни коробки передач ———

_AUTO_YEAR = {
    "key": "year", "type": "number", "required": False,
    "label": _label("Год", "Year", "Godina"),
}
_AUTO_MILEAGE = {
    "key": "mileage_km", "type": "number", "required": False,
    "label": _label("Пробег, км", "Mileage, km", "Kilometraža"),
}
_AUTO_TRANSMISSION = {
    "key": "transmission", "type": "select", "required": False,
    "label": _label("Коробка передач", "Transmission", "Menjač"),
    "options": _options(
        ("manual", "Механика", "Manual", "Manuelni"),
        ("automatic", "Автомат", "Automatic", "Automatik"),
    ),
}
_AUTO_VIN = {
    "key": "vin", "type": "text", "required": False,
    "label": _label("VIN (необязательно)", "VIN (optional)", "VIN (opciono)"),
}
_TYRE_SEASON = {
    "key": "season", "type": "select", "required": False,
    "label": _label("Сезон", "Season", "Sezona"),
    "options": _options(
        ("summer", "Летние", "Summer", "Letnje"),
        ("winter", "Зимние", "Winter", "Zimske"),
        ("all_season", "Всесезонные", "All-season", "Celogodišnje"),
    ),
}
_TYRE_SIZE = {
    "key": "tyre_size", "type": "text", "required": False,
    "label": _label("Размер (напр. 205/55 R16)", "Size (e.g. 205/55 R16)", "Dimenzije (npr. 205/55 R16)"),
}


# ——— электроника: у ТВ нет памяти телефона, у консоли нет диагонали
# экрана, у фотоаппарата нет оперативной памяти ———

_STORAGE_GB = {
    "key": "storage_gb", "type": "number", "required": False,
    "label": _label("Память, ГБ", "Storage, GB", "Memorija, GB"),
}
_RAM_GB = {
    "key": "ram_gb", "type": "number", "required": False,
    "label": _label("Оперативная память, ГБ", "RAM, GB", "RAM, GB"),
}
_SCREEN_INCH = {
    "key": "screen_inch", "type": "number", "required": False,
    "label": _label("Экран, дюймов", "Screen, inches", "Ekran, inča"),
}
_BATTERY_HEALTH = {
    "key": "battery_health", "type": "number", "required": False,
    "label": _label("Ёмкость аккумулятора, %", "Battery health, %", "Baterija, %"),
}
_CPU = {
    "key": "cpu", "type": "text", "required": False,
    "label": _label("Процессор", "Processor", "Procesor"),
}
_GPU = {
    "key": "gpu", "type": "text", "required": False,
    "label": _label("Видеокарта", "Graphics card", "Grafička kartica"),
}
_MEGAPIXELS = {
    "key": "megapixels", "type": "number", "required": False,
    "label": _label("Разрешение, Мп", "Resolution, MP", "Rezolucija, Mp"),
}


SCHEMAS: dict[str, list[dict]] = {
    "auto": [BRAND, MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _AUTO_TRANSMISSION, _AUTO_VIN],
    "electronics": [
        BRAND, MODEL, CONDITION, _STORAGE_GB, _RAM_GB, _SCREEN_INCH,
        _BATTERY_HEALTH, WARRANTY,
    ],
    "fashion": [BRAND, CONDITION, SIZE_TEXT, GENDER],
    "home-garden": [BRAND, CONDITION, MATERIAL, DIMENSIONS],
    "kids": [BRAND, CONDITION, AGE_GROUP, SIZE_TEXT],
    "hobby-sport": [BRAND, CONDITION, SIZE_TEXT],
    "pets": [
        {"key": "listing_kind", "type": "select", "required": False,
         "label": _label("Тип объявления", "Listing type", "Vrsta oglasa"),
         "options": _options(
             ("animal", "Животное", "Animal", "Životinja"),
             ("supplies", "Товары", "Supplies", "Oprema"),
         )},
        {"key": "species", "type": "text", "required": False,
         "label": _label("Вид", "Species", "Vrsta")},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "beauty": [BRAND, CONDITION],
    "business": [BRAND, CONDITION, YEAR],
}


SUB_SCHEMAS: dict[str, list[dict]] = {
    # ——— авто ———
    "cars": [BRAND, MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _AUTO_TRANSMISSION, _AUTO_VIN],
    "moto": [BRAND, MODEL, _AUTO_YEAR, _AUTO_MILEAGE],
    "trucks": [BRAND, MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _AUTO_TRANSMISSION],
    "car-parts": [BRAND, MODEL, CONDITION],
    "tyres": [BRAND, _TYRE_SIZE, _TYRE_SEASON, CONDITION],

    # ——— электроника ———
    "phones": [BRAND, MODEL, CONDITION, _STORAGE_GB, _RAM_GB, _SCREEN_INCH, _BATTERY_HEALTH, WARRANTY],
    "laptops": [BRAND, MODEL, CONDITION, _CPU, _RAM_GB, _STORAGE_GB, _SCREEN_INCH, WARRANTY],
    "computers": [BRAND, CONDITION, _CPU, _GPU, _RAM_GB, _STORAGE_GB, WARRANTY],
    "tablets": [BRAND, MODEL, CONDITION, _STORAGE_GB, _SCREEN_INCH, _BATTERY_HEALTH, WARRANTY],
    "tv-audio": [BRAND, MODEL, CONDITION, _SCREEN_INCH, WARRANTY],
    "photo": [BRAND, MODEL, CONDITION, _MEGAPIXELS, WARRANTY],
    "gaming": [BRAND, MODEL, CONDITION, _STORAGE_GB, WARRANTY],
    "gadgets": [BRAND, MODEL, CONDITION, _BATTERY_HEALTH, WARRANTY],

    # ——— одежда и обувь ———
    "women": [BRAND, CONDITION, SIZE_TEXT],
    "men": [BRAND, CONDITION, SIZE_TEXT],
    "shoes": [
        BRAND, CONDITION, SIZE_TEXT,
        {"key": "insole_cm", "type": "number", "required": False,
         "label": _label("Длина стельки, см", "Insole, cm", "Uložak, cm")},
        GENDER,
    ],
    "bags": [BRAND, CONDITION, MATERIAL],
    "watches": [BRAND, CONDITION, MATERIAL, GENDER],

    # ——— дом и сад ———
    "furniture": [MATERIAL, DIMENSIONS, CONDITION],
    "appliances": [BRAND, CONDITION, POWER_WATTS, WARRANTY],
    "kitchenware": [MATERIAL, CONDITION],
    "decor": [MATERIAL, DIMENSIONS, CONDITION],
    "garden": [CONDITION],
    "tools": [BRAND, CONDITION, POWER_WATTS],

    # ——— детям ———
    "kids-clothing": [BRAND, CONDITION, AGE_GROUP, SIZE_TEXT],
    "strollers": [BRAND, CONDITION, AGE_GROUP],
    "toys": [BRAND, CONDITION, AGE_GROUP],
    "kids-furniture": [MATERIAL, DIMENSIONS, CONDITION],
    "school": [BRAND, CONDITION, AGE_GROUP],

    # ——— хобби и спорт ———
    "bikes": [
        BRAND, MODEL, CONDITION,
        {"key": "wheel_size", "type": "text", "required": False,
         "label": _label("Размер колёс", "Wheel size", "Veličina točkova")},
    ],
    "fitness": [BRAND, CONDITION],
    "outdoor": [BRAND, CONDITION],
    "music": [BRAND, MODEL, CONDITION],
    "books": [
        CONDITION,
        {"key": "author", "type": "text", "required": False,
         "label": _label("Автор", "Author", "Autor")},
    ],
    "collecting": [CONDITION, YEAR],

    # ——— животные — вопрос «привит» нелеп для миски или переноски ———
    "pets-dogs": [
        {"key": "breed", "type": "text", "required": False,
         "label": _label("Порода", "Breed", "Rasa")},
        {"key": "age", "type": "text", "required": False,
         "label": _label("Возраст", "Age", "Uzrast")},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "pets-cats": [
        {"key": "breed", "type": "text", "required": False,
         "label": _label("Порода", "Breed", "Rasa")},
        {"key": "age", "type": "text", "required": False,
         "label": _label("Возраст", "Age", "Uzrast")},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "pets-other": [
        {"key": "species", "type": "text", "required": False,
         "label": _label("Вид", "Species", "Vrsta")},
        {"key": "age", "type": "text", "required": False,
         "label": _label("Возраст", "Age", "Uzrast")},
    ],
    "pets-supplies": [BRAND, CONDITION],

    # ——— красота: тот самый случай — духам нужен объём, фену нет ———
    "cosmetics": [
        BRAND, CONDITION,
        {"key": "volume_ml", "type": "number", "required": False,
         "label": _label("Объём, мл", "Volume, ml", "Zapremina, ml")},
        {"key": "shade", "type": "text", "required": False,
         "label": _label("Оттенок", "Shade", "Nijansa")},
    ],
    "beauty-devices": [BRAND, MODEL, CONDITION, WARRANTY],
    "health": [BRAND, CONDITION],

    # ——— бизнес ———
    "equipment": [BRAND, MODEL, CONDITION, YEAR],
    "ready-business": [
        {"key": "monthly_revenue", "type": "number", "unit": "currency", "required": False,
         "label": _label("Выручка в месяц", "Monthly revenue", "Mesečni prihod")},
        {"key": "employees", "type": "number", "required": False,
         "label": _label("Сотрудников", "Employees", "Zaposlenih")},
    ],
    "supplies": [BRAND, CONDITION],
}
