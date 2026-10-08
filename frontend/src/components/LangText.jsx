/**
 * Текст, который при смене языка не просто подменяется, а красиво переходит в новый:
 * mode="wave" — буквы старого текста уходят вверх по очереди, новые всплывают снизу (заголовки);
 * mode="scramble" — буквы перемешиваются и собираются слева направо (подводки, приветствие).
 * Анимация только при смене языка — обычные изменения текста (имя, счётчики) меняются сразу.
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

const CH = 'абвгдежзиклмнопрстуфхцabcdefghijklmnopqrsšđžčć#%&'

export default function LangText({ children, mode = 'wave', className, as: Tag = 'span' }) {
  const { i18n } = useTranslation()
  const text = String(children ?? '')
  const [shown, setShown] = useState(text)
  const [wave, setWave] = useState(null)        // { from, to, phase }
  const lang = useRef(i18n.language)
  const prev = useRef(text)
  useEffect(() => {
    const langChanged = lang.current !== i18n.language
    lang.current = i18n.language
    const from = prev.current
    prev.current = text
    const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (!langChanged || from === text || reduce) { setShown(text); setWave(null); return undefined }
    if (mode === 'scramble') {
      let raf = 0
      const t0 = performance.now(), ms = 600, len = Math.max(from.length, text.length)
      const tick = (now) => {
        const p = Math.min(1, (now - t0) / ms)
        let s = ''
        for (let i = 0; i < len; i++) {
          const ch = text[i] ?? ''
          s += i / len < p ? ch : (ch === ' ' || from[i] === ' ' ? ' ' : CH[Math.floor(Math.random() * CH.length)])
        }
        setShown(p < 1 ? s.trimEnd() : text)
        if (p < 1) raf = requestAnimationFrame(tick)
      }
      raf = requestAnimationFrame(tick)
      return () => cancelAnimationFrame(raf)
    }
    setWave({ from, to: text, phase: 'out' })
    const t1 = setTimeout(() => setWave({ from, to: text, phase: 'in' }), 260 + Math.min(from.length, 30) * 10)
    const t2 = setTimeout(() => { setWave(null); setShown(text) }, 900)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [text, i18n.language, mode])

  if (wave) {
    const str = wave.phase === 'out' ? wave.from : wave.to
    return (
      <Tag className={className} aria-label={text}>
        {[...str].map((c, i) => (
          <span key={`${wave.phase}${i}`} aria-hidden="true" className={`lt-ch lt-${wave.phase}`} style={{ animationDelay: `${Math.min(i, 30) * 12}ms` }}>{c}</span>
        ))}
      </Tag>
    )
  }
  return <Tag className={className}>{shown}</Tag>
}
