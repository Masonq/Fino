"""
Поля объявлений по категориям.

Блок характеристик — то, по чему вещь выбирают и сравнивают, не читая
описание: память у телефона, размер у обуви, состояние у всего подряд.
Пока схем не было, у половины категорий он оставался пустым.

Держим здесь, а не в сиде: список растёт, и в сиде он тонул среди
служебного кода.
"""


def _label(ru: str, en: str, sr: str) -> dict:
    return {"ru": ru, "en": en, "sr": sr}


def _options(*items: tuple[str, str, str, str]) -> list[dict]:
    return [{"value": v, "label": _label(ru, en, sr)} for v, ru, en, sr in items]


# Состояние спрашивают почти о любой вещи, поэтому поле общее.
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

SCHEMAS: dict[str, list[dict]] = {
    "electronics": [
        BRAND, MODEL, CONDITION,
        {"key": "storage_gb", "type": "number", "required": False,
         "label": _label("Память, ГБ", "Storage, GB", "Memorija, GB")},
        {"key": "ram_gb", "type": "number", "required": False,
         "label": _label("Оперативная память, ГБ", "RAM, GB", "RAM, GB")},
        {"key": "screen_inch", "type": "number", "required": False,
         "label": _label("Экран, дюймов", "Screen, inches", "Ekran, inča")},
        {"key": "battery_health", "type": "number", "required": False,
         "label": _label("Ёмкость аккумулятора, %", "Battery health, %", "Baterija, %")},
        {"key": "warranty", "type": "boolean", "required": False,
         "label": _label("Есть гарантия", "Under warranty", "Ima garanciju")},
    ],
    "fashion": [
        BRAND, CONDITION,
        {"key": "size", "type": "text", "required": False,
         "label": _label("Размер", "Size", "Veličina")},
        {"key": "insole_cm", "type": "number", "required": False,
         "label": _label("Длина стельки, см", "Insole, cm", "Uložak, cm")},
        {"key": "gender", "type": "select", "required": False,
         "label": _label("Кому", "For", "Za"),
         "options": _options(
             ("women", "Женское", "Women's", "Žensko"),
             ("men", "Мужское", "Men's", "Muško"),
             ("unisex", "Унисекс", "Unisex", "Uniseks"),
         )},
    ],
    "home-garden": [
        BRAND, CONDITION,
        {"key": "material", "type": "text", "required": False,
         "label": _label("Материал", "Material", "Materijal")},
        {"key": "dimensions", "type": "text", "required": False,
         "label": _label("Размеры", "Dimensions", "Dimenzije")},
    ],
    "kids": [
        BRAND, CONDITION,
        {"key": "age_group", "type": "select", "required": False,
         "label": _label("Возраст", "Age", "Uzrast"),
         "options": _options(
             ("baby", "0-1 год", "0-1 year", "0-1 godina"),
             ("toddler", "1-3 года", "1-3 years", "1-3 godine"),
             ("preschool", "3-7 лет", "3-7 years", "3-7 godina"),
             ("school", "7+ лет", "7+ years", "7+ godina"),
         )},
        {"key": "size", "type": "text", "required": False,
         "label": _label("Размер", "Size", "Veličina")},
    ],
    "hobby-sport": [
        BRAND, CONDITION,
        {"key": "size", "type": "text", "required": False,
         "label": _label("Размер", "Size", "Veličina")},
    ],
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
    "beauty": [
        BRAND, CONDITION,
        {"key": "volume_ml", "type": "number", "required": False,
         "label": _label("Объём, мл", "Volume, ml", "Zapremina, ml")},
    ],
    "business": [
        BRAND, CONDITION,
        {"key": "year", "type": "number", "required": False,
         "label": _label("Год выпуска", "Year", "Godište")},
    ],
}
