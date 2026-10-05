import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { RowSkeletons } from '../components/Skeletons'

const money = (v, c) => (v == null ? '' : `${Number(v).toLocaleString('ru-RU')} ${c === 'EUR' ? '€' : c}`)

/** Мои шопсы со статистикой, заказы шопсов (биржа продавцов и авторов) и заявка на «Автора». */
export default function ShopsCabinet() {
  const { t, i18n } = useTranslation()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [tab, setTab] = useState(['orders', 'creator'].includes(params.get('tab')) ? params.get('tab') : 'shops')
  const [data, setData] = useState(null)

  useEffect(() => { if (!loading && !user?.id) navigate('/login?returnTo=/shops/mine') }, [loading, user?.id, navigate])
  const reload = () => api.shopsMine().then(setData).catch(() => setData({ items: [], creator: {} }))
  useEffect(() => { if (user?.id) reload() }, [user?.id])

  const creator = data?.creator?.status
  return (
    <div className="page sh-cab">
      <PageHeader title={t('shops.cabinet')}>
        <Link className="jr-btn primary sm sh-head-btn" to="/shops/new">{t('shops.create_short')}</Link>
      </PageHeader>
      <div className="jr-tabs" role="tablist">
        {['shops', 'orders', 'creator'].map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} className={`jr-tab${tab === k ? ' on' : ''}`} onClick={() => setTab(k)}>{t(`shops.tab_${k}`)}</button>
        ))}
      </div>
      {tab === 'shops' && <MyShops data={data} reload={reload} />}
      {tab === 'orders' && <Orders creator={creator === 'approved'} lang={i18n.language} />}
      {tab === 'creator' && <Creator status={creator} onDone={reload} />}
    </div>
  )
}

function MyShops({ data, reload }) {
  const { t } = useTranslation()
  if (!data) return <RowSkeletons count={3} thumb="tall" />
  if (!data.items.length) return <div className="empty-state"><p className="empty-hint">{t('shops.none_mine')}</p><Link className="jr-btn primary" to="/shops/new">{t('shops.create_first')}</Link></div>
  return data.items.map((s) => (
    <div key={s.id} className="sh-mine">
      <div className="sh-mine-poster">{s.poster_url ? <img src={s.poster_url} alt="" /> : <span className="sh-spin" />}</div>
      <div className="sh-mine-body">
        <span className={`sh-status st-${s.status}`}>{t(`shops.st_${s.status}`)}</span>
        <div className="sh-mine-caption">{s.caption || t('shops.no_caption')}</div>
        {s.status === 'rejected' && s.reject_reason && <div className="jr-err sm">{s.reject_reason}</div>}
        {s.stats && (
          <div className="sh-stats">
            <span title={t('shops.views')}>👁 {s.stats.views}</span>
            <span title={t('shops.completes')}>✓ {s.stats.completes}</span>
            <span title={t('shops.taps')}>👆 {s.stats.taps}</span>
            <span title={t('shops.chats')}>💬 {s.stats.chats}</span>
          </div>
        )}
        <div className="jr-actions">
          {s.status === 'active' && <Link className="jr-btn ghost sm" to={`/shops?start=${s.id}`}>{t('shops.watch')}</Link>}
          {s.status !== 'processing' && <Link className="jr-btn ghost sm" to={`/shops/${s.id}/edit`}>{t('shops.edit')}</Link>}
          <button type="button" className="jr-btn danger sm" onClick={() => { if (window.confirm(t('shops.confirm_remove'))) api.shopRemove(s.id).then(reload) }}>{t('shops.remove')}</button>
        </div>
      </div>
    </div>
  ))
}

function Orders({ creator, lang }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(null)
  const [taken, setTaken] = useState([])
  const [mine, setMine] = useState([])
  const [listings, setListings] = useState([])
  const [form, setForm] = useState({ listing_id: '', fee: '', currency: 'EUR', note: '' })
  const [err, setErr] = useState('')
  const reload = () => {
    api.shopOrders('mine').then((r) => setMine(r.items)).catch(() => {})
    if (creator) {
      api.shopOrders('open').then((r) => setOpen(r.items)).catch(() => setOpen([]))
      api.shopOrders('taken').then((r) => setTaken(r.items)).catch(() => {})
    }
  }
  useEffect(() => {
    reload()
    api.myListings(lang).then((r) => setListings((r.items || []).filter((l) => l.status === 'active'))).catch(() => {})
  }, [creator, lang]) // eslint-disable-line react-hooks/exhaustive-deps

  const create = () => {
    if (!form.listing_id) { setErr(t('shops.err_pick_listing')); return }
    setErr('')
    api.shopOrderCreate({ ...form, fee: form.fee ? Number(form.fee) : null })
      .then(() => { setForm({ listing_id: '', fee: '', currency: 'EUR', note: '' }); reload() })
      .catch((e) => setErr(e.code === 'order_exists' ? t('shops.err_order_exists') : t('shops.err_save')))
  }
  const take = (o) => api.shopOrderTake(o.id).then((r) => navigate(`/chat/${r.chat_id}`)).catch(() => reload())

  const card = (o, actions) => (
    <div key={o.id} className="sh-order">
      {o.listing?.photo && <img src={o.listing.photo} alt="" />}
      <div className="sh-pick-text">
        <div className="sh-item-title">{o.listing?.title}</div>
        <div className="jr-muted">{o.fee ? t('shops.fee', { v: money(o.fee, o.currency) }) : t('shops.fee_none')} · {t(`shops.ost_${o.status}`)}</div>
        {o.note && <div className="sh-order-note">{o.note}</div>}
        <div className="jr-actions">{actions}</div>
      </div>
    </div>
  )

  return (
    <>
      <div className="sh-section-title">{t('shops.order_new')}</div>
      <div className="jr-hint">{t('shops.order_hint')}</div>
      <label className="jr-field"><span>{t('shops.order_listing')}</span>
        <select value={form.listing_id} onChange={(e) => setForm({ ...form, listing_id: e.target.value })}>
          <option value="">{t('shops.pick')}</option>
          {listings.map((l) => <option key={l.id} value={l.id}>{l.title}</option>)}
        </select>
      </label>
      <div className="sh-row">
        <label className="jr-field"><span>{t('shops.order_fee')}</span>
          <input inputMode="numeric" value={form.fee} onChange={(e) => setForm({ ...form, fee: e.target.value.replace(/\D/g, '').slice(0, 7) })} placeholder="0" />
        </label>
        <label className="jr-field sh-cur"><span>&nbsp;</span>
          <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}><option>EUR</option><option>RSD</option></select>
        </label>
      </div>
      <label className="jr-field"><span>{t('shops.order_note')}</span>
        <textarea rows={2} value={form.note} maxLength={1000} placeholder={t('shops.order_note_ph')} onChange={(e) => setForm({ ...form, note: e.target.value })} />
      </label>
      {err && <div className="jr-err">{err}</div>}
      <button type="button" className="jr-btn primary wide" onClick={create}>{t('shops.order_create')}</button>

      {mine.length > 0 && <div className="sh-section-title">{t('shops.my_orders')}</div>}
      {mine.map((o) => card(o, <>
        {o.creator && <span className="jr-muted">{t('shops.taken_by', { name: o.creator.name })}</span>}
        {(o.status === 'open' || o.status === 'taken') && <button type="button" className="jr-btn danger sm" onClick={() => api.shopOrderCancel(o.id).then(reload)}>{t('shops.cancel_order')}</button>}
      </>))}

      {creator && (
        <>
          {taken.length > 0 && <div className="sh-section-title">{t('shops.taken_orders')}</div>}
          {taken.map((o) => card(o, <>
            {o.status === 'taken' && <Link className="jr-btn primary sm" to={`/shops/new?order=${o.id}`}>{t('shops.shoot')}</Link>}
            {o.status === 'taken' && <button type="button" className="jr-btn ghost sm" onClick={() => api.shopOrderCancel(o.id).then(reload)}>{t('shops.drop_order')}</button>}
          </>))}
          <div className="sh-section-title">{t('shops.open_orders')}</div>
          {open === null ? <RowSkeletons count={2} /> : !open.length ? <div className="jr-hint">{t('shops.no_open_orders')}</div>
            : open.map((o) => card(o, <button type="button" className="jr-btn primary sm" onClick={() => take(o)}>{t('shops.take')}</button>))}
        </>
      )}
    </>
  )
}

function Creator({ status, onDone }) {
  const { t } = useTranslation()
  const [form, setForm] = useState({ links: '', audience: '', about: '' })
  const [err, setErr] = useState('')
  if (status === 'approved') return <div className="sh-creator ok">🎬 {t('shops.creator_ok')}</div>
  if (status === 'pending') return <div className="sh-creator">⏳ {t('shops.creator_pending')}</div>
  const send = () => {
    if (form.links.trim().length < 5) { setErr(t('shops.err_links')); return }
    api.shopCreatorApply({ ...form, audience: form.audience ? Number(form.audience) : null }).then(onDone).catch(() => setErr(t('shops.err_save')))
  }
  return (
    <>
      <div className="sh-creator">{status === 'rejected' ? t('shops.creator_rejected') : t('shops.creator_why')}</div>
      <label className="jr-field"><span>{t('shops.creator_links')}</span>
        <input value={form.links} placeholder="instagram.com/…, t.me/…" onChange={(e) => setForm({ ...form, links: e.target.value })} />
      </label>
      <label className="jr-field"><span>{t('shops.creator_audience')}</span>
        <input inputMode="numeric" value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value.replace(/\D/g, '').slice(0, 9) })} />
      </label>
      <label className="jr-field"><span>{t('shops.creator_about')}</span>
        <textarea rows={3} value={form.about} onChange={(e) => setForm({ ...form, about: e.target.value })} />
      </label>
      {err && <div className="jr-err">{err}</div>}
      <button type="button" className="jr-btn primary wide" onClick={send}>{t('shops.creator_send')}</button>
    </>
  )
}

/** Модерация: шопсы на проверке и заявки авторов. */
export function AdminShops() {
  const { t } = useTranslation()
  const [q, setQ] = useState(null)
  const reload = () => api.shopAdminQueue().then(setQ).catch(() => setQ({ shops: [], creators: [] }))
  useEffect(() => { reload() }, [])
  const decide = (fn, id, approve) => {
    const reason = approve ? null : window.prompt(t('shops.reject_reason'))
    if (!approve && reason === null) return
    fn(id, { approve, reason }).then(reload)
  }
  return (
    <div className="page sh-cab">
      <PageHeader title={t('shops.moderation')} />
      {q === null ? <RowSkeletons count={3} thumb="tall" /> : (
        <>
          <div className="sh-section-title">{t('shops.mod_shops', { n: q.shops.length })}</div>
          {q.shops.map((s) => (
            <div key={s.id} className="sh-mod">
              <video src={s.video_url} poster={s.poster_url} controls playsInline className="sh-mod-video" />
              <div className="sh-pick-text">
                <div className="sh-item-title">{s.author?.name}{s.is_ad ? ` · ${t('shops.ad')}` : ''}</div>
                {s.caption && <div className="sh-order-note">{s.caption}</div>}
                {s.items.map((it) => <Link key={it.item_id} className="jr-resume" to={it.path}>{it.title} · {t('shops.from_sec', { s: it.appear_at })}</Link>)}
                <div className="jr-actions">
                  <button type="button" className="jr-btn primary sm" onClick={() => decide(api.shopAdminShop, s.id, true)}>{t('shops.approve')}</button>
                  <button type="button" className="jr-btn danger sm" onClick={() => decide(api.shopAdminShop, s.id, false)}>{t('shops.reject')}</button>
                </div>
              </div>
            </div>
          ))}
          <div className="sh-section-title">{t('shops.mod_creators', { n: q.creators.length })}</div>
          {q.creators.map((a) => (
            <div key={a.id} className="jr-card">
              <div className="jr-name">{a.user.name}{a.audience ? ` · ${a.audience.toLocaleString('ru-RU')}` : ''}</div>
              <div className="sh-order-note">{a.links}</div>
              {a.about && <p className="jr-about">{a.about}</p>}
              <div className="jr-actions">
                <button type="button" className="jr-btn primary sm" onClick={() => decide(api.shopAdminCreator, a.id, true)}>{t('shops.approve')}</button>
                <button type="button" className="jr-btn danger sm" onClick={() => decide(api.shopAdminCreator, a.id, false)}>{t('shops.reject')}</button>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
