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
          'Для входа нужен email или Telegram — мы не проверяем личность документально, кроме добровольной проверки телефона и компании для деловых продавцов.',
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
          'Signing in requires an email or Telegram — we don\u2019t verify identity by documents, apart from optional phone and business verification for business sellers.',
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
          'Za prijavu je potreban email ili Telegram — ne proveravamo identitet dokumentima, osim dobrovoljne provere telefona i firme za poslovne prodavce.',
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
          'Технически: IP-адрес и данные браузера в служебных журналах сервера — для защиты от злоупотреблений, без сопоставления с личностью в обычном режиме.',
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
          'Technically: IP address and browser data in server logs — for abuse prevention, not normally matched to your identity.',
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
          'Tehnički: IP adresu i podatke pregledača u serverskim zapisima — radi zaštite od zloupotrebe, obično bez povezivanja sa identitetom.',
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
