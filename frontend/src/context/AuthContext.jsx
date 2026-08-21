import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, TOKEN_KEY, getToken } from '../api/client'

const AuthContext = createContext({
  user: null,
  loading: true,
  signIn: () => {},
  signOut: () => {},
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // при запуске проверяем сохранённый токен
  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch(() => {
        // токен просрочен или отозван — убираем, чтобы не мешал
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const signIn = useCallback((token, userData) => {
    localStorage.setItem(TOKEN_KEY, token)
    setUser(userData)
    // старая заглушка хранила id отдельно — держим в согласии,
    // пока избранное и чаты не переведены на токен
    if (userData?.id) localStorage.setItem('fino_user_id', userData.id)
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('fino_user_id')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
