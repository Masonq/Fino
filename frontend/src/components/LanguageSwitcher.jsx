import SlidePill from '../components/SlidePill'
import { useTranslation } from 'react-i18next'
import { switchLanguage } from '../i18n'

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
    // Через switchLanguage, а не напрямую: английский и сербский лежат
    // отдельными файлами и догружаются по требованию (см. i18n/index.js).
    switchLanguage(code)
    try { localStorage.setItem('fino_lang', code) } catch { /* не беда */ }

    // Вместе с языком меняем адрес: у каждого языка свой (/en/..., /sr/...,
    // русский без приставки). Иначе серб отправит другу ссылку, а тот
    // откроет её по-русски — и поисковик по той же причине видел бы
    // один адрес на три языка.
    //
    // Перезагружаем страницу целиком, а не переходим внутри приложения:
    // приставка задаётся роутеру один раз при запуске (basename в
    // main.jsx), и на ходу её не поменять.
    const path = window.location.pathname.replace(/^\/(en|sr|ru)(?=\/|$)/, '') || '/'
    const prefix = code === 'sr' ? '' : `/${code}`  // сербский — основной, без приставки
    const next = prefix + path + window.location.search + window.location.hash
    if (next !== window.location.pathname + window.location.search + window.location.hash) {
      window.location.assign(next)
    }
  }

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
