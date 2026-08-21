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

// В объявлениях город может быть сохранён как угодно (введён вручную, пришёл из старых данных).
// Пробуем сопоставить со справочником, иначе показываем как есть.
export function displayCity(value, lang = 'ru') {
  if (!value) return ''
  const found = CITIES.find(
    (c) => c.slug === value || [c.ru, c.en, c.sr].some((n) => n.toLowerCase() === String(value).toLowerCase())
  )
  return found ? (found[lang] || found.ru) : value
}
