import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { pushSupported, pushPermission, isPushSubscribed, enablePush, disablePush } from '../utils/push'

export default function PushToggle() {
  const { t } = useTranslation()
  const [supported, setSupported] = useState(true)
  const [on, setOn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!pushSupported()) {
      setSupported(false)
      return
    }
    setBlocked(pushPermission() === 'denied')
    isPushSubscribed().then(setOn).catch(() => setOn(false))
  }, [])

  const toggle = async () => {
    setBusy(true)
    setError('')
    try {
      if (on) {
        await disablePush()
        setOn(false)
      } else {
        await enablePush()
        setOn(true)
        setBlocked(false)
      }
    } catch (e) {
      if (e.message === 'denied') {
        setBlocked(true)
      } else if (e.message !== 'unsupported') {
        // Разрешение уже дано браузером, но что-то пошло не так дальше
        // (service worker, ключ с сервера, сама подписка) — раньше это
        // проглатывалось молча, тумблер просто не переключался без
        // всякого объяснения. console.error — чтобы было что показать
        // из консоли браузера при следующем разборе, если понадобится.
        console.error('push toggle:', e)
        setError(t('profile.push_error'))
      }
    } finally {
      setBusy(false)
    }
  }

  if (!supported) return <span className="push-toggle-unsupported">{t('profile.push_unsupported')}</span>
  if (blocked) return <span className="push-toggle-unsupported">{t('profile.push_blocked')}</span>

  return (
    <span className="push-toggle-wrap">
      <button
        type="button"
        className={on ? 'toggle-switch on' : 'toggle-switch'}
        onClick={toggle}
        disabled={busy}
        aria-label={t('profile.push_notifications')}
      >
        <span className="toggle-switch-knob" />
      </button>
      {error && <div className="push-toggle-error">{error}</div>}
    </span>
  )
}
