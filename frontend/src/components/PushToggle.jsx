import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { pushSupported, pushPermission, isPushSubscribed, enablePush, disablePush, needsHomeScreenInstall } from '../utils/push'

export default function PushToggle() {
  const { t } = useTranslation()
  const [supported, setSupported] = useState(true)
  const [needsInstall, setNeedsInstall] = useState(false)
  const [on, setOn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [blocked, setBlocked] = useState(false)

  useEffect(() => {
    if (!pushSupported()) {
      setSupported(false)
      setNeedsInstall(needsHomeScreenInstall())
      return
    }
    setBlocked(pushPermission() === 'denied')
    isPushSubscribed().then(setOn).catch(() => setOn(false))
  }, [])

  const toggle = async () => {
    setBusy(true)
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
      if (e.message === 'denied') setBlocked(true)
      // 'unsupported'/'no_key' — молча оставляем выключенным, тумблер уже это отражает
    } finally {
      setBusy(false)
    }
  }

  if (needsInstall) return <span className="push-toggle-unsupported">{t('profile.push_needs_install')}</span>
  if (!supported) return <span className="push-toggle-unsupported">{t('profile.push_unsupported')}</span>
  if (blocked) return <span className="push-toggle-unsupported">{t('profile.push_blocked')}</span>

  return (
    <button
      type="button"
      className={on ? 'toggle-switch on' : 'toggle-switch'}
      onClick={toggle}
      disabled={busy}
      aria-label={t('profile.push_notifications')}
    >
      <span className="toggle-switch-knob" />
    </button>
  )
}
