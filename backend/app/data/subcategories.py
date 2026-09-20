"""
Подкатегории.

Без них «Электроника» вмещает и телефоны, и холодильники, и приставки — по
такой категории невозможно ни искать, ни просматривать. Тем более это важно
до переноса объявлений из телеграм-чатов: разгребать тысячи записей в плоской
категории потом придётся руками.

Названия сразу на трёх языках — категории показываются на языке интерфейса,
и подкатегория без перевода выпадала бы из общего списка.

Своих атрибутов у части подкатегорий есть (см. SUB_SCHEMAS в
app/data/schemas.py) — там, где поля родителя не подходят: духам нужен
объём, фену для лица — нет. Где подкатегория не задана в SUB_SCHEMAS,
она наследует схему родителя как раньше.
"""

SUBCATEGORIES: dict[str, list[dict]] = {
    "real-estate": [
        {"slug": "flats", "name": {"ru": "Квартиры", "en": "Flats", "sr": "Stanovi"}},
        {"slug": "houses", "name": {"ru": "Дома и участки", "en": "Houses & land", "sr": "Kuće i placevi"}},
        {"slug": "rooms", "name": {"ru": "Комнаты", "en": "Rooms", "sr": "Sobe"}},
        {"slug": "commercial", "name": {"ru": "Коммерческая", "en": "Commercial", "sr": "Poslovni prostor"}},
        {"slug": "garages", "name": {"ru": "Гаражи и паркинг", "en": "Garages & parking", "sr": "Garaže i parking"}},
        {"slug": "land", "name": {"ru": "Участки и земля", "en": "Land & plots", "sr": "Placevi i zemljište"}},
        {"slug": "daily-rent", "name": {"ru": "Посуточная аренда", "en": "Short-term rentals", "sr": "Izdavanje na dan"}},
    ],
    "auto": [
        {"slug": "cars", "name": {"ru": "Легковые", "en": "Cars", "sr": "Automobili"}},
        {"slug": "moto", "name": {"ru": "Мото", "en": "Motorcycles", "sr": "Motocikli"}},
        {"slug": "trucks", "name": {"ru": "Грузовые и спецтехника", "en": "Trucks & machinery", "sr": "Kamioni i mašine"}},
        {"slug": "car-parts", "name": {"ru": "Запчасти", "en": "Parts", "sr": "Delovi"}},
        {"slug": "tyres", "name": {"ru": "Шины и диски", "en": "Tyres & wheels", "sr": "Gume i felne"}},
        {"slug": "trailers", "name": {"ru": "Прицепы и дома на колёсах", "en": "Trailers & campers", "sr": "Prikolice i kamperi"}},
        {"slug": "water", "name": {"ru": "Лодки и катера", "en": "Boats", "sr": "Čamci i plovila"}},
        {"slug": "agri", "name": {"ru": "Сельхозтехника", "en": "Farm machinery", "sr": "Poljoprivredne mašine"}},
        {"slug": "e-transport", "name": {"ru": "Самокаты и электротранспорт", "en": "Scooters & e-transport", "sr": "Trotineti i e-prevoz"}},
        {"slug": "car-rental", "name": {"ru": "Аренда авто", "en": "Car rental", "sr": "Rent a car"}},
    ],
    "electronics": [
        {"slug": "phones", "name": {"ru": "Телефоны", "en": "Phones", "sr": "Telefoni"}},
        {"slug": "laptops", "name": {"ru": "Ноутбуки", "en": "Laptops", "sr": "Laptopovi"}},
        {"slug": "computers", "name": {"ru": "Настольные компьютеры", "en": "Desktop computers", "sr": "Stoni računari"}},
        {"slug": "tablets", "name": {"ru": "Планшеты и электронные книги", "en": "Tablets & e-readers", "sr": "Tableti"}},
        {"slug": "tv-audio", "name": {"ru": "Аудио и видео", "en": "Audio & video", "sr": "Audio i video"}},
        {"slug": "photo", "name": {"ru": "Фототехника", "en": "Photo equipment", "sr": "Foto oprema"}},
        {"slug": "gaming", "name": {"ru": "Игры, приставки и программы", "en": "Games & consoles", "sr": "Igre i konzole"}},
        # Раньше один общий gadgets — умные часы, зарядки, клавиатуры,
        # чехлы вперемешку. У обучаемого классификатора для такой
        # разношёрстной корзины не набирается общего словаря (часы и
        # чехлы не делят почти ни одного слова), и она забирала на себя
        # больше трети всех объявлений раздела — не потому что их и
        # правда столько, а потому что была самой широкой сетью.
        # Разбито на четыре узких раздела — каждому есть свой узнаваемый
        # словарь, в отличие от одной общей «мелочи».
        {"slug": "wearables", "name": {"ru": "Умные часы и браслеты", "en": "Smartwatches & bands", "sr": "Pametni satovi i narukvice"}},
        {"slug": "charging", "name": {"ru": "Зарядки и повербанки", "en": "Chargers & power banks", "sr": "Punjači i pauerbanke"}},
        {"slug": "peripherals", "name": {"ru": "Периферия для компьютера", "en": "Computer peripherals", "sr": "Periferija za računar"}},
        {"slug": "cases", "name": {"ru": "Чехлы и защита", "en": "Cases & protection", "sr": "Maske i zaštita"}},
        {"slug": "components", "name": {"ru": "Комплектующие", "en": "PC components", "sr": "Komponente"}},
        {"slug": "smart-home", "name": {"ru": "Умный дом", "en": "Smart home", "sr": "Pametna kuća"}},
    ],
    "home-garden": [
        {"slug": "furniture", "name": {"ru": "Мебель", "en": "Furniture", "sr": "Nameštaj"}},
        {"slug": "appliances", "name": {"ru": "Бытовая техника", "en": "Appliances", "sr": "Bela tehnika"}},
        {"slug": "kitchenware", "name": {"ru": "Посуда и кухня", "en": "Kitchenware", "sr": "Posuđe i kuhinja"}},
        {"slug": "decor", "name": {"ru": "Декор и текстиль", "en": "Decor & textiles", "sr": "Dekoracija i tekstil"}},
        {"slug": "garden", "name": {"ru": "Сад и растения", "en": "Garden & plants", "sr": "Bašta i biljke"}},
        {"slug": "tools", "name": {"ru": "Инструменты и ремонт", "en": "Tools & DIY", "sr": "Alati"}},
        {"slug": "building", "name": {"ru": "Стройматериалы", "en": "Building materials", "sr": "Građevinski materijal"}},
        {"slug": "plumbing", "name": {"ru": "Сантехника и отопление", "en": "Plumbing & heating", "sr": "Vodovod i grejanje"}},
        {"slug": "textile", "name": {"ru": "Текстиль и посуда для дома", "en": "Home textile", "sr": "Tekstil za kuću"}},
        {"slug": "food", "name": {"ru": "Продукты и домашнее", "en": "Food and homemade", "sr": "Hrana i domaći proizvodi"}},
    ],
    "fashion": [
        {"slug": "women", "name": {"ru": "Женская одежда", "en": "Women's clothing", "sr": "Ženska odeća"}},
        {"slug": "men", "name": {"ru": "Мужская одежда", "en": "Men's clothing", "sr": "Muška odeća"}},
        {"slug": "shoes", "name": {"ru": "Обувь", "en": "Shoes", "sr": "Obuća"}},
        {"slug": "bags", "name": {"ru": "Сумки и аксессуары", "en": "Bags & accessories", "sr": "Torbe i dodaci"}},
        {"slug": "watches", "name": {"ru": "Часы и украшения", "en": "Watches & jewellery", "sr": "Satovi i nakit"}},
        {"slug": "jewelry", "name": {"ru": "Украшения", "en": "Jewellery", "sr": "Nakit"}},
    ],
    "kids": [
        {"slug": "kids-clothing", "name": {"ru": "Детская одежда и обувь", "en": "Kids' clothing", "sr": "Dečja odeća"}},
        {"slug": "strollers", "name": {"ru": "Коляски и автокресла", "en": "Strollers & car seats", "sr": "Kolica i auto-sedišta"}},
        {"slug": "toys", "name": {"ru": "Игрушки", "en": "Toys", "sr": "Igračke"}},
        {"slug": "kids-furniture", "name": {"ru": "Детская мебель", "en": "Kids' furniture", "sr": "Dečji nameštaj"}},
        {"slug": "school", "name": {"ru": "Школьные товары", "en": "School supplies", "sr": "Školski pribor"}},
        {"slug": "car-seats", "name": {"ru": "Автокресла", "en": "Car seats", "sr": "Auto-sedišta"}},
        {"slug": "kids-transport", "name": {"ru": "Детский транспорт", "en": "Kids bikes & scooters", "sr": "Bicikli i trotineti za decu"}},
    ],
    "hobby-sport": [
        {"slug": "bikes", "name": {"ru": "Велосипеды и самокаты", "en": "Bikes & scooters", "sr": "Bicikli i trotineti"}},
        {"slug": "fitness", "name": {"ru": "Спортинвентарь", "en": "Sports equipment", "sr": "Sportska oprema"}},
        {"slug": "outdoor", "name": {"ru": "Туризм и отдых", "en": "Outdoor", "sr": "Kamping i priroda"}},
        {"slug": "music", "name": {"ru": "Музыкальные инструменты", "en": "Musical instruments", "sr": "Muzički instrumenti"}},
        {"slug": "books", "name": {"ru": "Книги", "en": "Books", "sr": "Knjige"}},
        {"slug": "collecting", "name": {"ru": "Коллекционирование и винтаж", "en": "Collectibles & vintage", "sr": "Kolekcionarstvo"}},
        {"slug": "winter-sport", "name": {"ru": "Зимний спорт", "en": "Winter sports", "sr": "Zimski sportovi"}},
        {"slug": "fishing-hunting", "name": {"ru": "Рыбалка и охота", "en": "Fishing & hunting", "sr": "Pecanje i lov"}},
        {"slug": "board-games", "name": {"ru": "Настольные игры", "en": "Board games", "sr": "Društvene igre"}},
        {"slug": "tickets", "name": {"ru": "Билеты и сертификаты", "en": "Tickets and vouchers", "sr": "Karte i vaučeri"}},
    ],
    "pets": [
        {"slug": "pets-dogs", "name": {"ru": "Собаки", "en": "Dogs", "sr": "Psi"}},
        {"slug": "pets-cats", "name": {"ru": "Кошки", "en": "Cats", "sr": "Mačke"}},
        {"slug": "pets-other", "name": {"ru": "Другие животные", "en": "Other animals", "sr": "Ostale životinje"}},
        {"slug": "pets-supplies", "name": {"ru": "Товары для животных", "en": "Pet supplies", "sr": "Oprema za ljubimce"}},
        {"slug": "pets-birds", "name": {"ru": "Птицы", "en": "Birds", "sr": "Ptice"}},
        {"slug": "pets-farm", "name": {"ru": "Домашний скот и птица", "en": "Farm animals", "sr": "Domaće životinje"}},
    ],
    "beauty": [
        {"slug": "cosmetics", "name": {"ru": "Косметика и парфюмерия", "en": "Cosmetics & perfume", "sr": "Kozmetika i parfemi"}},
        {"slug": "beauty-devices", "name": {"ru": "Приборы для красоты", "en": "Beauty devices", "sr": "Aparati za lepotu"}},
        {"slug": "health", "name": {"ru": "Здоровье и уход", "en": "Health & care", "sr": "Zdravlje i nega"}},
    ],
    "services": [
        {"slug": "repair", "name": {"ru": "Ремонт и строительство", "en": "Repair & building", "sr": "Popravke i gradnja"}},
        {"slug": "transport", "name": {"ru": "Перевозки и визараны", "en": "Transport & visa runs", "sr": "Prevoz"}},
        {"slug": "beauty-services", "name": {"ru": "Красота и здоровье", "en": "Beauty & health", "sr": "Lepota i zdravlje"}},
        {"slug": "tutoring", "name": {"ru": "Обучение и репетиторы", "en": "Tutoring", "sr": "Časovi i obuka"}},
        {"slug": "cleaning", "name": {"ru": "Уборка и помощь по дому", "en": "Cleaning & household", "sr": "Čišćenje i pomoć"}},
        {"slug": "it-design", "name": {"ru": "IT и дизайн", "en": "IT & design", "sr": "IT i dizajn"}},
        {"slug": "legal", "name": {"ru": "Документы и юристы", "en": "Legal & paperwork", "sr": "Dokumenti i pravo"}},
        {"slug": "childcare", "name": {"ru": "Няни и уход", "en": "Childcare & care", "sr": "Čuvanje dece i nega"}},
        {"slug": "photo-video", "name": {"ru": "Фото и видео", "en": "Photo & video", "sr": "Foto i video"}},
        {"slug": "events", "name": {"ru": "Праздники и мероприятия", "en": "Events", "sr": "Proslave i događaji"}},
        {"slug": "docs-visa", "name": {"ru": "Документы и визы", "en": "Documents & visas", "sr": "Dokumenti i vize"}},
        {"slug": "medical", "name": {"ru": "Здоровье и медицина", "en": "Health & medical", "sr": "Zdravlje i medicina"}},
        {"slug": "auto-services", "name": {"ru": "Автосервис и шиномонтаж", "en": "Car service and tyres", "sr": "Auto servis i vulkanizer"}},
        {"slug": "lost-found", "name": {"ru": "Находки и пропажи", "en": "Lost and found", "sr": "Izgubljeno i nađeno"}},
    ],
    "jobs": [
        {"slug": "vacancies", "name": {"ru": "Вакансии", "en": "Vacancies", "sr": "Poslovi"}},
        {"slug": "resumes", "name": {"ru": "Резюме", "en": "Resumes", "sr": "Biografije"}},
    ],
    "business": [
        {"slug": "equipment", "name": {"ru": "Оборудование", "en": "Equipment", "sr": "Oprema"}},
        {"slug": "ready-business", "name": {"ru": "Готовый бизнес", "en": "Businesses for sale", "sr": "Biznis na prodaju"}},
        {"slug": "supplies", "name": {"ru": "Расходники и упаковка", "en": "Supplies & packaging", "sr": "Potrošni materijal"}},
        {"slug": "agriculture", "name": {"ru": "Сельское хозяйство", "en": "Agriculture", "sr": "Poljoprivreda"}},
        {"slug": "rental-equipment", "name": {"ru": "Аренда оборудования", "en": "Equipment rental", "sr": "Iznajmljivanje opreme"}},
    ],
}

# Третий уровень — родитель тут уже сама подкатегория (её slug —
# ключ), не корневая категория. По той же логике, что и раскол
# "gadgets" выше: "Игры, приставки и программы" объединяла три
# совсем разных типа товара под одной крышей (сама игра, железо
# приставки, программа/подписка) — у покупателя, который ищет
# конкретно PS5, нет способа отсеять диски с играми и наоборот.
# "Запчасти" для авто — то же самое: деталь двигателя и автомагнитола
# делят категорию, но не делят ни одного слова в описании.
# Добавляется только там, где реально есть эта путаница — не
# бездумно на каждую подкатегорию подряд.
SUB_SUBCATEGORIES: dict[str, list[dict]] = {
    "gaming": [
        {"slug": "consoles", "name": {"ru": "Игровые приставки", "en": "Game consoles", "sr": "Konzole"}},
        {"slug": "games-ps", "name": {"ru": "Игры для PlayStation", "en": "PlayStation games", "sr": "Igre za PlayStation"}},
        {"slug": "games-xbox", "name": {"ru": "Игры для Xbox", "en": "Xbox games", "sr": "Igre za Xbox"}},
        {"slug": "games-nintendo", "name": {"ru": "Игры для Nintendo", "en": "Nintendo games", "sr": "Igre za Nintendo"}},
        {"slug": "games-pc", "name": {"ru": "Игры и программы для ПК", "en": "PC games & software", "sr": "PC igre i softver"}},
        {"slug": "gaming-accessories", "name": {"ru": "Игровые аксессуары", "en": "Gaming accessories", "sr": "Gejming dodaci"}},
    ],
    "car-parts": [
        {"slug": "parts-engine", "name": {"ru": "Двигатель и трансмиссия", "en": "Engine & transmission", "sr": "Motor i menjač"}},
        {"slug": "parts-body", "name": {"ru": "Кузов и оптика", "en": "Body & lighting", "sr": "Karoserija i svetla"}},
        {"slug": "parts-interior", "name": {"ru": "Салон и электроника", "en": "Interior & electronics", "sr": "Enterijer i elektronika"}},
        {"slug": "parts-suspension", "name": {"ru": "Подвеска и тормоза", "en": "Suspension & brakes", "sr": "Ovešenje i kočnice"}},
        {"slug": "parts-audio", "name": {"ru": "Автозвук и мультимедиа", "en": "Car audio & multimedia", "sr": "Auto zvuk i multimedija"}},
    ],
    # Эвакуатор, автобус и трактор — все трое «Грузовые и спецтехника»,
    # но не делят почти ни одного слова в описании.
    "trucks": [
        {"slug": "trucks-vans", "name": {"ru": "Грузовики и фургоны", "en": "Trucks & vans", "sr": "Kamioni i kombiji"}},
        {"slug": "trucks-buses", "name": {"ru": "Автобусы и микроавтобусы", "en": "Buses & minibuses", "sr": "Autobusi i kombi vozila"}},
        {"slug": "trucks-construction", "name": {"ru": "Строительная и сельхозтехника", "en": "Construction & farm machinery", "sr": "Građevinske i poljoprivredne mašine"}},
        {"slug": "trucks-trailers", "name": {"ru": "Прицепы", "en": "Trailers", "sr": "Prikolice"}},
    ],
    # Офис, склад и магазинное помещение ищут по совсем разным
    # параметрам (проходимость против высоты потолков под стеллажи).
    "commercial": [
        {"slug": "commercial-office", "name": {"ru": "Офисы", "en": "Offices", "sr": "Kancelarije"}},
        {"slug": "commercial-retail", "name": {"ru": "Торговые помещения", "en": "Retail space", "sr": "Poslovni prostor za trgovinu"}},
        {"slug": "commercial-warehouse", "name": {"ru": "Склады и производство", "en": "Warehouses & production", "sr": "Magacini i proizvodnja"}},
    ],
    # Дом со спальнями и голый участок земли — разная суть объявления,
    # не просто разные слова.
    "houses": [
        {"slug": "houses-only", "name": {"ru": "Дома", "en": "Houses", "sr": "Kuće"}},
        {"slug": "land", "name": {"ru": "Участки", "en": "Land plots", "sr": "Placevi"}},
    ],
    # Холодильник и чайник оба «бытовая техника», но ищут их по-разному
    # (габариты и подключение против цены и цвета).
    "appliances": [
        {"slug": "appliances-major", "name": {"ru": "Крупная техника", "en": "Major appliances", "sr": "Bela tehnika"}},
        {"slug": "appliances-small", "name": {"ru": "Мелкая техника", "en": "Small appliances", "sr": "Mali kućni aparati"}},
    ],
    # Штанга, лыжи и мяч для футбола не делят словарь вовсе — самая
    # широкая сеть во всём разделе «Хобби, спорт, отдых».
    "fitness": [
        {"slug": "fitness-gym", "name": {"ru": "Тренажёры и фитнес", "en": "Gym & fitness", "sr": "Sprave i fitnes"}},
        {"slug": "fitness-winter", "name": {"ru": "Зимний спорт", "en": "Winter sports", "sr": "Zimski sportovi"}},
        {"slug": "fitness-water", "name": {"ru": "Водный спорт", "en": "Water sports", "sr": "Vodeni sportovi"}},
        {"slug": "fitness-team", "name": {"ru": "Командные игры", "en": "Team sports", "sr": "Timski sportovi"}},
    ],
    # Сантехник, электрик и маляр — три разные профессии под одной
    # услугой, у каждой свой узнаваемый словарь заявки.
    "repair": [
        {"slug": "repair-plumbing", "name": {"ru": "Сантехника", "en": "Plumbing", "sr": "Vodoinstalacije"}},
        {"slug": "repair-electrical", "name": {"ru": "Электрика", "en": "Electrical", "sr": "Elektrika"}},
        {"slug": "repair-finishing", "name": {"ru": "Отделка и ремонт", "en": "Finishing & renovation", "sr": "Završni radovi"}},
        {"slug": "repair-materials", "name": {"ru": "Стройматериалы", "en": "Building materials", "sr": "Građevinski materijal"}},
    ],
    # Программист и дизайнер — разные специальности, разные заказчики
    # ищут их по-разному.
    "it-design": [
        {"slug": "it-dev", "name": {"ru": "Разработка и IT", "en": "Development & IT", "sr": "Razvoj i IT"}},
        {"slug": "design-graphics", "name": {"ru": "Дизайн и графика", "en": "Design & graphics", "sr": "Dizajn i grafika"}},
    ],
    # Корм, переноска и когтеточка — три разных отдела в любом
    # зоомагазине не просто так.
    "pets-supplies": [
        {"slug": "pets-food", "name": {"ru": "Корм", "en": "Food", "sr": "Hrana"}},
        {"slug": "pets-carriers", "name": {"ru": "Переноски и клетки", "en": "Carriers & cages", "sr": "Nosiljke i kavezi"}},
        {"slug": "pets-accessories", "name": {"ru": "Аксессуары и игрушки", "en": "Accessories & toys", "sr": "Dodaci i igračke"}},
    ],
}
