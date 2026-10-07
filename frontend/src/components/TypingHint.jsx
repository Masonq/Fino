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
  const [frozen, setFrozen] = useState(false)
  const timer = useRef(0)
  const paused = useRef(false)

  // Пока страница прокручивается или поиск уже прилип сверху — не печатаем. Каждая новая буква (раз в 35–70 мс)
  // меняла текст в липком блоке, и Safari на iPhone на каждой букве пересчитывал липкий поиск посреди
  // инерционной прокрутки — поиск подрагивал. Печать — только когда страница стоит у самого верха.
  useEffect(() => {
    let idle = 0
    const onScroll = () => {
      paused.current = true
      setFrozen(true)
      clearTimeout(idle)
      idle = setTimeout(() => {
        if (window.scrollY < 40) { paused.current = false; setFrozen(false) }
      }, 700)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    if (window.scrollY >= 40) { paused.current = true; setFrozen(true) }
    return () => { window.removeEventListener('scroll', onScroll); clearTimeout(idle) }
  }, [])

  useEffect(() => {
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (still) { setText(list[0]); return }

    let word = 0
    let letters = 0
    let erasing = false

    const tick = () => {
      const target = list[word % list.length]
      if (paused.current) {
        // на паузе — целое слово без мигающего курсора, без изменений текста; проверяем раз в полсекунды
        letters = target.length; erasing = true
        setText(target)
        timer.current = setTimeout(tick, 500)
        return
      }
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
      {!frozen && <i className="typing-caret" aria-hidden="true" />}
    </span>
  )
}
