import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'

const FOLDERS = ['new', 'selected', 'invited', 'rejected']
const when = (iso) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

/** Работодатель: все вакансии с откликами (/jobs/responses) или отклики одной вакансии по папкам. */
export default function JobResponses() {
  const { id } = useParams()
  return id ? <VacancyResponses id={id} /> : <Incoming />
}

function Incoming() {
  const { t } = useTranslation()
  const [items, setItems] = useState(null)
  useEffect(() => { api.jobIncoming().then((r) => setItems(r.items)).catch(() => setItems([])) }, [])
  return (
    <div className="page jr-page">
      <PageHeader title={t('jobresp.responses')} />
      {items === null ? <div className="jr-skel" /> : items.length === 0 ? (
        <div className="empty-state"><p className="empty-hint">{t('jobresp.none_incoming')}</p></div>
      ) : items.map(({ vacancy, counts }) => (
        <Link key={vacancy.id} className="jr-vac" to={`/jobs/responses/${vacancy.id}`}>
          <div className="jr-vac-title">{vacancy.title}</div>
          <div className="jr-vac-counts">
            {counts.new > 0 && <span className="jr-badge">{t('jobresp.new_n', { count: counts.new })}</span>}
            <span className="jr-muted">{t('jobresp.total_n', { count: counts.total })}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}

function VacancyResponses({ id }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [folder, setFolder] = useState('new')
  const [data, setData] = useState(null)
  const [invite, setInvite] = useState(null) // { id, at, note }
  const [busy, setBusy] = useState('')

  const load = (f = folder) => api.jobResponses(id, f).then(setData).catch(() => setData({ items: [], counts: {} }))
  useEffect(() => { setData(null); load(folder) }, [id, folder]) // eslint-disable-line react-hooks/exhaustive-deps

  // открыл список новых — они «просмотрены» (остаются в папке «Новые», но кандидат видит, что его смотрели)
  useEffect(() => {
    if (folder !== 'new' || !data?.items) return
    data.items.filter((r) => r.status === 'new').forEach((r) => api.jobSetStatus(r.id, { status: 'viewed' }).catch(() => {}))
  }, [data, folder])

  const act = (r, status, extra = {}) => {
    setBusy(r.id)
    api.jobSetStatus(r.id, { status, ...extra }).then(() => { setInvite(null); load() }).finally(() => setBusy(''))
  }

  return (
    <div className="page jr-page">
      <PageHeader title={data?.vacancy?.title || t('jobresp.responses')} />
      <div className="jr-tabs" role="tablist">
        {FOLDERS.map((f) => (
          <button key={f} type="button" role="tab" aria-selected={folder === f} className={`jr-tab${folder === f ? ' on' : ''}`} onClick={() => setFolder(f)}>
            {t(`jobresp.f_${f}`)}{data?.counts?.[f] ? <span className="jr-tab-n">{data.counts[f]}</span> : null}
          </button>
        ))}
      </div>
      {data === null ? <div className="jr-skel" /> : data.items.length === 0 ? (
        <div className="empty-state"><p className="empty-hint">{t('jobresp.empty_folder')}</p></div>
      ) : data.items.map((r) => (
        <div key={r.id} className="jr-card">
          <div className="jr-card-head">
            <div className="jr-ava">{r.avatar ? <img src={r.avatar} alt="" /> : (r.name || '?')[0]}</div>
            <div className="jr-card-who">
              <div className="jr-name">{r.name}</div>
              <div className="jr-muted">{when(r.created_at)}</div>
            </div>
            {r.phone && <a className="jr-call" href={`tel:${r.phone}`} aria-label={t('jobresp.call')}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" /></svg>
            </a>}
          </div>
          {r.resume && <Link className="jr-resume" to={r.resume.path}>📄 {r.resume.title}</Link>}
          {r.about && <p className="jr-about">{r.about}</p>}
          {r.status === 'invited' && r.interview_at && <div className="jr-inv">✅ {t('jobresp.invited_at', { when: when(r.interview_at) })}</div>}
          {invite?.id === r.id ? (
            <div className="jr-invite">
              <label className="jr-field"><span>{t('jobresp.when')}</span>
                <input type="datetime-local" value={invite.at} onChange={(e) => setInvite({ ...invite, at: e.target.value })} />
              </label>
              <label className="jr-field"><span>{t('jobresp.where')}</span>
                <input value={invite.note} placeholder={t('jobresp.where_ph')} onChange={(e) => setInvite({ ...invite, note: e.target.value })} />
              </label>
              <div className="jr-actions">
                <button type="button" className="jr-btn ghost" onClick={() => setInvite(null)}>{t('jobresp.cancel')}</button>
                <button type="button" className="jr-btn primary" disabled={!invite.at || busy === r.id} onClick={() => act(r, 'invited', { interview_at: invite.at, note: invite.note })}>{t('jobresp.send_invite')}</button>
              </div>
            </div>
          ) : (
            <div className="jr-actions">
              {r.chat_id && <button type="button" className="jr-btn ghost" onClick={() => navigate(`/chat/${r.chat_id}`)}>{t('jobresp.write')}</button>}
              {r.status !== 'selected' && r.status !== 'invited' && r.status !== 'rejected' && <button type="button" className="jr-btn ghost" disabled={busy === r.id} onClick={() => act(r, 'selected')}>{t('jobresp.select')}</button>}
              {r.status !== 'rejected' && <button type="button" className="jr-btn primary" onClick={() => setInvite({ id: r.id, at: '', note: '' })}>{r.status === 'invited' ? t('jobresp.reinvite') : t('jobresp.invite')}</button>}
              {r.status !== 'rejected' && <button type="button" className="jr-btn danger" disabled={busy === r.id} onClick={() => act(r, 'rejected')}>{t('jobresp.reject')}</button>}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

/** Соискатель: «Мои отклики» со статусами. */
export function MyJobResponses() {
  const { t } = useTranslation()
  const [items, setItems] = useState(null)
  useEffect(() => { api.jobMyResponses().then((r) => setItems(r.items)).catch(() => setItems([])) }, [])
  return (
    <div className="page jr-page">
      <PageHeader title={t('jobresp.my')} />
      {items === null ? <div className="jr-skel" /> : items.length === 0 ? (
        <div className="empty-state"><p className="empty-hint">{t('jobresp.none_my')}</p>
          <Link className="jr-btn primary" to="/c/jobs">{t('jobresp.find_jobs')}</Link></div>
      ) : items.map((r) => (
        <div key={r.id} className="jr-card">
          {r.vacancy && <Link className="jr-name" to={r.vacancy.path}>{r.vacancy.title}</Link>}
          <div className={`jr-state jr-st-${r.status}`}><span className="jr-dot" />{t(`jobresp.st_${r.status}`)}</div>
          {r.status === 'invited' && r.interview_at && <div className="jr-inv">✅ {t('jobresp.invited_at', { when: when(r.interview_at) })}{r.interview_note ? ` · ${r.interview_note}` : ''}</div>}
          <div className="jr-actions">
            {r.chat_id && <Link className="jr-btn ghost" to={`/chat/${r.chat_id}`}>{t('jobresp.open_chat')}</Link>}
            <span className="jr-muted">{when(r.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
