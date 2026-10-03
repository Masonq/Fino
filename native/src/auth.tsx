import * as SecureStore from 'expo-secure-store'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Platform } from 'react-native'

import { API } from './config'

/**
 * Кто вошёл. Токен — в защищённом хранилище телефона (Keychain на iPhone, Keystore на Android), не в обычных
 * настройках. При запуске проверяем токен на сервере (/auth/me): сервер отказал (401 — токен отозван или истёк) —
 * честно выходим; нет сети — остаёмся в аккаунте и не пугаем человека.
 */
const KEY = 'plonk_token'

// В веб-превью (проверка на компьютере) защищённого хранилища нет — там обычное хранилище браузера
const store = Platform.OS === 'web'
  ? {
      getItemAsync: async (k: string) => globalThis.localStorage?.getItem(k) ?? null,
      setItemAsync: async (k: string, v: string) => { globalThis.localStorage?.setItem(k, v) },
      deleteItemAsync: async (k: string) => { globalThis.localStorage?.removeItem(k) },
    }
  : SecureStore

export type User = { id: string; display_name?: string | null; email?: string | null; avatar_url?: string | null; role?: string; phone?: string | null }

type Auth = {
  user: User | null
  token: string | null
  ready: boolean
  signIn: (token: string, user: User) => Promise<void>
  signOut: () => Promise<void>
  setUser: (u: User) => void
}

const Ctx = createContext<Auth>({ user: null, token: null, ready: false, signIn: async () => {}, signOut: async () => {}, setUser: () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let alive = true
    ;(async () => {
      const saved = await store.getItemAsync(KEY).catch(() => null)
      if (!saved) { if (alive) setReady(true); return }
      if (alive) setToken(saved)
      try {
        const res = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${saved}`, Accept: 'application/json' } })
        if (res.status === 401) {
          await store.deleteItemAsync(KEY).catch(() => {})
          if (alive) { setToken(null); setUser(null) }
        } else if (res.ok && alive) {
          setUser(await res.json())
        }
      } catch {
        // нет сети — остаёмся в аккаунте, данные подтянутся позже
      } finally {
        if (alive) setReady(true)
      }
    })()
    return () => { alive = false }
  }, [])

  const signIn = useCallback(async (t: string, u: User) => {
    await store.setItemAsync(KEY, t)
    setToken(t)
    setUser(u)
  }, [])

  const signOut = useCallback(async () => {
    const t = token
    await store.deleteItemAsync(KEY).catch(() => {})
    setToken(null)
    setUser(null)
    if (t) fetch(`${API}/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${t}` } }).catch(() => {})
  }, [token])

  const value = useMemo(() => ({ user, token, ready, signIn, signOut, setUser }), [user, token, ready, signIn, signOut])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
