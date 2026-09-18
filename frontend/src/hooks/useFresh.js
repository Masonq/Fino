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

// Просмотренные держим здесь, а не только в состоянии компонента.
//
// Отметка ставится в тот же миг, когда человек нажал на кружок, —
// и сразу после этого страница уходит на объявление, а шапка
// размонтируется. Запись в хранилище стояла внутри обновления
// состояния, а такое обновление React у размонтированного
// компонента просто выбрасывает: до хранилища дело не доходило, и
// кольцо после возврата оставалось прежним. Отсюда «иногда не
// отмечается»: успевало или нет, зависело от того, когда React
// добрался до очереди.
let seenSet = null

function seenNow() {
  if (!seenSet) seenSet = readSeen()
  return seenSet
}

function remember(id) {
  const set = seenNow()
  if (set.has(id)) return set
  set.add(id)
  // Сразу и без участия React: переход уже начался.
  try { localStorage.setItem(SEEN_KEY, JSON.stringify([...set].slice(-SEEN_CAP))) } catch { /* не беда */ }
  return set
}

export default function useFresh(city, lang) {
  const key = `${city}|${lang}`
  const [items, setItems] = useState(() => (last.key === key ? last.items : null))
  const [seen, setSeen] = useState(() => new Set(seenNow()))

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
    setSeen(new Set(remember(id)))
  }, [])

  // При возврате на главную состояние берём из общей памяти: пока
  // человек смотрел объявление, отметка уже была поставлена, а
  // состояние в этом новом монтировании о ней ещё не знает.
  useEffect(() => { setSeen(new Set(seenNow())) }, [])

  return { items, seen, markSeen }
}
