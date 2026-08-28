// Правила сервиса — Условия использования и Политика конфиденциальности.
//
// Отдельный файл, а не i18n/locales/*.json: там короткие фразы интерфейса,
// а здесь связный текст на несколько экранов — смешивать разное по природе
// содержимое в одном файле неудобно поддерживать.
//
// Это не готовый юридический документ, а разумный черновик под реальные
// особенности именно этого сервиса — стоит показать юристу перед тем, как
// полагаться на него всерьёз, особенно по обработке персональных данных.

export const CONTACT_EMAIL = 'account@plonk.rs'

export const TERMS = {
  ru: {
    title: 'Условия использования',
    updated: 'Обновлено: 27 августа 2026',
    sections: [
      {
        h: '1. Что такое PLONK',
        p: [
          'PLONK (plonk.rs) — сайт объявлений для Сербии: частные лица и компании размещают объявления о продаже вещей, недвижимости, услуг и прочего, а покупатели их находят и связываются с продавцом через встроенный чат.',
          'Часть объявлений размещается напрямую на сайте, часть — через бота в Telegram, часть переносится из открытых телеграм-чатов барахолок с согласия администрации этих чатов.',
        ],
      },
      {
        h: '2. Кто может пользоваться сервисом',
        p: [
          'Сервис предназначен для совершеннолетних. Создавая учётную запись, вы подтверждаете, что вам есть 18 лет.',
          'Для входа нужен email или Telegram. Проверка документа удостоверения личности — добровольная, через стороннего партнёра; отметка «Проверенный пользователь» подтверждает, что за аккаунтом стоит конкретный, реально проверенный человек.',
          'Аккаунт — личный и непередаваемый: продавать, дарить или иным образом передавать его другому человеку нельзя, даже если на нём уже есть отметка «Проверенный пользователь» или история отзывов. Мы вправе запросить повторное подтверждение личности в любой момент — если оно не пройдено, отметка снимается.',
        ],
      },
      {
        h: '3. Объявления',
        p: [
          'Публикуя объявление, вы подтверждаете, что вправе продавать указанную вещь или предлагать услугу, а сведения в объявлении достоверны — включая цену, состояние, фотографии (свои, а не чужие).',
          'Запрещены: заведомо ложные объявления, товары и услуги, запрещённые законом (оружие, наркотики, поддельные документы и подобное), объявления не по назначению раздела, спам и повторяющиеся публикации одного и того же.',
          'Каждое объявление проходит проверку модератором, прежде чем попасть в общую ленту. Мы вправе отклонить объявление или снять уже опубликованное без объяснения причин, если оно нарушает эти условия — обычно с указанием причины, но не обязаны это делать в каждом случае.',
          'Изменение цены, текста, фото или города возвращает объявление на повторную проверку.',
        ],
      },
      {
        h: '4. Сделки между пользователями',
        p: [
          'PLONK — площадка для знакомства покупателя и продавца, а не сторона сделки. Мы не участвуем в оплате, доставке и передаче вещи и не несём ответственности за качество товара, соблюдение договорённостей или действия других пользователей.',
          'Проверяйте вещь перед оплатой, встречайтесь в людных местах, будьте осторожны с предоплатой незнакомым людям — обычная осторожность на любой барахолке.',
        ],
      },
      {
        h: '5. Переписка, отзывы, жалобы',
        p: [
          'Чат в приложении — для общения о конкретном объявлении. Использовать его для рекламы посторонних услуг, рассылок или оскорблений нельзя.',
          'Вы можете закрыть конкретному человеку возможность писать вам — эта блокировка не распространяется на решения администрации.',
          'Отзыв можно оставить только после реального общения по объявлению. Отзывы не редактируются модерацией по содержанию, кроме явных нарушений (оскорбления, персональные данные третьих лиц, спам).',
          'Жалоба на объявление или пользователя рассматривается вручную. Ложные массовые жалобы — тоже нарушение этих условий.',
        ],
      },
      {
        h: '6. Блокировка аккаунта',
        p: [
          'Мы вправе ограничить или заблокировать учётную запись при нарушении этих условий, множественных обоснованных жалобах или попытке обойти модерацию. Решение можно обжаловать через поддержку.',
        ],
      },
      {
        h: '7. Ответственность',
        p: [
          'Сервис предоставляется «как есть». Мы стараемся поддерживать его в рабочем состоянии, но не гарантируем бесперебойную работу и не отвечаем за убытки, возникшие из-за сбоев, действий других пользователей или содержимого объявлений.',
        ],
      },
      {
        h: '8. Изменения условий',
        p: [
          'Мы можем обновлять эти условия — дата в начале страницы показывает последнее изменение. Продолжая пользоваться сервисом после изменений, вы соглашаетесь с новой версией.',
        ],
      },
      {
        h: '9. Связь с нами',
        p: [
          `По любым вопросам об условиях — через раздел поддержки в приложении или на ${CONTACT_EMAIL}.`,
        ],
      },
    ],
  },

  en: {
    title: 'Terms of Use',
    updated: 'Updated: August 27, 2026',
    sections: [
      {
        h: '1. What PLONK is',
        p: [
          'PLONK (plonk.rs) is a classifieds site for Serbia: individuals and businesses list items, real estate, services, and more for sale, and buyers find them and reach out through the built-in chat.',
          'Some listings are posted directly on the site, some through our Telegram bot, and some are carried over from public Telegram marketplace chats with the administration of those chats.',
        ],
      },
      {
        h: '2. Who can use the service',
        p: [
          'The service is intended for adults. By creating an account, you confirm that you are at least 18 years old.',
          'Signing in requires an email or Telegram. Identity document verification is optional, through a third-party partner; a \u201cVerified user\u201d badge confirms a specific, actually verified person stands behind the account.',
          'An account is personal and non-transferable: selling, gifting, or otherwise handing it to someone else is not allowed, even if it already carries a \u201cVerified user\u201d badge or a review history. We may request re-confirmation of identity at any time \u2014 if it is not completed, the badge is removed.',
        ],
      },
      {
        h: '3. Listings',
        p: [
          'By posting a listing you confirm you have the right to sell the item or offer the service, and that the details — including price, condition, and photos — are accurate and your own.',
          'Prohibited: knowingly false listings, items or services banned by law (weapons, drugs, forged documents, and similar), listings posted in the wrong category, spam, and repeated duplicate postings.',
          'Every listing is reviewed by a moderator before it appears in the feed. We may reject a listing or remove a published one without explanation if it violates these terms — usually with a reason given, but we are not obligated to in every case.',
          'Changing the price, text, photos, or city sends the listing back for review.',
        ],
      },
      {
        h: '4. Deals between users',
        p: [
          'PLONK connects buyers and sellers; it is not a party to the deal. We are not involved in payment, delivery, or handover, and we are not responsible for item quality, whether agreements are honored, or other users\u2019 actions.',
          'Inspect the item before paying, meet in public places, and be cautious about prepaying strangers — ordinary caution for any classifieds marketplace.',
        ],
      },
      {
        h: '5. Chat, reviews, reports',
        p: [
          'In-app chat is for discussing a specific listing. Using it to advertise unrelated services, send bulk messages, or harass others is not allowed.',
          'You can block a specific person from messaging you — this block doesn\u2019t apply to actions taken by the administration.',
          'A review can only be left after real contact about a listing. We don\u2019t edit review content except for clear violations (harassment, third-party personal data, spam).',
          'Reports on a listing or a user are reviewed manually. Filing false mass reports is also a violation of these terms.',
        ],
      },
      {
        h: '6. Account suspension',
        p: [
          'We may restrict or suspend an account for violating these terms, repeated substantiated reports, or attempts to bypass moderation. Decisions can be appealed through support.',
        ],
      },
      {
        h: '7. Liability',
        p: [
          'The service is provided \u201cas is.\u201d We try to keep it running smoothly but don\u2019t guarantee uninterrupted operation and aren\u2019t liable for losses arising from outages, other users\u2019 actions, or listing content.',
        ],
      },
      {
        h: '8. Changes to these terms',
        p: [
          'We may update these terms — the date at the top shows the last change. Continuing to use the service after changes means you accept the new version.',
        ],
      },
      {
        h: '9. Contact us',
        p: [
          `For any questions about these terms — through the support section in the app or at ${CONTACT_EMAIL}.`,
        ],
      },
    ],
  },

  sr: {
    title: 'Uslovi korišćenja',
    updated: 'Ažurirano: 27. avgust 2026.',
    sections: [
      {
        h: '1. Šta je PLONK',
        p: [
          'PLONK (plonk.rs) je sajt oglasa za Srbiju: fizička lica i firme postavljaju oglase za prodaju stvari, nekretnina, usluga i ostalog, a kupci ih pronalaze i kontaktiraju prodavca preko ugrađenog ćaskanja.',
          'Deo oglasa se postavlja direktno na sajtu, deo preko našeg Telegram bota, a deo se prenosi iz javnih Telegram grupa za oglase uz saglasnost administracije tih grupa.',
        ],
      },
      {
        h: '2. Ko može da koristi servis',
        p: [
          'Servis je namenjen punoletnim licima. Kreiranjem naloga potvrđujete da imate najmanje 18 godina.',
          'Za prijavu je potreban email ili Telegram. Provera ličnog dokumenta je dobrovoljna, preko spoljnog partnera; oznaka „Proveren korisnik" potvrđuje da iza naloga stoji konkretna, stvarno proverena osoba.',
          'Nalog je lični i neprenosiv: prodaja, poklanjanje ili na drugi način prenošenje drugoj osobi nije dozvoljeno, čak i ako nalog već ima oznaku „Proveren korisnik" ili istoriju recenzija. Zadržavamo pravo da u bilo kom trenutku zatražimo ponovnu potvrdu identiteta — ako ne bude izvršena, oznaka se uklanja.',
        ],
      },
      {
        h: '3. Oglasi',
        p: [
          'Objavljivanjem oglasa potvrđujete da imate pravo da prodate navedenu stvar ili ponudite uslugu, i da su podaci u oglasu tačni — uključujući cenu, stanje i fotografije (vaše, ne tuđe).',
          'Zabranjeno je: svesno lažni oglasi, roba i usluge zabranjene zakonom (oružje, droga, falsifikovana dokumenta i slično), oglasi postavljeni u pogrešnu kategoriju, spam i ponovljeno objavljivanje istog oglasa.',
          'Svaki oglas prolazi proveru moderatora pre nego što se pojavi u listi. Zadržavamo pravo da odbijemo oglas ili uklonimo već objavljeni bez obrazloženja ako krši ove uslove — obično uz naznaku razloga, ali nismo u obavezi da to činimo u svakom slučaju.',
          'Izmena cene, teksta, fotografija ili grada vraća oglas na ponovnu proveru.',
        ],
      },
      {
        h: '4. Poslovi između korisnika',
        p: [
          'PLONK povezuje kupca i prodavca, ali nije strana u poslu. Ne učestvujemo u plaćanju, dostavi ili predaji stvari i ne odgovaramo za kvalitet robe, poštovanje dogovora ili postupke drugih korisnika.',
          'Proverite stvar pre plaćanja, sastajte se na javnim mestima, budite oprezni sa avansnim plaćanjem nepoznatim ljudima — uobičajena opreznost na svakoj pijaci polovnih stvari.',
        ],
      },
      {
        h: '5. Ćaskanje, recenzije, prijave',
        p: [
          'Ćaskanje u aplikaciji služi za razgovor o konkretnom oglasu. Nije dozvoljeno korišćenje za reklamiranje nepovezanih usluga, masovne poruke ili uvrede.',
          'Možete blokirati određenu osobu da vam piše — ova blokada se ne odnosi na odluke administracije.',
          'Recenziju je moguće ostaviti samo nakon stvarnog kontakta povodom oglasa. Sadržaj recenzija ne menjamo osim kod očiglednih kršenja (uvrede, lični podaci trećih lica, spam).',
          'Prijava oglasa ili korisnika se razmatra ručno. Lažne masovne prijave takođe predstavljaju kršenje ovih uslova.',
        ],
      },
      {
        h: '6. Blokiranje naloga',
        p: [
          'Zadržavamo pravo da ograničimo ili blokiramo nalog zbog kršenja ovih uslova, više osnovanih prijava ili pokušaja zaobilaženja moderacije. Odluka se može osporiti preko podrške.',
        ],
      },
      {
        h: '7. Odgovornost',
        p: [
          'Servis se pruža „kakav jeste". Trudimo se da ga održavamo u ispravnom stanju, ali ne garantujemo neprekidan rad i ne odgovaramo za štetu nastalu usled prekida rada, postupaka drugih korisnika ili sadržaja oglasa.',
        ],
      },
      {
        h: '8. Izmene uslova',
        p: [
          'Ove uslove možemo ažurirati — datum na vrhu stranice pokazuje poslednju izmenu. Nastavak korišćenja servisa nakon izmena znači da prihvatate novu verziju.',
        ],
      },
      {
        h: '9. Kontakt',
        p: [
          `Za sva pitanja o uslovima — preko odeljka za podršku u aplikaciji ili na ${CONTACT_EMAIL}.`,
        ],
      },
    ],
  },
}

export const PRIVACY = {
  ru: {
    title: 'Политика конфиденциальности',
    updated: 'Обновлено: 27 августа 2026',
    sections: [
      {
        h: '1. Какие данные мы собираем',
        p: [
          'При регистрации: email или Telegram-аккаунт, имя, которое вы указали, необязательно — телефон, фото профиля, название и данные компании для деловых продавцов.',
          'При использовании сервиса: объявления и фотографии к ним, сообщения в чате с другими пользователями, отзывы, жалобы, избранные объявления, сохранённые поисковые запросы.',
          'Технически: IP-адрес, случайный id устройства (заводит браузер, хранится у вас, не отпечаток в строгом смысле) и приблизительные страна/город по IP — при каждом входе, для защиты от злоупотреблений: например, чтобы заметить, если аккаунт внезапно стал использоваться с совершенно другого устройства и из другой страны разом.',
        ],
      },
      {
        h: '2. Зачем нам эти данные',
        p: [
          'Чтобы сервис вообще работал: показать объявление, доставить сообщение в чат, прислать код для входа, уведомить о решении по объявлению.',
          'Чтобы бороться со злоупотреблениями: спамом, мошенническими объявлениями, повторной регистрацией заблокированных.',
          'Мы не продаём личные данные третьим лицам и не используем их для рекламы вне самого сервиса.',
        ],
      },
      {
        h: '3. Кому данные видны',
        p: [
          'Другим пользователям видны: имя, фото профиля, объявления, отзывы о вас, рейтинг. Телефон и email не показываются другим пользователям — общение идёт через встроенный чат, если вы сами не решите поделиться контактом в переписке.',
          'Модераторам сервиса — данные, нужные для проверки объявлений и разбора жалоб.',
        ],
      },
      {
        h: '4. Внешние сервисы',
        p: [
          'Для отправки писем (код входа, уведомления) мы используем стороннего почтового провайдера (Resend) — ему передаётся адрес получателя и текст письма.',
          'Для входа и части объявлений используется Telegram — при входе через бота мы получаем от Telegram ваш идентификатор и имя профиля, которые вы сами сделали доступными боту.',
        ],
      },
      {
        h: '5. Хранение и удаление',
        p: [
          'Данные хранятся, пока учётная запись активна и ещё некоторое время после удаления — для разбора возможных споров и жалоб, поданных до удаления.',
          'Вы можете запросить удаление аккаунта и данных через поддержку. Отзывы и переписка, где участвует другой человек, могут сохраняться в его копии данных даже после удаления вашей учётной записи.',
        ],
      },
      {
        h: '6. Технические данные на устройстве',
        p: [
          'Мы храним на вашем устройстве токен входа (чтобы не спрашивать код каждый раз), выбранный язык интерфейса и список недавних поисковых запросов — локально, не на сервере. Их можно очистить, выйдя из аккаунта или очистив данные сайта в браузере.',
        ],
      },
      {
        h: '7. Ваши права',
        p: [
          'Вы можете посмотреть и изменить свои данные в разделе профиля, а также запросить их полное удаление через поддержку. Мы отвечаем на такие запросы в разумный срок.',
        ],
      },
      {
        h: '8. Изменения политики',
        p: [
          'Мы можем обновлять этот документ — дата наверху страницы показывает последнее изменение.',
        ],
      },
      {
        h: '9. Связь с нами',
        p: [
          `По вопросам обработки персональных данных — через поддержку в приложении или на ${CONTACT_EMAIL}.`,
        ],
      },
    ],
  },

  en: {
    title: 'Privacy Policy',
    updated: 'Updated: August 27, 2026',
    sections: [
      {
        h: '1. What data we collect',
        p: [
          'On sign-up: your email or Telegram account, the name you provide, optionally a phone number, a profile photo, and company details for business sellers.',
          'While using the service: your listings and their photos, chat messages with other users, reviews, reports, favorited listings, saved searches.',
          'Technically: IP address, a random device id (set by the browser, stored on your device, not a strict fingerprint) and an approximate country/city from the IP \u2014 on each sign-in, for abuse prevention: for example, to notice if an account suddenly starts being used from a completely different device and country at once.',
        ],
      },
      {
        h: '2. Why we need this data',
        p: [
          'To make the service work at all: show a listing, deliver a chat message, send a sign-in code, notify you about a decision on your listing.',
          'To fight abuse: spam, fraudulent listings, re-registration by blocked users.',
          'We don\u2019t sell personal data to third parties or use it for advertising outside the service itself.',
        ],
      },
      {
        h: '3. Who can see your data',
        p: [
          'Other users can see: your name, profile photo, listings, reviews about you, and rating. Your phone and email are not shown to other users — communication happens through the built-in chat, unless you choose to share contact details yourself.',
          'Moderators see the data needed to review listings and handle reports.',
        ],
      },
      {
        h: '4. Third-party services',
        p: [
          'To send emails (sign-in codes, notifications) we use a third-party email provider (Resend), which receives the recipient\u2019s address and the message text.',
          'Telegram is used for sign-in and some listings — when you sign in via the bot, we receive your Telegram ID and profile name, which you\u2019ve made available to the bot yourself.',
        ],
      },
      {
        h: '5. Retention and deletion',
        p: [
          'Data is kept while your account is active and for some time after deletion — to handle possible disputes or reports filed before deletion.',
          'You can request account and data deletion through support. Reviews and chat messages involving another person may remain in their copy of the data even after your account is deleted.',
        ],
      },
      {
        h: '6. Technical data on your device',
        p: [
          'We store a sign-in token on your device (so you don\u2019t have to enter a code every time), your chosen interface language, and a list of recent searches — locally, not on the server. You can clear these by signing out or clearing site data in your browser.',
        ],
      },
      {
        h: '7. Your rights',
        p: [
          'You can view and change your data in the profile section, and request full deletion through support. We respond to such requests within a reasonable time.',
        ],
      },
      {
        h: '8. Changes to this policy',
        p: [
          'We may update this document — the date at the top shows the last change.',
        ],
      },
      {
        h: '9. Contact us',
        p: [
          `For questions about personal data handling — through support in the app or at ${CONTACT_EMAIL}.`,
        ],
      },
    ],
  },

  sr: {
    title: 'Politika privatnosti',
    updated: 'Ažurirano: 27. avgust 2026.',
    sections: [
      {
        h: '1. Koje podatke prikupljamo',
        p: [
          'Prilikom registracije: vaš email ili Telegram nalog, ime koje navedete, opciono broj telefona, profilnu fotografiju, i podatke o firmi za poslovne prodavce.',
          'Tokom korišćenja servisa: vaše oglase i fotografije uz njih, poruke u ćaskanju sa drugim korisnicima, recenzije, prijave, omiljene oglase, sačuvane pretrage.',
          'Tehnički: IP adresu, nasumični id uređaja (postavlja pregledač, čuva se kod vas, nije otisak u strogom smislu) i približnu zemlju/grad po IP adresi — pri svakoj prijavi, radi zaštite od zloupotrebe: na primer, da primetimo ako se nalog odjednom počne koristiti sa potpuno drugog uređaja i iz druge zemlje istovremeno.',
        ],
      },
      {
        h: '2. Zašto su nam potrebni ovi podaci',
        p: [
          'Da bi servis uopšte radio: prikazali oglas, dostavili poruku u ćaskanju, poslali kod za prijavu, obavestili vas o odluci povodom oglasa.',
          'Da bismo se borili protiv zloupotrebe: spama, prevarnih oglasa, ponovne registracije blokiranih korisnika.',
          'Ne prodajemo lične podatke trećim licima niti ih koristimo za reklamiranje van samog servisa.',
        ],
      },
      {
        h: '3. Kome su podaci vidljivi',
        p: [
          'Drugim korisnicima su vidljivi: vaše ime, profilna fotografija, oglasi, recenzije o vama i ocena. Telefon i email se ne prikazuju drugim korisnicima — komunikacija ide preko ugrađenog ćaskanja, osim ako sami ne odlučite da podelite kontakt.',
          'Moderatorima servisa — podaci potrebni za proveru oglasa i rešavanje prijava.',
        ],
      },
      {
        h: '4. Spoljni servisi',
        p: [
          'Za slanje imejlova (kod za prijavu, obaveštenja) koristimo spoljnog dobavljača (Resend), kome se prosleđuje adresa primaoca i tekst poruke.',
          'Telegram se koristi za prijavu i deo oglasa — prilikom prijave preko bota, dobijamo vaš Telegram identifikator i ime profila, koje ste sami učinili dostupnim botu.',
        ],
      },
      {
        h: '5. Čuvanje i brisanje',
        p: [
          'Podaci se čuvaju dok je nalog aktivan i još neko vreme nakon brisanja — radi rešavanja mogućih sporova ili prijava podnetih pre brisanja.',
          'Brisanje naloga i podataka možete zatražiti preko podrške. Recenzije i poruke u ćaskanju koje uključuju drugu osobu mogu ostati u njenoj kopiji podataka i nakon brisanja vašeg naloga.',
        ],
      },
      {
        h: '6. Tehnički podaci na uređaju',
        p: [
          'Na vašem uređaju čuvamo token za prijavu (da ne biste svaki put unosili kod), izabrani jezik interfejsa i listu nedavnih pretraga — lokalno, ne na serveru. Možete ih obrisati odjavom ili brisanjem podataka sajta u pregledaču.',
        ],
      },
      {
        h: '7. Vaša prava',
        p: [
          'Svoje podatke možete pogledati i izmeniti u odeljku profila, a njihovo potpuno brisanje zatražiti preko podrške. Na takve zahteve odgovaramo u razumnom roku.',
        ],
      },
      {
        h: '8. Izmene politike',
        p: [
          'Ovaj dokument možemo ažurirati — datum na vrhu stranice pokazuje poslednju izmenu.',
        ],
      },
      {
        h: '9. Kontakt',
        p: [
          `Za pitanja o obradi ličnih podataka — preko podrške u aplikaciji ili na ${CONTACT_EMAIL}.`,
        ],
      },
    ],
  },
}

// Правила размещения — что можно и нельзя выкладывать, каким должно
// быть само объявление. Отдельно от Условий использования (там —
// про аккаунт и площадку в целом), здесь — конкретно про содержимое.
export const RULES = {
  ru: {
    title: 'Правила размещения',
    updated: 'Обновлено: 28 августа 2026',
    sections: [
      {
        h: '1. Что нельзя размещать',
        p: [
          'Всё, что запрещено к обороту законом Сербии: оружие и боеприпасы без исключений, наркотики и любые вещества, имитирующие их эффект, поддельные документы, деньги и ценные бумаги, ворованные или полученные обманом вещи.',
          'Товары и услуги, требующие лицензии, которой у вас нет — рецептурные лекарства, финансовые и страховые услуги, азартные игры.',
          'Контент сексуального характера, услуги интимного характера под любым прикрытием, финансовые пирамиды и схемы «приведи друга — получи процент».',
          'Живые животные — можно искать новый дом бесплатно, но не продавать: этот раздел не про зоомагазин.',
          'Подделки под известные бренды, если это прямо заявлено или очевидно из фото и описания.',
        ],
      },
      {
        h: '2. Одно объявление — одна вещь',
        p: [
          'Если продаёте несколько разных вещей, на каждую — своё объявление, не список всего сразу в одном. Исключение — если это действительно единый комплект (сервиз, комплект мебели), который логично продать целиком.',
          'Дублировать одно и то же объявление в нескольких категориях или создавать его заново вместо того, чтобы поднять существующее — тоже не по правилам, для этого есть платное поднятие в поиске.',
        ],
      },
      {
        h: '3. Фото и описание',
        p: [
          'Фотографии — свои, самой вещи, а не найденные в интернете или взятые с сайта производителя. Исключение — если вещь ещё не куплена и это честно указано в описании.',
          'Категория выбирается по смыслу объявления, не по тому, где больше просмотров. Если сомневаетесь, ближе к тому, что человек будет искать этими словами.',
          'Цена и состояние — реальные на момент публикации. «Торг» и «цена не указана» — не повод писать заведомо заниженную цифру ради внимания.',
        ],
      },
      {
        h: '4. Продвижение не отменяет эти правила',
        p: [
          'Платное продвижение (поднятие в поиске, выделение цветом, крупная карточка) увеличивает заметность уже опубликованного объявления — оно всё равно должно соответствовать правилам выше, модерация проверяет одинаково и платные, и бесплатные объявления.',
          'Бизнес-аккаунт (после проверки личности) даёт видимый значок «Компания» и увеличенный лимит объявлений — но не освобождает от этих же правил.',
        ],
      },
      {
        h: '5. Что происходит при нарушении',
        p: [
          'Объявление, не прошедшее проверку, отклоняется с указанием причины — можно поправить и отправить заново. Уже опубликованное, но нарушающее правила, может быть снято без предупреждения.',
          'Жалобу на конкретное объявление или продавца можно оставить прямо на странице объявления или в профиле продавца — рассматривается вручную, не автоматически.',
          'Повторные или грубые нарушения ведут к ограничению или блокировке аккаунта — подробнее в Условиях использования.',
        ],
      },
    ],
  },

  en: {
    title: 'Posting Rules',
    updated: 'Updated: August 28, 2026',
    sections: [
      {
        h: '1. What you cannot post',
        p: [
          'Anything illegal under Serbian law: weapons and ammunition without exception, drugs and substances mimicking their effect, forged documents, money, or securities, stolen or fraudulently obtained items.',
          'Goods and services that require a license you don\u2019t have \u2014 prescription medication, financial and insurance services, gambling.',
          'Sexual content, services of an intimate nature under any label, financial pyramids and \u201crefer a friend for a cut\u201d schemes.',
          'Live animals \u2014 rehoming for free is fine, selling is not: this section isn\u2019t a pet store.',
          'Counterfeits of known brands, when stated outright or obvious from the photos and description.',
        ],
      },
      {
        h: '2. One listing, one item',
        p: [
          'If you\u2019re selling several different things, each gets its own listing, not one combined list. Exception: a genuine matching set (a dinner service, a furniture set) that makes sense to sell as one.',
          'Duplicating the same listing across categories, or re-creating it instead of bumping the existing one, isn\u2019t allowed either \u2014 that\u2019s what paid bump-to-top is for.',
        ],
      },
      {
        h: '3. Photos and description',
        p: [
          'Photos should be your own, of the actual item \u2014 not pulled from the internet or a manufacturer\u2019s site. Exception: if the item isn\u2019t in hand yet and the listing says so honestly.',
          'Pick the category that matches what the listing actually is, not whichever gets more views. When unsure, go with what a buyer would search for.',
          'Price and condition should be accurate at the time of posting. \u201cNegotiable\u201d or \u201cno price\u201d isn\u2019t a license to post a deliberately misleading number for attention.',
        ],
      },
      {
        h: '4. Promotion doesn\u2019t override these rules',
        p: [
          'Paid promotion (bump to top, color highlight, large card) makes an already-published listing more visible \u2014 it still has to follow the rules above; moderation checks paid and free listings the same way.',
          'A business account (after identity verification) shows a visible \u201cBusiness\u201d badge and a higher listing limit \u2014 it doesn\u2019t exempt you from these same rules.',
        ],
      },
      {
        h: '5. What happens if you break them',
        p: [
          'A listing that fails review is rejected with a reason \u2014 fix it and resubmit. An already-published listing that turns out to break the rules can be taken down without warning.',
          'You can report a specific listing or seller right from the listing page or the seller\u2019s profile \u2014 reports are reviewed by a person, not automatically.',
          'Repeated or serious violations lead to account restrictions or a ban \u2014 see the Terms of Use for details.',
        ],
      },
    ],
  },

  sr: {
    title: 'Pravila oglašavanja',
    updated: 'Ažurirano: 28. avgust 2026',
    sections: [
      {
        h: '1. Šta ne smete da objavite',
        p: [
          'Sve što je zakonom Srbije zabranjeno u prometu: oružje i municiju bez izuzetka, drogu i supstance koje imitiraju njeno dejstvo, falsifikovana dokumenta, novac ili hartije od vrednosti, ukradene ili prevarom stečene stvari.',
          'Robu i usluge koje zahtevaju dozvolu koju nemate \u2014 lekove na recept, finansijske i osiguravajuće usluge, igre na sreću.',
          'Sadržaj seksualne prirode, intimne usluge pod bilo kojim izgovorom, finansijske piramide i šeme \u201epreporuči prijatelja za procenat\u201c.',
          'Žive životinje \u2014 besplatno udomljavanje je u redu, prodaja nije: ovaj odeljak nije zoo prodavnica.',
          'Falsifikate poznatih brendova, kada je to izričito navedeno ili očigledno sa fotografija i opisa.',
        ],
      },
      {
        h: '2. Jedan oglas \u2014 jedna stvar',
        p: [
          'Ako prodajete više različitih stvari, svaka dobija svoj oglas, ne spisak svega u jednom. Izuzetak \u2014 kada je reč o pravom kompletu (servis, komplet nameštaja) koji ima smisla prodati kao celinu.',
          'Dupliranje istog oglasa u više kategorija, ili ponovno kreiranje umesto podizanja postojećeg, takođe nije dozvoljeno \u2014 za to postoji plaćeno podizanje u pretrazi.',
        ],
      },
      {
        h: '3. Fotografije i opis',
        p: [
          'Fotografije treba da budu vaše, same stvari \u2014 ne preuzete sa interneta ili sajta proizvođača. Izuzetak \u2014 ako stvar još nije nabavljena i to je pošteno navedeno u opisu.',
          'Kategoriju birajte prema suštini oglasa, ne prema tome gde ima više pregleda. Ako niste sigurni, birajte ono što bi kupac tražio tim rečima.',
          'Cena i stanje treba da budu tačni u trenutku objave. \u201eCena po dogovoru\u201c ili \u201ecena nije navedena\u201c nije razlog da upišete namerno pogrešan broj radi pažnje.',
        ],
      },
      {
        h: '4. Izdvajanje ne ukida ova pravila',
        p: [
          'Plaćeno izdvajanje (podizanje u pretrazi, isticanje bojom, velika kartica) čini već objavljen oglas vidljivijim \u2014 i dalje mora da poštuje pravila iznad, moderacija proverava plaćene i besplatne oglase na isti način.',
          'Poslovni nalog (posle provere identiteta) dobija vidljivu oznaku \u201eKompanija\u201c i veći limit oglasa \u2014 ne oslobađa vas ovih istih pravila.',
        ],
      },
      {
        h: '5. Šta sledi u slučaju kršenja',
        p: [
          'Oglas koji ne prođe proveru se odbija uz razlog \u2014 možete ga ispraviti i ponovo poslati. Već objavljen oglas koji krši pravila može biti uklonjen bez upozorenja.',
          'Prijavu konkretnog oglasa ili prodavca možete poslati direktno sa stranice oglasa ili profila prodavca \u2014 prijave pregleda osoba, ne automatski.',
          'Ponovljena ili ozbiljna kršenja vode ograničenju ili blokiranju naloga \u2014 detaljnije u Uslovima korišćenja.',
        ],
      },
    ],
  },
}
