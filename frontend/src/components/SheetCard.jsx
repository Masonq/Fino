import { useRef } from 'react'

/**
 * Карточка нижнего окна: полоска-ручка сверху и смахивание вниз пальцем.
 *
 * Тянуть можно, когда содержимое прокручено до верха (иначе палец прокручивает текст). Отпустили, оттянув
 * больше 90 точек или резким движением, — окно закрывается и уезжает вниз с того места, где был палец
 * (--sheet-drag); меньше — пружиной возвращается на место. Нажатие по карточке не закрывает окно.
 */
export default function SheetCard({ base = 'reasons-card', className = '', onClose, children, ...rest }) {
  const ref = useRef(null)
  const drag = useRef(null)

  const onTouchStart = (e) => {
    const el = ref.current
    if (!el || el.scrollTop > 0 || e.touches.length > 1) return
    drag.current = { y: e.touches[0].clientY, dy: 0, at: performance.now() }
  }
  const onTouchMove = (e) => {
    const d = drag.current
    const el = ref.current
    if (!d || !el) return
    d.dy = Math.max(0, e.touches[0].clientY - d.y)
    el.classList.add('sheet-dragging')
    el.style.transform = `translateY(${d.dy}px)`
    el.style.setProperty('--sheet-drag', `${d.dy}px`)
  }
  const onTouchEnd = () => {
    const d = drag.current
    const el = ref.current
    drag.current = null
    if (!d || !el) return
    el.classList.remove('sheet-dragging')
    const fast = d.dy > 30 && d.dy / Math.max(1, performance.now() - d.at) > 0.5
    if (d.dy > 90 || fast) { onClose?.(); return }
    el.style.transition = 'transform .28s cubic-bezier(.2,1.25,.4,1)'
    el.style.transform = ''
    el.style.setProperty('--sheet-drag', '0px')
    setTimeout(() => { if (el) el.style.transition = '' }, 300)
  }

  return (
    <div
      ref={ref}
      className={`${base} ${className}`.trim()}
      onClick={(e) => e.stopPropagation()}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onTouchCancel={onTouchEnd}
      {...rest}
    >
      <span className="sheet-handle" aria-hidden="true" />
      {children}
    </div>
  )
}
