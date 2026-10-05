import { useEffect, useState } from 'react'

/**
 * Шапка с поиском прячется, когда листают вниз, и возвращается при первом движении вверх (как в Safari
 * и Instagram). Прячется сдвигом (transform), а не высотой — раскладка страницы не дёргается.
 */
export default function useHideOnScroll(threshold = 80) {
  const [hidden, setHidden] = useState(false)
  useEffect(() => {
    let last = window.scrollY, ticking = false
    const update = () => {
      ticking = false
      const y = window.scrollY, dy = y - last
      if (y < threshold) setHidden(false)
      else if (dy > 6) setHidden(true)
      else if (dy < -6) setHidden(false)
      if (Math.abs(dy) > 6) last = y
    }
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(update) } }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [threshold])
  return hidden
}
