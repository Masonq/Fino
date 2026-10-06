"""
Четвёртая партия статей «Полезного» (октябрь 2026).

Откуда факты (пересказ своими словами):
  • коммуналка — Infostan (единая квитанция ~10 услуг: отопление, вода, канализация, обслуживание дома,
    вывоз мусора и др.), отопление жилья платится помесячно круглый год (годовая цена / 12), сезон с 15 октября
    по 15 апреля; EPS — зоны потребления (зелёная до 350 кВт·ч, красная свыше 1 200 кВт·ч), двухтарифный счётчик;
  • SIM — Закон об электронных коммуникациях (2023) и правилник: регистрация предоплаченных номеров обязательна
    с 10.02.2025, иностранцу — по паспорту; без регистрации — только экстренные службы и оператор;
  • продажа машины — тот же порядок, что при покупке (нотариус → налог платит покупатель → МУП), обязанность
    сообщить МУП о продаже, номера при истечении регистрации — вернуть в МУП в течение 60 дней.
"""

UTILITIES = {
    "slug": "racuni-infostan-struja",
    "date": "2026-10-07",
    "cover": "/cat/plumbing.png",
    "sr": {
        "title": "Računi u Beogradu: Infostan, struja i internet — šta se plaća i koliko",
        "lead": "Šta je Infostan, zašto se grejanje plaća i leti, kako struja poskupljuje po zonama potrošnje i šta pitati vlasnika pre useljenja.",
        "blocks": [
            ("h2", "Infostan"),
            ("p", "Infostan je jedinstveni račun za desetak komunalnih usluga: grejanje, hladnu vodu i kanalizaciju, održavanje zgrade i lifta, čišćenje ulaza, odvoz smeća i druge stavke — zavisno od toga na šta je stan prijavljen. Infostan ne određuje cene, samo naplaćuje."),
            ("h2", "Grejanje"),
            ("p", "Grejna sezona u Beogradu traje od 15. oktobra do 15. aprila, ali se centralno grejanje za stanove plaća svakog meseca tokom cele godine — godišnja cena podeljena na 12 rata. Zato je račun u julu isti kao u januaru. U zgradama sa merenjem po potrošnji postoji fiksni deo za održavanje sistema i promenljivi deo po potrošnji."),
            ("h2", "Struja (EPS)"),
            ("ul", [
                "Račun stiže posebno. Cena zavisi od zone potrošnje: zelena do 350 kWh mesečno je najjeftinija, crvena preko 1.200 kWh najskuplja.",
                "Sa dvotarifnim brojilom noćna struja je nekoliko puta jeftinija od dnevne — veš i sudomašinu pustite noću.",
                "Grejanje na struju (klima, grejalica) zimi lako gura račun u skuplju zonu — pitajte vlasnika za prošlogodišnje zimske račune.",
            ]),
            ("h2", "Internet i TV"),
            ("p", "Ugovara se posebno kod operatera (SBB, mts, Yettel, A1). Ugovori su često na 12 ili 24 meseca — ako iznajmljujete kraće, pitajte vlasnika da li je internet već uveden i uračunat u kiriju."),
            ("h2", "Pre useljenja pitajte"),
            ("ul", [
                "Koliko su prosečni računi zimi i leti i na čije ime stižu.",
                "Da li su svi računi izmireni na dan useljenja — dug ostaje na stanu.",
                "Ko plaća koje stavke: često kirija uključuje Infostan, a struju plaća stanar.",
            ]),
            ("p", "Provereno: oktobar 2026. Cene komunalija menja grad, a struje EPS — tačne iznose vidite na računu."),
            ("cta", ("Stanovi u Beogradu", "/beograd/c/flats")),
        ],
    },
    "ru": {
        "title": "Счета в Белграде: Infostan, свет и интернет — что платится и сколько",
        "lead": "Что такое Infostan, почему отопление оплачивается и летом, как свет дорожает по зонам потребления и что спросить у хозяина до заезда.",
        "blocks": [
            ("h2", "Infostan"),
            ("p", "Infostan — единая квитанция примерно за десять коммунальных услуг: отопление, холодная вода и канализация, обслуживание дома и лифта, уборка подъезда, вывоз мусора и другие — в зависимости от того, на что оформлена квартира. Infostan цены не устанавливает, только собирает оплату."),
            ("h2", "Отопление"),
            ("p", "Отопительный сезон в Белграде длится с 15 октября по 15 апреля, но центральное отопление квартир оплачивается каждый месяц круглый год — годовая цена, разделённая на 12 платежей. Поэтому квитанция в июле такая же, как в январе. В домах с поквартирным учётом есть постоянная часть за обслуживание системы и переменная — по потреблению."),
            ("h2", "Свет (EPS)"),
            ("ul", [
                "Счёт приходит отдельно. Цена зависит от зоны потребления: зелёная до 350 кВт·ч в месяц — самая дешёвая, красная свыше 1 200 кВт·ч — самая дорогая.",
                "С двухтарифным счётчиком ночное электричество в разы дешевле дневного — стирку и посудомойку ставьте на ночь.",
                "Отопление кондиционером или обогревателем зимой легко переводит счёт в дорогую зону — попросите у хозяина прошлогодние зимние счета.",
            ]),
            ("h2", "Интернет и ТВ"),
            ("p", "Подключаются отдельно у оператора (SBB, mts, Yettel, A1). Договоры часто на 12 или 24 месяца — если снимаете на меньший срок, спросите хозяина, есть ли уже интернет и входит ли он в аренду."),
            ("h2", "До заезда спросите"),
            ("ul", [
                "Сколько в среднем выходят счета зимой и летом и на чьё имя приходят.",
                "Оплачены ли все счета на день заезда — долг остаётся за квартирой.",
                "Кто что платит: часто в аренду входит Infostan, а свет оплачивает жилец.",
            ]),
            ("p", "Проверено: октябрь 2026. Тарифы на коммуналку меняет город, на свет — EPS; точные суммы видно в квитанции."),
            ("cta", ("Квартиры в Белграде", "/beograd/c/flats")),
        ],
    },
    "en": {
        "title": "Bills in Belgrade: Infostan, electricity and internet — what you pay and how much",
        "lead": "What Infostan is, why heating is billed in summer too, how electricity gets pricier by usage zone, and what to ask the landlord before moving in.",
        "blocks": [
            ("h2", "Infostan"),
            ("p", "Infostan is a single bill for about ten utility services: heating, cold water and sewage, building and lift maintenance, stairwell cleaning, waste collection and more — depending on what the flat is registered for. Infostan doesn't set prices; it only collects payment."),
            ("h2", "Heating"),
            ("p", "Belgrade's heating season runs from 15 October to 15 April, but central heating for flats is billed every month all year — the annual price split into 12 payments. That's why July's bill matches January's. Buildings with metered heating have a fixed part for system maintenance and a variable part for usage."),
            ("h2", "Electricity (EPS)"),
            ("ul", [
                "Billed separately. The price depends on your usage zone: green, up to 350 kWh a month, is cheapest; red, over 1,200 kWh, is most expensive.",
                "With a dual-tariff meter, night power is several times cheaper than daytime — run the washer and dishwasher at night.",
                "Heating with an air conditioner or electric heater easily pushes winter bills into a pricier zone — ask the landlord for last winter's bills.",
            ]),
            ("h2", "Internet and TV"),
            ("p", "Contracted separately with a provider (SBB, mts, Yettel, A1). Contracts often run 12 or 24 months — if you're renting for less, ask whether internet is already installed and included in the rent."),
            ("h2", "Ask before moving in"),
            ("ul", [
                "Typical winter and summer bills, and whose name they arrive in.",
                "Whether every bill is paid up to move-in day — debts stay with the flat.",
                "Who pays what: rent often includes Infostan, while the tenant pays electricity.",
            ]),
            ("p", "Checked: October 2026. The city sets utility prices and EPS sets electricity prices — your bill shows the exact amounts."),
            ("cta", ("Flats in Belgrade", "/beograd/c/flats")),
        ],
    },
}

SIM = {
    "slug": "sim-kartica-registracija",
    "date": "2026-10-07",
    "cover": "/cat/phones.png",
    "sr": {
        "title": "SIM kartica u Srbiji za strance: obavezna registracija i kako izabrati paket",
        "lead": "Od februara 2025. pripejd broj mora biti registrovan — inače radi samo poziv hitnim službama. Kako se registrujete sa pasošem i šta izabrati.",
        "blocks": [
            ("h2", "Registracija je obavezna"),
            ("p", "Po Zakonu o elektronskim komunikacijama, od 10. februara 2025. svaki pripejd broj mora biti registrovan na korisnika. Neregistrovan broj može da zove samo hitne službe i korisnički servis operatera. Stari saveti da se kartica kupi „na trafici bez dokumenata“ više ne važe."),
            ("h2", "Kako se registrujete"),
            ("ul", [
                "Stranac se registruje pasošem: u poslovnici operatera ili onlajn, u aplikaciji operatera — fotografišete dokument i lice.",
                "Registracija je moguća samo za punoletne.",
                "Ako izgubite karticu, registrovan broj možete zadržati — samo zamenite karticu.",
            ]),
            ("h2", "Pripejd ili postpejd"),
            ("p", "Tri operatera su mts, Yettel i A1. Pripejd je jednostavan i bez ugovora; postpejd (pretplata) je obično povoljniji za puno interneta, ali traži ugovor, a od stranaca često i boravak u Srbiji. Za prve mesece pripejd sa paketom interneta je najpraktičniji."),
            ("p", "Provereno: oktobar 2026. Paketi i cene se često menjaju — pogledajte sajt operatera."),
            ("cta", ("Telefoni na PLONK-u", "/c/phones")),
        ],
    },
    "ru": {
        "title": "SIM-карта в Сербии для иностранцев: обязательная регистрация и выбор тарифа",
        "lead": "С февраля 2025 года предоплаченный номер обязательно регистрируют — иначе можно звонить только в экстренные службы. Как зарегистрироваться по паспорту и что выбрать.",
        "blocks": [
            ("h2", "Регистрация обязательна"),
            ("p", "По Закону об электронных коммуникациях с 10 февраля 2025 года каждый предоплаченный номер должен быть зарегистрирован на владельца. С незарегистрированного номера можно звонить только в экстренные службы и в поддержку оператора. Старые советы «купить симку в киоске без документов» больше не работают."),
            ("h2", "Как зарегистрироваться"),
            ("ul", [
                "Иностранец регистрируется по паспорту: в салоне оператора или онлайн, в приложении оператора — фото документа и лица.",
                "Регистрация возможна только для совершеннолетних.",
                "Если потеряете SIM-карту, зарегистрированный номер можно сохранить — просто замените карту.",
            ]),
            ("h2", "Предоплата или контракт"),
            ("p", "Операторов три: mts, Yettel и A1. Предоплата проста и без договора; контракт (postpejd) обычно выгоднее при большом объёме интернета, но требует договора, а от иностранцев часто и ВНЖ. На первые месяцы удобнее всего предоплата с пакетом интернета."),
            ("p", "Проверено: октябрь 2026. Пакеты и цены часто меняются — смотрите на сайте оператора."),
            ("cta", ("Телефоны на PLONK", "/c/phones")),
        ],
    },
    "en": {
        "title": "SIM cards in Serbia for foreigners: mandatory registration and choosing a plan",
        "lead": "Since February 2025 every prepaid number must be registered — otherwise it can only call emergency services. How to register with a passport and what to choose.",
        "blocks": [
            ("h2", "Registration is mandatory"),
            ("p", "Under the Electronic Communications Law, since 10 February 2025 every prepaid number must be registered to its user. An unregistered number can only call emergency services and the operator's support line. Old advice to “buy a SIM at a kiosk, no ID needed” no longer applies."),
            ("h2", "How to register"),
            ("ul", [
                "Foreigners register with a passport: at an operator's shop or online in the operator's app — a photo of the document and your face.",
                "Only adults can register.",
                "If you lose the SIM, you can keep a registered number — just replace the card.",
            ]),
            ("h2", "Prepaid or contract"),
            ("p", "There are three operators: mts, Yettel and A1. Prepaid is simple with no contract; postpaid is usually better value for lots of data but needs a contract and, for foreigners, often residence in Serbia. For the first months, prepaid with a data bundle is the most practical."),
            ("p", "Checked: October 2026. Bundles and prices change often — see the operator's website."),
            ("cta", ("Phones on PLONK", "/c/phones")),
        ],
    },
}

CAR_SELL = {
    "slug": "prodaja-automobila",
    "date": "2026-10-07",
    "cover": "/cat/cars.png",
    "sr": {
        "title": "Kako prodati automobil u Srbiji: oglas, papiri i zaštita prodavca",
        "lead": "Kako napisati oglas koji prodaje, šta pripremiti od dokumenata i zašto prenos vlasništva morate završiti odmah — dok je auto na vama, kazne stižu vama.",
        "blocks": [
            ("h2", "Oglas koji prodaje"),
            ("ul", [
                "Fotografije danju, čist auto: spolja sa sve četiri strane, unutrašnjost, kilometar-sat, gume, motor.",
                "Godište, kilometraža, gorivo, menjač, registracija do kada važi, servisna istorija — prva pitanja svakog kupca.",
                "Pošteno navedite mane: kupac ih ionako nađe na pregledu, a poverenje ubrzava prodaju.",
                "Cenu uporedite sa sličnim oglasima — preskup auto stoji mesecima.",
            ]),
            ("h2", "Pre nego što predate ključeve"),
            ("ul", [
                "Ugovor o kupoprodaji sa overenim potpisima kod javnog beležnika — sa datumom i satom primopredaje.",
                "Novac primite na račun ili proverite gotovinu u banci; ne predajte auto „na veru“.",
                "Porez na prenos plaća kupac — to napišite i u ugovoru.",
            ]),
            ("h2", "Posle prodaje"),
            ("p", "Dok kupac ne prebaci vozilo na sebe u MUP-u, kazne i prekršaji vode se na vas. Dogovorite rok prenosa i pratite da li je obavljen. Prodaju je potrebno prijaviti MUP-u; ako registracija istekne, a kupac ne produži, tablice se vraćaju MUP-u u roku od 60 dana."),
            ("p", "Provereno: oktobar 2026. Postupak i takse proverite na sajtu MUP-a."),
            ("cta", ("Prodajte auto na PLONK-u", "/post")),
        ],
    },
    "ru": {
        "title": "Как продать машину в Сербии: объявление, документы и защита продавца",
        "lead": "Как написать объявление, которое продаёт, какие документы подготовить и почему переоформление нужно довести до конца сразу — пока машина на вас, штрафы приходят вам.",
        "blocks": [
            ("h2", "Объявление, которое продаёт"),
            ("ul", [
                "Фото днём, машина чистая: снаружи со всех четырёх сторон, салон, одометр, шины, мотор.",
                "Год, пробег, топливо, коробка, до какого числа регистрация, сервисная история — первые вопросы любого покупателя.",
                "Честно укажите недостатки: покупатель всё равно найдёт их на осмотре, а доверие ускоряет продажу.",
                "Сверьте цену с похожими объявлениями — машина дороже рынка стоит месяцами.",
            ]),
            ("h2", "Прежде чем отдать ключи"),
            ("ul", [
                "Договор купли-продажи с подписями, заверенными у нотариуса, — с датой и временем передачи.",
                "Деньги — переводом на счёт или проверьте наличные в банке; не отдавайте машину «под честное слово».",
                "Налог на переход права платит покупатель — пропишите это и в договоре.",
            ]),
            ("h2", "После продажи"),
            ("p", "Пока покупатель не переоформит машину в МУП, штрафы и нарушения записываются на вас. Договоритесь о сроке переоформления и проверьте, что оно сделано. О продаже нужно сообщить в МУП; если регистрация истекла, а покупатель её не продлил, номера возвращают в МУП в течение 60 дней."),
            ("p", "Проверено: октябрь 2026. Порядок и пошлины уточняйте на сайте МУП."),
            ("cta", ("Продать машину на PLONK", "/post")),
        ],
    },
    "en": {
        "title": "How to sell a car in Serbia: the ad, the paperwork and protecting yourself",
        "lead": "How to write an ad that sells, what documents to prepare, and why the transfer must be finished straight away — while the car is in your name, fines come to you.",
        "blocks": [
            ("h2", "An ad that sells"),
            ("ul", [
                "Daylight photos of a clean car: all four sides, interior, odometer, tyres, engine bay.",
                "Year, mileage, fuel, gearbox, registration expiry and service history — every buyer's first questions.",
                "Be honest about faults: the buyer will find them at inspection anyway, and trust speeds up the sale.",
                "Compare your price with similar ads — an overpriced car sits for months.",
            ]),
            ("h2", "Before handing over the keys"),
            ("ul", [
                "A sale contract with signatures certified by a notary — including the date and time of handover.",
                "Take payment by bank transfer, or check cash at a bank; never hand over the car on trust.",
                "The buyer pays the transfer tax — state this in the contract too.",
            ]),
            ("h2", "After the sale"),
            ("p", "Until the buyer re-registers the car with the police, fines and offences are recorded against you. Agree a deadline for the transfer and check it happened. The sale must be reported to the police; if the registration expires and the buyer doesn't renew it, the plates go back to the police within 60 days."),
            ("p", "Checked: October 2026. Confirm procedure and fees on the police (MUP) website."),
            ("cta", ("Sell your car on PLONK", "/post")),
        ],
    },
}
