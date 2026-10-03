/** Цена, даты и города — как на сайте. */
const CITIES: Record<string, string> = {
  beograd: 'Белград', 'novi-sad': 'Нови-Сад', nis: 'Ниш', kragujevac: 'Крагуевац', subotica: 'Суботица',
  zrenjanin: 'Зренянин', pancevo: 'Панчево', cacak: 'Чачак', 'novi-pazar': 'Нови-Пазар', kraljevo: 'Кралево',
}

/** Города для выбора — в том же порядке, что на сайте. */
export const CITY_LIST = Object.entries(CITIES).map(([slug, label]) => ({ slug, label }))

export function cityName(slug?: string | null): string {
  if (!slug) return ''
  return CITIES[slug] ?? slug
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

const MONTHS = ['янв.', 'февр.', 'марта', 'апр.', 'мая', 'июня', 'июля', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.']

/** «сегодня», «вчера», «3 дн. назад» или «9 сент.» — как подписи в ленте сайта. */
export function relTime(iso?: string | null): string {
  const d = parseTime(iso)
  if (!d) return ''
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((startOf(new Date()) - startOf(d)) / 86400000)
  if (days <= 0) return 'сегодня'
  if (days === 1) return 'вчера'
  if (days < 7) return `${days} дн. назад`
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`
}

/** «6 000 RSD», «250 €», «Даром», «Цена не указана». Тысячи — через неразрывный пробел. */
export function formatPrice(price: number | null | undefined, currency?: string | null, isFree?: boolean): string {
  if (isFree) return 'Даром'
  if (price == null) return 'Цена не указана'
  const n = Math.round(Number(price))
  const grouped = String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')
  return currency === 'EUR' ? `${grouped}\u00A0€` : `${grouped}\u00A0${currency || 'RSD'}`
}

/** Текст без разметки (служебные письма команды пишутся с «#», «**», «_») — для превью и пузырей. */
export function plainText(text?: string | null): string {
  return (text ?? '').replace(/^#{1,6}\s*/gm, '').replace(/\*\*|__|`/g, '').replace(/\s+\n/g, '\n').trim()
}

