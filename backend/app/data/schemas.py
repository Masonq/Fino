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

# «На запчасти» имеет смысл только для составной вещи, которую разбирают
# на части — телефон, ноутбук, техника, велосипед. Для шины, готовой
# детали, одежды или духов вариант бессмысленный: шина не «на запчасти»,
# она и есть отдельная деталь; духи на запчасти не бывают.
CONDITION_SIMPLE = {
    "key": "condition", "type": "select", "required": False,
    "label": _label("Состояние", "Condition", "Stanje"),
    "options": _options(
        ("new", "Новое", "New", "Novo"),
        ("like_new", "Как новое", "Like new", "Kao novo"),
        ("used", "Б/у", "Used", "Polovno"),
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

# Бренд и модель для авто/мото/грузовых — отдельно от общего BRAND/MODEL
# (тот остаётся текстом: для техники, одежды, духов и подобного —
# готового списка не построишь, брендов слишком много и они не
# перечислимы). Марка машины — наоборот, конечный и всем известный
# список: делаем выпадающим и обязательным, вместо пустого текстового
# поля, которое можно было проскочить не заполнив.
_AUTO_BRAND = {
    "key": "brand", "type": "select", "required": True,
    "label": _label("Марка", "Make", "Marka"),
    "options": _options(
        ("volkswagen", "Volkswagen", "Volkswagen", "Volkswagen"),
        ("opel", "Opel", "Opel", "Opel"),
        ("renault", "Renault", "Renault", "Renault"),
        ("peugeot", "Peugeot", "Peugeot", "Peugeot"),
        ("citroen", "Citroën", "Citroën", "Citroën"),
        ("fiat", "Fiat", "Fiat", "Fiat"),
        ("skoda", "Škoda", "Škoda", "Škoda"),
        ("ford", "Ford", "Ford", "Ford"),
        ("bmw", "BMW", "BMW", "BMW"),
        ("mercedes", "Mercedes-Benz", "Mercedes-Benz", "Mercedes-Benz"),
        ("audi", "Audi", "Audi", "Audi"),
        ("toyota", "Toyota", "Toyota", "Toyota"),
        ("hyundai", "Hyundai", "Hyundai", "Hyundai"),
        ("kia", "Kia", "Kia", "Kia"),
        ("nissan", "Nissan", "Nissan", "Nissan"),
        ("honda", "Honda", "Honda", "Honda"),
        ("mazda", "Mazda", "Mazda", "Mazda"),
        ("volvo", "Volvo", "Volvo", "Volvo"),
        ("seat", "Seat", "Seat", "Seat"),
        ("dacia", "Dacia", "Dacia", "Dacia"),
        ("suzuki", "Suzuki", "Suzuki", "Suzuki"),
        ("mitsubishi", "Mitsubishi", "Mitsubishi", "Mitsubishi"),
        ("chevrolet", "Chevrolet", "Chevrolet", "Chevrolet"),
        ("land_rover", "Land Rover", "Land Rover", "Land Rover"),
        ("jeep", "Jeep", "Jeep", "Jeep"),
        ("mini", "Mini", "Mini", "Mini"),
        ("porsche", "Porsche", "Porsche", "Porsche"),
        ("lexus", "Lexus", "Lexus", "Lexus"),
        ("subaru", "Subaru", "Subaru", "Subaru"),
        ("alfa_romeo", "Alfa Romeo", "Alfa Romeo", "Alfa Romeo"),
        ("lada", "Lada", "Lada", "Lada"),
        ("zastava", "Zastava", "Zastava", "Zastava"),
        ("yugo", "Yugo", "Yugo", "Yugo"),
        ("other", "Другая марка", "Other make", "Druga marka"),
    ),
}

_AUTO_MODEL = {
    "key": "model", "type": "text", "required": True,
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

COLOR = {
    "key": "color", "type": "text", "required": False,
    "label": _label("Цвет", "Color", "Boja"),
}

# ——— недвижимость: то, по чему реально ищут квартиру на любом сайте
# объявлений (Авито, mirkvartir) — этажность дома, санузел, ремонт,
# мебель, балкон. Раньше не было вовсе ни одного из этих полей.
TOTAL_FLOORS = {
    "key": "total_floors", "type": "number", "required": False,
    "label": _label("Этажей в доме", "Floors in building", "Spratova u zgradi"),
}
BATHROOM = {
    "key": "bathroom", "type": "select", "required": False,
    "label": _label("Санузел", "Bathroom", "Kupatilo"),
    "options": _options(
        ("separate", "Раздельный", "Separate", "Odvojeno"),
        ("combined", "Совмещённый", "Combined", "Zajedno"),
    ),
}
RENOVATION = {
    "key": "renovation", "type": "select", "required": False,
    "label": _label("Ремонт", "Renovation", "Renoviranje"),
    "options": _options(
        ("none", "Без ремонта", "No renovation", "Bez renoviranja"),
        ("cosmetic", "Косметический", "Cosmetic", "Kozmetičko"),
        ("euro", "Евроремонт", "Euro renovation", "Evro renoviranje"),
        ("designer", "Дизайнерский", "Designer", "Dizajnersko"),
    ),
}
FURNISHED = {
    "key": "furnished", "type": "boolean", "required": False,
    "label": _label("С мебелью", "Furnished", "Namešteno"),
}
BALCONY = {
    "key": "balcony", "type": "boolean", "required": False,
    "label": _label("Балкон/лоджия", "Balcony/loggia", "Balkon/loža"),
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
# Кузов, топливо, объём двигателя, привод — стандартный набор фильтров
# на любом авто-классифайде (Авито, drom.ru), у нас их не было вовсе.
_BODY_TYPE = {
    "key": "body_type", "type": "select", "required": False,
    "label": _label("Тип кузова", "Body type", "Tip karoserije"),
    "options": _options(
        ("sedan", "Седан", "Sedan", "Limuzina"),
        ("hatchback", "Хэтчбек", "Hatchback", "Hečbek"),
        ("wagon", "Универсал", "Wagon", "Karavan"),
        ("suv", "Внедорожник", "SUV", "Džip"),
        ("minivan", "Минивэн", "Minivan", "Minibus"),
        ("coupe", "Купе", "Coupe", "Kupe"),
        ("pickup", "Пикап", "Pickup", "Pikap"),
    ),
}
_FUEL_TYPE = {
    "key": "fuel_type", "type": "select", "required": False,
    "label": _label("Топливо", "Fuel", "Gorivo"),
    "options": _options(
        ("petrol", "Бензин", "Petrol", "Benzin"),
        ("diesel", "Дизель", "Diesel", "Dizel"),
        ("hybrid", "Гибрид", "Hybrid", "Hibrid"),
        ("electric", "Электро", "Electric", "Električni"),
        ("gas", "Газ", "Gas (LPG)", "Gas (TNG)"),
    ),
}
_ENGINE_VOLUME = {
    "key": "engine_volume", "type": "number", "required": False,
    "label": _label("Объём двигателя, л", "Engine volume, L", "Zapremina motora, L"),
}
_DRIVE_TYPE = {
    "key": "drive_type", "type": "select", "required": False,
    "label": _label("Привод", "Drive type", "Pogon"),
    "options": _options(
        ("fwd", "Передний", "Front-wheel", "Prednji"),
        ("rwd", "Задний", "Rear-wheel", "Zadnji"),
        ("awd", "Полный", "All-wheel", "Sve četiri"),
    ),
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
    "real-estate": [
        {"key": "deal_type", "type": "select", "required": True,
         "label": _label("Тип сделки", "Deal type", "Vrsta ponude"),
         "options": _options(
             ("rent", "Аренда", "Rent", "Izdavanje"),
             ("daily", "Посуточно", "Daily rent", "Na dan"),
             ("sale", "Продажа", "Sale", "Prodaja"),
         )},
        {"key": "area_m2", "type": "number", "required": True,
         "label": _label("Площадь, м²", "Area, m²", "Površina, m²")},
        {"key": "rooms", "type": "number", "required": False,
         "label": _label("Комнат", "Rooms", "Sobe")},
        {"key": "floor", "type": "number", "required": False,
         "label": _label("Этаж", "Floor", "Sprat")},
        TOTAL_FLOORS, BATHROOM, RENOVATION, FURNISHED, BALCONY,
        {"key": "no_commission", "type": "boolean", "required": False,
         "label": _label("Без комиссии", "No commission", "Bez provizije")},
    ],
    "auto": [BRAND, MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _AUTO_TRANSMISSION,
             _BODY_TYPE, _FUEL_TYPE, _ENGINE_VOLUME, COLOR, _AUTO_VIN],
    "electronics": [
        BRAND, MODEL, CONDITION, _STORAGE_GB, _RAM_GB, _SCREEN_INCH,
        _BATTERY_HEALTH, WARRANTY,
    ],
    "fashion": [BRAND, CONDITION_SIMPLE, SIZE_TEXT, GENDER],
    "home-garden": [BRAND, CONDITION_SIMPLE, MATERIAL, DIMENSIONS],
    "kids": [BRAND, CONDITION_SIMPLE, AGE_GROUP, SIZE_TEXT],
    "hobby-sport": [BRAND, CONDITION_SIMPLE, SIZE_TEXT],
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
    "beauty": [BRAND, CONDITION_SIMPLE],
    "business": [BRAND, CONDITION_SIMPLE, YEAR],
}


SUB_SCHEMAS: dict[str, list[dict]] = {
    # ——— недвижимость: у дома нет «этажа квартиры», у гаража нет
    # ремонта и мебели, у коммерческой — своё назначение и высота
    # потолков, а не количество комнат ———
    "flats": [
        {"key": "deal_type", "type": "select", "required": True,
         "label": _label("Тип сделки", "Deal type", "Vrsta ponude"),
         "options": _options(
             ("rent", "Аренда", "Rent", "Izdavanje"),
             ("daily", "Посуточно", "Daily rent", "Na dan"),
             ("sale", "Продажа", "Sale", "Prodaja"),
         )},
        {"key": "area_m2", "type": "number", "required": True,
         "label": _label("Площадь, м²", "Area, m²", "Površina, m²")},
        {"key": "rooms", "type": "number", "required": False,
         "label": _label("Комнат", "Rooms", "Sobe")},
        {"key": "floor", "type": "number", "required": False,
         "label": _label("Этаж", "Floor", "Sprat")},
        TOTAL_FLOORS, BATHROOM, RENOVATION, FURNISHED, BALCONY,
        {"key": "no_commission", "type": "boolean", "required": False,
         "label": _label("Без комиссии", "No commission", "Bez provizije")},
    ],
    "houses": [
        {"key": "deal_type", "type": "select", "required": True,
         "label": _label("Тип сделки", "Deal type", "Vrsta ponude"),
         "options": _options(
             ("rent", "Аренда", "Rent", "Izdavanje"),
             ("sale", "Продажа", "Sale", "Prodaja"),
         )},
        {"key": "area_m2", "type": "number", "required": True,
         "label": _label("Площадь дома, м²", "House area, m²", "Površina kuće, m²")},
        {"key": "land_area_sotka", "type": "number", "required": False,
         "label": _label("Участок, соток", "Land, sotka", "Plac, ari")},
        {"key": "floors_count", "type": "number", "required": False,
         "label": _label("Этажей в доме", "Floors", "Spratova")},
        RENOVATION, FURNISHED,
        {"key": "no_commission", "type": "boolean", "required": False,
         "label": _label("Без комиссии", "No commission", "Bez provizije")},
    ],
    "rooms": [
        {"key": "deal_type", "type": "select", "required": True,
         "label": _label("Тип сделки", "Deal type", "Vrsta ponude"),
         "options": _options(
             ("rent", "Аренда", "Rent", "Izdavanje"),
             ("daily", "Посуточно", "Daily rent", "Na dan"),
         )},
        {"key": "area_m2", "type": "number", "required": False,
         "label": _label("Площадь комнаты, м²", "Room area, m²", "Površina sobe, m²")},
        FURNISHED,
        {"key": "no_commission", "type": "boolean", "required": False,
         "label": _label("Без комиссии", "No commission", "Bez provizije")},
    ],
    "commercial": [
        {"key": "deal_type", "type": "select", "required": True,
         "label": _label("Тип сделки", "Deal type", "Vrsta ponude"),
         "options": _options(
             ("rent", "Аренда", "Rent", "Izdavanje"),
             ("sale", "Продажа", "Sale", "Prodaja"),
         )},
        {"key": "area_m2", "type": "number", "required": True,
         "label": _label("Площадь, м²", "Area, m²", "Površina, m²")},
        {"key": "purpose", "type": "select", "required": False,
         "label": _label("Назначение", "Purpose", "Namena"),
         "options": _options(
             ("office", "Офис", "Office", "Kancelarija"),
             ("retail", "Торговое", "Retail", "Prodajni prostor"),
             ("warehouse", "Склад", "Warehouse", "Magacin"),
             ("production", "Производство", "Production", "Proizvodnja"),
         )},
        {"key": "ceiling_height_m", "type": "number", "required": False,
         "label": _label("Высота потолков, м", "Ceiling height, m", "Visina plafona, m")},
    ],
    "garages": [
        {"key": "deal_type", "type": "select", "required": True,
         "label": _label("Тип сделки", "Deal type", "Vrsta ponude"),
         "options": _options(
             ("rent", "Аренда", "Rent", "Izdavanje"),
             ("sale", "Продажа", "Sale", "Prodaja"),
         )},
        {"key": "area_m2", "type": "number", "required": False,
         "label": _label("Площадь, м²", "Area, m²", "Površina, m²")},
        {"key": "secured", "type": "boolean", "required": False,
         "label": _label("Охраняется", "Secured", "Obezbeđeno")},
    ],

    # ——— авто ———
    "cars": [_AUTO_BRAND, _AUTO_MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _AUTO_TRANSMISSION,
             _BODY_TYPE, _FUEL_TYPE, _ENGINE_VOLUME, _DRIVE_TYPE, COLOR, _AUTO_VIN],
    "moto": [_AUTO_BRAND, _AUTO_MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _ENGINE_VOLUME, COLOR],
    "trucks": [_AUTO_BRAND, _AUTO_MODEL, _AUTO_YEAR, _AUTO_MILEAGE, _AUTO_TRANSMISSION, _BODY_TYPE, _FUEL_TYPE],
    "car-parts": [BRAND, MODEL, CONDITION_SIMPLE],
    "tyres": [BRAND, _TYRE_SIZE, _TYRE_SEASON, CONDITION_SIMPLE],

    # ——— электроника ———
    "phones": [BRAND, MODEL, CONDITION, _STORAGE_GB, _RAM_GB, _SCREEN_INCH, _BATTERY_HEALTH, COLOR, WARRANTY],
    "laptops": [BRAND, MODEL, CONDITION, _CPU, _RAM_GB, _STORAGE_GB, _SCREEN_INCH, COLOR, WARRANTY],
    "computers": [BRAND, CONDITION, _CPU, _GPU, _RAM_GB, _STORAGE_GB, WARRANTY],
    "tablets": [BRAND, MODEL, CONDITION, _STORAGE_GB, _SCREEN_INCH, _BATTERY_HEALTH, COLOR, WARRANTY],
    "tv-audio": [BRAND, MODEL, CONDITION, _SCREEN_INCH, WARRANTY],
    "photo": [BRAND, MODEL, CONDITION, _MEGAPIXELS, WARRANTY],
    "gaming": [BRAND, MODEL, CONDITION, _STORAGE_GB, WARRANTY],
    "wearables": [BRAND, MODEL, CONDITION, _BATTERY_HEALTH, COLOR, WARRANTY],
    "charging": [BRAND, MODEL, CONDITION, WARRANTY],
    "peripherals": [BRAND, MODEL, CONDITION, COLOR, WARRANTY],
    "cases": [BRAND, MODEL, CONDITION, COLOR],

    # ——— одежда и обувь ———
    "women": [BRAND, CONDITION_SIMPLE, SIZE_TEXT, COLOR],
    "men": [BRAND, CONDITION_SIMPLE, SIZE_TEXT, COLOR],
    "shoes": [
        BRAND, CONDITION_SIMPLE, SIZE_TEXT,
        {"key": "insole_cm", "type": "number", "required": False,
         "label": _label("Длина стельки, см", "Insole, cm", "Uložak, cm")},
        COLOR, GENDER,
    ],
    "bags": [BRAND, CONDITION_SIMPLE, MATERIAL, COLOR],
    "watches": [BRAND, CONDITION_SIMPLE, MATERIAL, GENDER],

    # ——— дом и сад ———
    "furniture": [MATERIAL, DIMENSIONS, COLOR, CONDITION_SIMPLE],
    "appliances": [BRAND, CONDITION, POWER_WATTS, WARRANTY],
    "kitchenware": [MATERIAL, CONDITION_SIMPLE],
    "decor": [MATERIAL, DIMENSIONS, CONDITION_SIMPLE],
    "garden": [CONDITION_SIMPLE],
    "tools": [BRAND, CONDITION, POWER_WATTS],

    # ——— детям ———
    "kids-clothing": [BRAND, CONDITION_SIMPLE, AGE_GROUP, SIZE_TEXT],
    "strollers": [
        BRAND, CONDITION_SIMPLE, AGE_GROUP,
        {"key": "stroller_type", "type": "select", "required": False,
         "label": _label("Тип коляски", "Stroller type", "Tip kolica"),
         "options": _options(
             ("stroller", "Прогулочная", "Stroller", "Sportska"),
             ("combo", "2 в 1 / 3 в 1", "2-in-1 / 3-in-1", "2 u 1 / 3 u 1"),
             ("car_seat", "Автокресло", "Car seat", "Auto-sedište"),
         )},
    ],
    "toys": [BRAND, CONDITION_SIMPLE, AGE_GROUP],
    "kids-furniture": [MATERIAL, DIMENSIONS, CONDITION_SIMPLE],
    "school": [BRAND, CONDITION_SIMPLE, AGE_GROUP],

    # ——— хобби и спорт ———
    "bikes": [
        BRAND, MODEL, CONDITION,
        {"key": "bike_type", "type": "select", "required": False,
         "label": _label("Тип велосипеда", "Bike type", "Tip bicikla"),
         "options": _options(
             ("mountain", "Горный", "Mountain", "Brdski"),
             ("road", "Шоссейный", "Road", "Trkački"),
             ("city", "Городской", "City", "Gradski"),
             ("electric", "Электро", "Electric", "Električni"),
             ("kids", "Детский", "Kids'", "Dečji"),
         )},
        {"key": "wheel_size", "type": "text", "required": False,
         "label": _label("Размер колёс", "Wheel size", "Veličina točkova")},
    ],
    "fitness": [BRAND, CONDITION_SIMPLE],
    "outdoor": [BRAND, CONDITION_SIMPLE],
    "music": [
        {"key": "instrument", "type": "text", "required": False,
         "label": _label("Инструмент", "Instrument", "Instrument")},
        BRAND, MODEL, CONDITION_SIMPLE,
    ],
    "books": [
        CONDITION_SIMPLE,
        {"key": "author", "type": "text", "required": False,
         "label": _label("Автор", "Author", "Autor")},
    ],
    "collecting": [CONDITION_SIMPLE, YEAR],

    # ——— животные — вопрос «привит» нелеп для миски или переноски ———
    "pets-dogs": [
        {"key": "breed", "type": "text", "required": False,
         "label": _label("Порода", "Breed", "Rasa")},
        {"key": "age", "type": "text", "required": False,
         "label": _label("Возраст", "Age", "Uzrast")},
        {"key": "sex", "type": "select", "required": False,
         "label": _label("Пол", "Sex", "Pol"),
         "options": _options(("male", "Кобель", "Male", "Mužjak"),
                              ("female", "Сука", "Female", "Ženka"))},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "pets-cats": [
        {"key": "breed", "type": "text", "required": False,
         "label": _label("Порода", "Breed", "Rasa")},
        {"key": "age", "type": "text", "required": False,
         "label": _label("Возраст", "Age", "Uzrast")},
        {"key": "sex", "type": "select", "required": False,
         "label": _label("Пол", "Sex", "Pol"),
         "options": _options(("male", "Кот", "Male", "Mužjak"),
                              ("female", "Кошка", "Female", "Ženka"))},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "pets-other": [
        {"key": "species", "type": "text", "required": False,
         "label": _label("Вид", "Species", "Vrsta")},
        {"key": "age", "type": "text", "required": False,
         "label": _label("Возраст", "Age", "Uzrast")},
    ],
    "pets-supplies": [BRAND, CONDITION_SIMPLE],

    # ——— красота: тот самый случай — духам нужен объём, фену нет ———
    "cosmetics": [
        BRAND, CONDITION_SIMPLE,
        {"key": "volume_ml", "type": "number", "required": False,
         "label": _label("Объём, мл", "Volume, ml", "Zapremina, ml")},
        {"key": "shade", "type": "text", "required": False,
         "label": _label("Оттенок", "Shade", "Nijansa")},
    ],
    "beauty-devices": [BRAND, MODEL, CONDITION, WARRANTY],
    "health": [BRAND, CONDITION_SIMPLE],

    # ——— бизнес ———
    "equipment": [BRAND, MODEL, CONDITION, YEAR],
    "ready-business": [
        {"key": "industry", "type": "text", "required": False,
         "label": _label("Сфера деятельности", "Industry", "Delatnost")},
        {"key": "monthly_revenue", "type": "number", "unit": "currency", "required": False,
         "label": _label("Выручка в месяц", "Monthly revenue", "Mesečni prihod")},
        {"key": "employees", "type": "number", "required": False,
         "label": _label("Сотрудников", "Employees", "Zaposlenih")},
    ],
    "supplies": [BRAND, CONDITION_SIMPLE],
}
