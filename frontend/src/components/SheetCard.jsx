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
    // Палец на прокручиваемом списке внутри окна (список разделов в «Перенести в раздел» и т. п.) — это всегда
    // прокрутка списка, окно не тянем вовсе: на iPhone любое изменение transform у окна во время жеста обрывает
    // прокрутку списка (поэтому он не листался ни вверх, ни вниз). Смахнуть окно можно за полоску, заголовок и
    // всё, что вне списка.
    for (let n = e.target; n && n !== el; n = n.parentElement) {
      const oy = getComputedStyle(n).overflowY
      if ((oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight + 1) return
    }
    drag.current = { y: e.touches[0].clientY, dy: 0, at: performance.now() }
  }
  const onTouchMove = (e) => {
    const d = drag.current
    const el = ref.current
    if (!d || !el) return
    d.dy = Math.max(0, e.touches[0].clientY - d.y)
    if (d.dy < 4 && !el.classList.contains('sheet-dragging')) return
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
