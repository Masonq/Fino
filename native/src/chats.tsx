import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { AppState } from 'react-native'

import { type Chat, chatList, notifications } from './api'
import { useAuth } from './auth'
import { readCache, writeCache } from './cache'
import { onRetry } from './net'

/**
 * Переписки и счётчик непрочитанных — один на всё приложение: значок на вкладке «Сообщения» и сам список.
 * Обновляется раз в 30 секунд, пока приложение открыто, и сразу при возвращении в него.
 */
type Chats = { chats: Chat[] | null; unread: number; notices: number; refresh: () => Promise<void>; failed: boolean }

const Ctx = createContext<Chats>({ chats: null, unread: 0, notices: 0, refresh: async () => {}, failed: false })

export function ChatsProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [chats, setChats] = useState<Chat[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [notices, setNotices] = useState(0)

  const refresh = useCallback(async () => {
    if (!token) { setChats(null); setNotices(0); return }
    notifications(token).then((r) => setNotices(r.unread || 0)).catch(() => {})
    try {
      const res = await chatList(token)
      setChats(res.items)
      setFailed(false)
      writeCache('chats', res.items)
    } catch {
      const cached = await readCache<Chat[]>('chats')
      if (cached) setChats((v) => v ?? cached)
      else setFailed(true)
    }
  }, [token])

  useEffect(() => {
    refresh()
    if (!token) return undefined
    const timer = setInterval(() => { if (AppState.currentState === 'active') refresh() }, 30000)
    const sub = AppState.addEventListener('change', (s) => { if (s === 'active') refresh() })
    return () => { clearInterval(timer); sub.remove() }
  }, [token, refresh])

  useEffect(() => onRetry(() => { refresh() }), [refresh])
  // Сохранённый список — сразу при входе, пока идёт первая загрузка
  useEffect(() => { if (token) readCache<Chat[]>('chats').then((c) => { if (c) setChats((v) => v ?? c) }) }, [token])

  const unread = useMemo(() => (chats ?? []).reduce((n, c) => n + (c.unread || 0), 0), [chats])
  const value = useMemo(() => ({ chats, unread, notices, refresh, failed }), [chats, unread, notices, refresh, failed])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useChats = () => useContext(Ctx)
