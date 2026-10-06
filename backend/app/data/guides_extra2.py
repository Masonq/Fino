"""
Вторая партия статей «Полезного» (октябрь 2026), сверенных с первоисточниками.

Откуда факты (пересказ своими словами):
  • счёт в банке — Решение НБС об открытии счетов нерезидентов (паспорт + документ об адресе за последний год),
    Закон о платёжных услугах: человеку с законным пребыванием без счёта банк обязан открыть базовый счёт,
    об отказе — письменно с причинами по просьбе клиента; портал welcometoserbia.gov.rs;
  • питомцы — условия ввоза Управы по ветеринарии (чип, прививка от бешенства минимум за 21 день, паспорт);
    с июня 2026 Сербия в списке ЕС стран без теста на антитела для поездок с питомцем в ЕС;
  • жильё — Закон о налогах на имущество (2,5 % при вторичке), Закон об НДС (10 % на жильё в новостройке),
    льготы первого жилья — только гражданам РС; взаимность для иностранцев; RGZ — цены за I кв. 2026;
  • аренда по районам — средние цены однокомнатных по Halo oglasi (2025) и данные RGZ по ценам м² (2026).

Где релокационные статьи расходятся с первоисточниками — пишем по первоисточнику и говорим об этом прямо.
"""

BANK = {
    "slug": "racun-u-banci-i-menjacnice",
    "date": "2026-10-07",
    "cover": "/cat/legal.png",
    "sr": {
        "title": "Račun u banci i menjačnice u Srbiji: šta treba strancu",
        "lead": "Kako otvoriti račun kao nerezident, šta uraditi ako banka odbije, gde menjati novac bez gubitka i kako platiti prodavcu na PLONK-u odmah, bez gotovine.",
        "blocks": [
            ("h2", "Otvaranje računa"),
            ("p", "Po odluci Narodne banke Srbije, nerezident uz zahtev pokazuje pasoš i dokument iz kog se vidi adresa boravka u poslednjih godinu dana. U praksi većina banaka traži i beli karton — prijavu boravka u Srbiji — a neke traže i razlog otvaranja računa. Uslovi se razlikuju od banke do banke, pa ako vas jedna odbije, probajte u drugoj."),
            ("h2", "Ako vas banka odbije"),
            ("ul", [
                "Banka je dužna da osobi koja zakonito boravi u Srbiji i nema račun otvori platni račun sa osnovnim uslugama.",
                "Na vaš zahtev banka mora pisano da navede razlog odbijanja — tražite ga, to pomaže u drugoj banci ili pri žalbi Narodnoj banci.",
                "Nijedna banka ne sme da odbije klijenta zbog državljanstva kao takvog.",
            ]),
            ("h2", "Menjačnice"),
            ("p", "Menjajte samo u ovlašćenim menjačnicama — imaju istaknut kursni listić i daju potvrdu o zameni. Uporedite kupovni i prodajni kurs u dve-tri menjačnice: razlika na 1.000 evra lako ide i do desetak evra. Ne menjajte novac na ulici niti preko „poznanika iz grupe“."),
            ("h2", "Gotovina preko granice"),
            ("p", "Gotovina od 10.000 evra i više mora se prijaviti carini pri ulasku i izlasku iz Srbije. Neprijavljen novac može biti privremeno oduzet."),
            ("h2", "Kako platiti prodavcu na PLONK-u"),
            ("p", "Sa računom u srpskoj banci možete platiti odmah — instant prenosom ili skeniranjem IPS QR koda u aplikaciji banke, novac stiže za nekoliko sekundi, i danju i noću. Plaćajte tek kad vidite stvar uživo."),
            ("p", "Provereno: oktobar 2026. Uslovi banaka se menjaju — proverite u svojoj banci."),
            ("cta", ("Pogledajte oglase", "/")),
        ],
    },
    "ru": {
        "title": "Счёт в банке и обменники в Сербии: что нужно иностранцу",
        "lead": "Как открыть счёт нерезиденту, что делать, если банк отказал, где менять деньги без потерь и как расплатиться с продавцом на PLONK мгновенно, без наличных.",
        "blocks": [
            ("h2", "Открытие счёта"),
            ("p", "По решению Народного банка Сербии нерезидент вместе с заявлением показывает паспорт и документ, из которого видно его адрес за последний год. На практике большинство банков просят ещё белый картон — регистрацию в Сербии, — а некоторые спрашивают цель открытия счёта. Условия у банков разные: отказали в одном — идите в другой."),
            ("h2", "Если банк отказал"),
            ("ul", [
                "Банк обязан открыть базовый платёжный счёт человеку, который законно находится в Сербии и не имеет счёта.",
                "По вашей просьбе банк должен письменно указать причину отказа — попросите, это пригодится в другом банке или при жалобе в Народный банк.",
                "Отказывать клиенту из-за гражданства как такового банк не вправе.",
            ]),
            ("h2", "Обменники"),
            ("p", "Меняйте только в официальных обменниках (menjačnica) — у них вывешен курс и выдаётся квитанция. Сравните курсы покупки и продажи в двух-трёх местах: разница на 1 000 евро легко доходит до десятка евро. Не меняйте с рук и у «знакомого из чата»."),
            ("h2", "Наличные через границу"),
            ("p", "Наличные от 10 000 евро и больше нужно декларировать на таможне при въезде и выезде из Сербии. Незадекларированные деньги могут временно изъять. Многие статьи пишут только про ввоз — правило работает в обе стороны."),
            ("h2", "Как заплатить продавцу на PLONK"),
            ("p", "Со счётом в сербском банке можно заплатить мгновенно — переводом или по IPS QR-коду в приложении банка: деньги приходят за секунды, днём и ночью. Платите только когда увидели вещь вживую."),
            ("p", "Проверено: октябрь 2026. Условия банков меняются — уточняйте в своём банке."),
            ("cta", ("Смотреть объявления", "/")),
        ],
    },
    "en": {
        "title": "Bank accounts and currency exchange in Serbia: what foreigners need",
        "lead": "How to open an account as a non-resident, what to do if a bank says no, where to exchange money without losing out, and how to pay a PLONK seller instantly without cash.",
        "blocks": [
            ("h2", "Opening an account"),
            ("p", "Under the National Bank of Serbia's rules, a non-resident shows a passport and a document proving their address over the past year. In practice most banks also ask for the white card (address registration in Serbia), and some ask why you need the account. Requirements differ between banks — if one refuses, try another."),
            ("h2", "If a bank refuses"),
            ("ul", [
                "A bank must open a basic payment account for anyone legally staying in Serbia who doesn't have one.",
                "On request, the bank must state its reason for refusal in writing — ask for it; it helps at the next bank or in a complaint to the National Bank.",
                "A bank may not refuse a client because of nationality as such.",
            ]),
            ("h2", "Exchange offices"),
            ("p", "Exchange money only at licensed exchange offices (menjačnica) — they display their rates and give a receipt. Compare buy and sell rates at two or three places: on €1,000 the difference can easily reach ten euros. Never exchange on the street or with “someone from a group chat”."),
            ("h2", "Cash across the border"),
            ("p", "Cash of €10,000 or more must be declared to customs both when entering and leaving Serbia. Undeclared cash can be temporarily seized."),
            ("h2", "Paying a PLONK seller"),
            ("p", "With a Serbian bank account you can pay instantly — by transfer or by scanning an IPS QR code in your banking app; the money arrives in seconds, day or night. Pay only once you've seen the item in person."),
            ("p", "Checked: October 2026. Bank requirements change — confirm with your bank."),
            ("cta", ("Browse listings", "/")),
        ],
    },
}

PETS = {
    "slug": "selidba-sa-ljubimcem",
    "date": "2026-10-07",
    "cover": "/cat/pets-dogs.png",
    "sr": {
        "title": "Selidba u Srbiju sa psom ili mačkom: dokumenta i novo pravilo za EU",
        "lead": "Šta treba ljubimcu za ulazak u Srbiju, šta se promenilo u junu 2026. za putovanja u EU i kako naći stan u kome su ljubimci dobrodošli.",
        "blocks": [
            ("h2", "Uslovi za ulazak u Srbiju"),
            ("ul", [
                "Mikročip — ljubimac mora biti trajno obeležen.",
                "Vakcina protiv besnila: pri prvoj vakcinaciji mora proći najmanje 21 dan pre putovanja.",
                "Pasoš za ljubimca ili veterinarski sertifikat, ispravno popunjen kod ovlašćenog veterinara zemlje iz koje dolazite.",
                "Za mlade životinje (do 16 nedelja) važe posebna pravila — izjava o odsustvu kontakta sa divljim životinjama ili putovanje sa vakcinisanom majkom.",
            ]),
            ("p", "Spisak zemalja i obrasce objavljuje Uprava za veterinu Ministarstva poljoprivrede. Proverite i pravila avio-kompanije: težina, transporter i broj ljubimaca u kabini određuje prevoznik, ne država."),
            ("h2", "Novo od juna 2026: putovanje u EU bez titar testa"),
            ("p", "EU je uvrstila Srbiju na listu zemalja za koje više nije potreban test na antitela protiv besnila pri nekomercijalnom putovanju sa psom, mačkom ili tvorom. Ranije se test radio najranije mesec dana posle vakcine, a granica se prelazila tek tri meseca posle analize. Sada to otpada — ostaju mikročip, važeća vakcina i sertifikat. Mnogi vodiči i dalje navode staro pravilo."),
            ("h2", "Stan sa ljubimcem"),
            ("p", "Pitajte vlasnika pre gledanja i upišite u ugovor da je ljubimac dozvoljen — tako izbegavate spor oko depozita. Na PLONK-u u opisu tražite „ljubimci dozvoljeni“ ili „pet friendly“."),
            ("p", "Provereno: oktobar 2026. Pre puta proverite važeće uslove na sajtu Uprave za veterinu i kod prevoznika."),
            ("cta", ("Oprema za ljubimce", "/c/pets-supplies")),
        ],
    },
    "ru": {
        "title": "Переезд в Сербию с собакой или кошкой: документы и новое правило для ЕС",
        "lead": "Что нужно питомцу для въезда в Сербию, что изменилось в июне 2026 для поездок в ЕС и как найти квартиру, где рады животным.",
        "blocks": [
            ("h2", "Условия въезда в Сербию"),
            ("ul", [
                "Микрочип — животное должно быть чипировано.",
                "Прививка от бешенства: при первой вакцинации до поездки должно пройти не меньше 21 дня.",
                "Паспорт животного или ветеринарный сертификат, правильно оформленный уполномоченным ветеринаром страны, откуда вы едете.",
                "Для молодых животных (до 16 недель) свои правила — заявление об отсутствии контакта с дикими животными или поездка с привитой матерью.",
            ]),
            ("p", "Список стран и формы публикует Управа по ветеринарии Министерства сельского хозяйства. Проверьте и правила авиакомпании: вес, переноску и число животных в салоне определяет перевозчик, а не государство."),
            ("h2", "С июня 2026: поездки в ЕС без теста на антитела"),
            ("p", "ЕС включил Сербию в список стран, для которых при некоммерческой поездке с собакой, кошкой или хорьком больше не нужен тест на антитела к бешенству. Раньше тест делали не раньше чем через месяц после прививки, а границу можно было пересечь только через три месяца после анализа. Теперь этого нет — остаются чип, действующая прививка и сертификат. Многие гайды до сих пор пишут про обязательный титр."),
            ("h2", "Квартира с питомцем"),
            ("p", "Спросите хозяина до просмотра и впишите в договор, что животное разрешено, — так не будет спора о депозите. На PLONK ищите в описании «ljubimci dozvoljeni» или «pet friendly»."),
            ("p", "Проверено: октябрь 2026. Перед поездкой сверьте условия на сайте Управы по ветеринарии и у перевозчика."),
            ("cta", ("Всё для питомцев", "/c/pets-supplies")),
        ],
    },
    "en": {
        "title": "Moving to Serbia with a dog or cat: documents and the new EU rule",
        "lead": "What your pet needs to enter Serbia, what changed in June 2026 for trips to the EU, and how to find a flat where pets are welcome.",
        "blocks": [
            ("h2", "Entry requirements for Serbia"),
            ("ul", [
                "Microchip — the animal must be permanently identified.",
                "Rabies vaccination: after a first vaccination, at least 21 days must pass before travel.",
                "Pet passport or veterinary certificate, correctly completed by an authorised vet in the country you're travelling from.",
                "Young animals (under 16 weeks) have special rules — a declaration of no contact with wild animals, or travelling with their vaccinated mother.",
            ]),
            ("p", "The country lists and forms are published by the Veterinary Directorate of the Ministry of Agriculture. Check your airline's rules too: weight, carrier and the number of pets in the cabin are set by the airline, not the state."),
            ("h2", "Since June 2026: EU travel without a titre test"),
            ("p", "The EU has added Serbia to the list of countries whose dogs, cats and ferrets no longer need a rabies antibody test for non-commercial travel. Previously the test could be done at the earliest a month after vaccination, and you could cross the border only three months after it. That's gone — the chip, a valid vaccination and the certificate remain. Many guides still describe the old rule."),
            ("h2", "Renting with a pet"),
            ("p", "Ask the owner before viewing and put the pet clause in the lease — it avoids deposit disputes. On PLONK, look for “ljubimci dozvoljeni” or “pet friendly” in the description."),
            ("p", "Checked: October 2026. Before travelling, confirm the rules with the Veterinary Directorate and your carrier."),
            ("cta", ("Pet supplies", "/c/pets-supplies")),
        ],
    },
}

PROPERTY = {
    "slug": "kupovina-stana-stranac",
    "date": "2026-10-07",
    "cover": "/cat/flats-sale.png",
    "sr": {
        "title": "Kupovina stana u Srbiji za strance: porezi, troškovi i provera",
        "lead": "Može li stranac da kupi stan, kada se plaća PDV a kada porez na prenos, koliko na kraju izlaze troškovi i šta proveriti pre nego što date kaparu.",
        "blocks": [
            ("h2", "Može li stranac da kupi stan"),
            ("p", "Može, ako postoji uzajamnost (reciprocitet) između Srbije i države čiji ste državljanin — za većinu zemalja, uključujući Rusiju, ona postoji. Ako niste sigurni, proverite pre ugovora kod javnog beležnika ili advokata. Vlasništvo nad stanom je i jedan od osnova za privremeni boravak, bez propisane minimalne vrednosti."),
            ("h2", "Porezi"),
            ("ul", [
                "Novogradnja od investitora u PDV sistemu: PDV 10 % je u ceni, porez na prenos se ne plaća.",
                "Starogradnja i kupovina od fizičkog lica: porez na prenos apsolutnih prava 2,5 % na osnovicu koju utvrđuje Poreska uprava. Po zakonu ga plaća prodavac, ali se ugovorom gotovo uvek prebacuje na kupca — proverite šta piše u vašem.",
                "Olakšice za prvi stan (povraćaj PDV-a, oslobođenje od poreza na prenos) važe samo za državljane Srbije.",
                "Posle kupovine podnosite prijavu za godišnji porez na imovinu.",
            ]),
            ("h2", "Ostali troškovi"),
            ("ul", [
                "Javni beležnik: najčešće 250–600 evra, zavisno od vrednosti stana.",
                "Upis u katastar i izvod iz lista nepokretnosti — sitne takse.",
                "Agencija, ako je ima: obično 2–3 % plus PDV.",
                "Kod stana od oko 120.000 evra ukupni dodatni troškovi lako dostižu 6.000–7.000 evra.",
            ]),
            ("h2", "Šta proveriti pre kapare"),
            ("ul", [
                "List nepokretnosti: ko je vlasnik i da li postoje hipoteka, zabeležba spora ili druga tereta.",
                "Da li je stan legalizovan i upisan, i da li se kvadratura iz oglasa poklapa sa katastrom.",
                "Da li su plaćeni porez na imovinu i Infostan — tražite potvrde.",
                "Kaparu dajte tek uz pisani predugovor koji kaže šta se dešava sa novcem ako posao propadne.",
            ]),
            ("p", "Provereno: oktobar 2026, prema Zakonu o porezima na imovinu, Zakonu o PDV-u i podacima RGZ-a. Za svoj slučaj konsultujte beležnika ili advokata."),
            ("cta", ("Stanovi na prodaju", "/c/flats")),
        ],
    },
    "ru": {
        "title": "Покупка квартиры в Сербии иностранцем: налоги, расходы и проверка",
        "lead": "Может ли иностранец купить квартиру, когда платится НДС, а когда налог на переход права, сколько в итоге уходит на расходы и что проверить до задатка.",
        "blocks": [
            ("h2", "Может ли иностранец купить квартиру"),
            ("p", "Может, если между Сербией и страной вашего гражданства есть взаимность — для большинства стран, включая Россию, она есть. Если сомневаетесь, проверьте до договора у нотариуса или юриста. Собственная квартира — ещё и одно из оснований для ВНЖ, без минимальной стоимости."),
            ("h2", "Налоги"),
            ("ul", [
                "Новостройка от застройщика-плательщика НДС: НДС 10 % уже в цене, налог на переход права не платится.",
                "Вторичка и покупка у частного лица: налог на переход права (porez na prenos apsolutnih prava) 2,5 % от базы, которую определяет Налоговая. По закону его платит продавец, но договором почти всегда перекладывают на покупателя — посмотрите, что написано в вашем.",
                "Льготы на первое жильё (возврат НДС, освобождение от налога на переход) — только для граждан Сербии.",
                "После покупки подаётся декларация на ежегодный налог на имущество.",
            ]),
            ("h2", "Прочие расходы"),
            ("ul", [
                "Нотариус: обычно 250–600 евро в зависимости от стоимости.",
                "Регистрация в кадастре и выписка из листа недвижимости — небольшие сборы.",
                "Агентство, если есть: обычно 2–3 % плюс НДС.",
                "Для квартиры около 120 000 евро все дополнительные расходы легко доходят до 6–7 тысяч евро.",
            ]),
            ("h2", "Что проверить до задатка"),
            ("ul", [
                "Лист недвижимости (list nepokretnosti): кто собственник и нет ли ипотеки, отметки о споре или других обременений.",
                "Легализована ли квартира и совпадает ли площадь в объявлении с кадастром.",
                "Оплачены ли налог на имущество и Infostan — попросите справки.",
                "Задаток отдавайте только по письменному предварительному договору, где сказано, что будет с деньгами, если сделка сорвётся.",
            ]),
            ("p", "Проверено: октябрь 2026, по Закону о налогах на имущество, Закону об НДС и данным RGZ. Для своего случая проконсультируйтесь с нотариусом или юристом."),
            ("cta", ("Квартиры на продажу", "/c/flats")),
        ],
    },
    "en": {
        "title": "Buying a flat in Serbia as a foreigner: taxes, costs and checks",
        "lead": "Can a foreigner buy a flat, when do you pay VAT and when transfer tax, what the extra costs add up to, and what to check before paying a deposit.",
        "blocks": [
            ("h2", "Can a foreigner buy?"),
            ("p", "Yes, if there is reciprocity between Serbia and your country — for most countries, including Russia, there is. If unsure, check with a notary or lawyer before signing. Owning a flat is also one of the grounds for temporary residence, with no minimum value."),
            ("h2", "Taxes"),
            ("ul", [
                "New build from a VAT-registered developer: 10% VAT is in the price; no transfer tax.",
                "Resale or buying from a private person: 2.5% transfer tax (porez na prenos apsolutnih prava) on a base set by the Tax Administration. By law the seller pays, but contracts almost always shift it to the buyer — check yours.",
                "First-home reliefs (VAT refund, transfer tax exemption) apply only to Serbian citizens.",
                "After buying you file a return for the annual property tax.",
            ]),
            ("h2", "Other costs"),
            ("ul", [
                "Notary: usually €250–600 depending on the price.",
                "Cadastre registration and title extract — small fees.",
                "Agency, if any: usually 2–3% plus VAT.",
                "For a flat of about €120,000, extra costs easily reach €6,000–7,000.",
            ]),
            ("h2", "What to check before a deposit"),
            ("ul", [
                "The title extract (list nepokretnosti): who owns it and whether there's a mortgage, a dispute note or other encumbrance.",
                "Whether the flat is legalised and registered, and the listed size matches the cadastre.",
                "Whether property tax and Infostan bills are paid — ask for certificates.",
                "Pay a deposit only under a written preliminary contract that says what happens to the money if the deal falls through.",
            ]),
            ("p", "Checked: October 2026, against the Property Tax Law, the VAT Law and Republic Geodetic Authority data. Consult a notary or lawyer for your case."),
            ("cta", ("Flats for sale", "/c/flats")),
        ],
    },
}

DISTRICTS = {
    "slug": "opstine-beograda-gde-ziveti",
    "date": "2026-10-07",
    "cover": "/cat/real-estate.png",
    "sr": {
        "title": "Gde živeti u Beogradu: opštine, kirije i cene kvadrata",
        "lead": "Kratak pregled beogradskih opština — kakav je život, koliko košta jednosoban stan u zakupu i koliko kvadrat pri kupovini.",
        "blocks": [
            ("h2", "Centar: Savski venac, Stari grad, Vračar"),
            ("p", "Sve je na pešačkoj udaljenosti, ali je i najskuplje. Prosečna kirija za jednosoban stan bila je oko 940 evra na Savskom vencu (sa Beogradom na vodi), oko 600 evra u Starom gradu i oko 500 evra na Vračaru. Kvadrat pri kupovini — oko 3.600–4.100 evra."),
            ("h2", "Novi Beograd"),
            ("p", "Široke ulice, blokovi, poslovni centri i tržni centri; mnogo novogradnje. Popularan kod porodica i onih koji rade u kancelarijama na Novom Beogradu. Kvadrat — oko 3.300 evra."),
            ("h2", "Zvezdara, Voždovac, Palilula"),
            ("p", "Dobar odnos cene i lokacije, blizu centra, dosta starogradnje. Pogodno ako vam je važno da kirija ne pojede pola plate."),
            ("h2", "Zemun, Čukarica (Banovo brdo), Rakovica"),
            ("p", "Mirnije, više zelenila, jeftiniji kvadrat — oko 2.600–2.800 evra. Kirija za jednosoban stan na Rakovici bila je oko 350 evra. Računajte na duži put do centra."),
            ("h2", "Saveti"),
            ("ul", [
                "Proverite prevoz do posla u špicu, a ne na mapi u nedelju ujutru.",
                "Pitajte za grejanje: centralno (preko Infostana) je zimi predvidljivije od struje.",
                "Na PLONK-u gledajte stanove po gradu i sortirajte po ceni — za nekoliko minuta vidite stvarne cene u kraju.",
            ]),
            ("p", "Izvori: prosečne kirije po opštinama — Halo oglasi (2025), cene kvadrata — Republički geodetski zavod (prvi kvartal 2026). Cene se brzo menjaju; tekuće vidite u oglasima."),
            ("cta", ("Stanovi u Beogradu", "/beograd/c/flats")),
        ],
    },
    "ru": {
        "title": "Где жить в Белграде: районы, аренда и цены за метр",
        "lead": "Коротко о районах Белграда — какая там жизнь, сколько стоит аренда однушки и сколько квадратный метр при покупке.",
        "blocks": [
            ("h2", "Центр: Савски-Венац, Стари-Град, Врачар"),
            ("p", "Всё в пешей доступности, но и дороже всего. Средняя аренда однокомнатной квартиры — около 940 евро в Савски-Венаце (вместе с «Белградом на воде»), около 600 евро в Стари-Граде и около 500 евро на Врачаре. Метр при покупке — около 3 600–4 100 евро."),
            ("h2", "Нови-Белград"),
            ("p", "Широкие улицы, кварталы-блоки, бизнес-центры и торговые центры, много новостроек. Популярен у семей и тех, кто работает в офисах Нови-Белграда. Метр — около 3 300 евро."),
            ("h2", "Звездара, Вождовац, Палилула"),
            ("p", "Хороший баланс цены и расположения, близко к центру, много вторички. Подойдёт, если важно, чтобы аренда не съедала половину зарплаты."),
            ("h2", "Земун, Чукарица (Баново-Брдо), Раковица"),
            ("p", "Спокойнее, больше зелени, метр дешевле — около 2 600–2 800 евро. Аренда однушки в Раковице — около 350 евро. Закладывайте больше времени на дорогу в центр."),
            ("h2", "Советы"),
            ("ul", [
                "Проверяйте дорогу до работы в час пик, а не по карте в воскресенье утром.",
                "Спрашивайте про отопление: центральное (через Infostan) зимой предсказуемее электрического.",
                "На PLONK смотрите квартиры по городу и сортируйте по цене — за пару минут увидите реальные цены в районе.",
            ]),
            ("p", "Источники: средняя аренда по районам — Halo oglasi (2025), цены за метр — Республиканский геодезический институт RGZ (I квартал 2026). Цены быстро меняются — актуальные видно в объявлениях."),
            ("cta", ("Квартиры в Белграде", "/beograd/c/flats")),
        ],
    },
    "en": {
        "title": "Where to live in Belgrade: districts, rents and price per m²",
        "lead": "A quick guide to Belgrade's districts — what life is like, what a one-bedroom rents for and what a square metre costs to buy.",
        "blocks": [
            ("h2", "Centre: Savski Venac, Stari Grad, Vračar"),
            ("p", "Everything is walkable, but it's the priciest. Average rent for a one-bedroom was about €940 in Savski Venac (including Belgrade Waterfront), about €600 in Stari Grad and about €500 in Vračar. Buying costs roughly €3,600–4,100 per m²."),
            ("h2", "New Belgrade"),
            ("p", "Wide streets, residential blocks, business and shopping centres, lots of new builds. Popular with families and people working in New Belgrade's offices. About €3,300 per m²."),
            ("h2", "Zvezdara, Voždovac, Palilula"),
            ("p", "A good balance of price and location, close to the centre, plenty of older buildings. A fit if you don't want rent to eat half your salary."),
            ("h2", "Zemun, Čukarica (Banovo Brdo), Rakovica"),
            ("p", "Quieter and greener, with cheaper square metres — about €2,600–2,800. A one-bedroom in Rakovica rented for about €350. Allow more time to get to the centre."),
            ("h2", "Tips"),
            ("ul", [
                "Test the commute at rush hour, not on a map on Sunday morning.",
                "Ask about heating: central heating (billed via Infostan) is more predictable in winter than electric.",
                "On PLONK, browse flats by city and sort by price — in a couple of minutes you'll see real local prices.",
            ]),
            ("p", "Sources: average rents by district — Halo oglasi (2025); price per m² — Republic Geodetic Authority (Q1 2026). Prices move fast — current ones are in the listings."),
            ("cta", ("Flats in Belgrade", "/beograd/c/flats")),
        ],
    },
}
