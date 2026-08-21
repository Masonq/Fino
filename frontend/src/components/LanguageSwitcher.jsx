import { useTranslation } from 'react-i18next'

const LANGS = [
  { code: 'ru', label: 'RU' },
  { code: 'en', label: 'EN' },
  { code: 'sr', label: 'SR' },
]

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()

  const change = (code) => {
    i18n.changeLanguage(code)
    localStorage.setItem('fino_lang', code)
  }

  return (
    <div className="lang-switch">
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
