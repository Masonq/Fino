import { router } from 'expo-router'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import { addFavorite, favoriteIds, removeFavorite } from './api'
import { useAuth } from './auth'

/**
 * Какие объявления в избранном — общий список для карточек ленты, экрана объявления и вкладки «Избранное».
 * Нажатие сердечка меняет его сразу, не дожидаясь сервера; сервер отказал — откатываем. Гостя ведём во вход.
 */
type Fav = { ids: Set<string>; loaded: boolean; isFav: (id: string) => boolean; toggle: (id: string) => Promise<void>; version: number }

const Ctx = createContext<Fav>({ ids: new Set(), loaded: false, isFav: () => false, toggle: async () => {}, version: 0 })

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [ids, setIds] = useState<Set<string>>(new Set())
  const [loaded, setLoaded] = useState(false)
  const [version, setVersion] = useState(0)
  const busy = useRef(new Set<string>())

  useEffect(() => {
    let alive = true
    setLoaded(false)
    if (!token) { setIds(new Set()); setLoaded(true); return undefined }
    favoriteIds(token)
      .then((r) => { if (alive) setIds(new Set(r.ids)) })
      .catch(() => {})
      .finally(() => { if (alive) setLoaded(true) })
    return () => { alive = false }
  }, [token])

  const toggle = useCallback(async (id: string) => {
    if (!token) { router.push('/login'); return }
    if (busy.current.has(id)) return
    busy.current.add(id)
    const wasFav = ids.has(id)
    const flip = (on: boolean) => setIds((prev) => { const n = new Set(prev); if (on) n.add(id); else n.delete(id); return n })
    flip(!wasFav)
    try {
      await (wasFav ? removeFavorite(token, id) : addFavorite(token, id))
      setVersion((v) => v + 1)
    } catch {
      flip(wasFav)
    } finally {
      busy.current.delete(id)
    }
  }, [token, ids])

  const value = useMemo(() => ({ ids, loaded, isFav: (id: string) => ids.has(id), toggle, version }), [ids, loaded, toggle, version])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useFavorites = () => useContext(Ctx)
