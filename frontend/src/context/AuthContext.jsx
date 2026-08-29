import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, TOKEN_KEY, getToken } from '../api/client'

const AuthContext = createContext({
  user: null,
  loading: true,
  signIn: () => {},
  signOut: () => {},
  updateUser: () => {},
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // при запуске проверяем сохранённый токен
  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch((err) => {
        // Токен снимаем только когда сервер прямо ответил «401 —
        // неверный/просроченный токен». Раньше снимали при ЛЮБОЙ
        // ошибке — а быстрое повторное обновление страницы обрывает
        // ещё не завершившийся запрос с прошлой загрузки (fetch
        // бросает AbortError/сетевую ошибку без err.status вовсе), и
        // это неотличимо не проверялось от настоящего «токен плохой»:
        // рабочий токен стирался, и человека выкидывало из профиля
        // на ровном месте.
        if (err?.status === 401) {
          localStorage.removeItem(TOKEN_KEY)
          setUser(null)
        }
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
    // Сервер — первым, пока сам токен ещё лежит в localStorage: это
    // единственное, чем можно авторизовать сам запрос logout. Раньше
    // тут вообще не было обращения к серверу — token_version на
    // сервере не менялся, и старый токен продолжал молча работать
    // весь оставшийся срок (30 дней), даже после «выхода» на этом
    // самом телефоне. Не ждём и не блокируем локальный выход её
    // результатом — если сети нет прямо сейчас, человек всё равно
    // должен выйти немедленно на этом устройстве; сервер тут просто
    // не узнает об этом конкретном выходе, но это не хуже прежнего
    // поведения (было не хуже никогда).
    api.logout().catch(() => {})
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('fino_user_id')
    setUser(null)
  }, [])

  // Правка профиля (имя, фото, компания) сохраняется на сервере, но
  // без этого в кэше входа оставались старые значения до следующей
  // полной перезагрузки приложения — страница профиля, чат и карточки
  // объявлений берут имя/аватар отсюда, не своим отдельным запросом,
  // и молча показывали бы прежнее, пока страницу не обновишь руками.
  // Сливаем поверх текущего, а не заменяем целиком — сервер в ответе
  // на PATCH /users/me может прислать не все поля, что были при входе.
  const updateUser = useCallback((partial) => {
    setUser((prev) => (prev ? { ...prev, ...partial } : prev))
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
