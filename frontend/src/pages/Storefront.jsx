import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import ListingCard from '../components/ListingCard'
import PageHeader from '../components/PageHeader'
import { CardSkeletons } from '../components/Skeletons'
import Sheet from '../components/Sheet'
import { toast } from 'sonner'
import VerifiedMark from '../components/VerifiedMark'

const REASONS = ['spam', 'fraud', 'prohibited_item', 'offensive_user', 'other']

/**
 * Витрина продавца /s/:slug (и подборка /s/:slug/c/:cid): обложка, кто продаёт, подписка и «Поделиться»,
 * подборки чипами, товары — обычными карточками PLONK, видео-шопсы продавца отдельной вкладкой.
 */
export default function Storefront() {
  const { slug, cid } = useParams()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [sf, setSf] = useState(null)
  const [error, setError] = useState(false)
  const [tab, setTab] = useState('items')
  const [busy, setBusy] = useState(false)
  const [report, setReport] = useState(false)

  useEffect(() => {
    setSf(null); setError(false)
    api.sfPublic(slug, i18n.language).then((d) => {
      setSf(d)
      if (d.moved) navigate(`/s/${d.slug}${cid ? `/c/${cid}` : ''}`, { replace: true })
    }).catch(() => setError(true))
  }, [slug, i18n.language]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!sf) return
    const coll = sf.collections.find((c) => c.id === cid)
    document.title = `${coll ? `${coll.title} — ` : ''}${sf.name} — ${t('sf.title_suffix')}`
  }, [sf, cid, t])

  const coll = sf?.collections.find((c) => c.id === cid)
  const items = useMemo(() => {
    if (!sf) return []
    if (!coll) return sf.items
    const byId = Object.fromEntries(sf.items.map((l) => [l.id, l]))
    return coll.listing_ids.map((id) => byId[id]).filter(Boolean)
  }, [sf, coll])

  const flash = (m) => toast(m)
  const follow = () => {
    if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`); return }
    setBusy(true)
    api.sfFollow(sf.slug, !sf.following).then((r) => setSf({ ...sf, following: r.following }))
      .finally(() => setBusy(false))
  }
  const share = async () => {
    const url = `${window.location.origin}/s/${sf.slug}${coll ? `/c/${coll.id}` : ''}`
    const title = coll ? `${coll.title} — ${sf.name}` : sf.name
    try {
      if (navigator.share) { await navigator.share({ title, url }); return }
    } catch { return }
    try { await navigator.clipboard.writeText(url); flash(t('sf.link_copied')) } catch { window.prompt(t('sf.copy_link'), url) }
  }
  const sendReport = (reason) => {
    if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`); return }
    api.sfReport(sf.slug, { reason }).then(() => { setReport(false); flash(t('sf.report_sent')) })
  }

  if (error) {
    return (
      <div className="page">
        <PageHeader title={t('sf.not_found_title')} />
        <div className="empty-state"><p className="empty-hint">{t('sf.not_found')}</p><Link className="jr-btn primary" to="/vitriny">{t('sf.discover')}</Link></div>
      </div>
    )
  }
  if (!sf) {
    // скелет витрины: обложка, аватар, имя, кнопки, сетка карточек — те же места, что у настоящей
    return (
      <div className="page sf-page" aria-hidden="true">
        <div className="sf-cover sk-block" />
        <div className="sf-head">
          <div className="sf-ava sk-block" />
          <div className="sk-block sf-sk-line" style={{ width: '46%', height: 26, marginTop: 10 }} />
          <div className="sk-block sf-sk-line" style={{ width: '30%', height: 14, marginTop: 8 }} />
          <div className="sf-actions"><span className="sk-block sf-sk-btn" /><span className="sk-block sf-sk-btn" /></div>
        </div>
        <div className="feed-grid sf-grid"><CardSkeletons count={4} /></div>
      </div>
    )
  }

  const pausedUntil = sf.status === 'paused' && sf.pause_until ? new Date(sf.pause_until).toLocaleDateString(undefined, { day: 'numeric', month: 'long' }) : null
  return (
    <div className="page sf-page">
      <div className="sf-cover">
        {sf.cover_url ? <img src={sf.cover_url} alt="" /> : <span className="sf-cover-empty" />}
        <button type="button" className="sf-back" onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))} aria-label={t('shops.close')}>
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
      </div>
      <div className="sf-head">
        <div className="sf-ava">{sf.owner.avatar ? <img src={sf.owner.avatar} alt="" /> : (sf.name || '?')[0]}</div>
        <h1 className="sf-name">{sf.name} <VerifiedMark official={sf.owner.official} verified={sf.owner.verified} size={22} /></h1>
        <div className="sf-sub">
          {sf.owner.name !== sf.name && <><Link to={`/seller/${sf.owner.id}`}>{sf.owner.name}</Link><span>·</span></>}
          <span>{t('sf.items_n', { count: sf.items.length })}</span>
          {sf.followers != null && <><span>·</span><span>{t('sf.followers_n', { count: sf.followers })}</span></>}
        </div>
        {sf.description && <p className="sf-desc">{sf.description}</p>}
        {sf.status === 'paused' && (
          <div className="sf-paused">🌴 {pausedUntil ? t('sf.paused_until', { date: pausedUntil }) : t('sf.paused')}{sf.pause_note ? ` · ${sf.pause_note}` : ''}</div>
        )}
        <div className="sf-actions">
          {sf.mine ? (
            <Link className="jr-btn primary" to="/vitrina">{t('sf.manage')}</Link>
          ) : (
            <button type="button" className={`jr-btn ${sf.following ? 'ghost' : 'primary'}`} disabled={busy} onClick={follow}>
              {sf.following ? t('sf.following') : t('sf.follow')}
            </button>
          )}
          <button type="button" className="jr-btn ghost" onClick={share}>{t('sf.share')}</button>
          {!sf.mine && <button type="button" className="jr-btn ghost sf-more" aria-label={t('sf.report')} onClick={() => setReport(true)}>···</button>}
        </div>
      </div>

      {(sf.shops.length > 0) && (
        <div className="jr-tabs sf-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={tab === 'items'} className={`jr-tab${tab === 'items' ? ' on' : ''}`} onClick={() => setTab('items')}>{t('sf.tab_items')}</button>
          <button type="button" role="tab" aria-selected={tab === 'video'} className={`jr-tab${tab === 'video' ? ' on' : ''}`} onClick={() => setTab('video')}>{t('sf.tab_video')}<span className="jr-tab-n">{sf.shops.length}</span></button>
        </div>
      )}

      {tab === 'video' ? (
        <div className="sf-videos">
          {sf.shops.map((s) => (
            <Link key={s.id} className="shs-tile sf-video" to={`/shops?start=${s.id}`}>
              {s.poster_url && <img src={s.poster_url} alt="" loading="lazy" />}
              <span className="shs-shade" /><span className="shs-author">{s.caption}</span>
            </Link>
          ))}
        </div>
      ) : (
        <>
          {sf.collections.length > 0 && (
            <div className="sf-colls">
              <Link className={`jr-tab${!coll ? ' on' : ''}`} to={`/s/${sf.slug}`} replace>{t('sf.all')}</Link>
              {sf.collections.map((c) => (
                <Link key={c.id} className={`jr-tab${coll?.id === c.id ? ' on' : ''}`} to={`/s/${sf.slug}/c/${c.id}`} replace>
                  {c.drop_at ? '⏳ ' : ''}{c.title}<span className="jr-tab-n">{c.count ?? c.listing_ids.length}</span>
                </Link>
              ))}
            </div>
          )}
          {coll?.description && <p className="sf-desc sf-coll-desc">{coll.description}</p>}
          {coll?.drop_at && <DropCountdown at={coll.drop_at} count={coll.count} following={sf.following} onFollow={sf.mine ? null : follow} />}
          {coll?.drop_at ? null : items.length === 0 ? (
            <div className="empty-state"><p className="empty-hint">{t('sf.empty')}</p></div>
          ) : (
            <div className="feed-grid sf-grid">{items.map((l, i) => <ListingCard key={l.id} listing={l} priority={i < 4} />)}</div>
          )}
        </>
      )}

      <SimilarStores slug={sf.slug} city={sf.city} />

      <Sheet open={report} onClose={() => setReport(false)} title={t('sf.report')}>
            {REASONS.map((r) => <button key={r} type="button" className="sf-reason" onClick={() => sendReport(r)}>{t(`sf.reason_${r}`)}</button>)}
      </Sheet>
    </div>
  )
}

/** Каталог витрин /vitriny: популярные и новые, поиск по названию и продавцу. */
export function StorefrontDiscover() {
  const { t } = useTranslation()
  const [sort, setSort] = useState('popular')
  const [q, setQ] = useState('')
  const [items, setItems] = useState(null)
  useEffect(() => {
    const tm = setTimeout(() => {
      const city = (() => { try { return localStorage.getItem('plonk_city') || '' } catch { return '' } })()
      api.sfDiscover({ sort, q: q.trim() || undefined, city: city || undefined }).then((r) => setItems(r.items)).catch(() => setItems([]))
    }, q ? 300 : 0)
    return () => clearTimeout(tm)
  }, [sort, q])
  return (
    <div className="page sf-discover">
      <PageHeader title={t('sf.discover_short')} kicker={t('sf.discover_kicker')}><Link className="jr-btn primary sm sh-head-btn" to="/vitrina">{t('sf.my')}</Link></PageHeader>
      <input className="sh-search" value={q} placeholder={t('sf.search_ph')} onChange={(e) => setQ(e.target.value)} />
      <div className="jr-tabs">
        {['popular', 'new'].map((k) => <button key={k} type="button" className={`jr-tab${sort === k ? ' on' : ''}`} onClick={() => setSort(k)}>{t(`sf.sort_${k}`)}</button>)}
      </div>
      {items === null ? <div className="sf-discover-sk">{[0, 1, 2].map((i) => <div key={i} className="sf-card"><div className="sf-card-previews">{[0, 1, 2].map((k) => <span key={k} className="sk-block" style={{ aspectRatio: '1', borderRadius: 10 }} />)}</div><div className="sk-block sf-sk-line" style={{ width: '50%', height: 18 }} /><div className="sk-block sf-sk-line" style={{ width: '35%', height: 13, marginTop: 6 }} /></div>)}</div> : items.length === 0 ? (
        <div className="empty-state"><p className="empty-hint">{t('sf.none')}</p></div>
      ) : items.map((s) => (
        <Link key={s.slug} className="sf-card" to={`/s/${s.slug}`}>
          <div className="sf-card-previews">{s.previews.map((p, i) => <img key={i} src={p} alt="" loading="lazy" />)}</div>
          <div className="sf-card-name">{s.name}</div>
          <div className="jr-muted">{t('sf.items_n', { count: s.count })}{s.city ? ` · ${s.city}` : ''}{s.followers != null ? ` · ${t('sf.followers_n', { count: s.followers })}` : ''}</div>
        </Link>
      ))}
    </div>
  )
}

/** Закрытый дроп: обратный отсчёт до открытия и подписка, чтобы не пропустить. */
function DropCountdown({ at, count, following, onFollow }) {
  const { t } = useTranslation()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id) }, [])
  const target = new Date(at).getTime()
  const left = Math.max(0, target - now)
  useEffect(() => { if (left === 0) { const id = setTimeout(() => window.location.reload(), 800); return () => clearTimeout(id) } return undefined }, [left === 0]) // eslint-disable-line react-hooks/exhaustive-deps
  const d = Math.floor(left / 864e5), h = Math.floor(left / 36e5) % 24, m = Math.floor(left / 6e4) % 60, sec = Math.floor(left / 1e3) % 60
  const pad = (n) => String(n).padStart(2, '0')
  return (
    <div className="sf-drop">
      <div className="sf-drop-label">{t('sf.drop_opens')}</div>
      <div className="sf-drop-timer">{d > 0 ? `${d} ${t('sf.drop_days')} ` : ''}{pad(h)}:{pad(m)}:{pad(sec)}</div>
      <div className="sf-drop-sub">{t('sf.drop_items', { count })} · {new Date(at).toLocaleString(undefined, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })}</div>
      {onFollow && !following && <button type="button" className="jr-btn primary" onClick={onFollow}>{t('sf.drop_notify')}</button>}
      {onFollow && following && <div className="sf-drop-sub">✓ {t('sf.drop_will_notify')}</div>}
    </div>
  )
}

/** «Похожие витрины» внизу витрины — продавцы того же города; покупатель не упирается в конец страницы. */
function SimilarStores({ slug, city }) {
  const { t } = useTranslation()
  const [items, setItems] = useState(null)
  useEffect(() => {
    let alive = true
    api.sfDiscover({ city: city || undefined, limit: 12 })
      .then((r) => alive && setItems((r.items || []).filter((x) => x.slug !== slug).slice(0, 8)))
      .catch(() => alive && setItems([]))
    return () => { alive = false }
  }, [slug, city])
  if (!items || items.length === 0) return null
  return (
    <section className="hs sf-similar">
      <div className="hs-head"><h2 className="hs-title">{t('sf.similar')}</h2><Link to="/vitriny" className="hs-all">{t('hs.all')}</Link></div>
      <div className="hs-row">
        {items.map((x) => (
          <Link key={x.slug} to={`/s/${x.slug}`} className="hs-store">
            <span className="hs-store-grid">{x.previews.slice(0, 3).map((p, i) => <img key={i} src={p} alt="" loading="lazy" />)}</span>
            <span className="hs-store-name">{x.name}</span>
            <span className="hs-store-sub">{t('sf.items_n', { count: x.count })}{x.city ? ` · ${x.city}` : ''}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
