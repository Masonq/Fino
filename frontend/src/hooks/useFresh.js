import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

// Свежие объявления для полоски «Только что» в шапке.
//
// Последний ответ живёт в памяти модуля: при возврате на главную
// полоска рисуется сразу тем, что было, а свежее подъезжает следом —
// иначе шапка мигала бы скелетом при каждом заходе в объявление и
// обратно. Обновляется раз в две минуты, пока вкладка на виду.
let last = { key: null, items: null }

const SEEN_KEY = 'plonk_seen_fresh'
const SEEN_CAP = 300

function readSeen() {
  try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || '[]')) } catch { return new Set() }
}

export default function useFresh(city, lang) {
  const key = `${city}|${lang}`
  const [items, setItems] = useState(() => (last.key === key ? last.items : null))
  const [seen, setSeen] = useState(readSeen)

  useEffect(() => {
    let alive = true
    const load = () => {
      if (document.hidden) return
      api.getFresh(city, lang).then((r) => {
        if (!alive) return
        last = { key, items: r.items || [] }
        setItems(r.items || [])
      }).catch(() => { if (alive && last.key !== key) setItems([]) })
    }
    if (last.key === key && last.items) setItems(last.items)
    load()
    const timer = setInterval(load, 120_000)
    document.addEventListener('visibilitychange', load)
    return () => { alive = false; clearInterval(timer); document.removeEventListener('visibilitychange', load) }
  }, [key, city, lang])

  // Просмотренное — кольцо гаснет, как у сторис. Помним последние
  // триста, чтобы хранилище не росло бесконечно.
  const markSeen = useCallback((id) => {
    setSeen((prev) => {
      if (prev.has(id)) return prev
      const next = new Set(prev)
      next.add(id)
      const arr = [...next].slice(-SEEN_CAP)
      try { localStorage.setItem(SEEN_KEY, JSON.stringify(arr)) } catch { /* не беда */ }
      return new Set(arr)
    })
  }, [])

  return { items, seen, markSeen }
}
