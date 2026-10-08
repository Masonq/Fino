/**
 * Переключатель языка в шапке — «барабан»: скруглённая кнопка с кодом языка; нажатие прокручивает код вверх,
 * как барабан игрового автомата (SR → RU → EN → SR), и язык меняется — заголовки страницы при этом
 * переходят на новый язык волной (LangText). Кружок с кольцом убран по решению владельца.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { changeLanguage } from './LanguageSwitcher'

const ORDER = ['sr', 'ru', 'en']
const NAMES = { sr: 'Srpski', ru: 'Русский', en: 'English' }

export default function LangOrb() {
  const { i18n } = useTranslation()
  const cur = ORDER.find((c) => i18n.language?.startsWith(c)) || 'sr'
  const next = ORDER[(ORDER.indexOf(cur) + 1) % ORDER.length]
  const [rolling, setRolling] = useState(false)
  const roll = () => {
    if (rolling) return
    setRolling(true)
    setTimeout(() => { changeLanguage(next); setRolling(false) }, 380)
  }
  return (
    <button type="button" className="lang-drum" onClick={roll} aria-label={`${NAMES[cur]} → ${NAMES[next]}`}>
      <span className={`lang-drum-reel${rolling ? ' roll' : ''}`} aria-hidden="true">
        <span>{cur.toUpperCase()}</span>
        <span>{next.toUpperCase()}</span>
      </span>
    </button>
  )
}
