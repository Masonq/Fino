import { createContext, type ReactNode, useContext, useEffect, useState } from 'react'

/**
 * Есть ли связь с сервером: запросы сами сообщают (сетевой сбой — нет, любой ответ сервера — есть).
 * Экраны подписываются на «Повторить», чтобы перезагрузиться, когда человек нажал на плашку.
 */
type Listener = (offline: boolean) => void
const listeners = new Set<Listener>()
const retries = new Set<() => void>()
let offlineNow = false

export function reportNetwork(ok: boolean) {
  const next = !ok
  if (next === offlineNow) return
  offlineNow = next
  listeners.forEach((l) => l(next))
}

export function onRetry(fn: () => void) { retries.add(fn); return () => { retries.delete(fn) } }
export function retryAll() { retries.forEach((fn) => fn()) }

const Ctx = createContext(false)
export function NetProvider({ children }: { children: ReactNode }) {
  const [offline, setOffline] = useState(offlineNow)
  useEffect(() => { listeners.add(setOffline); return () => { listeners.delete(setOffline) } }, [])
  return <Ctx.Provider value={offline}>{children}</Ctx.Provider>
}
export const useOffline = () => useContext(Ctx)
