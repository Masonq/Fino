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
        ("kids-transport", "Детский транспорт", "Kids' ride-ons", "Dečji prevoz", [
            ("kids-bikes", "Детские велосипеды", "Kids' bikes", "Dečji bicikli"),
            ("balance-bikes", "Беговелы", "Balance bikes", "Bicikli bez pedala"),
            ("kids-scooters", "Детские самокаты", "Kids' scooters", "Dečji trotineti"),
            ("ride-on-cars", "Электромобили и каталки", "Ride-on cars", "Auto-igračke na struju"),
        ]),
        ("kids-feeding", "Кормление и гигиена", "Feeding and care", "Ishrana i nega", []),
    ],
    "hobby-sport": [
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
    "home-garden": [
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
