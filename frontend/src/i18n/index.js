import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Русский — в первом файле, остальные догружаются по требованию.
//
// Раньше все три языка уезжали в общий файл: около 70 КБ, из которых
// человеку нужен один. Русский оставляем сразу — он основной, на нём
// открывается сайт по умолчанию и с ним не будет мигания при первой
// отрисовке. Английский и сербский подгружаются, когда язык выбран:
// это доли секунды и один раз за посещение.
import ru from './locales/ru.json'

const savedLang = localStorage.getItem('fino_lang')
const browserLang = navigator.language?.slice(0, 2)
// Язык из адреса главнее: человек пришёл по ссылке именно на нём
// (см. main.jsx).
const urlLang = ['en', 'sr'].includes(window.location.pathname.split('/')[1])
  ? window.location.pathname.split('/')[1]
  : null
const defaultLang = urlLang || savedLang
  || (['ru', 'en', 'sr'].includes(browserLang) ? browserLang : 'ru')

i18n.use(initReactI18next).init({
  resources: { ru: { translation: ru } },
  lng: 'ru',
  fallbackLng: 'ru',
  interpolation: { escapeValue: false },
})

const loaders = {
  en: () => import('./locales/en.json'),
  sr: () => import('./locales/sr.json'),
}

/**
 * Догружает язык и переключается на него.
 *
 * Пока перевод едет, на экране остаётся русский — это лучше пустых
 * подписей: человек видит рабочий сайт, а не рамки без слов.
 */
export async function useLanguage(code) {
  if (code === 'ru' || i18n.hasResourceBundle(code, 'translation')) {
    return i18n.changeLanguage(code)
  }
  const load = loaders[code]
  if (!load) return i18n.changeLanguage('ru')
  try {
    const pack = await load()
    i18n.addResourceBundle(code, 'translation', pack.default, true, true)
    return i18n.changeLanguage(code)
  } catch {
    // Не догрузилось (сеть отвалилась) — остаёмся на русском, а не
    // показываем пустые подписи.
    return i18n.changeLanguage('ru')
  }
}

// Язык по умолчанию — сразу после запуска, чтобы не ждать выбора.
if (defaultLang !== 'ru') useLanguage(defaultLang)

export default i18n
