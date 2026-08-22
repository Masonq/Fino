// Города Сербии: у каждого своё написание на кириллице (RU/SR-cyr) и латинице (EN/SR-lat).
// Ключ (slug) — то, что уходит в базу и в фильтры, чтобы поиск не зависел от языка интерфейса.
export const CITIES = [
  { slug: 'beograd',    ru: 'Белград',    en: 'Belgrade',    sr: 'Beograd' },
  { slug: 'novi-sad',   ru: 'Нови-Сад',   en: 'Novi Sad',    sr: 'Novi Sad' },
  { slug: 'nis',        ru: 'Ниш',        en: 'Niš',         sr: 'Niš' },
  { slug: 'kragujevac', ru: 'Крагуевац',  en: 'Kragujevac',  sr: 'Kragujevac' },
  { slug: 'subotica',   ru: 'Суботица',   en: 'Subotica',    sr: 'Subotica' },
  { slug: 'zrenjanin',  ru: 'Зренянин',   en: 'Zrenjanin',   sr: 'Zrenjanin' },
  { slug: 'pancevo',    ru: 'Панчево',    en: 'Pančevo',     sr: 'Pančevo' },
  { slug: 'cacak',      ru: 'Чачак',      en: 'Čačak',       sr: 'Čačak' },
  { slug: 'novi-pazar', ru: 'Нови-Пазар', en: 'Novi Pazar',  sr: 'Novi Pazar' },
  { slug: 'kraljevo',   ru: 'Кралево',    en: 'Kraljevo',    sr: 'Kraljevo' },
]

export function cityLabel(slug, lang = 'ru') {
  const city = CITIES.find((c) => c.slug === slug)
  if (!city) return slug || ''
  return city[lang] || city.ru
}

// Сербская кириллица: города приходят и в ней тоже — из старых данных,
// из ручного ввода, из внешних источников. «Београд» не совпадал ни с
// одним написанием в справочнике и показывался как есть, из-за чего на
// английской странице город оставался кириллицей.
const CYR_TO_LAT = {
  'љ': 'lj', 'њ': 'nj', 'џ': 'dz', 'ђ': 'd', 'ћ': 'c', 'ж': 'z', 'ч': 'c', 'ш': 's',
  'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'з': 'z', 'и': 'i',
  'ј': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
  'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ы': 'i', 'э': 'e',
  'ю': 'u', 'я': 'a', 'й': 'i', 'щ': 's', 'ъ': '', 'ь': '',
}

// Приводим написание к общему виду: строчные, без диакритики и разделителей,
// кириллица переложена в латиницу. «Београд», «Белград», «Beograd» и
// «beograd» дают одно и то же.
function fold(value) {
  return String(value)
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .split('').map((ch) => (ch in CYR_TO_LAT ? CYR_TO_LAT[ch] : ch)).join('')
    .replace(/[^a-z]/g, '')
}

// В объявлениях город может быть сохранён как угодно (введён вручную, пришёл из старых данных).
// Пробуем сопоставить со справочником, иначе показываем как есть.
export function displayCity(value, lang = 'ru') {
  if (!value) return ''
  const key = fold(value)
  const found = CITIES.find(
    (c) => fold(c.slug) === key || [c.ru, c.en, c.sr].some((n) => fold(n) === key)
  )
  return found ? (found[lang] || found.ru) : value
}
