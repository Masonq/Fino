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
    # Ключи здесь уникальны, и это важно: раньше один и тот же
    # родитель встречался дважды (services, auto, kids и ещё четыре),
    # а словарь оставляет только последнее значение — новые разделы
    # молча затирались старыми и до базы не доходили. Отсюда и
    # «родительского раздела construction нет»: он был в затёртом
    # блоке.
    # Марок здесь больше нет: телефон ищут по названию модели в поиске,
    # а не листая полки «iPhone» и «Samsung» — на полке всё равно
    # оказывается вперемешку и то и другое. Осталось только то, что
    # телефоном не является.
    "phones": [
        ("phones-parts", "Запчасти и ремонт", "Parts and repair", "Delovi i popravka", []),
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
    # Ремёсла жили под отдельным «Строительство и ремонт» — двойником
    # «Ремонта и строительства». Раздел слит, а «Электрик» и «Сантехник»
    # убраны: под той же крышей уже есть «Электрика» и «Сантехника».
    "repair": [
        ("con-tiler", "Плиточник", "Tiling", "Keramičar", []),
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
    "real-estate": [
        ("land", "Участки и земля", "Land and plots", "Placevi i zemljište", []),
        ("daily-rent", "Посуточная аренда", "Short-term rentals", "Izdavanje na dan", []),
    ],
    "auto": [
        ("trailers", "Прицепы и дома на колёсах", "Trailers and campers", "Prikolice i kamperi", []),
        ("water", "Лодки и катера", "Boats", "Čamci i plovila", []),
        ("agri", "Сельхозтехника", "Farm machinery", "Poljoprivredne mašine", []),
        ("e-transport", "Самокаты и электротранспорт", "Scooters and e-transport", "Trotineti i e-prevoz", []),
        ("car-rental", "Аренда авто", "Car rental", "Rent a car", []),
    ],
    "electronics": [
        ("components", "Комплектующие", "PC components", "Komponente", [('gpu', 'Видеокарты', 'Graphics cards', 'Grafičke karte'), ('cpu', 'Процессоры', 'Processors', 'Procesori'), ('ram', 'Оперативная память', 'Memory (RAM)', 'Memorija (RAM)'), ('motherboards', 'Материнские платы', 'Motherboards', 'Matične ploče'), ('storage-drives', 'Накопители SSD и HDD', 'SSD and HDD drives', 'SSD i HDD diskovi'), ('psu-cooling', 'Питание и охлаждение', 'Power and cooling', 'Napajanje i hlađenje'), ('pc-cases', 'Корпуса', 'PC cases', 'Kućišta')]),
        ("smart-home", "Умный дом", "Smart home", "Pametna kuća", []),
        ("monitors", "Мониторы", "Monitors", "Monitori", []),
        ("network-gear", "Сетевое оборудование", "Networking", "Mrežna oprema", []),
        ("tv-projectors", "Телевизоры и проекторы", "TVs and projectors", "Televizori i projektori", []),
    ],
    "home-garden": [
        ("building", "Стройматериалы", "Building materials", "Građevinski materijal", []),
        ("plumbing", "Сантехника и отопление", "Plumbing and heating", "Vodovod i grejanje", []),
        ("textile", "Текстиль для дома", "Home textile", "Tekstil za kuću", []),
        ("food", "Продукты и домашнее", "Food and homemade", "Hrana i domaći proizvodi", []),
        ("household-goods", "Бытовая химия и уборка", "Household supplies", "Sredstva za domaćinstvo", []),
        ("lighting", "Освещение", "Lighting", "Rasveta", []),
        ("storage-home", "Хранение и организация", "Storage and organisation", "Odlaganje i organizacija", []),
    ],
    "fashion": [
        ("jewelry", "Украшения", "Jewellery", "Nakit", []),
        ("hats-scarves", "Шапки и шарфы", "Hats and scarves", "Kape i šalovi", []),
        ("gloves", "Перчатки и варежки", "Gloves", "Rukavice", []),
        ("belts", "Ремни", "Belts", "Kaiševi", []),
        ("glasses", "Очки", "Glasses", "Naočare", []),
        ("umbrellas", "Зонты", "Umbrellas", "Kišobrani", []),
    ],
    "kids": [
        ("car-seats", "Автокресла", "Car seats", "Auto-sedišta", []),
        ("kids-transport", "Детский транспорт", "Kids bikes and scooters", "Bicikli i trotineti za decu", []),
        ("kids-hygiene", "Детская гигиена и подгузники", "Nappies and baby care", "Pelene i nega bebe", []),
        ("kids-feeding", "Кормление и гигиена", "Feeding and care", "Ishrana i nega", []),
    ],
    "hobby-sport": [
        ("winter-sport", "Зимний спорт", "Winter sports", "Zimski sportovi", []),
        ("fishing-hunting", "Рыбалка и охота", "Fishing and hunting", "Pecanje i lov", []),
        ("board-games", "Настольные игры", "Board games", "Društvene igre", []),
        ("tickets", "Билеты и сертификаты", "Tickets and vouchers", "Karte i vaučeri", []),
        ("skate-roller", "Скейтборды и ролики", "Skateboards and rollerblades", "Skejtbordi i rolere", []),
        ("crafts", "Рукоделие и творчество", "Crafts and hobbies", "Ručni rad i hobi", []),
        ("martial-arts", "Единоборства", "Martial arts", "Borilačke veštine", []),
        ("sport-nutrition", "Спортивное питание", "Sports nutrition", "Sportska ishrana", []),
    ],
    "pets": [
        ("pets-birds", "Птицы", "Birds", "Ptice", []),
        ("pets-farm", "Домашний скот и птица", "Farm animals", "Domaće životinje", []),
    ],
    "services": [
        ("childcare", "Няни и уход", "Childcare and care", "Čuvanje dece i nega", []),
        ("photo-video", "Фото и видео", "Photo and video", "Foto i video", []),
        ("events", "Праздники и мероприятия", "Events", "Proslave i događaji", []),
        ("docs-visa", "Документы и визы", "Documents and visas", "Dokumenti i vize", []),
        ("medical", "Здоровье и медицина", "Health and medical", "Zdravlje i medicina", []),
        ("auto-services", "Автосервис и шиномонтаж", "Car service and tyres", "Auto servis i vulkanizer", []),
        ("lost-found", "Находки и пропажи", "Lost and found", "Izgubljeno i nađeno", []),
        ("translation", "Переводы", "Translation", "Prevodi", []),
        ("pet-services", "Уход за животными", "Pet services", "Usluge za ljubimce", []),
    ],
    "business": [
        ("agriculture", "Сельское хозяйство", "Agriculture", "Poljoprivreda", []),
        ("rental-equipment", "Аренда оборудования", "Equipment rental", "Iznajmljivanje opreme", []),
    ],
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
        ("kitchen-small", "Кухонная техника", "Kitchen appliances", "Kuhinjski aparati", [('multicookers', 'Мультиварки и пароварки', 'Multicookers and steamers', 'Multikukeri i parni lonci'), ('blenders-mixers', 'Блендеры и миксеры', 'Blenders and mixers', 'Blenderi i mikseri'), ('coffee-kettles', 'Кофеварки и чайники', 'Coffee makers and kettles', 'Aparati za kafu i bokali'), ('microwaves', 'Микроволновки', 'Microwaves', 'Mikrotalasne')]),
        ("irons-steamers", "Утюги и отпариватели", "Irons and steamers", "Pegle i paročistači", []),
    ],
    "pets-supplies": [
        ("aquariums", "Аквариумы и террариумы", "Aquariums and terrariums", "Akvarijumi i terarijumi", []),
        ("pet-grooming", "Уход и груминг", "Grooming supplies", "Nega i timarenje", []),
    ],
    "beauty": [
        ("medical-supplies", "Медтовары и расходники", "Medical supplies", "Medicinski materijal", []),
    ],
}


def _make(db, slug, ru, en, sr, parent, order):
    return Category(slug=slug, name={"ru": ru, "en": en, "sr": sr},
                    parent_id=parent.id if parent else None, sort_order=order,
                    attribute_schema=[])


def _add_children(db, parent_slug, parent, children, known, apply) -> int:
    """Заводит детей одного родителя. Возвращает, сколько добавлено."""
    added = 0
    base = max([c.sort_order for c in db.query(Category)
                .filter(Category.parent_id == parent.id).all()] or [0])

    for i, (slug, ru, en, sr, deep) in enumerate(children, start=1):
        node = known.get(slug)
        if node is None:
            print(f"  + {parent_slug} → {ru}")
            added += 1
            node = _make(db, slug, ru, en, sr, parent, base + i)
            if apply:
                db.add(node)
                db.flush()
                known[slug] = node
            else:
                # Без записи в базу глубже не спускаемся: родителя для
                # внуков ещё не существует, и показывать их как
                # добавленные было бы неправдой.
                continue

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

    return added


def run(apply: bool) -> None:
    with SessionLocal() as db:
        known = {c.slug: c for c in db.query(Category).all()}
        added = 0

        # Два прохода. Раздел, чей родитель заводится в этом же
        # запуске, на первом проходе его не находит — второй забирает
        # такие. Так и вышло с мастерами внутри «Строительства и
        # ремонта»: сам раздел появился, а плиточник с электриком — нет.
        for _ in range(2):
            for parent_slug, children in NEW.items():
                parent = known.get(parent_slug)
                if parent is None:
                    continue
                added += _add_children(db, parent_slug, parent, children, known, apply)

        # Кто и после двух проходов без родителя — это уже не очередь, а
        # ошибка в списке, и о ней нужно сказать.
        for parent_slug in NEW:
            if parent_slug not in known:
                print(f"  ! родительского раздела «{parent_slug}» нет — пропускаю")

        if apply:
            db.commit()
            print(f"\nдобавлено разделов: {added}")
        else:
            print(f"\nбудет добавлено: {added}. Для добавления — с ключом --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
