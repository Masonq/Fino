import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

/**
 * Вход по ссылке из бота.
 *
 * Человек публиковал объявления через бота и нигде не регистрировался.
 * Здесь он попадает внутрь одним нажатием: ни пароля, ни кода.
 */
export default function Enter() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { signIn } = useAuth()
  const [failed, setFailed] = useState(false)
  const [blocked, setBlocked] = useState(false)

  useEffect(() => {
    const key = params.get('key')
    if (!key) { setFailed(true); return }

    api.enterByTelegram(key)
      .then((res) => {
        signIn(res.access_token, res.user)
        // Ведём сразу к объявлениям: за ними человек и шёл.
        // Куда человек шёл. Раньше всех уводило в «Мои объявления»,
        // и тот, кто нажал «разместить квартиру», попадал в список
        // вместо формы — и заново искал, куда нажать.
        const next = params.get('next')
        navigate(next && next.startsWith('/') ? next : '/my', { replace: true })
      })
      .catch((e) => { if (e.code === 'user_blocked') setBlocked(true); else setFailed(true) })
  }, [params, signIn, navigate])

  return (
    <div className="page no-header enter-page">
      {blocked ? (
        <>
          <p className="empty">{t('auth.err_blocked')}</p>
          <button className="support-send" onClick={() => navigate('/')}>
            {t('enter.to_home')}
          </button>
        </>
      ) : failed ? (
        <>
          <p className="empty">{t('enter.expired')}</p>
          <button className="support-send" onClick={() => navigate('/')}>
            {t('enter.to_home')}
          </button>
        </>
      ) : (
        <p className="empty">{t('enter.working')}</p>
      )}
    </div>
  )
}
