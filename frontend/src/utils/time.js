// Язык интерфейса → язык форматирования. Голый «sr» браузер понимает как
// кириллицу, и месяцы в сербском тексте на латинице выходили кириллицей
// («август 2026» посреди «Na PLONK-u od …»). Сербский на сайте всегда латиница.
const INTL = { ru: 'ru-RU', en: 'en-GB', sr: 'sr-Latn-RS' }
export const intlLocale = (lang) => INTL[lang] || lang || undefined

// Месяцы в родительном падеже — для фраз «с августа», «od avgusta». Стандартное
// форматирование даты отдаёт именительный («август 2026 г.») и читается как ошибка.
const MONTHS_OF = {
  ru: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'],
  sr: ['januara', 'februara', 'marta', 'aprila', 'maja', 'juna',
    'jula', 'avgusta', 'septembra', 'oktobra', 'novembra', 'decembra'],
}

// Сервер отдаёт UTC без пометки зоны: без «Z» браузер прочёл бы время как местное.
function parseServerDate(iso) {
  return new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
}

/**
 * «августа 2026» — месяц и год для фраз «На PLONK с …», «Здесь с …», «Na PLONK-u od …».
 * По-русски и по-сербски после предлога месяц в родительном падеже.
 */
export function sinceMonth(iso, lang) {
  if (!iso) return ''
  try {
    const d = parseServerDate(iso)
    const of = MONTHS_OF[lang]
    if (of) return `${of[d.getMonth()]} ${d.getFullYear()}`
    return d.toLocaleDateString(intlLocale(lang), { month: 'long', year: 'numeric' })
  } catch {
    return ''
  }
}

/**
 * «Сколько прошло» для дат с сервера.
 *
 * Сервер отдаёт время в UTC без пометки зоны, поэтому дописываем Z —
 * без этого браузер читал бы его как местное и промахивался на пару часов.
 */
export function timeAgo(iso, t, lang) {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso + 'Z').getTime()) / 1000
  if (diff < 60) return t('chats.just_now')
  if (diff < 3600) return `${Math.floor(diff / 60)} ${t('chats.min')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${t('chats.hour')}`
  const days = Math.floor(diff / 86400)
  if (days < 7) return `${days} ${t('chats.day')}`
  return new Date(iso + 'Z').toLocaleDateString(intlLocale(lang))
}

/**
 * Дата отзыва: месяц и год.
 *
 * Точный день ничего не решает, а вот свежий отзыв и трёхлетний — вес
 * у них разный, и без даты их было не отличить.
 */
export function monthYear(iso, lang) {
  if (!iso) return ''
  return new Date(iso + 'Z').toLocaleDateString(intlLocale(lang), { year: 'numeric', month: 'long' })
}

/**
 * «сегодня», «вчера», «3 дня назад» — как у Авито, вместо голой даты,
 * которую пришлось бы читать дольше, чем она того стоит. Раньше жила
 * только внутри ListingCard.jsx — теперь общая, использует её и
 * карточка объявления в ленте, и сама страница объявления.
 */
export function relativeDate(iso, t, lang) {
  if (!iso) return ''
  const d = new Date(iso)
  const days = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (days <= 0) return t('misc.date_today')
  if (days === 1) return t('misc.date_yesterday')
  if (days < 7) return t('misc.date_days_ago', { count: days })
  // Дальше недели — короткая дата «9 сент.», а не «09.09.2026»:
  // рядом с «вчера» полная дата с годом выглядела чужеродно и
  // читалась дольше. Год добавляем, только если он другой.
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return d.toLocaleDateString(intlLocale(lang), sameYear
    ? { day: 'numeric', month: 'short' }
    : { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Моложе суток — для метки «Новое» на карточке. */
export function isFresh(iso) {
  if (!iso) return false
  return Date.now() - new Date(iso).getTime() < 86400000
}

/**
 * «2 ч назад» или, если прошло больше недели, короткая дата «5 сент.».
 *
 * timeAgo() для давних дат отдаёт голую дату, и подпись «зарег.
 * 05.09.2026 назад» читалась как ошибка — потому что ею и была.
 */
export function since(iso, t, lang) {
  if (!iso) return ''
  const d = new Date(iso + 'Z')
  const days = (Date.now() - d.getTime()) / 86400000
  // «только что назад» — так не говорят: у «только что» своего «назад» нет.
  if (days * 86400 < 60) return t('chats.just_now')
  if (days < 7) return t('misc.ago', { when: timeAgo(iso, t, lang) })
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return d.toLocaleDateString(intlLocale(lang), sameYear
    ? { day: 'numeric', month: 'short' }
    : { day: 'numeric', month: 'short', year: 'numeric' })
}
