import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

// Насколько уезжает страница при потягивании.
//
// Было 86 и 125 — почти четверть экрана: шапка уходила вниз и
// перегораживалась полосой обновления. Человек тянет ленту, а видит,
// как всё съезжает.
//
// Шестьдесят четыре хватает, чтобы жест был заметен и понятен, а
// девяносто — предел, дальше страница просто пружинит.
const THRESHOLD = 64   // сколько нужно протянуть, чтобы сработало
const MAX_PULL = 90    // дальше не растягиваем

// Пока идёт обновление, держим страницу почти на месте: ждать удобнее,
// когда видно ленту, а не пустую полосу.
const HOLD_WHILE_REFRESHING = 48

export default function PullToRefresh({ onRefresh, children }) {
  const { t } = useTranslation()
  const [pull, setPull] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef(0)
  const active = useRef(false)

  useEffect(() => {
    const onTouchStart = (e) => {
      // тянуть можно только с самого верха страницы и когда не идёт обновление
      if (window.scrollY > 0 || refreshing) return
      startY.current = e.touches[0].clientY
      active.current = true
    }

    const onTouchMove = (e) => {
      if (!active.current) return
      const delta = e.touches[0].clientY - startY.current
      if (delta <= 0) { setPull(0); return }
      // сопротивление: чем дальше тянем, тем медленнее идёт
      const eased = Math.min(MAX_PULL, delta * 0.45)
      setPull(eased)
    }

    const onTouchEnd = async () => {
      if (!active.current) return
      active.current = false

      if (pull >= THRESHOLD) {
        setRefreshing(true)
        setPull(HOLD_WHILE_REFRESHING)
        try { await onRefresh?.() } finally {
          setRefreshing(false)
          setPull(0)
        }
      } else {
        setPull(0)
      }
    }

    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchmove', onTouchMove, { passive: true })
    document.addEventListener('touchend', onTouchEnd)
    return () => {
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchmove', onTouchMove)
      document.removeEventListener('touchend', onTouchEnd)
    }
  }, [pull, refreshing, onRefresh])

  const progress = Math.min(1, pull / THRESHOLD)
  const ready = progress >= 1

  const label = t(refreshing ? 'ptr.refreshing' : ready ? 'ptr.release' : 'ptr.pull')

  return (
    <div className="ptr-root">
      <div
        className="ptr-indicator"
        style={{
          height: pull,
          opacity: pull > 4 ? 1 : 0,
        }}
      >
        <div className="ptr-inner">
          {/* сцена: лупа едет вдоль ряда карточек и «проявляет» их */}
          <div className="ptr-scene" style={{ opacity: 0.35 + progress * 0.65 }}>
            <div className="ptr-shelf">
              {[0, 1, 2, 3].map((i) => (
                <span key={i} className={refreshing ? 'ptr-item scanning' : 'ptr-item'} style={{ animationDelay: `${i * 0.35}s` }} />
              ))}
            </div>
            <div
              className={refreshing ? 'ptr-lens moving' : 'ptr-lens'}
              style={!refreshing ? { transform: `translateX(${-26 + progress * 52}px) rotate(${-10 + progress * 10}deg)` } : undefined}
            >
              <img src="/logo-mark.png" alt="" />
            </div>
          </div>
          <span className={ready || refreshing ? 'ptr-label on' : 'ptr-label'}>{label}</span>
        </div>
      </div>

      <div
        className="ptr-content"
        // Страница не двигается вовсе.
        //
        // Раньше она уезжала вниз, и шапка вместе с ней: человек тянет
        // ленту, а видит, как всё съезжает. Уменьшение сдвига не
        // помогло — на глаз это то же самое.
        //
        // Теперь полоса обновления ложится поверх, а страница стоит на
        // месте. Жест виден по самой полосе, и этого довольно.
        style={undefined}
      >
        {children}
      </div>
    </div>
  )
}
