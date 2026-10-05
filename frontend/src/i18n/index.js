import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Сербский — язык по умолчанию (решение владельца, как и в приложении): он в первом файле, без мигания
// при первой отрисовке. Русский и английский догружаются, когда их выбрали, — доли секунды, один раз.
import sr from './locales/sr.json'

const savedLang = localStorage.getItem('fino_lang')
const browserLang = navigator.language?.slice(0, 2)
// Язык из адреса главнее: человек пришёл по ссылке именно на нём
// (см. main.jsx).
const urlLang = ['en', 'sr'].includes(window.location.pathname.split('/')[1])
  ? window.location.pathname.split('/')[1]
  : null
// Выбор человека (адрес или сохранённый язык) главнее; без выбора — сербский, а не язык браузера.
const defaultLang = urlLang || (['ru', 'en', 'sr'].includes(savedLang) ? savedLang : null) || 'sr'
void browserLang

i18n.use(initReactI18next).init({
  resources: { sr: { translation: sr } },
  lng: 'sr',
  fallbackLng: 'sr',
  interpolation: { escapeValue: false },
})

const loaders = {
  en: () => import('./locales/en.json'),
  ru: () => import('./locales/ru.json'),
}

/**
 * Догружает язык и переключается на него.
 *
 * Имя без «use» в начале намеренно: это обычная функция, а не хук
 * React. Назвал её useLanguage — и линт остановил деплой, потому что по
 * такому имени он считает функцию хуком и требует вызывать её только
 * внутри компонентов. Правило верное, имя было неудачным.
 *
 * Пока перевод едет, на экране остаётся русский — это лучше пустых
 * подписей: человек видит рабочий сайт, а не рамки без слов.
 */
export async function switchLanguage(code) {
  if (code === 'sr' || i18n.hasResourceBundle(code, 'translation')) {
    return i18n.changeLanguage(code)
  }
  const load = loaders[code]
  if (!load) return i18n.changeLanguage('sr')
  try {
    const pack = await load()
    i18n.addResourceBundle(code, 'translation', pack.default, true, true)
    return i18n.changeLanguage(code)
  } catch {
    // Не догрузилось (сеть отвалилась) — остаёмся на сербском, а не
    // показываем пустые подписи.
    return i18n.changeLanguage('sr')
  }
}

// атрибут lang у страницы — по текущему языку (читалки экрана, перевод браузера, проверка орфографии)
const setHtmlLang = (code) => { document.documentElement.lang = code }
setHtmlLang('sr')
i18n.on('languageChanged', setHtmlLang)

// Выбранный раньше язык — сразу после запуска, чтобы не ждать выбора.
if (defaultLang !== 'sr') switchLanguage(defaultLang)

export default i18n
