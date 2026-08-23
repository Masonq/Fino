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

  useEffect(() => {
    const key = params.get('key')
    if (!key) { setFailed(true); return }

    api.enterByTelegram(key)
      .then((res) => {
        signIn(res.access_token, res.user)
        // Ведём сразу к объявлениям: за ними человек и шёл.
        navigate('/my', { replace: true })
      })
      .catch(() => setFailed(true))
  }, [params, signIn, navigate])

  return (
    <div className="page enter-page">
      {failed ? (
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
