"""
Тексты подразделов второго уровня — тем, у кого своего текста не было.

Раньше подраздел показывал текст родителя: «Гараж» и «Посуточно» — одно
и то же описание «Недвижимости». Для поисковика это девяносто одинаковых
абзацев на разных страницах, то есть ни одного своего.

Правила те же, что в category_intros.py: так, как люди спрашивают вслух,
на каждом языке своими словами, коротко. Порядок в кортеже: сербский,
русский, английский.
"""

MORE: dict[str, tuple[str, str, str]] = {
    # ── Недвижимость
    "commercial": (
        "Poslovni prostor, kancelarije, lokali i magacini za izdavanje i prodaju u Beogradu i Srbiji.",
        "Офисы, магазины, склады и помещения под бизнес — аренда и продажа в Белграде и по Сербии.",
        "Offices, shops, warehouses and commercial space to rent or buy in Belgrade and across Serbia."),
    "garages": (
        "Garaže, garažna i parking mesta za izdavanje i prodaju — u zgradi, dvorištu ili na otvorenom.",
        "Гаражи и парковочные места — аренда и продажа: в доме, во дворе или на открытой стоянке.",
        "Garages and parking spaces to rent or buy — in buildings, yards or open lots."),
    "daily-rent": (
        "Stanovi i sobe na dan i na nekoliko noći — za turiste, poslovna putovanja i goste iz drugih gradova.",
        "Квартиры и комнаты посуточно — для туристов, командировок и гостей из других городов.",
        "Flats and rooms by the night — for tourists, business trips and visiting family."),
    # ── Авто
    "moto": (
        "Polovni motocikli, skuteri i mopedi, kao i kacige i oprema za vožnju.",
        "Подержанные мотоциклы, скутеры и мопеды, а ещё шлемы и экипировка.",
        "Used motorcycles, scooters and mopeds, plus helmets and riding gear."),
    "trucks": (
        "Kamioni, kombiji, autobusi i građevinske mašine — prodaja polovnih vozila za posao.",
        "Грузовики, фургоны, автобусы и спецтехника — подержанный транспорт для работы.",
        "Trucks, vans, buses and construction machinery — used vehicles for work."),
    "car-parts": (
        "Delovi za automobile — novi i polovni, za sve marke: motor, karoserija, elektrika, enterijer.",
        "Запчасти для автомобилей — новые и б/у, для любых марок: двигатель, кузов, электрика, салон.",
        "Car parts, new and used, for all makes — engine, body, electrics and interior."),
    "tyres": (
        "Letnje i zimske gume, felne i kompleti točkova — polovne i nove, po dimenziji.",
        "Летние и зимние шины, диски и колёса в сборе — б/у и новые, по размеру.",
        "Summer and winter tyres, rims and wheel sets — used and new, by size."),
    "trailers": (
        "Prikolice, kamperi i kamp-kućice za putovanja i prevoz tereta.",
        "Прицепы, автодома и кемперы — для путешествий и перевозки грузов.",
        "Trailers, campers and motorhomes for travel and hauling."),
    "water": (
        "Čamci, gumenjaci, jet-ski i vanbrodski motori — za Dunav, Savu i jezera.",
        "Лодки, надувные лодки, гидроциклы и лодочные моторы — для Дуная, Савы и озёр.",
        "Boats, inflatables, jet skis and outboard motors — for the Danube, the Sava and lakes."),
    "e-transport": (
        "Električni trotineti, bicikli i monocikli — polovni i novi, sa punjačem i baterijom.",
        "Электросамокаты, электровелосипеды и моноколёса — б/у и новые, с зарядкой и батареей.",
        "Electric scooters, e-bikes and unicycles — used and new, with charger and battery."),
    "car-rental": (
        "Rent a car u Beogradu i Srbiji — automobili na dan, nedelju ili mesec, od agencija i vlasnika.",
        "Аренда автомобилей в Белграде и Сербии — на день, неделю или месяц, от прокатов и владельцев.",
        "Car rental in Belgrade and Serbia — by the day, week or month, from agencies and owners."),
    # ── Услуги
    "transport": (
        "Selidbe, prevoz nameštaja i stvari, kombi sa vozačem i dostava po Beogradu i Srbiji.",
        "Переезды, перевозка мебели и вещей, грузовое такси и доставка по Белграду и Сербии.",
        "Moving, furniture transport, van with driver and deliveries around Belgrade and Serbia."),
    "beauty-services": (
        "Frizeri, manikir, šminka, masaža i kozmetičari — u salonu ili sa dolaskom kući.",
        "Парикмахеры, маникюр, макияж, массаж и косметологи — в салоне или с выездом на дом.",
        "Hairdressers, nails, make-up, massage and beauticians — in a salon or at your home."),
    "tutoring": (
        "Privatni časovi i obuka: srpski i strani jezici, matematika, muzika, priprema za ispite.",
        "Репетиторы и курсы: сербский и иностранные языки, математика, музыка, подготовка к экзаменам.",
        "Tutors and lessons: Serbian and foreign languages, maths, music and exam prep."),
    "cleaning": (
        "Čišćenje stanova i kancelarija, generalno čišćenje posle radova, pomoć u kući.",
        "Уборка квартир и офисов, генеральная уборка после ремонта, помощь по дому.",
        "Cleaning for flats and offices, deep cleans after renovation and help at home."),
    "it-design": (
        "Izrada sajtova, programiranje, dizajn, popravka računara i podešavanje mreže.",
        "Создание сайтов, программирование, дизайн, ремонт компьютеров и настройка сети.",
        "Websites, programming, design, computer repair and network setup."),
    "legal": (
        "Pomoć sa dokumentima: boravak, prijava, prevodi za MUP, knjigovodstvo i pravni saveti.",
        "Помощь с документами: ВНЖ, прописка, переводы для МУП, бухгалтерия и юристы.",
        "Help with paperwork: residence permits, registration, translations, accounting and legal advice."),
    "photo-video": (
        "Fotografi i snimatelji za venčanja, rođendane, portrete, proizvode i događaje.",
        "Фотографы и видеографы — свадьбы, дни рождения, портреты, предметная съёмка и мероприятия.",
        "Photographers and videographers for weddings, birthdays, portraits, products and events."),
    "events": (
        "Organizacija proslava i rođendana, animatori, keteringi, dekoracija i muzika.",
        "Организация праздников и дней рождения, аниматоры, кейтеринг, оформление и музыка.",
        "Party and birthday planning, entertainers, catering, decorations and music."),
    "auto-services": (
        "Auto servisi, vulkanizeri, auto-električari, limari i pranje automobila.",
        "Автосервисы, шиномонтаж, автоэлектрики, кузовной ремонт и мойка.",
        "Car services, tyre shops, auto electricians, body repair and car wash."),
    "lost-found": (
        "Izgubljeni i nađeni dokumenti, ključevi, telefoni i ljubimci — pomozite da se vrate vlasnicima.",
        "Потерянные и найденные документы, ключи, телефоны и животные — помогите им вернуться домой.",
        "Lost and found documents, keys, phones and pets — help them get back to their owners."),
    "translation": (
        "Prevodi i sudski tumači: srpski, ruski, engleski i drugi jezici — dokumenti, overe, tekstovi.",
        "Переводчики и судебные переводчики: сербский, русский, английский и другие — документы и заверение.",
        "Translators and certified court interpreters: Serbian, Russian, English and more."),
    "pet-services": (
        "Šišanje i kupanje ljubimaca, čuvanje, šetnja pasa i dresura.",
        "Груминг, передержка, выгул собак и дрессировка.",
        "Pet grooming, pet sitting, dog walking and training."),
    # ── Работа
    "vacancies": (
        "Oglasi za posao u Beogradu i Srbiji: stalni posao, honorarno, rad na daljinu — direktno od poslodavca.",
        "Вакансии в Белграде и Сербии: постоянная работа, подработка, удалёнка — напрямую от работодателя.",
        "Jobs in Belgrade and Serbia: full-time, part-time and remote — straight from employers."),
    "resumes": (
        "Biografije ljudi koji traže posao — pronađite radnika, majstora ili saradnika bez agencije.",
        "Резюме тех, кто ищет работу, — найдите сотрудника, мастера или помощника без агентства.",
        "CVs from people looking for work — find staff, tradespeople or helpers without an agency."),
    # ── Электроника
    "computers": (
        "Stoni računari, gejmerske konfiguracije i radne stanice — polovni i novi.",
        "Настольные компьютеры, игровые сборки и рабочие станции — б/у и новые.",
        "Desktop computers, gaming builds and workstations — used and new."),
    "tablets": (
        "Tableti i e-čitači: iPad, Samsung, Kindle — polovni, sa punjačem i futrolom.",
        "Планшеты и электронные книги: iPad, Samsung, Kindle — б/у, с зарядкой и чехлом.",
        "Tablets and e-readers: iPad, Samsung, Kindle — used, with charger and case."),
    "tv-audio": (
        "Zvučnici, slušalice, pojačala, gramofoni i kućni bioskopi.",
        "Колонки, наушники, усилители, проигрыватели и домашние кинотеатры.",
        "Speakers, headphones, amplifiers, turntables and home cinema."),
    "photo": (
        "Fotoaparati, objektivi, dronovi, akcione kamere i oprema za snimanje.",
        "Фотоаппараты, объективы, дроны, экшн-камеры и оборудование для съёмки.",
        "Cameras, lenses, drones, action cams and filming gear."),
    "gaming": (
        "Konzole PlayStation, Xbox i Nintendo, igre, džojstici i gejmerska oprema.",
        "Приставки PlayStation, Xbox и Nintendo, игры, джойстики и геймерские аксессуары.",
        "PlayStation, Xbox and Nintendo consoles, games, controllers and gaming gear."),
    "wearables": (
        "Pametni satovi i narukvice: Apple Watch, Garmin, Samsung, Xiaomi.",
        "Умные часы и фитнес-браслеты: Apple Watch, Garmin, Samsung, Xiaomi.",
        "Smartwatches and fitness bands: Apple Watch, Garmin, Samsung, Xiaomi."),
    "charging": (
        "Punjači, kablovi, pauerbanke i adapteri za telefone i laptopove.",
        "Зарядки, кабели, пауэрбанки и переходники для телефонов и ноутбуков.",
        "Chargers, cables, power banks and adapters for phones and laptops."),
    "peripherals": (
        "Tastature, miševi, štampači, veb-kamere i druga oprema za računar.",
        "Клавиатуры, мыши, принтеры, веб-камеры и другая периферия для компьютера.",
        "Keyboards, mice, printers, webcams and other computer peripherals."),
    "cases": (
        "Maske, futrole i zaštitna stakla za telefone i tablete.",
        "Чехлы, сумки и защитные стёкла для телефонов и планшетов.",
        "Cases, covers and screen protectors for phones and tablets."),
    "components": (
        "Grafičke karte, procesori, memorija, diskovi i matične ploče — za nadogradnju i sklapanje.",
        "Видеокарты, процессоры, память, диски и материнские платы — для апгрейда и сборки.",
        "Graphics cards, CPUs, RAM, drives and motherboards — for upgrades and builds."),
    "smart-home": (
        "Pametne sijalice, utičnice, kamere, senzori i usisivači-roboti.",
        "Умные лампы, розетки, камеры, датчики и роботы-пылесосы.",
        "Smart bulbs, plugs, cameras, sensors and robot vacuums."),
    "monitors": (
        "Monitori za posao i igre — polovni i novi, po dijagonali i rezoluciji.",
        "Мониторы для работы и игр — б/у и новые, по диагонали и разрешению.",
        "Monitors for work and gaming — used and new, by size and resolution."),
    "network-gear": (
        "Ruteri, Wi-Fi sistemi, svičevi i modemi za kuću i kancelariju.",
        "Роутеры, Wi-Fi системы, коммутаторы и модемы для дома и офиса.",
        "Routers, Wi-Fi systems, switches and modems for home and office."),
    "tv-projectors": (
        "Televizori i projektori — pametni TV, OLED i LED, polovni i novi.",
        "Телевизоры и проекторы — Smart TV, OLED и LED, б/у и новые.",
        "TVs and projectors — smart TVs, OLED and LED, used and new."),
    # ── Одежда
    "women": (
        "Ženska odeća: haljine, jakne, džemperi, farmerke — polovna i nova, po veličini.",
        "Женская одежда: платья, куртки, свитеры, джинсы — б/у и новая, по размеру.",
        "Women's clothing: dresses, jackets, sweaters, jeans — preloved and new, by size."),
    "men": (
        "Muška odeća: jakne, odela, košulje, farmerke i sportska odeća.",
        "Мужская одежда: куртки, костюмы, рубашки, джинсы и спортивная одежда.",
        "Men's clothing: jackets, suits, shirts, jeans and sportswear."),
    "shoes": (
        "Ženska i muška obuća: patike, cipele, čizme i sandale — po broju.",
        "Женская и мужская обувь: кроссовки, туфли, ботинки и сандалии — по размеру.",
        "Women's and men's shoes: trainers, boots, heels and sandals — by size."),
    "bags": (
        "Torbe, rančevi, novčanici, kaiševi i drugi modni dodaci.",
        "Сумки, рюкзаки, кошельки, ремни и другие аксессуары.",
        "Bags, backpacks, wallets, belts and other accessories."),
    "watches": (
        "Ručni satovi i nakit: prstenje, ogrlice, minđuše, narukvice.",
        "Наручные часы и украшения: кольца, цепочки, серьги, браслеты.",
        "Watches and jewellery: rings, necklaces, earrings and bracelets."),
    # ── Дом и сад
    "appliances": (
        "Bela tehnika: frižideri, veš-mašine, šporeti, sudomašine i klima uređaji.",
        "Крупная техника: холодильники, стиральные машины, плиты, посудомойки и кондиционеры.",
        "Major appliances: fridges, washing machines, cookers, dishwashers and air conditioners."),
    "kitchenware": (
        "Posuđe, šerpe, tiganji, pribor za jelo i sitni kuhinjski aparati.",
        "Посуда, кастрюли, сковороды, столовые приборы и мелкая кухонная техника.",
        "Cookware, pots, pans, cutlery and small kitchen appliances."),
    "decor": (
        "Dekoracija i tekstil za dom: zavese, tepisi, posteljina, slike i ogledala.",
        "Декор и текстиль для дома: шторы, ковры, постельное бельё, картины и зеркала.",
        "Home décor and textiles: curtains, rugs, bedding, pictures and mirrors."),
    "garden": (
        "Biljke, sadnice, saksije, baštenski nameštaj i oprema za dvorište.",
        "Растения, саженцы, горшки, садовая мебель и всё для двора.",
        "Plants, seedlings, pots, garden furniture and yard equipment."),
    "tools": (
        "Alati: bušilice, brusilice, testere, ručni alat i oprema za radionicu.",
        "Инструменты: дрели, болгарки, пилы, ручной инструмент и оборудование для мастерской.",
        "Tools: drills, grinders, saws, hand tools and workshop equipment."),
    "building": (
        "Građevinski materijal: cigla, blokovi, crep, pločice, laminat, boje i izolacija.",
        "Стройматериалы: кирпич, блоки, черепица, плитка, ламинат, краска и утеплитель.",
        "Building materials: bricks, blocks, roof tiles, tiles, laminate, paint and insulation."),
    "plumbing": (
        "Vodovod i grejanje: bojleri, radijatori, peći, sanitarije i cevi.",
        "Сантехника и отопление: бойлеры, радиаторы, печи, сантехника и трубы.",
        "Plumbing and heating: boilers, radiators, stoves, sanitary ware and pipes."),
    "food": (
        "Domaća hrana i proizvodi: med, rakija, ajvar, sir, jaja, voće i povrće od proizvođača.",
        "Домашние продукты: мёд, ракия, айвар, сыр, яйца, фрукты и овощи от производителей.",
        "Homemade food: honey, rakija, ajvar, cheese, eggs, fruit and veg from local producers."),
    "household-goods": (
        "Sredstva za čišćenje i pranje, papirna galanterija i potrepštine za domaćinstvo.",
        "Бытовая химия, средства для уборки и стирки, бумажные товары для дома.",
        "Cleaning and laundry products, paper goods and household supplies."),
    "lighting": (
        "Lusteri, lampe, podne i stone svetiljke, LED rasveta.",
        "Люстры, лампы, торшеры, настольные светильники и LED-освещение.",
        "Chandeliers, lamps, floor and desk lights and LED lighting."),
    "storage-home": (
        "Police, kutije, korpe i organizeri za odlaganje stvari u stanu.",
        "Полки, коробки, корзины и органайзеры для хранения вещей.",
        "Shelves, boxes, baskets and organisers to keep your home tidy."),
    # ── Хобби и спорт
    "bikes": (
        "Bicikli i trotineti: gradski, brdski, drumski — polovni, po veličini rama.",
        "Велосипеды и самокаты: городские, горные, шоссейные — б/у, по размеру рамы.",
        "Bikes and scooters: city, mountain and road — used, by frame size."),
    "fitness": (
        "Sportska oprema: tegovi, trake za trčanje, sobni bicikli, prostirke i oprema za teretanu.",
        "Спортинвентарь: гантели, беговые дорожки, велотренажёры, коврики и всё для зала.",
        "Sports gear: weights, treadmills, exercise bikes, mats and gym equipment."),
    "outdoor": (
        "Šatori, vreće za spavanje, rančevi i oprema za planinarenje i kampovanje.",
        "Палатки, спальники, рюкзаки и снаряжение для походов и кемпинга.",
        "Tents, sleeping bags, backpacks and gear for hiking and camping."),
    "music": (
        "Muzički instrumenti: gitare, klavijature, bubnjevi, violine i ozvučenje.",
        "Музыкальные инструменты: гитары, клавишные, барабаны, скрипки и звук.",
        "Musical instruments: guitars, keyboards, drums, violins and sound gear."),
    "books": (
        "Knjige na srpskom, ruskom i engleskom: romani, udžbenici, dečje knjige.",
        "Книги на сербском, русском и английском: романы, учебники, детские книги.",
        "Books in Serbian, Russian and English: novels, textbooks and children's books."),
    "collecting": (
        "Kolekcionarstvo: novčići, marke, ploče, antikviteti i retke stvari.",
        "Коллекционирование: монеты, марки, пластинки, антиквариат и редкие вещи.",
        "Collectibles: coins, stamps, records, antiques and rare finds."),
    "winter-sport": (
        "Skije, snoubordi, pancerice i oprema za Kopaonik i Jahorinu.",
        "Лыжи, сноуборды, ботинки и экипировка — для Копаоника и Яхорины.",
        "Skis, snowboards, boots and gear — ready for Kopaonik and Jahorina."),
    "fishing-hunting": (
        "Pecanje i lov: štapovi, mašinice, mamci i oprema za ribolov.",
        "Рыбалка и охота: удочки, катушки, приманки и снаряжение.",
        "Fishing and hunting: rods, reels, lures and gear."),
    "board-games": (
        "Društvene igre, slagalice i kartaške igre za porodicu i društvo.",
        "Настольные игры, пазлы и карточные игры для семьи и компании.",
        "Board games, puzzles and card games for family and friends."),
    "tickets": (
        "Karte za koncerte, utakmice i predstave, vaučeri i pokloni-kartice.",
        "Билеты на концерты, матчи и спектакли, сертификаты и подарочные карты.",
        "Tickets for concerts, matches and shows, vouchers and gift cards."),
    "skate-roller": (
        "Skejtbordi, longbordi, rolere i zaštitna oprema.",
        "Скейтборды, лонгборды, ролики и защита.",
        "Skateboards, longboards, roller skates and protective gear."),
    "crafts": (
        "Ručni rad i hobi: materijali za heklanje, šivenje, slikanje i rukotvorine.",
        "Рукоделие и хобби: материалы для вязания, шитья, рисования и поделки ручной работы.",
        "Crafts and hobbies: supplies for knitting, sewing, painting and handmade goods."),
    "martial-arts": (
        "Oprema za borilačke veštine: rukavice, kimona, džakovi i štitnici.",
        "Экипировка для единоборств: перчатки, кимоно, груши и защита.",
        "Martial arts gear: gloves, gis, punch bags and pads."),
    "sport-nutrition": (
        "Sportska ishrana: proteini, kreatin, vitamini i suplementi.",
        "Спортивное питание: протеин, креатин, витамины и добавки.",
        "Sports nutrition: protein, creatine, vitamins and supplements."),
    # ── Детям
    "kids-clothing": (
        "Dečja odeća i obuća po uzrastu — od bebe do školarca, polovna i nova.",
        "Детская одежда и обувь по возрасту — от малышей до школьников, б/у и новая.",
        "Kids' clothes and shoes by age — from babies to school kids, preloved and new."),
    "kids-furniture": (
        "Krevetići, stolice za hranjenje, komode i nameštaj za dečju sobu.",
        "Кроватки, стульчики для кормления, комоды и мебель для детской.",
        "Cots, high chairs, dressers and nursery furniture."),
    "school": (
        "Školski pribor, rančevi, udžbenici i sve za polazak u školu.",
        "Школьные принадлежности, рюкзаки, учебники и всё к школе.",
        "School supplies, backpacks, textbooks and everything for back to school."),
    "kids-transport": (
        "Dečji bicikli, trotineti, guralice i bicikli bez pedala po uzrastu.",
        "Детские велосипеды, самокаты, каталки и беговелы по возрасту.",
        "Kids' bikes, scooters, ride-ons and balance bikes by age."),
    "kids-feeding": (
        "Flašice, pumpe za izmlazanje, sterilizatori i sve za ishranu i negu bebe.",
        "Бутылочки, молокоотсосы, стерилизаторы и всё для кормления и ухода за малышом.",
        "Bottles, breast pumps, sterilisers and everything for feeding and baby care."),
    # ── Животные
    "pets-dogs": (
        "Psi i štenci za udomljavanje i prodaju — od odgajivača i vlasnika.",
        "Собаки и щенки — пристройство и продажа от заводчиков и владельцев.",
        "Dogs and puppies for adoption and sale — from breeders and owners."),
    "pets-cats": (
        "Mačke i mačići za udomljavanje i prodaju.",
        "Кошки и котята — пристройство и продажа.",
        "Cats and kittens for adoption and sale."),
    "pets-other": (
        "Glodari, zečevi, ribice, gmizavci i druge kućne životinje.",
        "Грызуны, кролики, рыбки, рептилии и другие домашние животные.",
        "Rodents, rabbits, fish, reptiles and other pets."),
    "pets-supplies": (
        "Oprema za ljubimce: hrana, povodci, transporteri, kreveti i akvarijumi.",
        "Всё для питомцев: корм, поводки, переноски, лежанки и аквариумы.",
        "Pet supplies: food, leads, carriers, beds and aquariums."),
    "pets-birds": (
        "Papagaji, kanarinci i druge ptice, kavezi i hrana.",
        "Попугаи, канарейки и другие птицы, клетки и корм.",
        "Parrots, canaries and other birds, cages and feed."),
    "pets-farm": (
        "Domaće životinje: kokoške, koze, ovce, svinje i krave.",
        "Сельскохозяйственные животные: куры, козы, овцы, свиньи и коровы.",
        "Farm animals: chickens, goats, sheep, pigs and cows."),
    # ── Красота
    "cosmetics": (
        "Kozmetika, parfemi i nega kože — nova i originalna, od prodavaca u Srbiji.",
        "Косметика, парфюмерия и уход за кожей — новые и оригинальные, от продавцов в Сербии.",
        "Cosmetics, perfume and skincare — new and genuine, from sellers in Serbia."),
    "beauty-devices": (
        "Fenovi, prese za kosu, epilatori, aparati za masažu i negu lica.",
        "Фены, утюжки, эпиляторы, массажёры и приборы для ухода за лицом.",
        "Hair dryers, straighteners, epilators, massagers and facial devices."),
    "health": (
        "Proizvodi za zdravlje i negu: merači pritiska, inhalatori, ortopedska pomagala.",
        "Товары для здоровья и ухода: тонометры, ингаляторы, ортопедические изделия.",
        "Health and care products: blood pressure monitors, inhalers and orthopaedic aids."),
    "medical-supplies": (
        "Medicinski materijal i pomagala: invalidska kolica, štake, hodalice, kreveti za negu.",
        "Медицинские товары: инвалидные коляски, костыли, ходунки, кровати для ухода.",
        "Medical supplies: wheelchairs, crutches, walkers and care beds."),
    # ── Бизнес
    "equipment": (
        "Oprema za posao: ugostiteljstvo, prodavnice, saloni, radionice i kancelarije.",
        "Оборудование для бизнеса: общепит, магазины, салоны, мастерские и офисы.",
        "Business equipment for cafés, shops, salons, workshops and offices."),
    "ready-business": (
        "Gotov biznis na prodaju: kafići, prodavnice, saloni i onlajn projekti.",
        "Готовый бизнес на продажу: кафе, магазины, салоны и онлайн-проекты.",
        "Businesses for sale: cafés, shops, salons and online projects."),
    "supplies": (
        "Potrošni materijal za posao: ambalaža, kancelarijski materijal, sirovine.",
        "Расходные материалы для бизнеса: упаковка, канцелярия, сырьё.",
        "Business supplies: packaging, stationery and raw materials."),
    "agriculture": (
        "Poljoprivreda: traktori, priključne mašine, seme, đubrivo i oprema za farmu.",
        "Сельское хозяйство: тракторы, навесное оборудование, семена, удобрения и всё для фермы.",
        "Agriculture: tractors, implements, seeds, fertiliser and farm equipment."),
    "rental-equipment": (
        "Iznajmljivanje opreme i alata: građevinske mašine, ozvučenje, šatori i oprema za događaje.",
        "Аренда оборудования и инструмента: спецтехника, звук, шатры и всё для мероприятий.",
        "Equipment and tool hire: machinery, sound systems, marquees and event gear."),
}
