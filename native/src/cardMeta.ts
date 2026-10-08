/**
 * Короткая строка характеристик на карточке — «2-комн. · 45 м² · 3/9 эт.», «2020 г. · 45 000 км» — как на сайте
 * (frontend/src/data/cardMeta.js). Раздел без записи — второй строки нет.
 */
import { tr } from './i18n'

const NB = '\u00A0'
const num = (n: unknown) => { const x = Number(n); return n === null || n === undefined || n === '' || Number.isNaN(x) ? null : x.toLocaleString('ru-RU') }
type A = Record<string, unknown>
const area = (a: A) => (a.area_m2 ? [`${num(a.area_m2)}${NB}м²`] : [])
const yearKm = (a: A) => [a.year ? `${a.year}${NB}${tr('г.')}` : '', a.mileage_km ? `${num(a.mileage_km)}${NB}${tr('км')}` : '']

const META: Record<string, (a: A) => string[]> = {
  flats: (a) => [a.rooms ? (a.rooms === 'studio' ? tr('Студия') : `${a.rooms}-${tr('комн.')}`) : '', ...area(a),
    a.floor ? (a.total_floors ? `${a.floor}/${a.total_floors}${NB}${tr('эт.')}` : `${a.floor}${NB}${tr('эт.')}`) : ''],
  houses: (a) => [...area(a), a.land_area_sotka ? `${num(a.land_area_sotka)}${NB}${tr('сот.')}` : ''],
  rooms: area, commercial: area, garages: area,
  cars: yearKm, moto: yearKm, trucks: yearKm,
  phones: (a) => (a.storage_gb ? [`${a.storage_gb}${NB}${tr('ГБ')}`] : []),
  tablets: (a) => (a.storage_gb ? [`${a.storage_gb}${NB}${tr('ГБ')}`] : []),
  laptops: (a) => [a.ram_gb ? `${a.ram_gb}${NB}${tr('ГБ')}` : '', a.storage_gb ? `${a.storage_gb}${NB}${tr('ГБ')}` : ''],
}

export function cardMeta(slug?: string | null, attrs?: A | null): string | null {
  const fn = slug ? META[slug] : undefined
  if (!fn || !attrs) return null
  const parts = fn(attrs).filter(Boolean)
  return parts.length ? parts.join(' · ') : null
}
