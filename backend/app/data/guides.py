"""
Статьи-путеводители PLONK (/vodic/<адрес>, /ru/vodic/…, /en/vodic/…) — полезные тексты под частые запросы диаспоры
и местных: аренда без агента, продажа вещей перед переездом, б/у мебель, безопасная покупка с рук.

Зачем: страницы приводят людей из поиска годами, без рекламы. Сайт отдаёт их и людям (страница /vodic), и роботам
(полный текст в HTML — app/routers/seo.py). Блоки: ("h2", текст), ("p", текст), ("ul", [пункты]),
("cta", (текст кнопки, адрес)) — ссылка в нужный раздел PLONK.

Факты — общие и проверяемые; где правила зависят от ситуации, текст прямо говорит уточнить.
"""

GUIDES = [
    {
        "slug": "stan-bez-agencije",
        "date": "2026-10-06",
        "cover": "/cat/flats-rent.png",
        "sr": {
            "title": "Kako iznajmiti stan u Beogradu bez agencije",
            "lead": "Agencija u Beogradu obično uzima proviziju u visini polovine ili cele mesečne kirije. Stan se može naći i direktno od vlasnika — evo kako da to uradite brzo i bez iznenađenja.",
            "blocks": [
                ("h2", "Gde tražiti"),
                ("p", "Najviše oglasa vlasnika ima na oglasnim sajtovima i u lokalnim grupama. Na PLONK-u filtrirajte nekretnine po gradu, ceni i broju soba, a u opisu tražite reči „vlasnik“ ili „bez provizije“."),
                ("h2", "Šta proveriti pre dogovora"),
                ("ul", [
                    "Da li je osoba sa kojom razgovarate zaista vlasnik — zamolite da vidite dokaz o vlasništvu ili ugovor sa vlasnikom.",
                    "Šta ulazi u kiriju: Infostan, struja, internet, održavanje zgrade — i koliko u proseku iznose računi zimi.",
                    "Koliki je depozit (najčešće jedna mesečna kirija) i pod kojim uslovima se vraća.",
                    "Stanje stana: grejanje, vlaga, bela tehnika, prozori — fotografišite sve pri useljenju.",
                ]),
                ("h2", "Ugovor i prijava boravka"),
                ("p", "Tražite pisani ugovor o zakupu sa rokom, iznosom kirije, depozitom i uslovima raskida. Strani državljani moraju prijaviti adresu boravka u propisanom roku — dogovorite se sa vlasnikom ko i kada podnosi prijavu i proverite važeća pravila u policiji."),
                ("h2", "Kako ne naleteti na prevaru"),
                ("ul", [
                    "Ne plaćajte depozit unapred za stan koji niste videli uživo.",
                    "Budite oprezni ako je cena mnogo niža od sličnih stanova u kraju.",
                    "Novac predajte uz potpisan ugovor i potvrdu o uplati.",
                ]),
                ("cta", ("Pogledajte stanove za izdavanje", "/c/flats")),
            ],
        },
        "ru": {
            "title": "Как снять квартиру в Белграде без агента",
            "lead": "Агентства в Белграде обычно берут комиссию — половину или целую месячную аренду. Квартиру можно найти и напрямую у хозяина: вот как сделать это быстро и без сюрпризов.",
            "blocks": [
                ("h2", "Где искать"),
                ("p", "Больше всего объявлений от хозяев — на досках объявлений и в местных группах. На PLONK отфильтруйте недвижимость по городу, цене и числу комнат, а в описании ищите слова «хозяин», «vlasnik» или «bez provizije»."),
                ("h2", "Что проверить до договорённости"),
                ("ul", [
                    "Что с вами общается действительно хозяин — попросите показать документ о собственности или договор с хозяином.",
                    "Что входит в аренду: Infostan (коммунальные), свет, интернет, обслуживание дома — и сколько примерно выходят счета зимой.",
                    "Размер депозита (чаще всего одна месячная аренда) и условия его возврата.",
                    "Состояние квартиры: отопление, сырость, техника, окна — сфотографируйте всё при заезде.",
                ]),
                ("h2", "Договор и регистрация адреса"),
                ("p", "Просите письменный договор аренды: срок, сумма, депозит, условия расторжения. Иностранцы обязаны зарегистрировать адрес проживания в установленный срок — договоритесь с хозяином, кто и когда подаёт регистрацию, и уточните действующие правила в полиции."),
                ("h2", "Как не нарваться на мошенников"),
                ("ul", [
                    "Не платите депозит заранее за квартиру, которую не видели вживую.",
                    "Насторожитесь, если цена намного ниже похожих квартир в районе.",
                    "Передавайте деньги только при подписанном договоре и с распиской.",
                ]),
                ("cta", ("Смотреть квартиры в аренду", "/c/flats")),
            ],
        },
        "en": {
            "title": "How to rent a flat in Belgrade without an agent",
            "lead": "Agencies in Belgrade usually charge a fee of half to a full month's rent. You can find a flat directly from the owner — here's how to do it quickly and without surprises.",
            "blocks": [
                ("h2", "Where to look"),
                ("p", "Most owner listings are on classifieds sites and in local groups. On PLONK, filter property by city, price and rooms, and look for “owner”, “vlasnik” or “bez provizije” in the description."),
                ("h2", "What to check before you agree"),
                ("ul", [
                    "That you are really talking to the owner — ask to see proof of ownership or their contract with the owner.",
                    "What the rent includes: Infostan (utilities), electricity, internet, building fees — and typical winter bills.",
                    "The deposit (usually one month's rent) and when it is returned.",
                    "The flat's condition: heating, damp, appliances, windows — photograph everything when you move in.",
                ]),
                ("h2", "Contract and address registration"),
                ("p", "Ask for a written lease: term, rent, deposit and termination terms. Foreign nationals must register their address within the required time — agree with the owner who files it and when, and check the current rules with the police."),
                ("h2", "How to avoid scams"),
                ("ul", [
                    "Never pay a deposit in advance for a flat you have not seen in person.",
                    "Be careful if the price is far below similar flats in the area.",
                    "Hand over money only with a signed contract and a receipt.",
                ]),
                ("cta", ("Browse flats for rent", "/c/flats")),
            ],
        },
    },
    {
        "slug": "prodaja-stvari-pre-selidbe",
        "date": "2026-10-06",
        "cover": "/cat/furniture.png",
        "sr": {
            "title": "Gde prodati stvari pre selidbe",
            "lead": "Selidba je pravi trenutak da se rešite viška — nameštaja, tehnike, dečjih stvari. Uz malo pripreme većinu stvari možete prodati za nekoliko dana.",
            "blocks": [
                ("h2", "Počnite dve-tri nedelje ranije"),
                ("p", "Kupcima treba vremena da dođu po krupne stvari. Napravite spisak šta prodajete, šta poklanjate, a šta nosite — i krenite od najvećih komada."),
                ("h2", "Oglas koji se prodaje"),
                ("ul", [
                    "Fotografije pri dnevnom svetlu, iz više uglova, bez nereda u pozadini.",
                    "Dimenzije za nameštaj i model za tehniku — to su prva pitanja kupaca.",
                    "Jasna cena i rok: „preuzimanje do 15. u mesecu“ ubrzava odluku.",
                    "Kratak video umesto deset fotografija — na PLONK-u ga možete dodati oglasu.",
                ]),
                ("h2", "Poklonite ono što se ne prodaje"),
                ("p", "Stvari koje nisu otišle za nedelju dana ponudite besplatno — u odeljku „Besplatno“ uvek ima ljudi koji dolaze brzo i sami nose."),
                ("h2", "Sve stvari na jednom linku"),
                ("p", "Ako prodajete mnogo, napravite izlog prodavca: svi vaši oglasi na jednoj stranici koju možete poslati poznanicima i u grupe."),
                ("cta", ("Objavite oglas besplatno", "/post")),
            ],
        },
        "ru": {
            "title": "Где продать вещи перед переездом",
            "lead": "Переезд — лучший момент избавиться от лишнего: мебели, техники, детских вещей. С небольшой подготовкой большую часть можно продать за несколько дней.",
            "blocks": [
                ("h2", "Начните за две-три недели"),
                ("p", "Покупателям нужно время, чтобы приехать за крупными вещами. Составьте список: что продаёте, что отдаёте, что забираете — и начните с самого крупного."),
                ("h2", "Объявление, которое продаёт"),
                ("ul", [
                    "Фото при дневном свете, с нескольких сторон, без беспорядка на фоне.",
                    "Размеры для мебели и модель для техники — это первые вопросы покупателей.",
                    "Понятная цена и срок: «забрать до 15 числа» ускоряет решение.",
                    "Короткое видео вместо десяти фото — на PLONK его можно добавить к объявлению.",
                ]),
                ("h2", "Отдайте то, что не продаётся"),
                ("p", "Вещи, которые не ушли за неделю, предложите бесплатно — в разделе «Даром» всегда есть люди, которые приезжают быстро и забирают сами."),
                ("h2", "Все вещи по одной ссылке"),
                ("p", "Если продаёте много, сделайте витрину продавца: все ваши объявления на одной странице, которую можно отправить знакомым и в группы."),
                ("cta", ("Разместить объявление бесплатно", "/post")),
            ],
        },
        "en": {
            "title": "Where to sell your things before moving",
            "lead": "Moving is the perfect moment to clear out furniture, electronics and kids' things. With a little preparation you can sell most of it within days.",
            "blocks": [
                ("h2", "Start two or three weeks early"),
                ("p", "Buyers need time to come for bulky items. Make a list of what you sell, give away and keep — and start with the biggest pieces."),
                ("h2", "A listing that sells"),
                ("ul", [
                    "Photos in daylight, from several angles, with a tidy background.",
                    "Dimensions for furniture and model for electronics — buyers ask these first.",
                    "A clear price and deadline: “pick-up by the 15th” speeds up decisions.",
                    "A short video instead of ten photos — on PLONK you can add one to the listing.",
                ]),
                ("h2", "Give away what doesn't sell"),
                ("p", "Offer anything still left after a week for free — the “Free” section always has people who come quickly and carry it themselves."),
                ("h2", "All your items in one link"),
                ("p", "If you sell a lot, create a seller storefront: all your listings on one page you can send to friends and groups."),
                ("cta", ("Post a listing for free", "/post")),
            ],
        },
    },
    {
        "slug": "polovni-namestaj-beograd",
        "date": "2026-10-06",
        "cover": "/cat/furn-sofa.png",
        "sr": {
            "title": "Polovni nameštaj u Beogradu — gde kupiti i na šta paziti",
            "lead": "Polovan nameštaj često je kvalitetniji od novog iz iste cene, a do dobre garniture ili ormara u Beogradu može se doći za nekoliko dana.",
            "blocks": [
                ("h2", "Gde tražiti"),
                ("p", "Najveći izbor je u oglasima privatnih prodavaca — posebno krajem meseca i leti, kada se ljudi sele. Na PLONK-u pretražite „Dom i bašta“ i filtrirajte po gradu i ceni."),
                ("h2", "Šta proveriti uživo"),
                ("ul", [
                    "Mehanizme na garniturama i krevetima — da se rasklapaju bez škripe.",
                    "Fleke, mirise i tragove kućnih ljubimaca na tapaciranom nameštaju.",
                    "Stabilnost i šarke na ormarima i komodama.",
                    "Dimenzije — izmerite prostor kod kuće i vrata kroz koja nameštaj prolazi.",
                ]),
                ("h2", "Prevoz"),
                ("p", "Unapred se dogovorite ko rastavlja nameštaj i ima li lifta. Za krupne komade zgodno je naći prevoz u odeljku „Usluge“."),
                ("cta", ("Pogledajte nameštaj", "/c/home-garden")),
            ],
        },
        "ru": {
            "title": "Б/у мебель в Белграде — где купить и на что смотреть",
            "lead": "Подержанная мебель часто качественнее новой за те же деньги, а хороший диван или шкаф в Белграде можно найти за несколько дней.",
            "blocks": [
                ("h2", "Где искать"),
                ("p", "Самый большой выбор — у частных продавцов, особенно в конце месяца и летом, когда люди переезжают. На PLONK ищите в разделе «Дом и сад» и фильтруйте по городу и цене."),
                ("h2", "Что проверить вживую"),
                ("ul", [
                    "Механизмы диванов и кроватей — раскладываются ли без скрипа.",
                    "Пятна, запахи и следы животных на мягкой мебели.",
                    "Устойчивость и петли у шкафов и комодов.",
                    "Размеры — измерьте место дома и двери, через которые понесёте мебель.",
                ]),
                ("h2", "Перевозка"),
                ("p", "Заранее договоритесь, кто разбирает мебель и есть ли лифт. Для крупных вещей удобно найти перевозчика в разделе «Услуги»."),
                ("cta", ("Смотреть мебель", "/c/home-garden")),
            ],
        },
        "en": {
            "title": "Second-hand furniture in Belgrade — where to buy and what to check",
            "lead": "Used furniture is often better quality than new at the same price, and a good sofa or wardrobe in Belgrade can be found within days.",
            "blocks": [
                ("h2", "Where to look"),
                ("p", "The widest choice is from private sellers — especially at the end of the month and in summer, when people move. On PLONK, search “Home & Garden” and filter by city and price."),
                ("h2", "What to check in person"),
                ("ul", [
                    "Sofa and bed mechanisms — do they fold out without squeaking.",
                    "Stains, smells and pet marks on upholstery.",
                    "Stability and hinges on wardrobes and dressers.",
                    "Dimensions — measure your space and the doors it has to pass through.",
                ]),
                ("h2", "Transport"),
                ("p", "Agree in advance who takes the furniture apart and whether there is a lift. For bulky items, find a mover in the “Services” section."),
                ("cta", ("Browse furniture", "/c/home-garden")),
            ],
        },
    },
    {
        "slug": "bezbedna-kupovina",
        "date": "2026-10-06",
        "cover": "/cat/business.png",
        "sr": {
            "title": "Kako bezbedno kupiti polovnu stvar",
            "lead": "Većina kupovina preko oglasa prođe bez problema. Nekoliko jednostavnih pravila štiti od retkih prevara.",
            "blocks": [
                ("h2", "Pre sastanka"),
                ("ul", [
                    "Dopisujte se u četu na sajtu — tako ostaje istorija razgovora.",
                    "Pitajte za dodatne fotografije ili kratak video stvari.",
                    "Proverite profil prodavca: koliko dugo je na sajtu, ocene, druge oglase.",
                ]),
                ("h2", "Plaćanje"),
                ("ul", [
                    "Plaćajte pri preuzimanju, kada vidite stvar uživo.",
                    "Ne šaljite avans i ne otvarajte linkove „za plaćanje“ ili „dostavu“ koje vam neko pošalje.",
                    "Ne delite kodove iz SMS poruka i podatke kartice.",
                ]),
                ("h2", "Sastanak"),
                ("p", "Nađite se na javnom mestu tokom dana, a skupu tehniku proverite na licu mesta — uključite je i proverite osnovne funkcije."),
                ("cta", ("Pogledajte oglase", "/")),
            ],
        },
        "ru": {
            "title": "Как безопасно купить вещь с рук",
            "lead": "Большинство покупок по объявлениям проходят без проблем. Несколько простых правил защищают от редких мошенников.",
            "blocks": [
                ("h2", "До встречи"),
                ("ul", [
                    "Переписывайтесь в чате на сайте — так сохраняется история разговора.",
                    "Попросите дополнительные фото или короткое видео вещи.",
                    "Посмотрите профиль продавца: как давно на сайте, отзывы, другие объявления.",
                ]),
                ("h2", "Оплата"),
                ("ul", [
                    "Платите при получении, когда увидели вещь вживую.",
                    "Не отправляйте предоплату и не открывайте присланные ссылки «на оплату» или «доставку».",
                    "Не сообщайте коды из СМС и данные карты.",
                ]),
                ("h2", "Встреча"),
                ("p", "Встречайтесь в людном месте днём, а дорогую технику проверьте на месте — включите и проверьте основные функции."),
                ("cta", ("Смотреть объявления", "/")),
            ],
        },
        "en": {
            "title": "How to buy second-hand safely",
            "lead": "Most classifieds purchases go smoothly. A few simple rules protect you from the rare scam.",
            "blocks": [
                ("h2", "Before you meet"),
                ("ul", [
                    "Chat on the site — the conversation history is kept.",
                    "Ask for extra photos or a short video of the item.",
                    "Check the seller's profile: time on the site, reviews, other listings.",
                ]),
                ("h2", "Payment"),
                ("ul", [
                    "Pay on pick-up, once you have seen the item in person.",
                    "Never send a prepayment or open “payment” or “delivery” links someone sends you.",
                    "Never share SMS codes or card details.",
                ]),
                ("h2", "The meeting"),
                ("p", "Meet in a public place during the day, and test expensive electronics on the spot — switch them on and check the basics."),
                ("cta", ("Browse listings", "/")),
            ],
        },
    },
]

# Расширенная аренда и новые статьи, сверенные с законом (см. guides_extra.py). Свежие — сверху списка.
from app.data.guides_extra import CAR, JOBS, PARCELS, SAFE_EXTRA, STAN  # noqa: E402
from app.data.guides_extra2 import BANK, DISTRICTS, PETS, PROPERTY  # noqa: E402
from app.data.guides_extra3 import CARSEAT, LICENSE, PHONE, SCOOTER  # noqa: E402
from app.data.guides_extra4 import CAR_SELL, SIM, UTILITIES  # noqa: E402

GUIDES = ([STAN, UTILITIES, DISTRICTS, PROPERTY, CAR, CAR_SELL, LICENSE, SIM, PARCELS, BANK, JOBS, PETS,
           PHONE, SCOOTER, CARSEAT]
          + [g for g in GUIDES if g["slug"] != STAN["slug"]])
for _g in GUIDES:
    if _g["slug"] == "bezbedna-kupovina":
        for _lang, _extra in SAFE_EXTRA.items():
            _blocks = _g[_lang]["blocks"]
            _at = next((i for i, b in enumerate(_blocks) if b[0] == "cta"), len(_blocks))
            _g[_lang]["blocks"] = _blocks[:_at] + _extra + _blocks[_at:]

# Свои обложки статей (frontend/public/guides/<адрес статьи>.png) — вместо картинок разделов, если файл есть.
from pathlib import Path as _Path  # noqa: E402

_COVERS = _Path(__file__).resolve().parents[3] / "frontend" / "public" / "guides"
for _g in GUIDES:
    _file = _COVERS / f"{_g['slug']}.png"
    if _file.exists():
        # Метка содержимого в адресе: заменили картинку — у неё новый адрес, и телефон не покажет старую из кэша.
        _ver = __import__("hashlib").sha1(_file.read_bytes()).hexdigest()[:8]
        _g["cover"] = f"/guides/{_g['slug']}.png?v={_ver}"

BY_SLUG = {g["slug"]: g for g in GUIDES}
TITLES = {"sr": "Vodič — saveti za kupovinu i prodaju | PLONK", "ru": "Полезное — советы по покупке и продаже | PLONK",
          "en": "Guides — buying and selling tips | PLONK"}
HEADINGS = {"sr": "Vodič", "ru": "Полезное", "en": "Guides"}


def localized(g: dict, lang: str) -> dict:
    return g.get(lang) or g["sr"]
