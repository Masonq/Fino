"""
Тексты для страниц разделов.

У страницы раздела не было ни одного своего слова: только плитки
подразделов и список объявлений. Поисковику нечего показать в выдаче, а
человеку — понять, чем этот раздел отличается от соседнего.

Пишем так, как люди спрашивают вслух: «снять квартиру в Белграде»,
«купить коляску», «отдам даром». Это же и есть те слова, которые они
набирают в поиске, — подгонять текст под поисковик отдельно не нужно,
достаточно писать по-человечески.

Три языка: русский для диаспоры, сербский для местных, английский для
приезжих. Не перевод слово в слово — на каждом языке спрашивают
по-своему: серб ищет «izdavanje stana», а не «аренду квартиры».

Коротко, два-три предложения. Длинные тексты внизу раздела никто не
читает, а поисковику довольно и этого.
"""

INTROS: dict[str, dict[str, str]] = {
    "real-estate": {
        "ru": "Квартиры, дома и комнаты в Белграде, Нови-Саде и других городах "
              "Сербии — снять на месяц или купить. Объявления от собственников "
              "и агентств, с ценой в евро и динарах, без посредников между вами "
              "и продавцом.",
        "en": "Flats, houses and rooms in Belgrade, Novi Sad and across Serbia — "
              "long-term rentals and sales. Listings from owners and agencies, "
              "prices in euros and dinars.",
        "sr": "Stanovi, kuće i sobe u Beogradu, Novom Sadu i širom Srbije — "
              "izdavanje i prodaja. Oglasi od vlasnika i agencija, cene u evrima "
              "i dinarima.",
    },
    "auto": {
        "ru": "Подержанные автомобили, мотоциклы и запчасти в Сербии. Смотрите "
              "год, пробег и цену прямо в списке, пишите продавцу напрямую — "
              "и договаривайтесь о просмотре без комиссий.",
        "en": "Used cars, motorcycles and spare parts in Serbia. Year, mileage "
              "and price right in the list; message the seller directly and "
              "arrange a viewing.",
        "sr": "Polovni automobili, motocikli i auto-delovi u Srbiji. Godište, "
              "kilometraža i cena odmah u listi; pišite prodavcu direktno.",
    },
    "electronics": {
        "ru": "Телефоны, ноутбуки, комплектующие для компьютера и техника для "
              "дома — новое и с рук. Проверяйте состояние на фото, спрашивайте "
              "о гарантии в переписке и встречайтесь в удобном месте.",
        "en": "Phones, laptops, PC components and home electronics — new and "
              "used. Check the condition in photos, ask about warranty in chat "
              "and meet where it suits you.",
        "sr": "Telefoni, laptopovi, računarske komponente i kućna elektronika — "
              "novo i polovno. Proverite stanje na slikama i pitajte za "
              "garanciju u poruci.",
    },
    "kids": {
        "ru": "Детская одежда, коляски, автокресла, игрушки и детский транспорт. "
              "Дети вырастают из вещей быстрее, чем те успевают износиться, — "
              "здесь их отдают и продают недорого, а часто и даром.",
        "en": "Kids' clothes, prams, car seats, toys and ride-ons. Children "
              "outgrow things faster than they wear out — here they are sold "
              "cheaply or given away for free.",
        "sr": "Dečja odeća, kolica, auto-sedišta, igračke i dečji prevoz. Deca "
              "prerastu stvari brže nego što se pohabaju — ovde se prodaju "
              "jeftino ili poklanjaju.",
    },
    "fashion": {
        "ru": "Одежда и обувь для женщин, мужчин и детей — от повседневных вещей "
              "до брендовых. Указывайте размер и состояние, смотрите фото и "
              "договаривайтесь о примерке при встрече.",
        "en": "Clothes and shoes for women, men and kids — everyday items and "
              "brands. Sizes and condition in every listing; try things on when "
              "you meet.",
        "sr": "Odeća i obuća za žene, muškarce i decu — od svakodnevnih stvari do "
              "brendova. Veličina i stanje u svakom oglasu.",
    },
    "home-garden": {
        "ru": "Мебель, техника, посуда, инструменты и всё для дома и сада. "
              "Переезжаете или обновляете обстановку — здесь можно недорого "
              "обставить квартиру и так же легко отдать то, что больше не нужно.",
        "en": "Furniture, appliances, kitchenware, tools and everything for home "
              "and garden. Moving in or refreshing a room — furnish a flat "
              "cheaply and pass on what you no longer need.",
        "sr": "Nameštaj, aparati, posuđe, alat i sve za kuću i baštu. Selite se "
              "ili menjate enterijer — ovde jeftino opremite stan.",
    },
    "services": {
        "ru": "Мастера, няни, репетиторы, перевозки и уборка в Белграде и по "
              "Сербии. Частные специалисты и небольшие команды — с отзывами, "
              "ценами и возможностью написать напрямую.",
        "en": "Handymen, nannies, tutors, movers and cleaners in Belgrade and "
              "across Serbia. Independent professionals and small teams, with "
              "reviews and direct messaging.",
        "sr": "Majstori, dadilje, privatni časovi, selidbe i čišćenje u Beogradu "
              "i Srbiji. Nezavisni profesionalci sa ocenama i direktnom porukom.",
    },
    "pets": {
        "ru": "Кошки, собаки и другие животные — в добрые руки и от заводчиков, "
              "а также корма, переноски и всё для ухода. Пишите хозяину напрямую "
              "и договаривайтесь о встрече.",
        "en": "Cats, dogs and other pets — from shelters, private homes and "
              "breeders — plus food, carriers and grooming supplies.",
        "sr": "Mačke, psi i druge životinje — udomljavanje i odgajivači — kao i "
              "hrana, transporteri i oprema za negu.",
    },
    "hobby-sport": {
        "ru": "Велосипеды, самокаты, скейты, тренажёры, музыкальные инструменты и "
              "снаряжение для походов. Спорт и увлечения, на которые жалко "
              "тратить полную цену в магазине.",
        "en": "Bikes, scooters, skateboards, gym gear, musical instruments and "
              "camping equipment — sports and hobbies without paying full retail.",
        "sr": "Bicikli, trotineti, skejtbordi, sprave za vežbanje, instrumenti i "
              "oprema za kampovanje.",
    },
    "jobs": {
        "ru": "Работа и подработка в Белграде и других городах Сербии: вакансии "
              "от работодателей и резюме тех, кто ищет. Русскоязычные и "
              "местные предложения в одном месте.",
        "en": "Jobs and side work in Belgrade and across Serbia — vacancies from "
              "employers and CVs from people looking. Local and "
              "Russian-speaking offers in one place.",
        "sr": "Poslovi i honorarni rad u Beogradu i Srbiji — oglasi poslodavaca i "
              "biografije onih koji traže posao.",
    },
    "beauty": {
        "ru": "Косметика, парфюмерия, украшения и личные вещи. Новое и почти "
              "новое — то, что не подошло по оттенку или досталось в подарок и "
              "осталось нераспечатанным.",
        "en": "Cosmetics, perfume, jewellery and personal items — new and barely "
              "used, often unopened gifts that didn't suit.",
        "sr": "Kozmetika, parfemi, nakit i lične stvari — novo i skoro novo.",
    },
    "business": {
        "ru": "Оборудование для кафе, магазинов и мастерских, торговая мебель и "
              "готовый бизнес. Для тех, кто открывается или, наоборот, "
              "распродаёт после закрытия.",
        "en": "Equipment for cafés, shops and workshops, retail furniture and "
              "businesses for sale — for those opening up or closing down.",
        "sr": "Oprema za kafiće, radnje i radionice, prodajni nameštaj i biznis "
              "na prodaju.",
    },
    "appliances-major": {
        "ru": "Холодильники, стиральные машины, плиты и посудомоечные — с рук и "
              "из магазинов. При переезде технику часто продают за половину "
              "цены просто потому, что её некуда везти.",
        "en": "Fridges, washing machines, cookers and dishwashers — used and new. "
              "People moving out often sell them at half price simply because "
              "they can't take them along.",
        "sr": "Frižideri, veš mašine, šporeti i mašine za sudove — polovno i novo.",
    },
    "appliances-small": {
        "ru": "Пылесосы, мультиварки, блендеры, кофеварки и другая мелкая "
              "техника для кухни и дома — новая и бывшая в употреблении.",
        "en": "Vacuum cleaners, multicookers, blenders, coffee makers and other "
              "small appliances for kitchen and home.",
        "sr": "Usisivači, multikukeri, blenderi, aparati za kafu i drugi mali "
              "kućni aparati.",
    },
}


# Подразделы, которые ищут чаще всего.
#
# У остальных текста нет — они берут родительский (см. intro ниже).
# Писать своё каждому из девяноста подразделов работа не на один день, а
# наследование закрывает их сразу и не оставляет пустых страниц.
#
# Здесь те, где запрос конкретнее: человек ищет не «недвижимость», а
# «однушку на Врачаре», и слова у него другие.
INTROS.update({
    "flats": {
        "ru": "Квартиры в аренду и на продажу в Белграде, Нови-Саде и других "
              "городах Сербии — от студий до многокомнатных. Указан этаж, "
              "площадь и что входит в цену; договаривайтесь о просмотре прямо в "
              "переписке.",
        "en": "Flats to rent and buy in Belgrade, Novi Sad and across Serbia — "
              "from studios to family-sized. Floor, area and what's included in "
              "the price; arrange a viewing in chat.",
        "sr": "Stanovi za izdavanje i prodaju u Beogradu, Novom Sadu i širom "
              "Srbije — od garsonjera do porodičnih. Sprat, kvadratura i šta "
              "ulazi u cenu.",
    },
    "rooms": {
        "ru": "Комнаты и места в общей квартире — вариант для студентов и тех, "
              "кто только приехал. Дешевле отдельного жилья, а соседей и район "
              "можно расспросить заранее в переписке.",
        "en": "Rooms and shared flats — the option for students and newcomers. "
              "Cheaper than renting alone; ask about flatmates and the "
              "neighbourhood before you come.",
        "sr": "Sobe i cimeri — opcija za studente i one koji su tek stigli. "
              "Jeftinije od zasebnog stana; raspitajte se o cimerima unapred.",
    },
    "houses": {
        "ru": "Дома и участки в пригородах Белграда и по Сербии — с садом, "
              "гаражом или под строительство. Указана площадь дома и земли, "
              "рядом фотографии участка.",
        "en": "Houses and land near Belgrade and across Serbia — with a garden, "
              "garage or a plot to build on. House and land area with photos.",
        "sr": "Kuće i placevi u okolini Beograda i širom Srbije — sa baštom, "
              "garažom ili za gradnju.",
    },
    "cars": {
        "ru": "Легковые автомобили с пробегом и новые — в Белграде и по всей "
              "Сербии. Марка, год, пробег и коробка видны сразу в списке, а "
              "документы и историю можно обсудить с владельцем напрямую.",
        "en": "Used and new cars in Belgrade and across Serbia. Make, year, "
              "mileage and gearbox right in the list; discuss papers and history "
              "with the owner directly.",
        "sr": "Polovni i novi automobili u Beogradu i širom Srbije. Marka, "
              "godište, kilometraža i menjač odmah u listi.",
    },
    "phones": {
        "ru": "Телефоны и смартфоны с рук — iPhone, Samsung, Xiaomi и другие. "
              "Смотрите состояние на фото, спрашивайте о ёмкости батареи и "
              "проверяйте аппарат при встрече.",
        "en": "Used phones and smartphones — iPhone, Samsung, Xiaomi and others. "
              "Check the photos, ask about battery health and test the device "
              "when you meet.",
        "sr": "Polovni telefoni i pametni telefoni — iPhone, Samsung, Xiaomi i "
              "drugi. Proverite stanje baterije i uređaj uživo.",
    },
    "laptops": {
        "ru": "Ноутбуки и ультрабуки — рабочие, игровые и для учёбы. Процессор, "
              "память и состояние экрана указаны в объявлении; включить и "
              "проверить можно при встрече.",
        "en": "Laptops and ultrabooks — for work, gaming and study. Processor, "
              "memory and screen condition in the listing; test it when you meet.",
        "sr": "Laptopovi i ultrabukovi — za posao, igre i studiranje. Procesor, "
              "memorija i stanje ekrana u oglasu.",
    },
    "strollers": {
        "ru": "Коляски и автокресла — прогулочные, люльки, трости и «два в "
              "одном». Дети вырастают за сезон, поэтому коляски здесь часто "
              "почти новые и заметно дешевле магазина.",
        "en": "Prams and car seats — buggies, carrycots and 2-in-1 systems. Kids "
              "outgrow them in a season, so most are nearly new and much cheaper "
              "than in shops.",
        "sr": "Kolica i auto-sedišta — sportska, nosiljke i „dva u jedan“. Deca "
              "ih prerastu za sezonu, pa su često skoro nova.",
    },
    "toys": {
        "ru": "Игрушки, настольные игры и конструкторы для любого возраста. "
              "Многое отдают даром: ребёнок наигрался за месяц, а вещь как новая.",
        "en": "Toys, board games and building sets for all ages. Much of it is "
              "given away free — a month of play and it's as good as new.",
        "sr": "Igračke, društvene igre i kocke za sve uzraste. Mnogo toga se "
              "poklanja — dete se naigra za mesec dana.",
    },
    "furniture": {
        "ru": "Диваны, шкафы, столы и стулья — новые и с рук, в том числе из "
              "IKEA и JYSK. При переезде мебель отдают за половину цены просто "
              "потому, что её некуда везти.",
        "en": "Sofas, wardrobes, tables and chairs — new and used, including IKEA "
              "and JYSK. People moving out sell at half price simply because they "
              "can't take it along.",
        "sr": "Sofe, ormari, stolovi i stolice — novo i polovno, uključujući IKEA "
              "i JYSK. Pri selidbi se prodaje upola jeftinije.",
    },
    "repair": {
        "ru": "Ремонт квартир и мелкие работы по дому: сантехника, электрика, "
              "сборка мебели, покраска. Частные мастера с ценами за работу и "
              "отзывами тех, кто уже вызывал.",
        "en": "Flat renovation and small home jobs: plumbing, electrics, "
              "furniture assembly, painting. Independent handymen with prices and "
              "reviews.",
        "sr": "Renoviranje stanova i sitni radovi: vodoinstalater, električar, "
              "montaža nameštaja, krečenje.",
    },
    "nannies": {
        "ru": "Няни и помощь с детьми в Белграде: на час, на полдня или "
              "постоянно. Русскоязычные и сербские няни, с опытом и отзывами "
              "родителей.",
        "en": "Nannies and childcare in Belgrade — by the hour, half-day or "
              "full-time. Russian- and Serbian-speaking, with experience and "
              "parent reviews.",
        "sr": "Dadilje i čuvanje dece u Beogradu — na sat, pola dana ili stalno.",
    },
    "kids-bikes": {
        "ru": "Детские велосипеды, беговелы и самокаты — по росту и возрасту. "
              "Ребёнок пересаживается на следующий размер за год, поэтому "
              "покупать новый каждый раз незачем.",
        "en": "Kids' bikes, balance bikes and scooters by age and height. "
              "Children move up a size every year — no need to buy new each time.",
        "sr": "Dečji bicikli, bicikli bez pedala i trotineti po uzrastu i visini.",
    },
})


def intro(slug: str, lang: str = "ru", parent_slug: str | None = None) -> str | None:
    """
    Текст раздела на нужном языке.

    Если у подраздела своего текста нет, берём родительский: «Квартиры»
    без текста лучше покажут описание «Недвижимости», чем пустую
    страницу. Подразделов почти сотня, и написать каждому своё — работа
    не на один день; наследование закрывает их все сразу, а свои тексты
    добавляются по мере надобности.
    """
    texts = INTROS.get(slug)
    if not texts and parent_slug:
        texts = INTROS.get(parent_slug)
    if not texts:
        return None
    return texts.get(lang) or texts.get("ru")
