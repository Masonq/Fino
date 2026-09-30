import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, TOKEN_KEY, getToken } from '../api/client'

const AuthContext = createContext({
  user: null,
  loading: true,
  lastKnownRole: null,
  signIn: () => {},
  signOut: () => {},
  updateUser: () => {},
})

// Роль с прошлого раза — не для прав доступа (те всегда сверяются по
// настоящему user.role после ответа сервера), а только чтобы скелетон
// профиля мог заранее прикинуть, показывать ли заглушку раздела для
// модераторов/админов. user на старте — null, роль неоткуда взять,
// пока не придёт ответ /me — у модератора/админа реальная страница
// после загрузки всегда была на одну секцию длиннее скелетона.
const LAST_ROLE_KEY = 'fino_last_role'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Нет токена — проверять нечего, человек гость с первого кадра. Раньше loading стартовал как «true» у всех: гость на
  // 55 мс видел кружок-заглушку на месте «Войти», и строка поиска ужималась на 23 точки.
  const [loading, setLoading] = useState(() => Boolean(getToken()))
  const [lastKnownRole, setLastKnownRole] = useState(() => localStorage.getItem(LAST_ROLE_KEY))

  // при запуске проверяем сохранённый токен
  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    const attempt = (n) => api.me()
      .then((userData) => {
        setUser(userData)
        if (userData?.role) {
          localStorage.setItem(LAST_ROLE_KEY, userData.role)
          setLastKnownRole(userData.role)
        }
      })
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
          return                                   // токен плохой — повторять нечего
        }
        // Временная ошибка (сеть, 5xx, 429), а не «токен плохой»: один повтор вместо «вы не вошли». Иначе служебная
        // страница (переписки с жалобами и другие) видит user=null и выбрасывает модератора на главную из-за одного
        // сорвавшегося запроса.
        // Три попытки с растущей паузой: 429 («слишком много запросов») за общим адресом мобильной сети проходит за секунду-две.
        if (n < 2) return new Promise((resolve) => setTimeout(resolve, 700 * (n + 1))).then(() => attempt(n + 1))
      })
    attempt(0).finally(() => setLoading(false))
  }, [])

  const signIn = useCallback((token, userData) => {
    localStorage.setItem(TOKEN_KEY, token)
    setUser(userData)
    // старая заглушка хранила id отдельно — держим в согласии,
    // пока избранное и чаты не переведены на токен
    if (userData?.id) localStorage.setItem('fino_user_id', userData.id)
    if (userData?.role) {
      localStorage.setItem(LAST_ROLE_KEY, userData.role)
      setLastKnownRole(userData.role)
    }
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
    localStorage.removeItem(LAST_ROLE_KEY)
    setUser(null)
    setLastKnownRole(null)
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
    <AuthContext.Provider value={{ user, loading, lastKnownRole, signIn, signOut, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
