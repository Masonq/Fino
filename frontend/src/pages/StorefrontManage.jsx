import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

const priceOf = (l) => (l.price == null ? '' : `${Math.round(l.price).toLocaleString('ru-RU')} ${l.currency === 'EUR' ? '€' : l.currency || ''}`)
const photoOf = (l) => l.photos?.[0] || l.cover_photo || l.photo
const ERR = { slug_format: 'sf.err_slug_format', slug_reserved: 'sf.err_slug_reserved', slug_taken: 'sf.err_slug_taken', name_length: 'sf.err_name', no_active_items: 'sf.err_empty', title_length: 'sf.err_title' }

/**
 * Моя витрина /vitrina. Нет витрины — предложение собрать за одно нажатие (ТЗ: автосборка).
 * Есть — всё на одной странице: статус и публикация, оформление, товары (порядок, убрать/добавить), подборки.
 */
export default function StorefrontManage() {
  const { t, i18n } = useTranslation()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const lang = i18n.language
  const [data, setData] = useState(null)
  const [sf, setSf] = useState(null)
  const [form, setForm] = useState(null)
  const [err, setErr] = useState('')
  const [saved, setSaved] = useState('')
  const [coll, setColl] = useState(null) // редактируемая подборка
  const [pause, setPause] = useState(null)

  useEffect(() => { if (!loading && !user?.id) navigate('/login?returnTo=/vitrina') }, [loading, user?.id, navigate])
  const take = (r) => { setSf(r.storefront); if (r.storefront) setForm({ name: r.storefront.name, description: r.storefront.description || '', slug: r.storefront.slug }) }
  useEffect(() => { if (user?.id) api.sfMe(lang).then((r) => { setData(r); take(r) }).catch(() => setData({})) }, [user?.id, lang])

  const run = (p, msg = 'sf.saved') => {
    setErr('')
    return p.then((r) => { take(r); setSaved(t(msg)); setTimeout(() => setSaved(''), 1800); return true })
      .catch((e) => { setErr(t(ERR[e.code] || 'shops.err_save')); return false })
  }

  if (!data) return <div className="page"><div className="jr-skel" /></div>

  if (!sf) {
    return (
      <div className="page sf-manage">
        <PageHeader title={t('sf.my')} />
        <div className="sf-build">
          <div className="sf-build-title">{t('sf.build_title')}</div>
          <p className="sf-build-text">{data.active_count ? t('sf.build_text', { count: data.active_count }) : t('sf.build_none')}</p>
          {data.active_count > 0 ? (
            <button type="button" className="jr-btn primary wide" onClick={() => run(api.sfAutobuild({}, lang), 'sf.built')}>{t('sf.build_go')}</button>
          ) : (
            <Link className="jr-btn primary wide" to="/post">{t('sf.post_first')}</Link>
          )}
          <ul className="sf-build-list">
            <li>{t('sf.build_p1')}</li><li>{t('sf.build_p2')}</li><li>{t('sf.build_p3')}</li>
          </ul>
        </div>
      </div>
    )
  }

  const ids = sf.items.map((l) => l.id)
  const move = (i, d) => { const n = [...ids]; const j = i + d; if (j < 0 || j >= n.length) return; [n[i], n[j]] = [n[j], n[i]]; run(api.sfItems(n, lang)) }
  const url = `${window.location.origin}/s/${sf.slug}`
  const live = sf.status === 'published' || sf.status === 'paused'

  return (
    <div className="page sf-manage">
      <PageHeader title={t('sf.my')}>{live && <Link className="jr-btn ghost sm sh-head-btn" to={`/s/${sf.slug}`}>{t('sf.open')}</Link>}</PageHeader>

      <div className={`sf-state st-${sf.status}`}>
        <div className="sf-state-row">
          <span className={`sh-status st-${sf.status === 'published' ? 'active' : sf.status === 'blocked' ? 'rejected' : sf.status === 'paused' ? 'moderation' : 'draft'}`}>{t(`sf.st_${sf.status}`)}</span>
          <span className="jr-muted">{t('sf.views_n', { count: sf.views })} · {t('sf.followers_n', { count: sf.followers })}</span>
        </div>
        {live && <div className="sf-url"><span>{url.replace(/^https?:\/\//, '')}</span><button type="button" className="jr-btn ghost sm" onClick={() => navigator.clipboard?.writeText(url).then(() => { setSaved(t('sf.link_copied')); setTimeout(() => setSaved(''), 1800) })}>{t('sf.copy')}</button></div>}
        <div className="jr-actions">
          {sf.status === 'draft' && <button type="button" className="jr-btn primary" onClick={() => run(api.sfState({ action: 'publish' }, lang), 'sf.published')}>{t('sf.publish')}</button>}
          {sf.status === 'published' && <button type="button" className="jr-btn ghost" onClick={() => setPause({ until: '', note: '' })}>{t('sf.pause')}</button>}
          {sf.status === 'paused' && <button type="button" className="jr-btn primary" onClick={() => run(api.sfState({ action: 'resume' }, lang))}>{t('sf.resume')}</button>}
          {live && <button type="button" className="jr-btn ghost" onClick={() => run(api.sfState({ action: 'unpublish' }, lang))}>{t('sf.unpublish')}</button>}
        </div>
        {pause && (
          <div className="jr-invite">
            <label className="jr-field"><span>{t('sf.pause_until')}</span><input type="date" value={pause.until} onChange={(e) => setPause({ ...pause, until: e.target.value })} /></label>
            <label className="jr-field"><span>{t('sf.pause_note')}</span><input value={pause.note} maxLength={160} placeholder={t('sf.pause_note_ph')} onChange={(e) => setPause({ ...pause, note: e.target.value })} /></label>
            <div className="jr-actions">
              <button type="button" className="jr-btn ghost" onClick={() => setPause(null)}>{t('jobresp.cancel')}</button>
              <button type="button" className="jr-btn primary" onClick={() => run(api.sfState({ action: 'pause', until: pause.until || null, note: pause.note }, lang)).then((ok) => ok && setPause(null))}>{t('sf.pause')}</button>
            </div>
          </div>
        )}
      </div>

      <div className="sh-section-title">{t('sf.look')}</div>
      <label className="jr-field"><span>{t('sf.name')}</span><input value={form.name} maxLength={60} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label className="jr-field"><span>{t('sf.description')}</span><textarea rows={3} maxLength={300} value={form.description} placeholder={t('sf.description_ph')} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
      <label className="jr-field"><span>{t('sf.address')}</span>
        <div className="sf-slug"><span>plonk.rs/s/</span><input value={form.slug} maxLength={40} onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })} /></div>
      </label>
      {sf.cover_options.length > 0 && (
        <>
          <div className="jr-field"><span>{t('sf.cover')}</span></div>
          <div className="sf-covers">
            {sf.cover_options.map((c) => (
              <button key={c} type="button" className={`sf-cover-opt${sf.cover_url === c ? ' on' : ''}`} onClick={() => run(api.sfEdit({ cover_url: c }, lang))}><img src={c} alt="" /></button>
            ))}
          </div>
        </>
      )}
      <button type="button" className="jr-btn primary wide" onClick={() => run(api.sfEdit(form, lang))}>{t('shops.save_draft')}</button>

      <div className="sh-section-title">{t('sf.items_title', { n: sf.items.length })}</div>
      {sf.items.map((l, i) => (
        <div key={l.id} className="sh-pick picked">
          {photoOf(l) && <img src={photoOf(l)} alt="" />}
          <div className="sh-pick-text"><div className="sh-item-title">{l.title}</div><div className="jr-muted">{priceOf(l)}</div></div>
          <button type="button" className="sf-arrow" disabled={i === 0} aria-label={t('sf.up')} onClick={() => move(i, -1)}>↑</button>
          <button type="button" className="sf-arrow" disabled={i === sf.items.length - 1} aria-label={t('sf.down')} onClick={() => move(i, 1)}>↓</button>
          <button type="button" className="sh-x" aria-label={t('shops.remove')} onClick={() => run(api.sfItems(ids.filter((x) => x !== l.id), lang))}>×</button>
        </div>
      ))}
      {sf.not_added.length > 0 && <div className="jr-hint">{t('sf.not_added')}</div>}
      {sf.not_added.map((l) => (
        <button key={l.id} type="button" className="sh-pick" onClick={() => run(api.sfItems([...ids, l.id], lang))}>
          {photoOf(l) && <img src={photoOf(l)} alt="" />}
          <div className="sh-pick-text"><div className="sh-item-title">{l.title}</div><div className="jr-muted">{priceOf(l)}</div></div>
          <span className="sh-add">+</span>
        </button>
      ))}

      <div className="sh-section-title">{t('sf.collections')}</div>
      <div className="jr-hint sf-left">{t('sf.collections_hint')}</div>
      {sf.collections.map((c) => (
        <div key={c.id} className="sf-coll-row">
          <div className="sh-pick-text"><div className="sh-item-title">{c.title}{c.status === 'hidden' ? ` · ${t('sf.hidden')}` : ''}</div><div className="jr-muted">{t('sf.items_n', { count: c.listing_ids.length })}</div></div>
          <button type="button" className="jr-btn ghost sm" onClick={() => setColl({ ...c })}>{t('shops.edit')}</button>
        </div>
      ))}
      {!coll && <button type="button" className="jr-btn ghost wide" onClick={() => setColl({ id: null, title: '', description: '', status: 'active', sort: 'manual', listing_ids: [] })}>{t('sf.add_collection')}</button>}
      {coll && (
        <div className="sf-coll-edit">
          <label className="jr-field"><span>{t('sf.coll_title')}</span><input value={coll.title} maxLength={40} placeholder={t('sf.coll_title_ph')} onChange={(e) => setColl({ ...coll, title: e.target.value })} /></label>
          <label className="jr-field"><span>{t('sf.description')}</span><input value={coll.description || ''} maxLength={160} onChange={(e) => setColl({ ...coll, description: e.target.value })} /></label>
          <div className="sf-coll-opts">
            <label><input type="checkbox" checked={coll.sort === 'newest'} onChange={(e) => setColl({ ...coll, sort: e.target.checked ? 'newest' : 'manual' })} /> {t('sf.newest_first')}</label>
            <label><input type="checkbox" checked={coll.status === 'hidden'} onChange={(e) => setColl({ ...coll, status: e.target.checked ? 'hidden' : 'active' })} /> {t('sf.hide')}</label>
          </div>
          <div className="sf-coll-items">
            {sf.items.map((l) => {
              const on = coll.listing_ids.includes(l.id)
              return (
                <button key={l.id} type="button" className={`sf-coll-item${on ? ' on' : ''}`} onClick={() => setColl({ ...coll, listing_ids: on ? coll.listing_ids.filter((x) => x !== l.id) : [...coll.listing_ids, l.id] })}>
                  {photoOf(l) && <img src={photoOf(l)} alt="" />}<span>{l.title}</span>{on && <span className="sf-check">✓</span>}
                </button>
              )
            })}
          </div>
          <div className="jr-actions">
            {coll.id && <button type="button" className="jr-btn danger" onClick={() => { if (window.confirm(t('sf.confirm_delete_coll'))) run(api.sfDeleteCollection(coll.id, lang)).then((ok) => ok && setColl(null)) }}>{t('shops.remove')}</button>}
            <button type="button" className="jr-btn ghost" onClick={() => setColl(null)}>{t('jobresp.cancel')}</button>
            <button type="button" className="jr-btn primary" onClick={() => {
              const body = { title: coll.title, description: coll.description, status: coll.status, sort: coll.sort, listing_ids: coll.listing_ids }
              run(coll.id ? api.sfEditCollection(coll.id, body, lang) : api.sfAddCollection(body, lang)).then((ok) => ok && setColl(null))
            }}>{t('shops.save_draft')}</button>
          </div>
        </div>
      )}
      {err && <div className="jr-err sf-sticky-msg">{err}</div>}
      {saved && <div className="sf-toast" role="status">{saved}</div>}
    </div>
  )
}
