import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import ShopsExplainer from '../components/ShopsExplainer'

const MAX_ITEMS = 5
const priceOf = (l) => (l.price == null ? '' : `${Math.round(l.price).toLocaleString('ru-RU')} ${l.currency === 'EUR' ? '€' : l.currency || ''}`)

/**
 * Снять шопс: видео (до минуты, вертикальное) → до 5 объявлений, у каждого своя секунда появления →
 * подпись → на проверку. Видео обрабатывается на сервере, пока человек выбирает товары.
 */
export default function ShopEditor() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const orderId = params.get('order')
  const { t, i18n } = useTranslation()
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [shop, setShop] = useState(null)
  const [progress, setProgress] = useState(null)
  const [err, setErr] = useState('')
  const [caption, setCaption] = useState('')
  const [items, setItems] = useState([]) // [{ id, title, photo, price, currency, appear_at }]
  const [mine, setMine] = useState([])
  const [creator, setCreator] = useState(false)
  const [q, setQ] = useState('')
  const [found, setFound] = useState([])
  const [busy, setBusy] = useState(false)
  const preview = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => { if (!loading && !user?.id) navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname + window.location.search)}`) }, [loading, user?.id, navigate])

  useEffect(() => {
    if (!user?.id) return
    api.myListings(i18n.language).then((r) => setMine((r.items || []).filter((l) => l.status === 'active'))).catch(() => {})
    api.shopsMine().then((r) => setCreator(r.creator?.status === 'approved')).catch(() => {})
    if (orderId) {
      api.shopOrders('taken').then((r) => {
        const o = (r.items || []).find((x) => x.id === orderId)
        if (o?.listing) setItems((cur) => (cur.some((x) => x.id === o.listing.id) ? cur : [{ ...o.listing, appear_at: 0 }, ...cur]))
      }).catch(() => {})
    }
  }, [user?.id, i18n.language, orderId])

  useEffect(() => {
    if (!id) return
    api.shopGet(id).then((s) => {
      setShop(s); setCaption(s.caption || '')
      setItems(s.items.map((it) => ({ ...it, id: it.id })))
    }).catch(() => setErr(t('shops.err_load')))
  }, [id, t])

  // пока видео обрабатывается — спрашиваем раз в 2 секунды
  useEffect(() => {
    if (shop?.status !== 'processing') return undefined
    const tm = setInterval(() => api.shopGet(shop.id).then((s) => { if (s.status !== 'processing') setShop((cur) => ({ ...cur, ...s, caption: cur.caption })) }).catch(() => {}), 2000)
    return () => clearInterval(tm)
  }, [shop?.status, shop?.id])

  // поиск чужих объявлений — только авторам
  useEffect(() => {
    if (!creator || q.trim().length < 2) { setFound([]); return undefined }
    const tm = setTimeout(() => api.searchListings({ q: q.trim(), limit: 10, lang: i18n.language })
      .then((r) => setFound(r.items || [])).catch(() => setFound([])), 300)
    return () => clearTimeout(tm)
  }, [q, creator, i18n.language])

  const pick = async (file) => {
    if (!file) return
    setErr('')
    if (file.size > 150 * 1024 * 1024) { setErr(t('shops.err_big')); return }
    // длину проверяем ещё до загрузки — чтобы не ждать минуту ради отказа
    const dur = await new Promise((res) => {
      const v = document.createElement('video')
      v.preload = 'metadata'
      v.onloadedmetadata = () => { res(v.duration); URL.revokeObjectURL(v.src) }
      v.onerror = () => res(0)
      v.src = URL.createObjectURL(file)
    })
    if (dur > 61) { setErr(t('shops.err_long')); return }
    setProgress(0)
    try {
      const s = await api.shopUpload(file, setProgress)
      setShop(s)
      navigate(`/shops/${s.id}/edit${orderId ? `?order=${orderId}` : ''}`, { replace: true })
    } catch (e) {
      setErr(e.code === 'file_too_large' ? t('shops.err_big') : e.code === 'unsupported_format' ? t('shops.err_format') : t('shops.err_upload'))
    } finally { setProgress(null) }
  }

  const add = (l) => {
    if (items.length >= MAX_ITEMS || items.some((x) => x.id === l.id)) return
    const at = preview.current ? Math.round(preview.current.currentTime * 10) / 10 : 0
    setItems([...items, { id: l.id, title: l.title, photo: l.photo || l.cover_photo || l.photos?.[0], price: l.price, currency: l.currency, appear_at: at }])
    setQ('')
  }
  const setAt = (lid) => {
    const at = preview.current ? Math.round(preview.current.currentTime * 10) / 10 : 0
    setItems(items.map((x) => (x.id === lid ? { ...x, appear_at: at } : x)))
  }

  const save = async (submit) => {
    if (!shop) return
    if (submit && !items.length) { setErr(t('shops.err_no_items')); return }
    setBusy(true); setErr('')
    try {
      await api.shopUpdate(shop.id, { caption, items: items.map((x) => ({ listing_id: x.id, appear_at: x.appear_at || 0 })), order_id: orderId || null })
      if (submit) await api.shopSubmit(shop.id)
      navigate('/shops/mine')
    } catch (e) {
      setErr(e.code === 'only_own_listings' ? t('shops.err_own') : e.code === 'not_ready' ? t('shops.err_wait') : t('shops.err_save'))
    } finally { setBusy(false) }
  }

  const ready = shop && shop.status !== 'processing' && shop.status !== 'failed'
  const candidates = (creator && q.trim().length >= 2 ? found : mine).filter((l) => !items.some((x) => x.id === l.id))

  return (
    <div className="page sh-editor">
      <PageHeader title={id ? t('shops.edit_title') : t('shops.new_title')} />
      {!shop ? (
        <div className="sh-drop" onClick={() => fileRef.current?.click()} role="button" tabIndex={0}>
          <input ref={fileRef} type="file" accept="video/*" hidden onChange={(e) => pick(e.target.files?.[0])} />
          {progress != null ? (
            <><div className="sh-bar"><span style={{ width: `${Math.round(progress * 100)}%` }} /></div><div>{t('shops.uploading', { p: Math.round(progress * 100) })}</div></>
          ) : (
            <>
              <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2.5" y="6" width="13" height="12" rx="2.5" /><path d="m15.5 10.5 6-3.5v10l-6-3.5" /></svg>
              <div className="sh-drop-title">{t('shops.pick_video')}</div>
              <div className="jr-muted">{t('shops.pick_hint')}</div>
            </>
          )}
        </div>
      ) : (
        <div className="sh-preview">
          {shop.status === 'processing' && <div className="sh-processing"><span className="sh-spin" />{t('shops.processing')}</div>}
          {shop.status === 'failed' && <div className="jr-err">{t('shops.failed')}</div>}
          {ready && <video ref={preview} src={shop.video_url} poster={shop.poster_url} controls playsInline className="sh-preview-video" />}
          {shop.status === 'rejected' && shop.reject_reason && <div className="jr-err">{t('shops.rejected_because', { reason: shop.reject_reason })}</div>}
        </div>
      )}

      {shop && (
        <>
          <div className="sh-section-title">{t('shops.items_title', { n: items.length, max: MAX_ITEMS })}</div>
          {items.map((x) => (
            <div key={x.id} className="sh-pick picked">
              {x.photo && <img src={x.photo} alt="" />}
              <div className="sh-pick-text"><div className="sh-item-title">{x.title}</div><div className="jr-muted">{priceOf(x)} · {t('shops.from_sec', { s: x.appear_at || 0 })}</div></div>
              {ready && <button type="button" className="jr-btn ghost sm" onClick={() => setAt(x.id)}>{t('shops.set_time')}</button>}
              <button type="button" className="sh-x" aria-label={t('shops.remove')} onClick={() => setItems(items.filter((y) => y.id !== x.id))}>×</button>
            </div>
          ))}
          {ready && items.length > 0 && <div className="jr-hint">{t('shops.time_hint')}</div>}
          {items.length < MAX_ITEMS && (
            <>
              {creator && <input className="sh-search" value={q} placeholder={t('shops.search_ph')} onChange={(e) => setQ(e.target.value)} />}
              <div className="sh-cands">
                {candidates.slice(0, 20).map((l) => (
                  <button key={l.id} type="button" className="sh-pick" onClick={() => add(l)}>
                    {(l.cover_photo || l.photos?.[0]) && <img src={l.cover_photo || l.photos?.[0]} alt="" />}
                    <div className="sh-pick-text"><div className="sh-item-title">{l.title}</div><div className="jr-muted">{priceOf(l)}</div></div>
                    <span className="sh-add">+</span>
                  </button>
                ))}
                {!candidates.length && <div className="jr-hint">{creator ? t('shops.search_hint') : t('shops.no_own')}</div>}
              </div>
            </>
          )}
          <label className="jr-field"><span>{t('shops.caption')}</span>
            <textarea rows={3} maxLength={500} value={caption} placeholder={t('shops.caption_ph')} onChange={(e) => setCaption(e.target.value)} />
          </label>
          {err && <div className="jr-err">{err}</div>}
          <div className="jr-actions sh-save">
            <button type="button" className="jr-btn ghost" disabled={busy} onClick={() => save(false)}>{t('shops.save_draft')}</button>
            <button type="button" className="jr-btn primary" disabled={busy || !ready} onClick={() => save(true)}>{ready ? t('shops.publish') : t('shops.wait_video')}</button>
          </div>
          <div className="jr-hint">{t('shops.rules')}</div>
        </>
      )}
      {!shop && err && <div className="jr-err">{err}</div>}
      {/* пока видео не выбрано — что это такое и зачем, с картинками */}
      {!shop && progress == null && <ShopsExplainer />}
    </div>
  )
}
