/**
 * Короткая строка характеристик на карточке — «2-комн., 45 м², 3/9 эт.»,
 * «2020 г., 45 000 км». Раньше заполненные при публикации параметры
 * никуда не попадали дальше формы: ни на карточку, ни в ленту — человек
 * их вводил, а толку с них не было никакого.
 *
 * Список полей и порядок — по подразделу (у квартиры «этаж», у дома его
 * не показываем — там своя площадь дома и участка). Раздел без записи
 * тут — карточка просто не показывает вторую строку, как было раньше.
 */

const NBSP = '\u00A0'

function fmtNum(n) {
  if (n === null || n === undefined || n === '') return null
  const num = Number(n)
  if (Number.isNaN(num)) return null
  return num.toLocaleString('ru-RU')
}

// { ru, en, sr } — валюты в атрибутах нет, поэтому просто слова, не formatPrice
const CARD_META = {
  flats: (a, t) => {
    const parts = []
    // «studio» — не число: «Студия», а не «studio-комн.»
    if (a.rooms) parts.push(a.rooms === 'studio' ? t('card.studio') : `${a.rooms}-${t('card.rooms_short')}`)
    if (a.area_m2) parts.push(`${fmtNum(a.area_m2)}${NBSP}${t('card.sqm')}`)
    if (a.floor) parts.push(a.total_floors ? `${a.floor}/${a.total_floors}${NBSP}${t('card.floor_short')}` : `${a.floor}${NBSP}${t('card.floor_short')}`)
    return parts
  },
  houses: (a, t) => {
    const parts = []
    if (a.area_m2) parts.push(`${fmtNum(a.area_m2)}${NBSP}${t('card.sqm')}`)
    if (a.land_area_sotka) parts.push(`${fmtNum(a.land_area_sotka)}${NBSP}${t('card.sotka')}`)
    return parts
  },
  rooms: (a, t) => {
    const parts = []
    if (a.area_m2) parts.push(`${fmtNum(a.area_m2)}${NBSP}${t('card.sqm')}`)
    return parts
  },
  commercial: (a, t) => {
    const parts = []
    if (a.area_m2) parts.push(`${fmtNum(a.area_m2)}${NBSP}${t('card.sqm')}`)
    return parts
  },
  garages: (a, t) => {
    const parts = []
    if (a.area_m2) parts.push(`${fmtNum(a.area_m2)}${NBSP}${t('card.sqm')}`)
    return parts
  },
  cars: (a, t) => {
    const parts = []
    if (a.year) parts.push(`${a.year}${NBSP}${t('card.year_short')}`)
    if (a.mileage_km) parts.push(`${fmtNum(a.mileage_km)}${NBSP}${t('card.km')}`)
    return parts
  },
  moto: (a, t) => {
    const parts = []
    if (a.year) parts.push(`${a.year}${NBSP}${t('card.year_short')}`)
    if (a.mileage_km) parts.push(`${fmtNum(a.mileage_km)}${NBSP}${t('card.km')}`)
    return parts
  },
  trucks: (a, t) => {
    const parts = []
    if (a.year) parts.push(`${a.year}${NBSP}${t('card.year_short')}`)
    if (a.mileage_km) parts.push(`${fmtNum(a.mileage_km)}${NBSP}${t('card.km')}`)
    return parts
  },
  phones: (a, t) => (a.storage_gb ? [`${a.storage_gb}${NBSP}${t('card.gb')}`] : []),
  tablets: (a, t) => (a.storage_gb ? [`${a.storage_gb}${NBSP}${t('card.gb')}`] : []),
  laptops: (a, t) => {
    const parts = []
    if (a.ram_gb) parts.push(`${a.ram_gb}${NBSP}${t('card.gb')}`)
    if (a.storage_gb) parts.push(`${a.storage_gb}${NBSP}${t('card.gb')}`)
    return parts
  },
}

export function cardMeta(categorySlug, attributes, t) {
  const fn = CARD_META[categorySlug]
  if (!fn || !attributes) return null
  const parts = fn(attributes, t).filter(Boolean)
  return parts.length ? parts.join(' · ') : null
}
