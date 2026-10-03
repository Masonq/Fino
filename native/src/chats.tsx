import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { AppState } from 'react-native'

import { type Chat, chatList } from './api'
import { useAuth } from './auth'

/**
 * Переписки и счётчик непрочитанных — один на всё приложение: значок на вкладке «Сообщения» и сам список.
 * Обновляется раз в 30 секунд, пока приложение открыто, и сразу при возвращении в него.
 */
type Chats = { chats: Chat[] | null; unread: number; refresh: () => Promise<void>; failed: boolean }

const Ctx = createContext<Chats>({ chats: null, unread: 0, refresh: async () => {}, failed: false })

export function ChatsProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [chats, setChats] = useState<Chat[] | null>(null)
  const [failed, setFailed] = useState(false)

  const refresh = useCallback(async () => {
    if (!token) { setChats(null); return }
    try {
      const res = await chatList(token)
      setChats(res.items)
      setFailed(false)
    } catch {
      setFailed(true)
    }
  }, [token])

  useEffect(() => {
    refresh()
    if (!token) return undefined
    const timer = setInterval(() => { if (AppState.currentState === 'active') refresh() }, 30000)
    const sub = AppState.addEventListener('change', (s) => { if (s === 'active') refresh() })
    return () => { clearInterval(timer); sub.remove() }
  }, [token, refresh])

  const unread = useMemo(() => (chats ?? []).reduce((n, c) => n + (c.unread || 0), 0), [chats])
  const value = useMemo(() => ({ chats, unread, refresh, failed }), [chats, unread, refresh, failed])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useChats = () => useContext(Ctx)
