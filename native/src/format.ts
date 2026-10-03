import { getLang, type Lang, tr } from './i18n'

/** Цена, даты и города — как на сайте. */
// Названия городов на трёх языках — как в справочнике сайта (data/cities.js)
const CITIES: Record<string, Record<Lang, string>> = {
  'beograd': { ru: 'Белград', en: 'Belgrade', sr: 'Beograd' },
  'novi-sad': { ru: 'Нови-Сад', en: 'Novi Sad', sr: 'Novi Sad' },
  'nis': { ru: 'Ниш', en: 'Niš', sr: 'Niš' },
  'kragujevac': { ru: 'Крагуевац', en: 'Kragujevac', sr: 'Kragujevac' },
  'subotica': { ru: 'Суботица', en: 'Subotica', sr: 'Subotica' },
  'zrenjanin': { ru: 'Зренянин', en: 'Zrenjanin', sr: 'Zrenjanin' },
  'pancevo': { ru: 'Панчево', en: 'Pančevo', sr: 'Pančevo' },
  'cacak': { ru: 'Чачак', en: 'Čačak', sr: 'Čačak' },
  'novi-pazar': { ru: 'Нови-Пазар', en: 'Novi Pazar', sr: 'Novi Pazar' },
  'kraljevo': { ru: 'Кралево', en: 'Kraljevo', sr: 'Kraljevo' },
}

/** Города для выбора — в том же порядке, что на сайте. */
export const cityList = () => Object.entries(CITIES).map(([slug, names]) => ({ slug, label: names[getLang()] }))

export function cityName(slug?: string | null): string {
  if (!slug) return ''
  return CITIES[slug]?.[getLang()] ?? slug
}

/** Сервер отдаёт время без часового пояса — это UTC. */
export function parseTime(iso?: string | null): Date | null {
  if (!iso) return null
  const withZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`
  const d = new Date(withZone)
  return Number.isNaN(d.getTime()) ? null : d
}

export function isFresh(iso?: string | null): boolean {
  const d = parseTime(iso)
  return !!d && Date.now() - d.getTime() < 24 * 3600 * 1000
}

const MONTHS: Record<Lang, string[]> = {
  ru: ['янв.', 'февр.', 'марта', 'апр.', 'мая', 'июня', 'июля', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  sr: ['jan.', 'feb.', 'mar.', 'apr.', 'maj', 'jun', 'jul', 'avg.', 'sep.', 'okt.', 'nov.', 'dec.'],
}
const MONTHS_GEN: Record<Lang, string[]> = {
  ru: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'],
  en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
  sr: ['januara', 'februara', 'marta', 'aprila', 'maja', 'juna', 'jula', 'avgusta', 'septembra', 'oktobra', 'novembra', 'decembra'],
}

/** «сентября 2026» / «September 2026» / «septembra 2026» — для «На PLONK с …». */
export function monthYear(d: Date): string {
  return `${MONTHS_GEN[getLang()][d.getMonth()]} ${d.getFullYear()}`
}

/** «сегодня», «вчера», «3 дн. назад» или «9 сент.» — как подписи в ленте сайта. */
export function relTime(iso?: string | null): string {
  const d = parseTime(iso)
  if (!d) return ''
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((startOf(new Date()) - startOf(d)) / 86400000)
  if (days <= 0) return tr('сегодня')
  if (days === 1) return tr('вчера')
  if (days < 7) return tr('{n} дн. назад', { n: days })
  return getLang() === 'en' ? `${MONTHS.en[d.getMonth()]} ${d.getDate()}` : `${d.getDate()} ${MONTHS[getLang()][d.getMonth()]}`
}

/** «6 000 RSD», «250 €», «Даром», «Цена не указана». Тысячи — через неразрывный пробел. */
export function formatPrice(price: number | null | undefined, currency?: string | null, isFree?: boolean): string {
  if (isFree) return tr('Даром')
  if (price == null) return tr('Цена не указана')
  const n = Math.round(Number(price))
  const grouped = String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')
  return currency === 'EUR' ? `${grouped}\u00A0€` : `${grouped}\u00A0${currency || 'RSD'}`
}

/** Текст без разметки (служебные письма команды пишутся с «#», «**», «_») — для превью и пузырей. */
export function plainText(text?: string | null): string {
  return (text ?? '').replace(/^#{1,6}\s*/gm, '').replace(/\*\*|__|`/g, '').replace(/\s+\n/g, '\n').trim()
}

/** Короткое время для списка переписок — как на сайте: «14:05» сегодня, «вчера», «3 дн», дальше дата. */
export function shortTime(iso?: string | null): string {
  const d = parseTime(iso)
  if (!d) return ''
  const now = new Date()
  const start = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((start(now) - start(d)) / 86400000)
  if (days <= 0) return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (days === 1) return tr('вчера')
  if (days < 7) return tr('{n} дн', { n: days })
  return getLang() === 'en' ? `${MONTHS.en[d.getMonth()]} ${d.getDate()}` : `${d.getDate()} ${MONTHS[getLang()][d.getMonth()]}`
}

