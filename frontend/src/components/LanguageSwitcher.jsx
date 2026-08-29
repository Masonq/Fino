import { useTranslation } from 'react-i18next'

const LANGS = [
  { code: 'ru', label: 'RU' },
  { code: 'en', label: 'EN' },
  { code: 'sr', label: 'SR' },
]

// variant="light" — тот же переключатель, но для светлого фона (профиль,
// настройки): тёмный текст на серой подложке вместо белого текста на
// полупрозрачной подложке цветной шапки главной.
export default function LanguageSwitcher({ variant }) {
  const { i18n } = useTranslation()

  const change = (code) => {
    i18n.changeLanguage(code)
    localStorage.setItem('fino_lang', code)
  }

  return (
    <div className={variant === 'light' ? 'lang-switch light' : 'lang-switch'}>
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
