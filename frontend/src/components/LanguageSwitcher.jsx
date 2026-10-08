import SlidePill from '../components/SlidePill'
import { useTranslation } from 'react-i18next'
import { changeLanguageAnimated } from '../utils/langSwitch'

const LANGS = [
  { code: 'ru', label: 'RU' },
  { code: 'en', label: 'EN' },
  { code: 'sr', label: 'SR' },
]

// variant="light" — тот же переключатель, но для светлого фона (профиль,
// настройки): тёмный текст на серой подложке вместо белого текста на
// полупрозрачной подложке цветной шапки главной.
export function changeLanguage(code) {
  // без перезагрузки: заголовки красиво переходят на новый язык (utils/langSwitch.js, LangText)
  return changeLanguageAnimated(code)
}
export default function LanguageSwitcher({ variant }) {
  const { i18n } = useTranslation()

  const change = changeLanguage


  return (
    <div className={variant === 'light' ? 'lang-switch light pill-row' : 'lang-switch pill-row'}>
      <SlidePill />
      {LANGS.map((l) => (
        <button
          key={l.code}
          className={i18n.language === l.code ? 'lang-btn active' : 'lang-btn'}
          onClick={() => change(l.code)}
        >
          {l.label}
        </button>
      ))}
    </div>
  )
}
