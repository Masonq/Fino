"""
Статьи «Полезного», сверенные с законом и свежими изменениями (октябрь 2026).

Откуда факты (пересказ своими словами, не копия):
  • регистрация иностранца (beli karton) — Закон об иностранцах РС, сл. гласник 24/2018, 31/2019, 62/2023:
    принимающий обязан подать регистрацию в полицию в течение 24 часов; штраф для физлица 5 000–25 000 RSD;
  • налог при покупке б/у машины — Закон о налогах на имущество: 2,5 % (porez na prenos apsolutnih prava),
    платит покупатель, считается по формуле (объём, мощность, возраст), с 2021 г. — самому на plati.euprava.gov.rs;
  • посылки — порядок Почты Сербии и Таможни с 23.02.2026: до 50 € — НДС 20 % + 200 RSD, дороже — пошлина 10 %
    и НДС на сумму, + 200 RSD и 1 % за перевод; подарок от частного лица — без сборов до 70 €;
  • работа иностранцам — единая разрешение (jedinstvena dozvola) на пребывание и работу, действует с 01.02.2024.

Цифры и правила меняются: в каждой статье стоит дата проверки и совет уточнить у ведомства.
Сверяли с материалами релокационных изданий (Т—Ж, v-serbii, parallax и др.) и с первоисточниками: где
издания расходились с законом или устарели (например, «посылки до 50 € без налогов» — так было до 2026 г.),
написано по закону.
"""

STAN = {
    "slug": "stan-bez-agencije",
    "date": "2026-10-07",
    "cover": "/cat/flats-rent.png",
    "sr": {
        "title": "Kako iznajmiti stan u Beogradu bez agencije",
        "lead": "Agencija obično uzima proviziju od pola do cele mesečne kirije. Stan se može naći direktno od vlasnika — evo kako da to uradite brzo, bezbedno i po zakonu, uključujući prijavu boravka za strance.",
        "blocks": [
            ("h2", "Gde tražiti"),
            ("p", "Najviše oglasa vlasnika ima na oglasnim sajtovima i u lokalnim grupama. Na PLONK-u filtrirajte nekretnine po gradu, ceni i broju soba, a u opisu tražite reči „vlasnik“ ili „bez provizije“. Dobri stanovi odlaze za dan-dva: pišite odmah i dogovarajte gledanje za isti ili sledeći dan."),
            ("h2", "Šta proveriti pre dogovora"),
            ("ul", [
                "Da li razgovarate sa vlasnikom — zamolite da vidite list nepokretnosti (možete ga proveriti i sami u katastru po adresi) ili ovlašćenje vlasnika.",
                "Šta ulazi u kiriju: Infostan (voda, grejanje, smeće), struja, internet, održavanje zgrade — i koliko računi iznose zimi, kada je grejanje najskuplje.",
                "Depozit — najčešće jedna mesečna kirija — i tačni uslovi pod kojima se vraća.",
                "Stanje stana: grejanje, vlaga u uglovima, bela tehnika, prozori, brava. Fotografišite sve na dan useljenja i pošaljite slike vlasniku — to je vaš dokaz kad se vraća depozit.",
                "Da li vlasnik pristaje da vas prijavi na adresi (za strance ovo je obavezno — vidi dole).",
            ]),
            ("h2", "Ugovor"),
            ("p", "Tražite pisani ugovor o zakupu: strane sa brojevima ličnih isprava, adresa, rok, iznos i valuta kirije, dan plaćanja, depozit i uslovi povraćaja, otkazni rok, ko plaća koje račune. Ugovor ne mora da se overava kod javnog beležnika, ali overen potpis olakšava sporove i neke administrativne postupke."),
            ("h2", "Prijava boravka za strance (beli karton)"),
            ("p", "Po Zakonu o strancima, onaj kod koga stranac boravi dužan je da prijavi njegov boravak policiji u roku od 24 časa od dolaska. Kod privatnog zakupa to je vlasnik stana; prijava se može podneti u policijskoj stanici ili elektronski. Vlasniku koji to ne uradi preti novčana kazna od 5.000 do 25.000 dinara. Beli karton vam treba za otvaranje računa u banci i za zahtev za boravak, a pravi se iznova posle svakog ulaska u zemlju."),
            ("h2", "Kako ne naleteti na prevaru"),
            ("ul", [
                "Ne plaćajte depozit unapred za stan koji niste videli uživo — „vlasnik je u inostranstvu, pošaljite novac pa šaljem ključeve“ je klasična prevara.",
                "Budite oprezni ako je cena mnogo niža od sličnih stanova u kraju.",
                "Novac predajte tek uz potpisan ugovor, uz potvrdu o prijemu ili uplatom na račun.",
                "Dopisujte se u četu na sajtu — prepiska ostaje kao dokaz dogovora.",
            ]),
            ("p", "Provereno: oktobar 2026. Pravila o prijavi boravka i iznosi kazni mogu se menjati — za svoj slučaj proverite u policijskoj upravi."),
            ("cta", ("Pogledajte stanove za izdavanje", "/c/flats")),
        ],
    },
    "ru": {
        "title": "Как снять квартиру в Белграде без агента",
        "lead": "Агентства берут комиссию — от половины до целой месячной аренды. Квартиру можно найти напрямую у хозяина: как сделать это быстро, безопасно и по закону, включая белый картон для иностранцев.",
        "blocks": [
            ("h2", "Где искать"),
            ("p", "Больше всего объявлений от хозяев — на досках объявлений и в местных группах. На PLONK отфильтруйте недвижимость по городу, цене и числу комнат, а в описании ищите «хозяин», «vlasnik» или «bez provizije». Хорошие квартиры уходят за день-два: пишите сразу и договаривайтесь о просмотре на сегодня или завтра."),
            ("h2", "Что проверить до договорённости"),
            ("ul", [
                "Что с вами говорит хозяин — попросите выписку о собственности (list nepokretnosti; по адресу её можно проверить и самому в кадастре) или доверенность от владельца.",
                "Что входит в аренду: Infostan (вода, отопление, мусор), свет, интернет, обслуживание дома — и сколько выходят счета зимой, когда отопление дороже всего.",
                "Депозит — обычно одна месячная аренда — и точные условия его возврата.",
                "Состояние квартиры: отопление, сырость в углах, техника, окна, замок. Сфотографируйте всё в день заезда и отправьте фото хозяину — это ваше доказательство при возврате депозита.",
                "Согласен ли хозяин оформить вам белый картон — для иностранца это обязательно (см. ниже).",
            ]),
            ("h2", "Договор"),
            ("p", "Просите письменный договор аренды: стороны с номерами документов, адрес, срок, сумма и валюта, день оплаты, депозит и условия возврата, срок предупреждения о выезде, кто какие счета платит. Заверять договор у нотариуса не обязательно, но заверенные подписи упрощают споры и некоторые процедуры."),
            ("h2", "Белый картон: регистрация иностранца"),
            ("p", "По Закону об иностранцах тот, у кого вы живёте, обязан зарегистрировать вас в полиции в течение 24 часов после приезда. При частной аренде это хозяин квартиры; подать можно в отделении полиции или онлайн. Хозяину, который этого не сделал, грозит штраф от 5 000 до 25 000 динаров. Белый картон нужен для счёта в банке и подачи на ВНЖ, а делать его приходится заново после каждого въезда в страну."),
            ("h2", "Как не нарваться на мошенников"),
            ("ul", [
                "Не платите депозит заранее за квартиру, которую не видели вживую: «хозяин за границей, переведите деньги — вышлю ключи» — классическая схема.",
                "Насторожитесь, если цена заметно ниже похожих квартир в районе.",
                "Передавайте деньги только после подписания договора — под расписку или переводом на счёт.",
                "Переписывайтесь в чате на сайте — переписка останется доказательством договорённостей.",
            ]),
            ("p", "Проверено: октябрь 2026. Правила регистрации и размеры штрафов могут меняться — для своего случая уточните в полиции."),
            ("cta", ("Смотреть квартиры в аренду", "/c/flats")),
        ],
    },
    "en": {
        "title": "How to rent a flat in Belgrade without an agency",
        "lead": "Agencies charge a fee of half to a full month's rent. You can rent directly from the owner — here's how to do it quickly, safely and legally, including the white card registration for foreigners.",
        "blocks": [
            ("h2", "Where to look"),
            ("p", "Most owner listings are on classifieds sites and in local groups. On PLONK, filter property by city, price and rooms, and look for “vlasnik” (owner) or “bez provizije” (no fee) in the description. Good flats go within a day or two — message right away and book a viewing for today or tomorrow."),
            ("h2", "What to check before agreeing"),
            ("ul", [
                "That you're talking to the owner — ask to see the property title (list nepokretnosti; you can also check it yourself in the cadastre by address) or the owner's power of attorney.",
                "What the rent covers: Infostan (water, heating, waste), electricity, internet, building maintenance — and how high bills get in winter, when heating costs most.",
                "The deposit — usually one month's rent — and exactly when it is returned.",
                "The flat's condition: heating, damp corners, appliances, windows, the lock. Photograph everything on move-in day and send the photos to the owner — that's your evidence when the deposit is returned.",
                "Whether the owner will register your address — mandatory for foreigners (see below).",
            ]),
            ("h2", "The contract"),
            ("p", "Ask for a written lease: both parties with ID numbers, address, term, amount and currency, payment day, deposit and return terms, notice period, and who pays which bills. Notarising the lease isn't required, but notarised signatures make disputes and some paperwork easier."),
            ("h2", "White card: address registration for foreigners"),
            ("p", "Under the Law on Foreigners, whoever hosts a foreigner must register their stay with the police within 24 hours of arrival. With a private rental that's the landlord; it can be done at a police station or online. A landlord who fails to do it faces a fine of 5,000 to 25,000 dinars. You need the white card to open a bank account and apply for residence, and it has to be done again after every entry into Serbia."),
            ("h2", "Avoiding scams"),
            ("ul", [
                "Never pay a deposit for a flat you haven't seen in person — “the owner is abroad, send the money and I'll post the keys” is a classic scam.",
                "Be wary if the price is far below similar flats nearby.",
                "Hand over money only once the lease is signed — against a receipt or by bank transfer.",
                "Keep the conversation in the site chat — it stays as a record of what was agreed.",
            ]),
            ("p", "Checked: October 2026. Registration rules and fines can change — confirm your case with the police."),
            ("cta", ("Browse flats for rent", "/c/flats")),
        ],
    },
}

CAR = {
    "slug": "kupovina-polovnog-automobila",
    "date": "2026-10-07",
    "cover": "/cat/cars-sale.png",
    "sr": {
        "title": "Kupovina polovnog automobila u Srbiji: provera, porez i prenos vlasništva",
        "lead": "Šta proveriti pre kupovine, koliki je porez od 2,5 % i kako se plaća onlajn, i kojim redom ići kod beležnika i u MUP — korak po korak.",
        "blocks": [
            ("h2", "Pre nego što platite"),
            ("ul", [
                "Uporedite broj šasije (VIN) na vozilu i u saobraćajnoj dozvoli, i da li je prodavac upisan kao vlasnik.",
                "Proverite istoriju: servisnu knjižicu, kilometražu i da li je vozilo havarisano — za uvozna vozila postoje plaćene provere po VIN-u.",
                "Pitajte do kada važi registracija i da li je vozilo pod zalogom ili lizingom.",
                "Odvezite auto na pregled kod svog majstora pre dogovora o ceni — to je najjeftinije osiguranje od skupe greške.",
            ]),
            ("h2", "Korak 1: ugovor kod javnog beležnika"),
            ("p", "Kupoprodajni ugovor potpisuju obe strane, a beležnik overava potpise. Ponesite lične isprave, saobraćajnu dozvolu i dogovorenu cenu. Novac je najsigurnije preneti na račun prodavca istog dana."),
            ("h2", "Korak 2: porez na prenos apsolutnih prava"),
            ("p", "Kupac plaća porez od 2,5 % vrednosti vozila. Vrednost se ne računa po ceni iz ugovora nego po propisanoj formuli — po zapremini motora, snazi i starosti vozila. Kada kupujete od fizičkog lica, porez sami obračunavate i plaćate na portalu plati.euprava.gov.rs, bez odlaska u Poresku upravu; uplatnica se može platiti i u pošti ili banci."),
            ("h2", "Korak 3: MUP i nova saobraćajna dozvola"),
            ("p", "Sa overenim ugovorom i dokazom o plaćenom porezu idete u policijsku upravu i podnosite zahtev za izdavanje saobraćajne dozvole na novog vlasnika. Ako se tablice ne menjaju, postupak je kraći; ako prodavac i kupac nisu iz istog grada, menjaju se i tablice. Prenos uradite odmah: dok je auto na prodavcu, kazne i prekršaji vode se na njega, a vama nije zaštićeno vlasništvo."),
            ("h2", "Za strance"),
            ("p", "Za registraciju vozila na stranca u praksi se traži odobren boravak u Srbiji. Pre kupovine proverite u MUP-u šta tačno treba za vaš slučaj."),
            ("p", "Provereno: oktobar 2026. Takse i postupak se menjaju — tačne iznose proverite na sajtovima MUP-a i Poreske uprave."),
            ("cta", ("Pogledajte automobile", "/c/cars")),
        ],
    },
    "ru": {
        "title": "Покупка б/у машины в Сербии: проверка, налог и переоформление",
        "lead": "Что проверить до покупки, как считается налог 2,5 % и как заплатить его онлайн, в каком порядке идти к нотариусу и в МУП — по шагам.",
        "blocks": [
            ("h2", "До того как платить"),
            ("ul", [
                "Сверьте номер кузова (VIN) на машине и в техпаспорте (saobraćajna dozvola) и что продавец записан как владелец.",
                "Проверьте историю: сервисную книжку, пробег и не битая ли машина — для пригнанных из-за границы есть платные проверки по VIN.",
                "Спросите, до какого числа действует регистрация и нет ли залога или лизинга.",
                "Покажите машину своему мастеру до торга — это самая дешёвая страховка от дорогой ошибки.",
            ]),
            ("h2", "Шаг 1: договор у нотариуса"),
            ("p", "Договор купли-продажи подписывают обе стороны, нотариус (javni beležnik) заверяет подписи. Возьмите документы, техпаспорт и договорённую цену. Деньги надёжнее всего перевести на счёт продавца в тот же день."),
            ("h2", "Шаг 2: налог 2,5 %"),
            ("p", "Покупатель платит налог на переход права (porez na prenos apsolutnih prava) — 2,5 % от стоимости машины. Стоимость считается не по цене из договора, а по формуле — по объёму двигателя, мощности и возрасту. При покупке у частного лица налог вы сами рассчитываете и оплачиваете на портале plati.euprava.gov.rs, без похода в налоговую; квитанцию можно оплатить и на почте или в банке."),
            ("h2", "Шаг 3: МУП и новый техпаспорт"),
            ("p", "С заверенным договором и подтверждением оплаты налога идёте в отделение полиции и подаёте заявление на техпаспорт на нового владельца. Если номера не меняются — быстрее; если продавец и покупатель из разных городов — меняют и номера. Переоформляйте сразу: пока машина на продавце, штрафы приходят ему, а ваше право собственности не защищено."),
            ("h2", "Если вы иностранец"),
            ("p", "Чтобы зарегистрировать машину на себя, на практике нужен одобренный ВНЖ в Сербии. До покупки уточните в МУП, что нужно именно в вашем случае."),
            ("p", "Проверено: октябрь 2026. Пошлины и порядок меняются — точные суммы смотрите на сайтах МУП и Налоговой управы."),
            ("cta", ("Смотреть машины", "/c/cars")),
        ],
    },
    "en": {
        "title": "Buying a used car in Serbia: checks, tax and transfer of ownership",
        "lead": "What to check before you buy, how the 2.5% tax works and how to pay it online, and in what order to visit the notary and the police — step by step.",
        "blocks": [
            ("h2", "Before you pay"),
            ("ul", [
                "Match the VIN on the car with the registration document (saobraćajna dozvola) and check the seller is listed as the owner.",
                "Check the history: service book, mileage and accident damage — paid VIN checks exist for imported cars.",
                "Ask when the registration expires and whether the car is under a lien or lease.",
                "Have your own mechanic inspect the car before you negotiate — the cheapest insurance against an expensive mistake.",
            ]),
            ("h2", "Step 1: contract at a notary"),
            ("p", "Both parties sign the sale contract and a public notary (javni beležnik) certifies the signatures. Bring ID, the registration document and the agreed price. Paying into the seller's bank account the same day is the safest option."),
            ("h2", "Step 2: the 2.5% transfer tax"),
            ("p", "The buyer pays a transfer tax (porez na prenos apsolutnih prava) of 2.5% of the car's value. The value isn't the contract price but a set formula based on engine size, power and age. When buying from a private person you calculate and pay it yourself at plati.euprava.gov.rs — no tax office visit; the payment slip can also be paid at a post office or bank."),
            ("h2", "Step 3: police and new registration"),
            ("p", "With the certified contract and proof of tax payment, apply at the police administration for a registration document in the new owner's name. It's quicker if the plates stay; if buyer and seller are from different cities, plates are changed too. Transfer straight away: until you do, fines go to the seller and your ownership isn't protected."),
            ("h2", "For foreigners"),
            ("p", "In practice, registering a car in a foreigner's name requires approved residence in Serbia. Check with the police what your case needs before buying."),
            ("p", "Checked: October 2026. Fees and procedure change — confirm exact amounts on the police and Tax Administration websites."),
            ("cta", ("Browse cars", "/c/cars")),
        ],
    },
}

PARCELS = {
    "slug": "paketi-iz-inostranstva-carina",
    "date": "2026-10-07",
    "cover": "/cat/transport.png",
    "sr": {
        "title": "Paketi iz inostranstva u 2026: koliko se plaća PDV i carina",
        "lead": "Od 23. februara 2026. Pošta Srbije obračunava dažbine na sve pošiljke sa stranih sajtova — i one ispod 50 evra. Evo koliko to stvarno košta i kada se više isplati kupiti ovde.",
        "blocks": [
            ("h2", "Šta se promenilo"),
            ("p", "Pošiljke sa stranih internet prodavnica (Temu, AliExpress, Shein i drugih) sada se automatski očitavaju po dolasku u Srbiju: vrednost i sadržaj se proveravaju isti dan, a dažbine plaćate pri preuzimanju. Paket brže stiže, ali „do 50 evra bez ikakvih troškova“ više ne važi."),
            ("h2", "Koliko se plaća"),
            ("ul", [
                "Pošiljka do 50 € od firme: bez carine, ali 20 % PDV na vrednost robe, plus 200 dinara za carinski pregled i mala provizija za plaćanje.",
                "Pošiljka preko 50 €: 10 % carine na vrednost robe, pa 20 % PDV na zbir robe i carine — ukupno oko 32 %, plus 200 dinara i 1 % provizije.",
                "Poklon koji šalje fizičko lice fizičkom licu: oslobođen dažbina do 70 €.",
                "Kada putujete: roba za lične potrebe do 100 € unosi se bez carine i PDV-a, po osobi.",
            ]),
            ("h2", "Primer"),
            ("p", "Patike od 80 €: carina 8 €, PDV 20 % na 88 € = 17,60 €, plus troškovi pregleda — ukupno oko 27 € više od cene na sajtu, a na to ide i čekanje."),
            ("h2", "Kada se isplati kupiti lokalno"),
            ("p", "Za tehniku, odeću i stvari za decu polovna roba od ljudi iz vašeg grada često je jeftinija od nove iz inostranstva kad se doda PDV i carina — bez čekanja i bez rizika da ne odgovara veličina. Pogledajte i sekciju „Besplatno“: mnogo toga ljudi poklanjaju pred selidbu."),
            ("p", "Provereno: oktobar 2026, prema obaveštenjima Pošte Srbije i Uprave carina. Iznosi se mogu menjati — tačan obračun vidite u obaveštenju o pošiljci."),
            ("cta", ("Pogledajte elektroniku", "/c/electronics")),
        ],
    },
    "ru": {
        "title": "Посылки из-за границы в 2026: сколько платить НДС и пошлину",
        "lead": "С 23 февраля 2026 года Почта Сербии берёт сборы со всех посылок с иностранных сайтов — и тех, что дешевле 50 евро. Сколько это стоит на самом деле и когда выгоднее купить здесь.",
        "blocks": [
            ("h2", "Что изменилось"),
            ("p", "Посылки с иностранных магазинов (Temu, AliExpress, Shein и других) теперь автоматически считываются по прибытии в Сербию: стоимость и содержимое проверяют в тот же день, а сборы вы оплачиваете при получении. Доходят быстрее, но правило «до 50 евро — без всяких платежей», которое до сих пор пишут во многих статьях, больше не действует."),
            ("h2", "Сколько платить"),
            ("ul", [
                "Посылка до 50 € от магазина: без пошлины, но 20 % НДС от стоимости, плюс 200 динаров за таможенный досмотр и небольшая комиссия за оплату.",
                "Посылка дороже 50 €: 10 % пошлины от стоимости, затем 20 % НДС на сумму товара и пошлины — всего около 32 %, плюс 200 динаров и 1 % комиссии.",
                "Подарок от частного лица частному лицу: без сборов до 70 €.",
                "Если везёте сами: вещи для личных нужд до 100 € на человека ввозятся без пошлины и НДС.",
            ]),
            ("h2", "Пример"),
            ("p", "Кроссовки за 80 €: пошлина 8 €, НДС 20 % с 88 € = 17,60 €, плюс досмотр — примерно на 27 € дороже цены на сайте, и ещё ожидание."),
            ("h2", "Когда выгоднее купить на месте"),
            ("p", "Технику, одежду и детские вещи б/у у людей из вашего города часто выходит дешевле, чем новое из-за границы с НДС и пошлиной, — без ожидания и без риска не угадать с размером. Загляните и в раздел «Даром»: перед переездом люди многое отдают бесплатно."),
            ("p", "Проверено: октябрь 2026, по сообщениям Почты Сербии и Таможенной управы. Суммы могут меняться — точный расчёт виден в уведомлении о посылке."),
            ("cta", ("Смотреть электронику", "/c/electronics")),
        ],
    },
    "en": {
        "title": "Parcels from abroad in 2026: how much VAT and customs you pay",
        "lead": "Since 23 February 2026, Post of Serbia charges fees on every parcel from foreign online shops — including those under €50. What it really costs, and when buying locally is cheaper.",
        "blocks": [
            ("h2", "What changed"),
            ("p", "Parcels from foreign online shops (Temu, AliExpress, Shein and others) are now scanned automatically on arrival in Serbia: value and contents are checked the same day, and you pay the charges on delivery. Parcels arrive faster, but “under €50 means no charges” — still repeated in many articles — no longer applies."),
            ("h2", "What you pay"),
            ("ul", [
                "Parcel under €50 from a business: no duty, but 20% VAT on the value, plus 200 dinars for customs processing and a small payment fee.",
                "Parcel over €50: 10% duty on the value, then 20% VAT on goods plus duty — about 32% in total, plus 200 dinars and a 1% payment fee.",
                "Gift from one private person to another: exempt up to €70.",
                "Carrying it yourself: goods for personal use up to €100 per person enter free of duty and VAT.",
            ]),
            ("h2", "Example"),
            ("p", "Trainers for €80: duty €8, VAT 20% on €88 = €17.60, plus processing — roughly €27 on top of the website price, plus the wait."),
            ("h2", "When buying locally wins"),
            ("p", "Used electronics, clothes and kids' things from people in your city often cost less than new items from abroad once VAT and duty are added — no waiting, no wrong sizes. Check the Free section too: people give a lot away before moving."),
            ("p", "Checked: October 2026, based on announcements by Post of Serbia and the Customs Administration. Amounts can change — the exact charge appears in your parcel notice."),
            ("cta", ("Browse electronics", "/c/electronics")),
        ],
    },
}

JOBS = {
    "slug": "posao-za-strance-u-srbiji",
    "date": "2026-10-07",
    "cover": "/cat/jobs-no_serbian.png",
    "sr": {
        "title": "Posao u Srbiji za strance: jedinstvena dozvola i kako izbeći lažne oglase",
        "lead": "Od februara 2024. stranci dobijaju jednu dozvolu za boravak i rad umesto dve. Šta to znači za vas i poslodavca, i kako prepoznati oglas za posao koji je zapravo prevara.",
        "blocks": [
            ("h2", "Jedinstvena dozvola"),
            ("p", "Od 1. februara 2024. primenjuje se jedinstvena dozvola za privremeni boravak i rad: umesto da prvo dobijete boravak pa posebno radnu dozvolu, podnosi se jedan zahtev, uglavnom elektronski, i dobija jedna biometrijska kartica. Zahtev najčešće pokreće poslodavac, a dok traje postupak, stranac može zakonito da boravi i radi."),
            ("h2", "Šta to znači u praksi"),
            ("ul", [
                "Pre nego što počnete da radite, dogovorite sa poslodavcem ko podnosi zahtev i kada.",
                "Dozvola je vezana za poslodavca — promena posla znači i promenu dozvole.",
                "Dozvole izdate po starom sistemu važe do isteka, nova nije potrebna.",
                "Rad „na crno“ bez dozvole rizikuje i radnik i poslodavac — kazne za poslodavce su pooštrene.",
            ]),
            ("h2", "Kako prepoznati lažan oglas"),
            ("ul", [
                "Traže novac unapred — za „obuku“, „dokumenta“, „uniformu“ ili „rezervaciju mesta“. Pravi poslodavac ne naplaćuje zapošljavanje.",
                "Plata je mnogo veća od proseka za taj posao, a opis je nejasan.",
                "Žure vas da odmah pređete u drugi mesindžer i pošaljete kopiju pasoša.",
                "Nema imena firme ili adrese — proverite firmu po nazivu ili matičnom broju u registru APR.",
            ]),
            ("p", "Provereno: oktobar 2026. Uslovi se menjaju — za svoj slučaj proverite na portalu za strance (welcometoserbia.gov.rs) ili kod advokata."),
            ("cta", ("Pogledajte oglase za posao", "/c/jobs")),
        ],
    },
    "ru": {
        "title": "Работа в Сербии для иностранцев: единое разрешение и как не попасть на фейковую вакансию",
        "lead": "С февраля 2024 года иностранцы получают одно разрешение на пребывание и работу вместо двух. Что это значит для вас и работодателя и как распознать вакансию-ловушку.",
        "blocks": [
            ("h2", "Единое разрешение"),
            ("p", "С 1 февраля 2024 года действует единое разрешение на временное пребывание и работу (jedinstvena dozvola): вместо того чтобы сначала получать ВНЖ, а потом отдельно разрешение на работу, подаётся одно заявление, обычно онлайн, и выдаётся одна биометрическая карта. Заявление чаще всего подаёт работодатель, а пока идёт рассмотрение, иностранец может законно находиться в стране и работать."),
            ("h2", "Что это значит на практике"),
            ("ul", [
                "До выхода на работу договоритесь с работодателем, кто и когда подаёт заявление.",
                "Разрешение привязано к работодателю — смена работы означает и смену разрешения.",
                "Выданные по старой схеме ВНЖ и разрешения действуют до конца срока, менять их не нужно.",
                "Работа без разрешения — риск и для работника, и для работодателя: штрафы для работодателей ужесточили.",
            ]),
            ("h2", "Как распознать фейковую вакансию"),
            ("ul", [
                "Просят деньги заранее — за «обучение», «документы», «форму» или «бронь места». Настоящий работодатель за трудоустройство не берёт.",
                "Зарплата сильно выше средней для такой работы, а описание размытое.",
                "Торопят сразу перейти в другой мессенджер и прислать скан паспорта.",
                "Нет названия компании или адреса — проверьте фирму по названию или матичному номеру в реестре APR.",
            ]),
            ("p", "Проверено: октябрь 2026. Условия меняются — для своего случая уточните на портале для иностранцев (welcometoserbia.gov.rs) или у юриста."),
            ("cta", ("Смотреть вакансии", "/c/jobs")),
        ],
    },
    "en": {
        "title": "Working in Serbia as a foreigner: the single permit and how to spot fake job ads",
        "lead": "Since February 2024 foreigners get one permit for residence and work instead of two. What it means for you and your employer, and how to recognise a job ad that's really a scam.",
        "blocks": [
            ("h2", "The single permit"),
            ("p", "Since 1 February 2024 Serbia has issued a single permit for temporary residence and work (jedinstvena dozvola): instead of getting residence first and a work permit separately, you file one application, usually online, and receive one biometric card. The employer usually starts the application, and while it's being processed the foreigner can legally stay and work."),
            ("h2", "What it means in practice"),
            ("ul", [
                "Before you start, agree with the employer who files the application and when.",
                "The permit is tied to the employer — changing jobs means changing the permit.",
                "Permits issued under the old system stay valid until they expire; no new one is needed.",
                "Working without a permit puts both worker and employer at risk — fines for employers have been raised.",
            ]),
            ("h2", "Spotting a fake job ad"),
            ("ul", [
                "They want money upfront — for “training”, “documents”, a “uniform” or “reserving the spot”. Real employers don't charge for hiring.",
                "The pay is far above average for the role and the description is vague.",
                "They push you to switch to another messenger right away and send a passport scan.",
                "No company name or address — look the company up by name or registration number in the APR business register.",
            ]),
            ("p", "Checked: October 2026. Rules change — confirm your case on the official portal for foreigners (welcometoserbia.gov.rs) or with a lawyer."),
            ("cta", ("Browse jobs", "/c/jobs")),
        ],
    },
}

# Доп. блок для «Как безопасно купить с рук»: сербская схема с поддельной доставкой.
SAFE_EXTRA = {
    "sr": [
        ("h2", "Lažna dostava i „link za uplatu“"),
        ("p", "Česta prevara u Srbiji: „kupac“ ili „prodavac“ šalje link navodno od pošte ili kurirske službe da „potvrdite dostavu“ ili „primite uplatu“, a stranica traži podatke kartice. Ni jedan oglasni sajt ni pošta ne traže podatke kartice da biste primili novac. Takve linkove ne otvarajte i prijavite korisnika."),
    ],
    "ru": [
        ("h2", "Фальшивая доставка и «ссылка на оплату»"),
        ("p", "Частая схема в Сербии: «покупатель» или «продавец» присылает ссылку якобы от почты или курьерской службы, чтобы «подтвердить доставку» или «получить оплату», а страница просит данные карты. Ни сайты объявлений, ни почта не требуют данные карты, чтобы вы получили деньги. Такие ссылки не открывайте и пожалуйтесь на пользователя."),
    ],
    "en": [
        ("h2", "Fake delivery and “payment links”"),
        ("p", "A common scam in Serbia: a “buyer” or “seller” sends a link supposedly from the post office or a courier to “confirm delivery” or “receive payment”, and the page asks for card details. No classifieds site or post office needs your card details for you to receive money. Don't open such links — report the user."),
    ],
}
