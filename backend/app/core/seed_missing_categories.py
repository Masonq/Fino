"""
Добавляет разделы, которых в дереве не хватало.

Собрано по живой ленте: раскладывая объявления руками, некуда было
деть плашки памяти и видеокарты (лежали в «Настольных компьютерах»),
детские велосипеды (в «Игрушки» их не отнесёшь — это не игрушка),
городской скейт (в «Хобби» такого раздела просто нет). Плюс два
корневых раздела, «Крупная техника» и «Мелкая техника», стояли вовсе
без подразделов — объявления валились в них общей кучей.

Скрипт можно запускать сколько угодно раз: существующие разделы он не
трогает, добавляет только отсутствующие.

Запуск:
    python3 -m app.core.seed_missing_categories            # показать
    python3 -m app.core.seed_missing_categories --apply    # добавить
"""
import argparse

from app.core.database import SessionLocal
from app.models import Category

# Что добавляем: родительский slug → список новых разделов.
#
# Названия сразу на трёх языках: раздел без перевода показывается
# служебным именем, и мы это уже проходили.
NEW = {
    # Третий уровень у крупных разделов.
    #
    # «Бытовая техника» вмещает холодильник, стиралку и микроволновку —
    # по такому разделу не ищут, его листают. Дальше дробим там, где
    # объявлений много и они разные по смыслу: телефоны по маркам,
    # мебель по предметам, услуги мастеров по ремеслу.
    "phones": [
        ("phones-iphone", "iPhone", "iPhone", "iPhone", []),
        ("phones-samsung", "Samsung", "Samsung", "Samsung", []),
        ("phones-xiaomi", "Xiaomi и прочие", "Xiaomi and others", "Xiaomi i ostali", []),
        ("phones-parts", "Запчасти и ремонт", "Parts and repair", "Delovi i popravka", []),
    ],
    "appliances": [
        ("app-fridge", "Холодильники и морозильники", "Fridges", "Frižideri", []),
        ("app-washer", "Стиральные и сушильные", "Washers and dryers", "Veš mašine i sušare", []),
        ("app-stove", "Плиты и духовки", "Stoves and ovens", "Šporeti i rerne", []),
        ("app-dishwasher", "Посудомоечные", "Dishwashers", "Mašine za sudove", []),
        ("app-small", "Мелкая техника", "Small appliances", "Mali aparati", []),
        ("app-climate", "Климат: кондиционеры и обогреватели", "Climate", "Klime i grejalice", []),
    ],
    "furniture": [
        ("furn-sofa", "Диваны и кресла", "Sofas and armchairs", "Sofe i fotelje", []),
        ("furn-bed", "Кровати и матрасы", "Beds and mattresses", "Kreveti i dušeci", []),
        ("furn-wardrobe", "Шкафы и комоды", "Wardrobes and dressers", "Ormari i komode", []),
        ("furn-table", "Столы и стулья", "Tables and chairs", "Stolovi i stolice", []),
        ("furn-kitchen", "Кухни", "Kitchen units", "Kuhinje", []),
        ("furn-office", "Для офиса", "Office furniture", "Kancelarijski nameštaj", []),
    ],
    "tools": [
        ("tools-power", "Электроинструмент", "Power tools", "Električni alat", []),
        ("tools-hand", "Ручной инструмент", "Hand tools", "Ručni alat", []),
        ("tools-measure", "Измерительный", "Measuring tools", "Merni alat", []),
        ("tools-welding", "Сварка и компрессоры", "Welding and compressors", "Varenje i kompresori", []),
    ],
    "garden": [
        ("garden-plants", "Растения и саженцы", "Plants and seedlings", "Biljke i sadnice", []),
        ("garden-mower", "Газонокосилки и триммеры", "Mowers and trimmers", "Kosačice i trimeri", []),
        ("garden-bbq", "Мангалы и барбекю", "BBQ and grills", "Roštilji", []),
        ("garden-pool", "Бассейны и спа", "Pools and spa", "Bazeni i spa", []),
        ("garden-furniture", "Садовая мебель", "Garden furniture", "Baštenski nameštaj", []),
    ],
    "toys": [
        ("toys-construct", "Конструкторы", "Building sets", "Kocke i setovi", []),
        ("toys-dolls", "Куклы и фигурки", "Dolls and figures", "Lutke i figure", []),
        ("toys-outdoor", "Для улицы и песочницы", "Outdoor toys", "Igračke za napolje", []),
        ("toys-baby", "Для малышей", "Baby toys", "Igračke za bebe", []),
    ],
    "bikes": [
        ("bikes-mtb", "Горные", "Mountain bikes", "Brdski bicikli", []),
        ("bikes-city", "Городские и шоссейные", "City and road bikes", "Gradski i drumski", []),
        ("bikes-kids", "Детские", "Kids bikes", "Dečiji bicikli", []),
        ("bikes-electric", "Электровелосипеды", "E-bikes", "Električni bicikli", []),
        ("bikes-parts", "Запчасти и аксессуары", "Parts and accessories", "Delovi i oprema", []),
    ],
    "construction": [
        ("con-tiler", "Плиточник", "Tiling", "Keramičar", []),
        ("con-electric", "Электрик", "Electrician", "Električar", []),
        ("con-plumber", "Сантехник", "Plumber", "Vodoinstalater", []),
        ("con-painter", "Маляр и штукатур", "Painter and plasterer", "Moler i fasader", []),
        ("con-carpenter", "Столяр и мебельщик", "Carpenter", "Stolar", []),
        ("con-full", "Ремонт под ключ", "Full renovation", "Renoviranje ključ u ruke", []),
    ],
    "flats": [
        ("flats-sale", "Продажа квартир", "Flats for sale", "Prodaja stanova", []),
        ("flats-rent", "Аренда квартир", "Flats for rent", "Izdavanje stanova", []),
        ("flats-studio", "Гарсоньеры и студии", "Studios", "Garsonjere", []),
    ],
    "kids-clothing": [
        ("kids-cl-baby", "Для малышей до 2 лет", "Baby clothes", "Odeća za bebe", []),
        ("kids-cl-boys", "Для мальчиков", "Boys", "Za dečake", []),
        ("kids-cl-girls", "Для девочек", "Girls", "Za devojčice", []),
        ("kids-cl-shoes", "Детская обувь", "Kids shoes", "Dečija obuća", []),
    ],
    "cars": [
        ("cars-sale", "Легковые с пробегом", "Used cars", "Polovni automobili", []),
        ("cars-new", "Новые", "New cars", "Novi automobili", []),
        ("cars-damaged", "После аварии и на запчасти", "Damaged cars", "Havarisana vozila", []),
    ],
    "vacancies": [
        ("vac-service", "Кафе, рестораны, магазины", "Service and retail", "Ugostiteljstvo i trgovina", []),
        ("vac-build", "Стройка и производство", "Construction and industry", "Građevina i proizvodnja", []),
        ("vac-it", "IT и офис", "IT and office", "IT i kancelarija", []),
        ("vac-drivers", "Водители и логистика", "Drivers and logistics", "Vozači i logistika", []),
        ("vac-home", "Уборка, уход, няни", "Cleaning and care", "Čišćenje i nega", []),
    ],
    # Разделы, которых не хватало по сравнению с сербскими площадками.
    #
    # Собрано по KupujemProdajem и OLX.ba — тому, чем здесь и правда
    # торгуют. Часть из этого для Сербии обязательна: участки и
    # посуточная аренда (сплавы, Златибор, Копаоник), сельхозтехника и
    # домашний скот, стройматериалы, зимний спорт, рыбалка.
    #
    # Услуги расширены сильнее всего: у нас было семь видов, а люди
    # ищут мастеров, нянь, фотографов, помощь с документами и визами —
    # без этих разделов объявления оседали в «Разном».
    "real-estate": [
        ("land", "Участки и земля", "Land and plots", "Placevi i zemljište", []),
        ("daily-rent", "Посуточно и на отдых", "Daily and holiday rent", "Dnevni najam i vikendice", []),
    ],
    "auto": [
        ("trailers", "Прицепы и дома на колёсах", "Trailers and campers", "Prikolice i kamperi", []),
        ("water", "Лодки и катера", "Boats", "Čamci i plovila", []),
        ("agri", "Сельхозтехника", "Farm machinery", "Poljoprivredne mašine", []),
        ("e-transport", "Самокаты и электротранспорт", "Scooters and e-transport", "Trotineti i e-prevoz", []),
        ("car-rental", "Аренда авто", "Car rental", "Rent a car", []),
    ],
    "electronics": [
        ("components", "Комплектующие", "PC components", "Komponente", []),
        ("smart-home", "Умный дом", "Smart home", "Pametna kuća", []),
    ],
    "home-garden": [
        ("building", "Стройматериалы", "Building materials", "Građevinski materijal", []),
        ("plumbing", "Сантехника и отопление", "Plumbing and heating", "Vodovod i grejanje", []),
        ("textile", "Текстиль для дома", "Home textile", "Tekstil za kuću", []),
        ("food", "Продукты и домашнее", "Food and homemade", "Hrana i domaći proizvodi", []),
    ],
    "fashion": [
        ("jewelry", "Украшения", "Jewellery", "Nakit", []),
    ],
    "kids": [
        ("car-seats", "Автокресла", "Car seats", "Auto-sedišta", []),
        ("kids-transport", "Детский транспорт", "Kids bikes and scooters", "Bicikli i trotineti za decu", []),
    ],
    "hobby-sport": [
        ("winter-sport", "Зимний спорт", "Winter sports", "Zimski sportovi", []),
        ("fishing-hunting", "Рыбалка и охота", "Fishing and hunting", "Pecanje i lov", []),
        ("board-games", "Настольные игры", "Board games", "Društvene igre", []),
        ("tickets", "Билеты и сертификаты", "Tickets and vouchers", "Karte i vaučeri", []),
    ],
    "pets": [
        ("pets-birds", "Птицы", "Birds", "Ptice", []),
        ("pets-farm", "Домашний скот и птица", "Farm animals", "Domaće životinje", []),
    ],
    "services": [
        ("construction", "Строительство и ремонт", "Construction and renovation", "Građevina i renoviranje", []),
        ("childcare", "Няни и уход", "Childcare and care", "Čuvanje dece i nega", []),
        ("photo-video", "Фото и видео", "Photo and video", "Foto i video", []),
        ("events", "Праздники и мероприятия", "Events", "Proslave i događaji", []),
        ("docs-visa", "Документы и визы", "Documents and visas", "Dokumenti i vize", []),
        ("medical", "Здоровье и медицина", "Health and medical", "Zdravlje i medicina", []),
        ("auto-services", "Автосервис и шиномонтаж", "Car service and tyres", "Auto servis i vulkanizer", []),
        ("lost-found", "Находки и пропажи", "Lost and found", "Izgubljeno i nađeno", []),
    ],
    "business": [
        ("agriculture", "Сельское хозяйство", "Agriculture", "Poljoprivreda", []),
        ("rental-equipment", "Аренда оборудования", "Equipment rental", "Iznajmljivanje opreme", []),
    ],
    # Одежда: внутри «Женского» и «Мужского» не было ничего, и пятьсот
    # объявлений висели в родительском разделе — искать в них
    # невозможно.
    #
    # Набор собран по тому, что реально лежит в базе: платья, футболки,
    # куртки, джинсы, худи, костюмы. Свитеры и куртки держим порознь —
    # это разные сезоны, и вместе их искать неудобно.
    "women": [
        ("women-dresses", "Платья и сарафаны", "Dresses", "Haljine", []),
        ("women-skirts", "Юбки", "Skirts", "Suknje", []),
        ("women-tops", "Футболки, майки и топы", "T-shirts and tops", "Majice i topovi", []),
        ("women-shirts", "Рубашки и блузки", "Shirts and blouses", "Košulje i bluze", []),
        ("women-knitwear", "Свитеры, худи и кардиганы", "Sweaters and hoodies", "Džemperi i duksevi", []),
        ("women-outerwear", "Куртки, пальто и пуховики", "Jackets and coats", "Jakne i kaputi", []),
        ("women-pants", "Джинсы, брюки и шорты", "Jeans, trousers and shorts", "Farmerke, pantalone i šorc", []),
        ("women-suits", "Костюмы и комбинезоны", "Suits and jumpsuits", "Odela i kombinezoni", []),
        ("women-underwear", "Бельё и купальники", "Underwear and swimwear", "Donji veš i kupaći", []),
        ("women-sportswear", "Спортивная одежда", "Sportswear", "Sportska odeća", []),
        # Обувь внутри пола: женские босоножки и мужские ботинки в одной
        # куче искать неудобно. Общий раздел «Обувь» при этом остаётся —
        # туда идёт то, где пол не определить.
        ("women-shoes", "Женская обувь", "Women's shoes", "Ženska obuća", []),
    ],
    "men": [
        ("men-tops", "Футболки и поло", "T-shirts and polos", "Majice i polo majice", []),
        ("men-shirts", "Рубашки", "Shirts", "Košulje", []),
        ("men-knitwear", "Свитеры, худи и толстовки", "Sweaters and hoodies", "Džemperi i duksevi", []),
        ("men-outerwear", "Куртки, пальто и пуховики", "Jackets and coats", "Jakne i kaputi", []),
        ("men-pants", "Джинсы, брюки и шорты", "Jeans, trousers and shorts", "Farmerke, pantalone i šorc", []),
        ("men-suits", "Костюмы и пиджаки", "Suits and blazers", "Odela i sakoi", []),
        ("men-underwear", "Бельё и носки", "Underwear and socks", "Donji veš i čarape", []),
        ("men-sportswear", "Спортивная одежда", "Sportswear", "Sportska odeća", []),
        ("men-shoes", "Мужская обувь", "Men's shoes", "Muška obuća", []),
    ],

    # Аксессуары: шапки, шарфы и очки шли отдельным потоком и оседали в
    # родительском разделе — своих полок для них не было.
    "fashion": [
        ("hats-scarves", "Шапки и шарфы", "Hats and scarves", "Kape i šalovi", []),
        ("gloves", "Перчатки и варежки", "Gloves", "Rukavice", []),
        ("belts", "Ремни", "Belts", "Kaiševi", []),
        ("glasses", "Очки", "Glasses", "Naočare", []),
        ("umbrellas", "Зонты", "Umbrellas", "Kišobrani", []),
    ],

    # Комплектующие: сейчас видеокарты и память лежат в «Настольных
    # компьютерах» вперемешку с целыми системными блоками.
    "electronics": [
        ("pc-parts", "Комплектующие для ПК", "PC components", "Komponente za računar", [
            ("gpu", "Видеокарты", "Graphics cards", "Grafičke karte"),
            ("cpu", "Процессоры", "Processors", "Procesori"),
            ("ram", "Оперативная память", "Memory (RAM)", "Memorija (RAM)"),
            ("motherboards", "Материнские платы", "Motherboards", "Matične ploče"),
            ("storage-drives", "Накопители SSD и HDD", "SSD and HDD drives", "SSD i HDD diskovi"),
            ("psu-cooling", "Питание и охлаждение", "Power and cooling", "Napajanje i hlađenje"),
            ("pc-cases", "Корпуса", "PC cases", "Kućišta"),
        ]),
        ("monitors", "Мониторы", "Monitors", "Monitori", []),
        ("network-gear", "Сетевое оборудование", "Networking", "Mrežna oprema", []),
        ("tv-projectors", "Телевизоры и проекторы", "TVs and projectors", "Televizori i projektori", []),
        ("smart-home", "Умный дом", "Smart home", "Pametna kuća", []),
    ],
    # Раздел стоял пустым: холодильник и стиральную машину класть было
    # некуда, кроме как в него самого.
    "appliances-major": [
        ("fridges", "Холодильники и морозильники", "Fridges and freezers", "Frižideri i zamrzivači", []),
        ("washing-machines", "Стиральные и сушильные машины", "Washers and dryers", "Veš mašine i sušilice", []),
        ("stoves-ovens", "Плиты и духовые шкафы", "Stoves and ovens", "Šporeti i rerne", []),
        ("dishwashers", "Посудомоечные машины", "Dishwashers", "Mašine za sudove", []),
        ("climate", "Кондиционеры и обогреватели", "Air conditioners and heaters", "Klime i grejalice", []),
        ("water-heaters", "Водонагреватели", "Water heaters", "Bojleri", []),
    ],
    "appliances-small": [
        ("vacuum-cleaners", "Пылесосы", "Vacuum cleaners", "Usisivači", []),
        ("kitchen-small", "Кухонная техника", "Kitchen appliances", "Kuhinjski aparati", [
            ("multicookers", "Мультиварки и пароварки", "Multicookers and steamers", "Multikukeri i parni lonci"),
            ("blenders-mixers", "Блендеры и миксеры", "Blenders and mixers", "Blenderi i mikseri"),
            ("coffee-kettles", "Кофеварки и чайники", "Coffee makers and kettles", "Aparati za kafu i bokali"),
            ("microwaves", "Микроволновки", "Microwaves", "Mikrotalasne"),
        ]),
        ("irons-steamers", "Утюги и отпариватели", "Irons and steamers", "Pegle i paročistači", []),
        ("personal-care-devices", "Техника для ухода", "Personal care devices", "Aparati za negu", []),
    ],
    # Детский транспорт — не игрушки: велосипед, самокат и беговел
    # покупают как транспорт и ищут отдельно.
    "kids": [
        ("kids-hygiene", "Детская гигиена и подгузники", "Nappies and baby care", "Pelene i nega bebe", []),
        ("kids-transport", "Детский транспорт", "Kids' ride-ons", "Dečji prevoz", [
            ("kids-bikes", "Детские велосипеды", "Kids' bikes", "Dečji bicikli"),
            ("balance-bikes", "Беговелы", "Balance bikes", "Bicikli bez pedala"),
            ("kids-scooters", "Детские самокаты", "Kids' scooters", "Dečji trotineti"),
            ("ride-on-cars", "Электромобили и каталки", "Ride-on cars", "Auto-igračke na struju"),
        ]),
        ("kids-feeding", "Кормление и гигиена", "Feeding and care", "Ishrana i nega", []),
    ],
    # Бюро находок: потерянные и найденные вещи. В диаспорных чатах это
    # постоянный жанр — «нашли ключи у Калемегдана», «потерял рюкзак в
    # 26-м автобусе», — а деваться таким объявлениям было некуда.
    "services": [
        ("lost-found", "Бюро находок", "Lost and found", "Izgubljeno i nađeno", []),
    ],
    "hobby-sport": [
        ("tickets", "Билеты и сертификаты", "Tickets and gift cards", "Karte i vaučeri", []),
        ("skate-roller", "Скейтборды и ролики", "Skateboards and rollerblades", "Skejtbordi i rolere", []),
        ("hunting-fishing", "Охота и рыбалка", "Hunting and fishing", "Lov i ribolov", []),
        ("board-games", "Настольные игры", "Board games", "Društvene igre", []),
        ("crafts", "Рукоделие и творчество", "Crafts and hobbies", "Ručni rad i hobi", []),
        ("martial-arts", "Единоборства", "Martial arts", "Borilačke veštine", []),
        ("sport-nutrition", "Спортивное питание", "Sports nutrition", "Sportska ishrana", []),
    ],
    # Услуги — самый бедный раздел: няня, фотограф и переводчик подать
    # объявление попросту не могли, кроме как «в общее».
    "services": [
        ("nannies", "Няни и уход за детьми", "Nannies and childcare", "Dadilje i čuvanje dece", []),
        ("photo-video", "Фото и видеосъёмка", "Photo and video", "Foto i video", []),
        ("translation", "Переводы", "Translation", "Prevodi", []),
        ("pet-services", "Уход за животными", "Pet services", "Usluge za ljubimce", []),
        ("events", "Праздники и мероприятия", "Events", "Proslave i događaji", []),
        ("car-service", "Автосервис и шиномонтаж", "Car service", "Auto-servis i vulkanizer", []),
    ],
    # Белград стоит на двух реках, и лодки тут продают всерьёз.
    "auto": [
        ("boats", "Водный транспорт", "Boats and watercraft", "Plovila", []),
    ],
    # У «Товаров для животных» не было ни одного подраздела.
    "pets-supplies": [
        # «Корм» в этом разделе уже есть — второй такой же завёл по
        # невнимательности, увидел на записи экрана: «Food» и «Pet food»
        # стояли рядом.
        ("aquariums", "Аквариумы и террариумы", "Aquariums and terrariums", "Akvarijumi i terarijumi", []),
        # «Переноски и клетки» в этом разделе уже есть — второй такой же
        # завёл по невнимательности, увидел на снимке: две плитки рядом,
        # с одинаковым смыслом и разными словами.
        ("pet-grooming", "Уход и груминг", "Grooming supplies", "Nega i timarenje", []),
    ],
    # Медицина и гигиена: перчатки, маски, тесты и бинты приезжают
    # пачками (их продают и отдают после болезни), а деть их было
    # некуда — уходили в «Расходники и упаковку» к бизнесу, где их
    # никто не ищет. «Здоровье и уход» рядом — но это витамины и
    # тонометры, а не расходники.
    "beauty": [
        ("medical-supplies", "Медтовары и расходники", "Medical supplies", "Medicinski materijal", []),
        ("personal-hygiene", "Личная гигиена", "Personal hygiene", "Lična higijena", []),
    ],
    # Еду в диаспорных чатах продают всерьёз: домашняя выпечка, мёд,
    # кофе, сыры из деревни. Раздела под это не было вовсе.
    "home-garden": [
        ("food", "Продукты и напитки", "Food and drinks", "Hrana i piće", []),
        ("household-goods", "Бытовая химия и уборка", "Household supplies", "Sredstva za domaćinstvo", []),
        ("lighting", "Освещение", "Lighting", "Rasveta", []),
        ("building-materials", "Стройматериалы", "Building materials", "Građevinski materijal", []),
        ("plumbing", "Сантехника", "Plumbing", "Vodovodna oprema", []),
        ("storage-home", "Хранение и организация", "Storage and organisation", "Odlaganje i organizacija", []),
    ],
}


def _make(db, slug, ru, en, sr, parent, order):
    return Category(slug=slug, name={"ru": ru, "en": en, "sr": sr},
                    parent_id=parent.id if parent else None, sort_order=order,
                    attribute_schema=[])


def run(apply: bool) -> None:
    with SessionLocal() as db:
        known = {c.slug: c for c in db.query(Category).all()}
        added = 0

        for parent_slug, children in NEW.items():
            parent = known.get(parent_slug)
            if not parent:
                print(f"  ! родительского раздела «{parent_slug}» нет — пропускаю")
                continue

            base = max([c.sort_order for c in db.query(Category)
                        .filter(Category.parent_id == parent.id).all()] or [0])

            for i, (slug, ru, en, sr, deep) in enumerate(children, start=1):
                if slug in known:
                    continue
                print(f"  + {parent_slug} → {ru}")
                added += 1
                node = _make(db, slug, ru, en, sr, parent, base + i)
                if apply:
                    db.add(node)
                    db.flush()
                    known[slug] = node

                for j, (dslug, dru, den, dsr) in enumerate(deep, start=1):
                    if dslug in known:
                        continue
                    print(f"      + {dru}")
                    added += 1
                    if apply:
                        child = _make(db, dslug, dru, den, dsr, node, j)
                        db.add(child)
                        db.flush()
                        known[dslug] = child

        if apply:
            db.commit()
            print(f"\nдобавлено разделов: {added}")
        else:
            print(f"\nбудет добавлено: {added}. Для добавления — с ключом --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
