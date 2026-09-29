import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

/*
 * Остров — одна капсула вверху экрана вместо россыпи разных всплывашек.
 *
 * Появляется из точки, раздувается под текст, через пару секунд
 * сжимается обратно. Новое сообщение заменяет прежнее на месте, капсула
 * не мигает: текст меняется через короткое размытие. Смахнуть вверх —
 * убрать. Нажатие на сообщение ведёт туда, где его читать.
 *
 * Монтируется один раз в App; показывают его через utils/island.js.
 */
const SHOW_MS = { ok: 2600, warn: 4000, msg: 5000 }

export default function Island() {
  const navigate = useNavigate()
  const [item, setItem] = useState(null)
  const [open, setOpen] = useState(false)
  const [serial, setSerial] = useState(0)   // меняется с каждым показом — перезапускает размытие текста
  const timer = useRef(null)
  const startY = useRef(null)

  const hide = useCallback(() => {
    clearTimeout(timer.current)
    setOpen(false)
  }, [])

  useEffect(() => {
    const onShow = (e) => {
      const next = e.detail
      if (!next?.text) return
      clearTimeout(timer.current)
      setItem(next)
      setSerial((n) => n + 1)
      setOpen(true)
      timer.current = setTimeout(() => setOpen(false), next.ms || SHOW_MS[next.kind] || SHOW_MS.ok)
    }
    window.addEventListener('plonk:island', onShow)
    return () => { window.removeEventListener('plonk:island', onShow); clearTimeout(timer.current) }
  }, [])

  const onTap = () => {
    if (item?.to) navigate(item.to)
    hide()
  }

  if (!item) return null

  return (
    <div
      className={`island ${open ? 'is-open' : ''} kind-${item.kind || 'ok'}`}
      role="status"
      aria-live="polite"
      onClick={onTap}
      onTouchStart={(e) => { startY.current = e.touches[0].clientY }}
      onTouchEnd={(e) => {
        if (startY.current != null && e.changedTouches[0].clientY - startY.current < -18) hide()
        startY.current = null
      }}
    >
      <span className="island-dot" />
      <span key={serial} className="island-text">{item.text}</span>
    </div>
  )
}
