import { useRef, useState } from 'react'

// Насколько далеко открывается красная кнопка — совпадает с её
// собственной шириной в CSS (.notif-delete-btn), иначе кнопка
// открывалась бы не полностью или с зазором.
const REVEAL_WIDTH = 76
// Свайп короче этого — не считается намерением удалить, просто
// вернётся на место. Тот же лишний ход пальца, что бывает при обычной
// прокрутке списка вертикально, не должен открывать кнопку случайно.
const OPEN_THRESHOLD = 36

export default function SwipeableNotification({ notification: n, isOpen, onOpenChange, onOpen, onDelete, children }) {
  const rowRef = useRef(null)
  const startX = useRef(0)
  const startY = useRef(0)
  const dragging = useRef(false)
  const decided = useRef(null)   // null пока не решили, 'x' — горизонтальный свайп, 'y' — обычная прокрутка
  const [dragX, setDragX] = useState(isOpen ? -REVEAL_WIDTH : 0)

  const setX = (x) => {
    setDragX(x)
    if (rowRef.current) rowRef.current.style.transform = `translateX(${x}px)`
  }

  const onTouchStart = (e) => {
    startX.current = e.touches[0].clientX
    startY.current = e.touches[0].clientY
    dragging.current = true
    decided.current = null
    if (rowRef.current) rowRef.current.style.transition = 'none'
  }

  const onTouchMove = (e) => {
    if (!dragging.current) return
    const dx = e.touches[0].clientX - startX.current
    const dy = e.touches[0].clientY - startY.current

    // Решаем один раз, в самом начале жеста — вертикальный это свайп
    // (обычная прокрутка страницы) или горизонтальный (наш, на
    // удаление). Не даём это тут же передумать на середине жеста —
    // дёргано выглядело бы, если бы направление могло переключиться
    // туда-обратно от дрожания пальца.
    if (!decided.current) {
      if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return
      decided.current = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y'
    }
    if (decided.current === 'y') return   // обычная прокрутка — со свайпом не мешаем вовсе

    e.preventDefault()
    const base = isOpen ? -REVEAL_WIDTH : 0
    let next = base + dx
    // Дальше REVEAL_WIDTH тянуть незачем — кнопка и так уже вся видна.
    // Вправо утянуть в плюс тоже нельзя — там просто пусто.
    next = Math.min(0, Math.max(-REVEAL_WIDTH, next))
    setX(next)
  }

  const onTouchEnd = () => {
    dragging.current = false
    if (rowRef.current) rowRef.current.style.transition = ''
    if (decided.current !== 'x') return
    const shouldOpen = dragX < -OPEN_THRESHOLD
    setX(shouldOpen ? -REVEAL_WIDTH : 0)
    onOpenChange(shouldOpen ? n.id : null)
  }

  const handleRowClick = () => {
    // Открыто крестиком/кнопкой — тап по самой строке просто закрывает
    // её обратно, не переходит по ссылке. Тот же принцип, что и в
    // Telegram: пока кнопка удаления видна, строка временно не кликабельна.
    if (isOpen) { setX(0); onOpenChange(null); return }
    onOpen(n)
  }

  return (
    <div className="notif-swipe-wrap">
      <button
        type="button"
        className="notif-delete-btn"
        onClick={() => onDelete(n)}
        aria-label="delete"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m3 0-1 14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1L5 6" />
        </svg>
      </button>
      <button
        ref={rowRef}
        className={n.is_read ? 'notif-row' : 'notif-row unread'}
        style={{ transform: `translateX(${isOpen ? -REVEAL_WIDTH : 0}px)` }}
        onClick={handleRowClick}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {children}
      </button>
    </div>
  )
}
