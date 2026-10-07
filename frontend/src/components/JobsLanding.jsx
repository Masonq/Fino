import { goBack } from '../utils/goBack'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import ListingCard from './ListingCard'
import { artLayoutMeasured, jobArt, tileFor } from '../utils/artFit'
import TileArt, { useTileMeasure } from './TileArt'
import { CardSkeletons } from './Skeletons'

/**
 * Раздел «Работа» — по образцу Авито, так же, как в приложении (native/src/components/JobsLanding.tsx):
 * вкладки «Ищу работу» / «Ищу сотрудников». Плитки-подборки — настоящие фильтры по полям вакансии (attr_eq).
 * Картинки — /cat/jobs-КЛЮЧ.png в стиле остальных разделов (пока новой нет — прежняя /jobs/КЛЮЧ.webp).
 */
const ROW1 = [
  { key: 'part_time', eq: { employment_type: 'part_time' }, wide: true },
  { key: 'full_time', eq: { employment_type: 'full_time' } },
  { key: 'remote', eq: { work_format: 'remote' } },
  { key: 'shift', eq: { employment_type: 'shift' } },
]
const ROW2 = [
  { key: 'no_exp', eq: { experience: 'none' } },
  { key: 'no_serbian', eq: { serbian_needed: false }, wide: true },
  { key: 'one_off', eq: { employment_type: 'one_off' } },
]

export default function JobsLanding() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [tab, setTab] = useState('seek')
  const measure = useTileMeasure()
  const [tile, setTile] = useState(null)
  const [query, setQuery] = useState('')
  const [q, setQ] = useState('')
  const [items, setItems] = useState(null)
  const [total, setTotal] = useState(0)
  const [myVac, setMyVac] = useState(null)
  const [tipsOpen, setTipsOpen] = useState(false)
  const resultsRef = useRef(null)

  useEffect(() => { const id = setTimeout(() => setQ(query.trim()), 350); return () => clearTimeout(id) }, [query])
  const sub = tab === 'seek' ? 'vacancies' : 'resumes'
  useEffect(() => {
    let alive = true
    setItems(null)
    const params = { category_slug: sub, lang: i18n.language, limit: 24 }
    if (q) params.q = q
    if (tab === 'seek' && tile) params.attr_eq = JSON.stringify(tile.eq)
    api.searchListings(params).then((r) => { if (alive) { setItems(r.items || []); setTotal(r.total || 0) } })
      .catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [sub, q, tile, tab, i18n.language])
  useEffect(() => {
    if (!user) { setMyVac(null); return }
    api.myListings(i18n.language).then((r) => setMyVac((r.items || []).filter((l) => l.status === 'active' && l.category_slug === 'vacancies').length)).catch(() => {})
  }, [user, i18n.language])

  const switchTab = (v) => { setTab(v); setTile(null); setQuery(''); setQ('') }
  const toResults = () => setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 350)
  const needLogin = (path) => navigate(user ? path : `/login?returnTo=${encodeURIComponent(path)}`)

  const tileButton = (x) => {
    const on = tile?.key === x.key
    const label = t(`jobs.tile_${x.key}`)
    const base = tileFor(label)
    // как плитки разделов: колонка надписи по точному замеру, картинка в углу чуть за краем
    const { fit } = artLayoutMeasured(label, base, `jobs-${x.key}`, measure, base.tile - 26)
    return (
      <button key={x.key} type="button" className={`jl-tile${base.kind ? ' ' + base.kind : ''}${on ? ' on' : ''}`} aria-pressed={on}
        onClick={() => { setTile(on ? null : x); if (!on) toResults() }}>
        <span className="jl-tile-text" style={{ maxWidth: fit.text }}>{label}</span>
        <TileArt src={jobArt(x.key)} name={label} fit={fit} />
        {on && <span className="jl-tile-check" aria-hidden>✓</span>}
      </button>
    )
  }

  const searchBox = (ph) => (
    <div className="jl-search">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={ph}
        onKeyDown={(e) => { if (e.key === 'Enter') toResults() }} />
      {query && <button type="button" className="jl-clear" onClick={() => setQuery('')} aria-label={t('actions.clear', 'Очистить')}>×</button>}
    </div>
  )

  return (
    <div className="landing jobs-landing">
      <div className="jl-top">
        <button type="button" className="topbar-btn" onClick={() => goBack(navigate, '/')} aria-label={t('actions.back')}>
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="jl-tabs" role="tablist">
          {['seek', 'hire'].map((v) => (
            <button key={v} type="button" role="tab" aria-selected={tab === v} className={`jl-tab${tab === v ? ' on' : ''}`} onClick={() => switchTab(v)}>
              {t(v === 'seek' ? 'jobs.tab_seek' : 'jobs.tab_hire')}
            </button>
          ))}
        </div>
      </div>

      {tab === 'seek' ? (
        <div className="jl-head">
          <h1 className="jl-h1">{t('jobs.seek_title')}</h1>
          {searchBox(t('jobs.seek_search'))}
          <div className="jl-tiles">
            <div className="jl-tile-row">{ROW1.map(tileButton)}</div>
            <div className="jl-tile-row">{ROW2.map(tileButton)}</div>
          </div>
          <button type="button" className="jl-h2-row" onClick={() => needLogin('/my')}>
            <span className="jl-h2">{t('jobs.cabinet')}</span><span className="jl-h2-arrow" aria-hidden>›</span>
          </button>
          <div className="jl-cabinet">
            <button type="button" className="jl-cab" onClick={() => needLogin('/post?category=resumes')}>
              <span className="jl-cab-icon" aria-hidden><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01" /></svg></span>
              <span><b>{t('jobs.cab_resume')}</b><small>{t('jobs.cab_resume_text')}</small></span>
            </button>
            <button type="button" className="jl-cab" onClick={() => needLogin('/chats')}>
              <span className="jl-cab-icon" aria-hidden><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" /></svg></span>
              <span><b>{t('jobs.responses')}</b><small>{t('jobs.cab_responses_text')}</small></span>
            </button>
          </div>
        </div>
      ) : (
        <div className="jl-head">
          <div className="jl-hero">
            <div className="jl-hero-body">
              <div className="jl-hero-title">{t('jobs.hire_title')}</div>
              <div className="jl-hero-text">{t('jobs.hire_text')}</div>
              <button type="button" className="jl-hero-btn" onClick={() => needLogin('/post?category=vacancies')}>{t('jobs.hire_title')}</button>
            </div>
            <img className="jl-hero-img" src={jobArt('hire')} alt="" />
          </div>
          <div className="jl-grid">
            <div className="jl-col">
              <button type="button" className="jl-card" onClick={() => needLogin('/my')}>
                <b>{myVac ? t('jobs.my_vacancies') : t('jobs.no_vacancies')}</b>
                {!!myVac && <small>{t('jobs.active_count', { count: myVac })}</small>}
              </button>
              <button type="button" className="jl-card tall" onClick={toResults}>
                <b>{t('jobs.search_resumes')}</b>
                <small>{items ? t('jobs.resumes_count', { count: total }) : ' '}</small>
              </button>
            </div>
            <div className="jl-col">
              <button type="button" className="jl-card tall" onClick={() => needLogin('/chats')}>
                <b>{t('jobs.responses')}</b><small>{t('jobs.hire_responses_text')}</small>
              </button>
              <button type="button" className="jl-card how" onClick={() => setTipsOpen(true)}><b>{t('jobs.how_title')}</b></button>
            </div>
          </div>
          <h2 className="jl-h2 jl-h2-gap">{t('jobs.find_employee')}</h2>
          {searchBox(t('jobs.hire_search'))}
        </div>
      )}

      <h2 className="jl-h2 jl-results-title" ref={resultsRef}>
        {tab === 'seek' ? (tile ? t(`jobs.tile_${tile.key}`) : t('jobs.fresh_vacancies')) : t('jobs.resumes')}{items ? ` · ${total}` : ''}
      </h2>
      <div className="infinite-grid">
        {items === null ? <CardSkeletons count={6} /> : items.map((l) => <ListingCard key={l.id} listing={l} />)}
      </div>
      {items && !items.length && <p className="jl-empty">{t(tab === 'seek' ? 'jobs.empty_vacancies' : 'jobs.empty_resumes')}</p>}

      {tipsOpen && (
        <div className="jl-tips-layer" onClick={() => setTipsOpen(false)}>
          <div className="jl-tips" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={t('jobs.how_title')}>
            <div className="jl-tips-title">{t('jobs.how_title')}</div>
            <ul>{[1, 2, 3, 4].map((n) => <li key={n}>{t(`jobs.tip_${n}`)}</li>)}</ul>
            <button type="button" className="jl-hero-btn" onClick={() => setTipsOpen(false)}>{t('jobs.tips_ok')}</button>
          </div>
        </div>
      )}
    </div>
  )
}
