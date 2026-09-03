import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import { useAuth } from './AuthContext'

const FavoritesContext = createContext({ ids: new Set(), toggle: () => {}, isFavorite: () => false })

export function FavoritesProvider({ children }) {
  const [ids, setIds] = useState(() => new Set())

  const { user } = useAuth()
  const userId = user?.id

  useEffect(() => {
    if (!userId) return
    api.getFavoriteIds()
      .then((res) => setIds(new Set(res.ids || [])))
      .catch(() => {})
  }, [userId])

  // вышли из аккаунта — сердечки гаснут
  useEffect(() => {
    if (!userId) setIds(new Set())
  }, [userId])

  const toggle = useCallback(async (listingId) => {
    const uid = userId
    if (!uid) return { needAuth: true }

    const has = ids.has(listingId)
    // Лёгкий толчок в руку на телефоне: сердечко и так меняется
    // мгновенно, а вибрация подтверждает нажатие, не глядя на экран.
    // Только при добавлении — снятие с избранного событие менее
    // радостное, и отмечать его ни к чему. Где вибрации нет (ноутбук,
    // iPhone в Safari), вызов просто ничего не делает.
    if (!has && typeof navigator !== 'undefined' && navigator.vibrate) {
      try { navigator.vibrate(12) } catch { /* не беда */ }
    }
    // сразу меняем состояние, не дожидаясь сервера — так сердечко реагирует мгновенно
    setIds((prev) => {
      const next = new Set(prev)
      has ? next.delete(listingId) : next.add(listingId)
      return next
    })

    try {
      if (has) await api.removeFavorite(listingId)
      else await api.addFavorite(listingId)
    } catch {
      // не получилось — возвращаем как было
      setIds((prev) => {
        const next = new Set(prev)
        has ? next.add(listingId) : next.delete(listingId)
        return next
      })
    }
    return { needAuth: false }
  }, [ids, userId])

  const isFavorite = useCallback((id) => ids.has(id), [ids])

  return (
    <FavoritesContext.Provider value={{ ids, toggle, isFavorite }}>
      {children}
    </FavoritesContext.Provider>
  )
}

export const useFavorites = () => useContext(FavoritesContext)
