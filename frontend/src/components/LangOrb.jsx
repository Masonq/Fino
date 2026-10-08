/**
 * Переключатель языка в шапке — «шар»: круглая кнопка с кодом языка внутри живого кольца (мята → лайм → коралл,
 * медленно вращается). Нажатие раскрывает шар в капсулу с тремя языками и бегунком под выбранным — без
 * выпадающего списка; второе нажатие или выбор сворачивает обратно.
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { changeLanguage } from './LanguageSwitcher'

const LANGS = [
  { code: 'sr', label: 'SR', name: 'Srpski' },
  { code: 'ru', label: 'RU', name: 'Русский' },
  { code: 'en', label: 'EN', name: 'English' },
]

export default function LangOrb() {
  const { i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const cur = LANGS.find((l) => i18n.language?.startsWith(l.code)) || LANGS[0]
  const idx = LANGS.indexOf(cur)

  // нажатие мимо — свернуть
  useEffect(() => {
    if (!open) return undefined
    const off = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false) }
    document.addEventListener('pointerdown', off)
    return () => document.removeEventListener('pointerdown', off)
  }, [open])

  return (
    <div ref={box} className={`lang-orb${open ? ' open' : ''}`} style={{ '--i': idx }}>
      {!open ? (
        <button type="button" className="lang-orb-btn" onClick={() => setOpen(true)} aria-label={`${cur.name} — change language`} aria-expanded="false">
          <span className="lang-orb-ring" aria-hidden="true" />
          <span className="lang-orb-code">{cur.label}</span>
        </button>
      ) : (
        <div className="lang-orb-pill" role="radiogroup" aria-label="Language">
          <span className="lang-orb-thumb" aria-hidden="true" />
          {LANGS.map((l) => (
            <button key={l.code} type="button" role="radio" aria-checked={l.code === cur.code} title={l.name}
              className={l.code === cur.code ? 'on' : ''}
              onClick={() => { setOpen(false); if (l.code !== cur.code) changeLanguage(l.code) }}>
              {l.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
