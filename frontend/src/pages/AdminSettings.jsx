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
      {!denied && !state && !error && <div aria-hidden="true">{[0, 1, 2, 3].map((i) => <div key={i} className="sk-block" style={{ height: 76, borderRadius: 20, marginBottom: 10 }} />)}</div>}

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

      {state && <PartnersCard partners={state.partners || {}} onSaved={load} />}

      {error && <p className="form-error">{error}</p>}
    </div>
  )
}

const SECTIONS = ['auto', 'real-estate', 'electronics', 'home-garden', 'services', 'pets', 'kids', 'fashion', 'jobs']
// названия разделов по-человечески, а не служебные slug
const SECTION_NAMES = {
  ru: { auto: 'Авто', 'real-estate': 'Недвижимость', electronics: 'Электроника', 'home-garden': 'Дом и сад', services: 'Услуги', pets: 'Животные', kids: 'Детские товары', fashion: 'Одежда и обувь', jobs: 'Работа' },
  en: { auto: 'Cars', 'real-estate': 'Real estate', electronics: 'Electronics', 'home-garden': 'Home & garden', services: 'Services', pets: 'Pets', kids: 'Kids', fashion: 'Fashion', jobs: 'Jobs' },
  sr: { auto: 'Auto', 'real-estate': 'Nekretnine', electronics: 'Elektronika', 'home-garden': 'Kuća i bašta', services: 'Usluge', pets: 'Ljubimci', kids: 'Za decu', fashion: 'Odeća i obuća', jobs: 'Posao' },
}

// Партнёрские предложения в нужный момент (128): владелец заводит для раздела — под объявлениями раздела
// появляется карточка «Партнёр PLONK» (страховка к машине, интернет к квартире…). Пустой адрес — убрать.
function PartnersCard({ partners, onSaved }) {
  const { t, i18n } = useTranslation()
  const nm = (x) => (SECTION_NAMES[i18n.language] || SECTION_NAMES.ru)[x] || x
  const [f, setF] = useState({ section: 'auto', title: '', text: '', cta: '', url: '' })
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const save = async (body) => { setBusy(true); try { await api.setPartner(body); await onSaved() } catch { /* — */ } setBusy(false) }
  return (
    <div className="setting-card partners-card">
      <h3>{t('partners.admin_title')}</h3>
      <p className="setting-hint">{t('partners.admin_hint')}</p>
      {Object.entries(partners).map(([sec, o]) => (
        <div key={sec} className="partner-row">
          <div><b>{nm(sec)}</b><span>{o.title} → {o.url}</span></div>
          <button type="button" className="jr-btn ghost sm" disabled={busy} onClick={() => save({ section: sec, url: '' })}>{t('partners.remove')}</button>
        </div>
      ))}
      <div className="partner-form">
        <select value={f.section} onChange={set('section')}>{SECTIONS.map((x) => <option key={x} value={x}>{nm(x)}</option>)}</select>
        <input placeholder={t('partners.f_title')} value={f.title} onChange={set('title')} maxLength={60} />
        <input placeholder={t('partners.f_text')} value={f.text} onChange={set('text')} maxLength={160} />
        <input placeholder={t('partners.f_cta')} value={f.cta} onChange={set('cta')} maxLength={30} />
        <input placeholder="https://…" value={f.url} onChange={set('url')} />
        <button type="button" className="jr-btn primary" disabled={busy || !f.url.startsWith('https://') || !f.title} onClick={() => save(f)}>{t('partners.save')}</button>
      </div>
    </div>
  )
}
