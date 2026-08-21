import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

const FavoritesContext = createContext({ ids: new Set(), toggle: () => {}, isFavorite: () => false })

export function FavoritesProvider({ children }) {
  const [ids, setIds] = useState(() => new Set())

  const userId = localStorage.getItem('fino_user_id')

  useEffect(() => {
    if (!userId) return
    api.getFavoriteIds(userId)
      .then((res) => setIds(new Set(res.ids || [])))
      .catch(() => {})
  }, [userId])

  const toggle = useCallback(async (listingId) => {
    const uid = localStorage.getItem('fino_user_id')
    if (!uid) return { needAuth: true }

    const has = ids.has(listingId)
    // сразу меняем состояние, не дожидаясь сервера — так сердечко реагирует мгновенно
    setIds((prev) => {
      const next = new Set(prev)
      has ? next.delete(listingId) : next.add(listingId)
      return next
    })

    try {
      if (has) await api.removeFavorite(listingId, uid)
      else await api.addFavorite(listingId, uid)
    } catch {
      // не получилось — возвращаем как было
      setIds((prev) => {
        const next = new Set(prev)
        has ? next.add(listingId) : next.delete(listingId)
        return next
      })
    }
    return { needAuth: false }
  }, [ids])

  const isFavorite = useCallback((id) => ids.has(id), [ids])

  return (
    <FavoritesContext.Provider value={{ ids, toggle, isFavorite }}>
      {children}
    </FavoritesContext.Provider>
  )
}

export const useFavorites = () => useContext(FavoritesContext)
