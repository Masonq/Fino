import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Подсказка в строке поиска, которая печатается сама.
 *
 * «Что ищете?» ничего не подсказывает: человек и так знает, что тут
 * ищут. А вот «Найти холодильник», «Найти квартиру», «Найти подработку»
 * показывают, что на площадке вообще есть, — особенно новичку, который
 * не догадывается, что тут сдают жильё и ищут работу. Так сделано у
 * Avito, и по той же причине.
 *
 * Печатаем по букве, ждём и стираем. Движение останавливается, когда
 * человек просит систему не анимировать (prefers-reduced-motion) — тогда
 * просто показываем первый пример целиком.
 */
const TYPE_MS = 70
const ERASE_MS = 35
const HOLD_MS = 1400

export default function TypingHint({ className = '' }) {
  const { t, i18n } = useTranslation()
  const examples = t('search.hints', { returnObjects: true })
  const list = Array.isArray(examples) ? examples : [t('search.placeholder')]

  const [text, setText] = useState('')
  const timer = useRef(0)

  useEffect(() => {
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (still) { setText(list[0]); return }

    let word = 0
    let letters = 0
    let erasing = false

    const tick = () => {
      const target = list[word % list.length]
      if (!erasing) {
        letters += 1
        setText(target.slice(0, letters))
        if (letters >= target.length) {
          erasing = true
          timer.current = setTimeout(tick, HOLD_MS)
          return
        }
        timer.current = setTimeout(tick, TYPE_MS)
        return
      }
      letters -= 1
      setText(target.slice(0, letters))
      if (letters <= 0) {
        erasing = false
        word += 1
        timer.current = setTimeout(tick, TYPE_MS * 3)
        return
      }
      timer.current = setTimeout(tick, ERASE_MS)
    }

    timer.current = setTimeout(tick, 400)
    return () => clearTimeout(timer.current)
    // Пересобираем при смене языка: примеры на каждом свои.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.language])

  return (
    <span className={className}>
      {text}
      <i className="typing-caret" aria-hidden="true" />
    </span>
  )
}
