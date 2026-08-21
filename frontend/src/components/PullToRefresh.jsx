import { useEffect, useRef, useState } from 'react'

const THRESHOLD = 86   // сколько нужно протянуть, чтобы сработало
const MAX_PULL = 125   // дальше не растягиваем

export default function PullToRefresh({ onRefresh, children }) {
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
        setPull(THRESHOLD)
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

  const label = refreshing ? 'Ищем свежие объявления…' : ready ? 'Отпустите' : 'Потяните вниз'

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
              style={!refreshing ? { transform: `translateX(${-26 + progress * 52}px) rotate(${-12 + progress * 12}deg)` } : undefined}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round">
                <circle cx="10.5" cy="10.5" r="6.5" />
                <path d="m20 20-4.7-4.7" />
              </svg>
            </div>
          </div>
          <span className={ready || refreshing ? 'ptr-label on' : 'ptr-label'}>{label}</span>
        </div>
      </div>

      <div
        className="ptr-content"
        style={{
          transform: `translateY(${pull}px)`,
          transition: active.current ? 'none' : 'transform .32s cubic-bezier(.25,.46,.45,.94)',
        }}
      >
        {children}
      </div>
    </div>
  )
}
