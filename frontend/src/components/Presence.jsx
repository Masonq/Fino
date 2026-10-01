import { cloneElement, isValidElement, useEffect, useRef, useState } from 'react'

/**
 * Окно закрывается так же, как открывается: красиво, а не рывком.
 *
 * Пока show истинно — рисует содержимое как есть. Когда show стало ложным, ещё ms миллисекунд рисует последнее
 * показанное содержимое с классом is-closing на корневом элементе (CSS проигрывает уход), потом убирает.
 * Последнее содержимое «заморожено»: данные, по которым окно рисовалось, к этому моменту могут уже обнулиться.
 * Пока окно уходит, нажатия по нему не проходят (pointer-events в CSS). При «уменьшить движение» — сразу.
 */
export default function Presence({ show, ms = 230, children }) {
  const last = useRef(null)
  const [, rerender] = useState(0)
  if (show && isValidElement(children)) last.current = children

  useEffect(() => {
    if (show || !last.current) return undefined
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const timer = setTimeout(() => { last.current = null; rerender((n) => n + 1) }, reduce ? 0 : ms)
    return () => clearTimeout(timer)
  }, [show, ms])

  if (show) return children
  if (last.current) return cloneElement(last.current, { className: `${last.current.props.className || ''} is-closing` })
  return null
}
