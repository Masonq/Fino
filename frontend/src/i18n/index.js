import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import ru from './locales/ru.json'
import en from './locales/en.json'
import sr from './locales/sr.json'

const savedLang = localStorage.getItem('fino_lang')
const browserLang = navigator.language?.slice(0, 2)
const defaultLang = savedLang || (['ru', 'en', 'sr'].includes(browserLang) ? browserLang : 'ru')

i18n.use(initReactI18next).init({
  resources: {
    ru: { translation: ru },
    en: { translation: en },
    sr: { translation: sr },
  },
  lng: defaultLang,
  fallbackLng: 'ru',
  interpolation: { escapeValue: false },
})

export default i18n
