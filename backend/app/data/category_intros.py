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


def intro(slug: str, lang: str = "ru") -> str | None:
    """Текст раздела на нужном языке; None — если текста ещё нет."""
    texts = INTROS.get(slug)
    if not texts:
        return None
    return texts.get(lang) or texts.get("ru")
