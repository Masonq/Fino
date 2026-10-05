import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Sheet from './Sheet'

/**
 * «Откликнуться» на вакансии — как у Авито: своё резюме с PLONK или короткая анкета; отклик уходит
 * работодателю в чат карточкой. Уже откликнулся — вместо кнопки статус. Работодателю — «Отклики (N)».
 */
export default function JobRespond({ listing }) {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const mine = user?.id && listing?.owner?.id === user.id
  const [state, setState] = useState(null) // мой отклик
  const [counts, setCounts] = useState(null)
  const [open, setOpen] = useState(false)
  const [resumes, setResumes] = useState([])
  const [form, setForm] = useState({ name: '', phone: '', about: '', resume_listing_id: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!user?.id || !listing?.id) return
    if (mine) api.jobResponses(listing.id, 'new').then((r) => setCounts(r.counts)).catch(() => {})
    else api.jobMyResponse(listing.id).then((r) => setState(r.response)).catch(() => {})
  }, [user?.id, listing?.id, mine])

  const openForm = () => {
    if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`); return }
    setForm((f) => ({ ...f, name: f.name || user.display_name || '', phone: f.phone || user.phone || '' }))
    api.myListings(i18n.language).then((r) => {
      const items = (r.items || r || []).filter((l) => l.attributes?.listing_kind === 'resume' && l.status === 'active')
      setResumes(items)
      if (items.length) setForm((f) => ({ ...f, resume_listing_id: f.resume_listing_id || items[0].id }))
    }).catch(() => {})
    setErr('')
    setOpen(true)
  }

  const send = () => {
    if (form.name.trim().length < 2) { setErr(t('jobresp.err_name')); return }
    setBusy(true)
    api.jobRespond(listing.id, { ...form, resume_listing_id: form.resume_listing_id || null })
      .then((r) => { setState(r); setOpen(false) })
      .catch((e) => setErr(e.code === 'already_responded' ? t('jobresp.err_twice') : t('jobresp.err_generic')))
      .finally(() => setBusy(false))
  }

  if (mine) {
    const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : 0
    return (
      <Link className="jr-owner" to={`/jobs/responses/${listing.id}`}>
        <span>{t('jobresp.responses')}</span>
        {counts?.new > 0 && <span className="jr-badge">{t('jobresp.new_n', { count: counts.new })}</span>}
        {!counts?.new && <span className="jr-muted">{total}</span>}
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
      </Link>
    )
  }

  if (state) {
    return (
      <Link className={`jr-state jr-st-${state.status}`} to="/jobs/my">
        <span className="jr-dot" />
        <span>{t(`jobresp.st_${state.status}`)}</span>
        {state.status === 'invited' && state.interview_at && (
          <span className="jr-muted">{new Date(state.interview_at).toLocaleString(undefined, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })}</span>
        )}
      </Link>
    )
  }

  return (
    <>
      <button type="button" className="jr-cta" onClick={openForm}>{t('jobresp.respond')}</button>
      <Sheet open={open} onClose={() => setOpen(false)} title={t('jobresp.form_title')}>
            {resumes.length > 0 && (
              <label className="jr-field">
                <span>{t('jobresp.resume')}</span>
                <select value={form.resume_listing_id} onChange={(e) => setForm({ ...form, resume_listing_id: e.target.value })}>
                  {resumes.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
                  <option value="">{t('jobresp.no_resume')}</option>
                </select>
              </label>
            )}
            <label className="jr-field"><span>{t('jobresp.name')}</span>
              <input value={form.name} maxLength={120} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label className="jr-field"><span>{t('jobresp.phone')}</span>
              <input value={form.phone} inputMode="tel" maxLength={40} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </label>
            <label className="jr-field"><span>{t('jobresp.about')}</span>
              <textarea rows={4} value={form.about} maxLength={2000} placeholder={t('jobresp.about_ph')} onChange={(e) => setForm({ ...form, about: e.target.value })} />
            </label>
            {err && <div className="jr-err">{err}</div>}
            <button type="button" className="jr-cta" disabled={busy} onClick={send}>{busy ? t('jobresp.sending') : t('jobresp.send')}</button>
            <div className="jr-hint">{t('jobresp.hint')}</div>
      </Sheet>
    </>
  )
}
