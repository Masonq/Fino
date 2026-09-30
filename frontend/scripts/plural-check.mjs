// Формы множественного числа: проверка настоящим i18next, тем же, что на сайте.
//   node scripts/plural-check.mjs         печатает найденное; код выхода 1, если есть что чинить
//
// Ключ считается «счётным», если у него есть хотя бы две разные формы (_one и _other, ...):
// одинокие «..._other» (в смысле «другой») и «..._one» («один») — не множественное число.
// Для каждого счётного ключа подставляем типичные числа языка и смотрим, не осталось ли дыры.
import i18next from 'i18next'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const LOC = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src', 'i18n', 'locales')
const COUNTS = { ru: [0, 1, 2, 4, 5, 11, 12, 21, 22, 25, 101], en: [0, 1, 2, 5], sr: [0, 1, 2, 4, 5, 11, 12, 21, 22, 25, 101] }
// Слова после числа, которые склоняются: если в строке со {{count}} встречаются эти корни, а форм нет — ошибка.
const NOUNS = /(объявлен|просмотр|отзыв|обращени|сообщени|фото|снимк|listing|view|review|message|photo|oglas|pregled|recenzij|poruk|fotograf)/i

const flat = (o, p = '', out = {}) => {
  for (const [k, v] of Object.entries(o)) {
    const key = p ? `${p}.${k}` : k
    typeof v === 'string' ? (out[key] = v) : flat(v, key, out)
  }
  return out
}

let problems = 0
for (const lang of ['ru', 'en', 'sr']) {
  const data = JSON.parse(fs.readFileSync(path.join(LOC, `${lang}.json`), 'utf8'))
  const inst = i18next.createInstance()
  await inst.init({ resources: { [lang]: { translation: data } }, lng: lang, fallbackLng: false, interpolation: { escapeValue: false } })
  const map = flat(data)
  const forms = {}
  for (const k of Object.keys(map)) {
    const m = k.match(/^(.+)_(zero|one|two|few|many|other)$/)
    if (m) (forms[m[1]] ||= new Set()).add(m[2])
  }
  for (const [base, set] of Object.entries(forms)) {
    if (set.size < 2) continue
    const bad = COUNTS[lang].filter((n) => inst.t(base, { count: n, defaultValue: '§' }) === '§')
    if (bad.length) { problems += 1; console.log(`[${lang}] ${base}: нет формы для чисел ${bad.join(', ')} — вместо текста покажется ключ`) }
  }
  for (const [k, v] of Object.entries(map)) {
    if (!v.includes('{{count}}') || /_(zero|one|two|few|many|other)$/.test(k) || forms[k]) continue
    // число, сразу за которым идёт склоняемое слово: «{{count}} просмотров», «с {{count}} похожими объявлениями»
    const next = ((v.split('{{count}}')[1] || '').trim().split(/\s+/)[0] || '')
    if (NOUNS.test(next) || /^(похож|slič|similar)/i.test(next)) {
      problems += 1
      console.log(`[${lang}] ${k}: «${v.slice(0, 70)}» — слово после числа не склоняется`)
    }
  }
}
process.exit(problems ? 1 : 0)
