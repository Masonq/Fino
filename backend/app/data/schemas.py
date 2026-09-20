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
    "key": "condition", "type": "select", "required": True,
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
    "key": "condition", "type": "select", "required": True,
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

# Тот же BRAND, но обязательный — для разделов, где бренд практически
# всегда известен и есть на самой вещи (коробка, шильдик, бирка):
# техника, инструмент, велосипед. Для одежды и белья без бирки бренд
# знают не всегда — там остаётся необязательный BRAND.
_BRAND_REQUIRED = {
    "key": "brand", "type": "text", "required": True,
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

# Тот же SIZE_TEXT, но обязательный — для взрослой и детской одежды и
# обуви размер решает, подойдёт ли вещь вообще, покупателю без него
# смотреть на объявление почти незачем.
_SIZE_REQUIRED = {
    "key": "size", "type": "text", "required": True,
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

# Тот же AGE_GROUP, но обязательный — для игрушек и колясок это
# главный ориентир покупателя (годится ли ребёнку по возрасту), не
# второстепенная деталь.
_AGE_GROUP_REQUIRED = {
    "key": "age_group", "type": "select", "required": True,
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


# Комнатность по-сербски.
#
# Числовое поле «Комнат» не давало записать полуторку и двушку с
# половиной — а в Сербии жильё описывают именно так: jednoiposoban,
# dvoiposoban. Человек с «1.5» вписывал 1 или 2, и объявление
# терялось в фильтре у тех, кто искал ровно полуторку.
ROOMS = {
    "key": "rooms", "type": "select", "required": False,
    "label": _label("Комнат", "Rooms", "Sobe"),
    "options": _options(
        ("studio", "Студия", "Studio", "Garsonjera"),
        ("1", "1 комната", "1 room", "Jednosoban"),
        ("1.5", "1.5 комнаты", "1.5 rooms", "Jednoiposoban"),
        ("2", "2 комнаты", "2 rooms", "Dvosoban"),
        ("2.5", "2.5 комнаты", "2.5 rooms", "Dvoiposoban"),
        ("3", "3 комнаты", "3 rooms", "Trosoban"),
        ("4", "4 и больше", "4 or more", "Četvorosoban i više"),
    ),
}

def rooms_value(raw) -> str | None:
    """
    Комнаты в словаре списка ROOMS: «2», «1.5», «4» (четыре и больше).

    Поле было числом, и в базе остались числа, а разбор объявлений из
    Telegram писал их до последнего. Список сравнивает значения строго:
    число 2 не равно строке «2», и в форме редактирования комнаты
    оказывались не выбраны.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, str) and raw.strip().lower() == "studio":
        return "studio"
    try:
        n = float(str(raw).replace(",", "."))
    except ValueError:
        return None
    if n <= 0:
        return None
    if n >= 4:
        return "4"
    return {1.0: "1", 1.5: "1.5", 2.0: "2", 2.5: "2.5", 3.0: "3", 3.5: "3"}.get(n)


# Как платить и как передавать вещь.
#
# Самые частые вопросы в первом же сообщении покупателя — «наличными
# или на карту?» и «встретимся или отправите почтой?». Спрашивать это
# перепиской значит терять время обеих сторон; спрошенное один раз при
# размещении экономит по два сообщения на каждой сделке.
PAYMENT_WAY = {
    "key": "payment_way", "type": "select", "required": False,
    "label": _label("Оплата", "Payment", "Plaćanje"),
    "options": _options(
        ("cash", "Наличными", "Cash", "Gotovina"),
        ("card", "Переводом на карту", "Bank transfer", "Uplata na račun"),
        ("any", "Наличными или переводом", "Cash or transfer", "Gotovina ili uplata"),
    ),
}
HANDOVER = {
    "key": "handover", "type": "select", "required": False,
    "label": _label("Как передать", "Handover", "Preuzimanje"),
    "options": _options(
        ("meet", "Личная встреча", "In person", "Lično preuzimanje"),
        ("post", "Отправлю почтой", "By courier", "Slanje kurirskom službom"),
        ("any", "Встреча или почта", "In person or courier", "Lično ili kurirom"),
    ),
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
        ROOMS,
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
        _BATTERY_HEALTH, WARRANTY, PAYMENT_WAY, HANDOVER,
    ],
    "fashion": [BRAND, CONDITION_SIMPLE, SIZE_TEXT, GENDER, PAYMENT_WAY, HANDOVER],
    "home-garden": [BRAND, CONDITION_SIMPLE, MATERIAL, DIMENSIONS, PAYMENT_WAY, HANDOVER],
    "kids": [BRAND, CONDITION_SIMPLE, AGE_GROUP, SIZE_TEXT, PAYMENT_WAY, HANDOVER],
    "hobby-sport": [BRAND, CONDITION_SIMPLE, SIZE_TEXT, PAYMENT_WAY, HANDOVER],
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
    "beauty": [BRAND, CONDITION_SIMPLE, PAYMENT_WAY, HANDOVER],
    # Вакансии: первое, что смотрят — можно ли удалённо и сколько часов.
    # До сих пор у раздела «Работа» не было полей вовсе, и это стояло в
    # описании вперемешку с обязанностями.
    # Собрано из двух версий. В базе с самого начала живёт схема из
    # seed_categories (тип объявления, занятость, зарплата), а 18 сентября
    # в коде появилась другая — формат, график, опыт, сербский — без
    # первых. Заменить одну другой нельзя: на listing_kind держатся плитки
    # «Вакансии»/«Резюме» (listings.py), страница резюме и автопост, а
    # зарплата — первое, что смотрят в вакансии.
    "jobs": [
        {"key": "listing_kind", "type": "select", "required": True,
         "label": _label("Тип объявления", "Listing type", "Vrsta oglasa"),
         "options": _options(
             ("vacancy", "Вакансия", "Vacancy", "Slobodno radno mesto"),
             ("resume", "Резюме", "Resume", "Radna biografija"),
         )},
        # Ключ и первые два значения — прежние: так пишет разбор из
        # Telegram и так лежит в объявлениях. «График» из новой версии
        # был тем же вопросом под другим ключом; его значения — сюда.
        {"key": "employment_type", "type": "select", "required": False,
         "label": _label("Занятость", "Employment type", "Vrsta zaposlenja"),
         "options": _options(
             ("full_time", "Полная занятость", "Full-time", "Puno radno vreme"),
             ("part_time", "Частичная занятость", "Part-time", "Skraćeno radno vreme"),
             ("shift", "Сменный график", "Shifts", "Smenski rad"),
             ("one_off", "Разовая работа", "One-off job", "Povremeni posao"),
         )},
        {"key": "work_format", "type": "select", "required": False,
         "label": _label("Формат работы", "Work format", "Način rada"),
         "options": _options(
             ("office", "В офисе", "On-site", "U kancelariji"),
             ("remote", "Удалённо", "Remote", "Rad od kuće"),
             ("hybrid", "Гибрид", "Hybrid", "Hibridno"),
         )},
        {"key": "experience", "type": "select", "required": False,
         "label": _label("Опыт", "Experience", "Iskustvo"),
         "options": _options(
             ("none", "Без опыта", "No experience needed", "Bez iskustva"),
             ("some", "От года", "1+ years", "Od godinu dana"),
             ("senior", "От трёх лет", "3+ years", "Od tri godine"),
         )},
        {"key": "serbian_needed", "type": "boolean", "required": False,
         "label": _label("Нужен сербский", "Serbian required", "Potreban srpski")},
        {"key": "salary_min", "type": "number", "unit": "currency", "required": False,
         "label": _label("Зарплата от", "Salary from", "Plata od")},
        {"key": "salary_max", "type": "number", "unit": "currency", "required": False,
         "label": _label("Зарплата до", "Salary to", "Plata do")},
    ],
    "business": [BRAND, CONDITION_SIMPLE, YEAR, PAYMENT_WAY, HANDOVER],
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
        ROOMS,
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
    "car-parts": [_BRAND_REQUIRED, MODEL, CONDITION_SIMPLE],
    "tyres": [_BRAND_REQUIRED, _TYRE_SIZE, _TYRE_SEASON, CONDITION_SIMPLE],

    # ——— электроника ———
    "phones": [_BRAND_REQUIRED, MODEL, CONDITION, _STORAGE_GB, _RAM_GB, _SCREEN_INCH, _BATTERY_HEALTH, COLOR, WARRANTY],
    "laptops": [_BRAND_REQUIRED, MODEL, CONDITION, _CPU, _RAM_GB, _STORAGE_GB, _SCREEN_INCH, COLOR, WARRANTY],
    "computers": [_BRAND_REQUIRED, CONDITION, _CPU, _GPU, _RAM_GB, _STORAGE_GB, WARRANTY],
    "tablets": [_BRAND_REQUIRED, MODEL, CONDITION, _STORAGE_GB, _SCREEN_INCH, _BATTERY_HEALTH, COLOR, WARRANTY],
    # Без диагонали: раздел переименован в «Аудиотехника и колонки»,
    # телевизоры живут в tv-projectors.
    "tv-audio": [_BRAND_REQUIRED, MODEL, CONDITION, WARRANTY],
    "photo": [_BRAND_REQUIRED, MODEL, CONDITION, _MEGAPIXELS, WARRANTY],
    "gaming": [_BRAND_REQUIRED, MODEL, CONDITION, _STORAGE_GB, WARRANTY],
    "wearables": [_BRAND_REQUIRED, MODEL, CONDITION, _BATTERY_HEALTH, COLOR, WARRANTY],
    "charging": [_BRAND_REQUIRED, MODEL, CONDITION, WARRANTY],
    "peripherals": [_BRAND_REQUIRED, MODEL, CONDITION, COLOR, WARRANTY],
    "cases": [BRAND, MODEL, CONDITION, COLOR],

    # ——— одежда и обувь ———
    "women": [BRAND, CONDITION_SIMPLE, _SIZE_REQUIRED, COLOR],
    "men": [BRAND, CONDITION_SIMPLE, _SIZE_REQUIRED, COLOR],
    "shoes": [
        BRAND, CONDITION_SIMPLE, _SIZE_REQUIRED,
        {"key": "insole_cm", "type": "number", "required": False,
         "label": _label("Длина стельки, см", "Insole, cm", "Uložak, cm")},
        COLOR, GENDER,
    ],
    "bags": [BRAND, CONDITION_SIMPLE, MATERIAL, COLOR],
    "watches": [BRAND, CONDITION_SIMPLE, MATERIAL, GENDER],

    # ——— дом и сад ———
    "furniture": [MATERIAL, DIMENSIONS, COLOR, CONDITION_SIMPLE],
    "appliances": [_BRAND_REQUIRED, CONDITION, POWER_WATTS, WARRANTY],
    "kitchenware": [MATERIAL, CONDITION_SIMPLE],
    "decor": [MATERIAL, DIMENSIONS, CONDITION_SIMPLE],
    "garden": [CONDITION_SIMPLE],
    "tools": [_BRAND_REQUIRED, CONDITION, POWER_WATTS],

    # ——— детям ———
    "kids-clothing": [BRAND, CONDITION_SIMPLE, AGE_GROUP, _SIZE_REQUIRED],
    "strollers": [
        _BRAND_REQUIRED, CONDITION_SIMPLE, _AGE_GROUP_REQUIRED,
        {"key": "stroller_type", "type": "select", "required": False,
         "label": _label("Тип коляски", "Stroller type", "Tip kolica"),
         "options": _options(
             ("stroller", "Прогулочная", "Stroller", "Sportska"),
             ("combo", "2 в 1 / 3 в 1", "2-in-1 / 3-in-1", "2 u 1 / 3 u 1"),
             ("car_seat", "Автокресло", "Car seat", "Auto-sedište"),
         )},
    ],
    "toys": [BRAND, CONDITION_SIMPLE, _AGE_GROUP_REQUIRED],
    "kids-furniture": [MATERIAL, DIMENSIONS, CONDITION_SIMPLE],
    "school": [BRAND, CONDITION_SIMPLE, _AGE_GROUP_REQUIRED],

    # ——— хобби и спорт ———
    "bikes": [
        _BRAND_REQUIRED, MODEL, CONDITION,
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
        {"key": "instrument", "type": "text", "required": True,
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
        {"key": "age", "type": "text", "required": True,
         "label": _label("Возраст", "Age", "Uzrast")},
        {"key": "sex", "type": "select", "required": True,
         "label": _label("Пол", "Sex", "Pol"),
         "options": _options(("male", "Кобель", "Male", "Mužjak"),
                              ("female", "Сука", "Female", "Ženka"))},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "pets-cats": [
        {"key": "breed", "type": "text", "required": False,
         "label": _label("Порода", "Breed", "Rasa")},
        {"key": "age", "type": "text", "required": True,
         "label": _label("Возраст", "Age", "Uzrast")},
        {"key": "sex", "type": "select", "required": True,
         "label": _label("Пол", "Sex", "Pol"),
         "options": _options(("male", "Кот", "Male", "Mužjak"),
                              ("female", "Кошка", "Female", "Ženka"))},
        {"key": "vaccinated", "type": "boolean", "required": False,
         "label": _label("Привит", "Vaccinated", "Vakcinisan")},
    ],
    "pets-other": [
        {"key": "species", "type": "text", "required": True,
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
    "beauty-devices": [_BRAND_REQUIRED, MODEL, CONDITION, WARRANTY],
    "health": [BRAND, CONDITION_SIMPLE],

    # ——— бизнес ———
    "equipment": [_BRAND_REQUIRED, MODEL, CONDITION, YEAR],
    "ready-business": [
        {"key": "industry", "type": "text", "required": True,
         "label": _label("Сфера деятельности", "Industry", "Delatnost")},
        {"key": "monthly_revenue", "type": "number", "unit": "currency", "required": False,
         "label": _label("Выручка в месяц", "Monthly revenue", "Mesečni prihod")},
        {"key": "employees", "type": "number", "required": False,
         "label": _label("Сотрудников", "Employees", "Zaposlenih")},
    ],
    "supplies": [BRAND, CONDITION_SIMPLE],
}

# ——— подразделы, которым схема раздела не подходит ———
#
# Подраздел без своей схемы берёт схему раздела. Для «Лодок» это значило
# пробег, коробку передач и VIN, для «Мониторов» — память и состояние
# аккумулятора, для «Билетов» — размер. Продавца спрашивали о том, чего
# у его вещи нет, а на странице подраздела по этому же предлагали искать.

def _kind(key: str, ru: str, en: str, sr: str, *items) -> dict:
    return {"key": key, "type": "select", "required": False,
            "label": _label(ru, en, sr), "options": _options(*items)}


_AGE_TEXT = {"key": "age", "type": "text", "required": False,
             "label": _label("Возраст", "Age", "Uzrast")}
_SPECIES = {"key": "species", "type": "text", "required": True,
            "label": _label("Вид", "Species", "Vrsta")}

SUB_SCHEMAS.update({
    # ——— авто ———
    "water": [
        _kind("boat_type", "Тип", "Type", "Tip",
              ("motorboat", "Моторная лодка", "Motorboat", "Motorni čamac"),
              ("cruiser", "Катер", "Cruiser", "Gliser"),
              ("yacht", "Яхта", "Yacht", "Jahta"),
              ("inflatable", "Надувная лодка", "Inflatable", "Gumenjak"),
              ("jetski", "Гидроцикл", "Jet ski", "Skuter za vodu"),
              ("kayak", "Каяк, сап, байдарка", "Kayak, SUP", "Kajak, SUP"),
              ("engine", "Лодочный мотор", "Outboard engine", "Vanbrodski motor")),
        BRAND, MODEL, YEAR,
        {"key": "length_m", "type": "number", "required": False,
         "label": _label("Длина, м", "Length, m", "Dužina, m")},
        {"key": "engine_power_hp", "type": "number", "required": False,
         "label": _label("Мощность мотора, л.с.", "Engine power, hp", "Snaga motora, KS")},
    ],
    # «Сельхозтехника» слита в «Строительную и сельхозтехнику» (третий
    # уровень в «Грузовых»): схема нужна там, иначе трактор спрашивают
    # про кузов и коробку, как грузовик.
    "trucks-construction": [
        _kind("agri_type", "Тип", "Type", "Tip",
              ("tractor", "Трактор", "Tractor", "Traktor"),
              ("excavator", "Экскаватор", "Excavator", "Bager"),
              ("loader", "Погрузчик", "Loader", "Utovarivač"),
              ("combine", "Комбайн", "Combine", "Kombajn"),
              ("tiller", "Мотоблок, мотокультиватор", "Tiller", "Motokultivator"),
              ("attachment", "Навесное и прицепное", "Attachments", "Priključne mašine"),
              ("other", "Другое", "Other", "Drugo")),
        BRAND, MODEL, YEAR,
        {"key": "engine_hours", "type": "number", "required": False,
         "label": _label("Наработка, моточасов", "Engine hours", "Radni sati")},
        {"key": "engine_power_hp", "type": "number", "required": False,
         "label": _label("Мощность, л.с.", "Power, hp", "Snaga, KS")},
    ],
    "trailers": [
        _kind("trailer_type", "Тип", "Type", "Tip",
              ("cargo", "Грузовой прицеп", "Cargo trailer", "Teretna prikolica"),
              ("boat", "Для лодки", "Boat trailer", "Prikolica za čamac"),
              ("caravan", "Дом на колёсах, караван", "Caravan", "Kamp prikolica"),
              ("camper", "Автодом", "Motorhome", "Kamper"),
              ("other", "Другое", "Other", "Drugo")),
        BRAND, YEAR,
        {"key": "payload_kg", "type": "number", "required": False,
         "label": _label("Грузоподъёмность, кг", "Payload, kg", "Nosivost, kg")},
    ],
    "e-transport": [
        _kind("etransport_type", "Тип", "Type", "Tip",
              ("scooter", "Электросамокат", "E-scooter", "Električni trotinet"),
              ("ebike", "Электровелосипед", "E-bike", "Električni bicikl"),
              ("moped", "Электроскутер", "E-moped", "Električni skuter"),
              ("unicycle", "Моноколесо, гироскутер", "Unicycle, hoverboard", "Monocikl, hoverbord"),
              ("other", "Другое", "Other", "Drugo")),
        _BRAND_REQUIRED, MODEL, CONDITION,
        {"key": "range_km", "type": "number", "required": False,
         "label": _label("Запас хода, км", "Range, km", "Domet, km")},
    ],
    "car-rental": [_AUTO_BRAND, _AUTO_MODEL, _AUTO_YEAR, _AUTO_TRANSMISSION, _BODY_TYPE],

    # ——— электроника ———
    "components": [_BRAND_REQUIRED, MODEL, CONDITION, WARRANTY],
    "smart-home": [_BRAND_REQUIRED, MODEL, CONDITION, WARRANTY],
    "network-gear": [_BRAND_REQUIRED, MODEL, CONDITION, WARRANTY],
    "monitors": [_BRAND_REQUIRED, MODEL, CONDITION, _SCREEN_INCH, WARRANTY],
    "tv-projectors": [_BRAND_REQUIRED, MODEL, CONDITION, _SCREEN_INCH, WARRANTY],

    # ——— одежда ———
    # «Украшения» слиты в «Часы и украшения» (watches) — у них эти же поля.

    # ——— хобби и спорт ———
    "fishing-hunting": [BRAND, CONDITION_SIMPLE],
    "board-games": [CONDITION_SIMPLE],
    "crafts": [CONDITION_SIMPLE],
    "sport-nutrition": [BRAND],
    "tickets": [
        _kind("ticket_kind", "Что это", "Kind", "Vrsta",
              ("concert", "Концерт, фестиваль", "Concert, festival", "Koncert, festival"),
              ("sport", "Спорт", "Sport", "Sport"),
              ("theatre", "Театр, кино", "Theatre, cinema", "Pozorište, bioskop"),
              ("travel", "Поездка, перелёт", "Travel", "Putovanje"),
              ("voucher", "Сертификат, абонемент", "Voucher, pass", "Vaučer, članarina"),
              ("other", "Другое", "Other", "Drugo")),
    ],

    # ——— дом и сад ———
    "building": [BRAND, CONDITION_SIMPLE],
    "plumbing": [BRAND, CONDITION_SIMPLE],
    "lighting": [BRAND, CONDITION_SIMPLE],
    "storage-home": [MATERIAL, DIMENSIONS, CONDITION_SIMPLE],

    # ——— детям ———
    "kids-transport": [BRAND, CONDITION_SIMPLE, AGE_GROUP],
    "kids-feeding": [BRAND, CONDITION_SIMPLE],

    # ——— животные ———
    "pets-birds": [_SPECIES, _AGE_TEXT],
    "pets-farm": [_SPECIES, _AGE_TEXT],
})

# Подразделы, у которых полей нет вовсе, и наследовать чужие незачем:
# у домашней еды и бытовой химии нет ни «материала», ни «габаритов».
# Пустая схема в базе значит «возьми у раздела», поэтому отдельный список.
NO_FIELDS = {"food", "household-goods"}

# Прежние версии схем из кода, по отпечатку «ключ:тип».
#
# Если в базе лежит ровно такая — схему на месте не правили, это наша же
# старая версия, и sync_schemas заменяет её новой. Всё остальное он
# считает ручной правкой и не трогает.
#
# Список — правка 18 сентября (комнаты списком, оплата и передача): она
# изменила код, а до базы донести её было нечем, и форма размещения три
# дня работала по старым схемам.
_GOODS_OLD = ["brand:text", "condition:select"]
_FLAT_OLD = ["deal_type:select", "area_m2:number", "rooms:number", "floor:number",
             "total_floors:number", "bathroom:select", "renovation:select",
             "furnished:boolean", "balcony:boolean", "no_commission:boolean"]
SUPERSEDED: dict[str, list[list[str]]] = {
    "flats": [_FLAT_OLD],
    "real-estate": [_FLAT_OLD],
    "beauty": [_GOODS_OLD],
    "business": [_GOODS_OLD + ["year:number"]],
    "fashion": [_GOODS_OLD + ["size:text", "gender:select"]],
    "hobby-sport": [_GOODS_OLD + ["size:text"]],
    "home-garden": [_GOODS_OLD + ["material:text", "dimensions:text"]],
    "kids": [_GOODS_OLD + ["age_group:select", "size:text"]],
    "electronics": [["brand:text", "model:text", "condition:select", "storage_gb:number",
                     "ram_gb:number", "screen_inch:number", "battery_health:number",
                     "warranty:boolean"]],
    "tv-audio": [["brand:text", "model:text", "condition:select", "screen_inch:number",
                  "warranty:boolean"]],
    # схема из seed_categories.py, с которой раздел живёт с самого начала
    "jobs": [["listing_kind:select", "employment_type:select",
              "salary_min:number", "salary_max:number"]],
}


def fingerprint(schema: list[dict]) -> list[str]:
    return [f"{f.get('key')}:{f.get('type')}" for f in schema or []]
