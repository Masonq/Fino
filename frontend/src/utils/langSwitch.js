/**
 * Смена языка без перезагрузки страницы — чтобы было видно анимацию заголовков (LangText).
 *
 * Раньше язык менялся полной перезагрузкой: приставка языка в адресе (/ru, /en) задаётся роутеру при запуске
 * (basename), на ходу её не поменять. Теперь: 1) догружаем язык и меняем его — заголовки в LangText
 * «рассыпаются» и собираются на новом языке; 2) когда анимация отыграла, меняем адрес и пересоздаём роутер
 * с новой приставкой (main.jsx, ключ по приставке) — без перезагрузки, без заставки.
 */
import { switchLanguage } from '../i18n'

let setBase = null
export function registerBaseSetter(fn) { setBase = fn }

const ANIM_MS = 750

export async function changeLanguageAnimated(code) {
  try { localStorage.setItem('fino_lang', code) } catch { /* не беда */ }
  const path = window.location.pathname.replace(/^\/(en|sr|ru)(?=\/|$)/, '') || '/'
  const prefix = code === 'sr' ? '' : `/${code}`   // сербский — основной, без приставки
  const next = prefix + path + window.location.search + window.location.hash
  if (!setBase) { window.location.assign(next); return }
  await switchLanguage(code)
  document.documentElement.lang = code
  await new Promise((r) => setTimeout(r, ANIM_MS))
  window.history.replaceState(null, '', next)
  setBase(prefix || '/')
}
