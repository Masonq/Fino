import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import { intlLocale } from '../utils/time'

/**
 * Настройки сайта. Пока одна: оплата картой.
 *
 * Пока у владельца нет зарегистрированного предпринимателя или фирмы, брать деньги за услуги как частное лицо
 * рискованно, поэтому по умолчанию оплата выключена. Здесь её включают и выключают одним нажатием — без
 * сервера и без выкладки. Только владелец: сервер отвечает 403 остальным.
 */
export default function AdminSettings() {
  const { t, i18n } = useTranslation()
  const [state, setState] = useState(null)
  const [denied, setDenied] = useState(false)
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(() => (
    api.adminSettings()
      .then(setState)
      .catch((e) => { if (e.status === 403) setDenied(true); else setError(t('support.failed')) })
  ), [t])

  useEffect(() => { load() }, [load])

  // Вернулись на вкладку — спрашиваем сервер ещё раз: переключили с другого устройства или в соседней вкладке,
  // и показывать прежнее значение до ручного обновления страницы нельзя.
  useEffect(() => {
    const onShow = () => { if (!document.hidden) load() }
    document.addEventListener('visibilitychange', onShow)
    window.addEventListener('focus', onShow)
    return () => { document.removeEventListener('visibilitychange', onShow); window.removeEventListener('focus', onShow) }
  }, [load])

  const on = !!state?.card_payments_enabled

  const apply = async (next) => {
    setBusy(true); setError(''); setConfirming(false)
    try {
      setState(await api.setCardPayments(next))
    } catch {
      setError(t('support.failed'))
      load()                                   // не знаем, дошло ли: берём правду с сервера, а не гадаем
    } finally {
      setBusy(false)
    }
  }

  // Включение — с вопросом, но не системным окном: в приложении на главном экране iPhone и во встроенных
  // браузерах confirm() бывает подавлен и молча возвращает «нет» — тумблер тогда «не срабатывает».
  const toggle = () => { if (on) apply(false); else setConfirming((v) => !v) }

  const when = state?.updated_at
    ? new Date(`${state.updated_at}Z`).toLocaleString(intlLocale(i18n.language), { dateStyle: 'medium', timeStyle: 'short' })
    : null

  return (
    <div className="page">
      <PageHeader title={t('settings.title')} />

      {denied && <p className="empty-hint">{t('settings.no_access')}</p>}
      {!denied && !state && !error && <p className="empty-hint">{t('actions.loading')}</p>}

      {state && (
        <div className="setting-card">
          <div className="setting-head">
            <div className="setting-titles">
              <div className="setting-title">{t('settings.card_title')}</div>
              <div className={on ? 'setting-state is-on' : 'setting-state'}>{on ? t('settings.on') : t('settings.off')}</div>
            </div>
            <button
              type="button" role="switch" aria-checked={on} aria-label={t('settings.card_title')}
              className={on ? 'toggle-switch on' : 'toggle-switch'} disabled={busy} onClick={toggle}
            >
              <span className="toggle-switch-knob" />
            </button>
          </div>
          <p className="setting-text">{t('settings.card_text')}</p>
          {confirming && !on && (
            <div className="setting-confirm" role="alertdialog" aria-label={t('settings.confirm_on')}>
              <p>{t('settings.confirm_on')}</p>
              <div className="setting-confirm-actions">
                <button type="button" className="setting-confirm-yes" disabled={busy} onClick={() => apply(true)}>{t('settings.yes_on')}</button>
                <button type="button" className="setting-confirm-no" disabled={busy} onClick={() => setConfirming(false)}>{t('rev.cancel')}</button>
              </div>
            </div>
          )}
          {on && <p className="setting-warn">{t('settings.warn_on')}</p>}
          <p className="setting-meta">
            {when ? t('settings.changed', { who: state.updated_by || '—', when }) : t('settings.never')}
          </p>
        </div>
      )}

      {error && <p className="form-error">{error}</p>}
    </div>
  )
}
