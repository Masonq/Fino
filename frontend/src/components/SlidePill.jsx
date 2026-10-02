import { useLayoutEffect, useRef } from 'react'

/**
 * Переезжающая плашка под активным вариантом ряда — тот же приём, что у «Все / Новое / Даром».
 *
 * Ставится первым ребёнком ряда с классом pill-row. Сама находит активный вариант (.active, .on, .chip-active),
 * следит за сменой выбора (MutationObserver) и за размером ряда (ResizeObserver) и переезжает к нему с лёгкой
 * пружиной — где бы он ни стоял: в ряду, в прокручиваемой строке, в переносе на новую строку. При первом показе
 * встаёт на место без движения. Вид плашки (цвет, скругление) задаётся в CSS для каждого ряда.
 */
export default function SlidePill() {
  const ref = useRef(null)

  useLayoutEffect(() => {
    const pill = ref.current
    const row = pill?.parentElement
    if (!row) return undefined
    let first = true
    const place = () => {
      const active = row.querySelector(':scope > .active, :scope > .on, :scope > .chip-active')
      if (!active) { pill.style.opacity = '0'; return }
      if (first) pill.classList.add('no-anim')
      pill.style.opacity = '1'
      pill.style.width = `${active.offsetWidth}px`
      pill.style.height = `${active.offsetHeight}px`
      pill.style.transform = `translate(${active.offsetLeft}px, ${active.offsetTop}px)`
      if (first) {
        void pill.offsetWidth
        pill.classList.remove('no-anim')
        first = false
      }
    }
    place()
    const mo = new MutationObserver(place)
    mo.observe(row, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] })
    const ro = new ResizeObserver(place)
    ro.observe(row)
    return () => { mo.disconnect(); ro.disconnect() }
  }, [])

  return <span ref={ref} className="slide-pill" aria-hidden="true" />
}
