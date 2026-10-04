import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const PAGE = 8
// плохая связь или «экономия трафика» — берём 480p
const lowData = () => {
  const c = typeof navigator !== 'undefined' ? navigator.connection : null
  return Boolean(c && (c.saveData || /(^|-)2g|3g/.test(c.effectiveType || '')))
}
const price = (it) => (it.price == null ? '' : `${Math.round(it.price).toLocaleString('ru-RU')} ${it.currency === 'EUR' ? '€' : it.currency}`)

/**
 * Лента шопсов: свайп вверх — следующий ролик. Играет только видимый; источник есть у текущего,
 * предыдущего и двух следующих (буфер готов к моменту свайпа), у остальных — только обложка.
 * Карточки объявлений поверх видео, каждая со своей секунды.
 */
export default function ShopsFeed() {
  const { t, i18n } = useTranslation()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(null)
  const [active, setActive] = useState(0)
  const [muted, setMuted] = useState(true)
  const loading = useRef(false)
  const start = params.get('start')

  const load = useCallback((offset) => {
    if (loading.current) return
    loading.current = true
    api.shopsFeed({ offset, limit: PAGE, lang: i18n.language, ...(offset === 0 && start ? { start } : {}) })
      .then((r) => {
        setTotal(r.total)
        setItems((prev) => {
          const have = new Set(prev.map((x) => x.id))
          return [...prev, ...(r.items || []).filter((x) => !have.has(x.id))]
        })
      })
      .catch(() => setTotal((v) => v ?? 0))
      .finally(() => { loading.current = false })
  }, [i18n.language, start])

  useEffect(() => { load(0) }, [load])
  useEffect(() => { if (items.length && active >= items.length - 3 && items.length < (total || 0)) load(items.length) }, [active, items.length, total, load])

  // страница поверх всего: без прокрутки body и без нижнего меню
  useEffect(() => {
    document.body.classList.add('sh-open')
    return () => document.body.classList.remove('sh-open')
  }, [])

  const close = () => (window.history.length > 1 ? navigate(-1) : navigate('/'))

  return (
    <div className="sh-feed">
      <button type="button" className="sh-close" onClick={close} aria-label={t('shops.close')}>
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round"><path d="m15 18-6-6 6-6" /></svg>
      </button>
      <button type="button" className="sh-sound" onClick={() => setMuted((m) => !m)} aria-label={muted ? t('shops.sound_on') : t('shops.sound_off')}>
        {muted
          ? <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 5 6 9H3v6h3l5 4V5Z" /><path d="m22 9-6 6M16 9l6 6" /></svg>
          : <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 5 6 9H3v6h3l5 4V5Z" /><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" /></svg>}
      </button>
      {total === 0 && (
        <div className="sh-empty">
          <p>{t('shops.empty')}</p>
          <Link className="jr-btn primary" to="/shops/new">{t('shops.create_first')}</Link>
        </div>
      )}
      {items.map((s, i) => (
        <Slide key={s.id} shop={s} index={i} active={i === active} near={i >= active - 1 && i <= active + 2}
          muted={muted} onActive={setActive} />
      ))}
    </div>
  )
}

function Slide({ shop, index, active, near, muted, onActive }) {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const ref = useRef(null)
  const video = useRef(null)
  const [time, setTime] = useState(0)
  const [paused, setPaused] = useState(false)
  const [sheet, setSheet] = useState(false)
  const sent = useRef({ view: false, complete: false })

  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting && e.intersectionRatio >= 0.6) onActive(index) }, { threshold: [0.6] })
    io.observe(el)
    return () => io.disconnect()
  }, [index, onActive])

  useEffect(() => {
    const v = video.current
    if (!v) return
    if (active && !paused) { v.play().catch(() => {}) } else { v.pause() }
    if (!active) { setPaused(false) }
  }, [active, paused, near])

  // просмотр — после 2 секунд на экране, досмотр — 90% ролика
  useEffect(() => {
    if (!active || sent.current.view) return undefined
    const id = setTimeout(() => { sent.current.view = true; api.shopEvent(shop.id, { type: 'view' }) }, 2000)
    return () => clearTimeout(id)
  }, [active, shop.id])

  const onTime = (e) => {
    const v = e.currentTarget
    setTime(v.currentTime)
    if (!sent.current.complete && v.duration && v.currentTime / v.duration > 0.9) {
      sent.current.complete = true
      api.shopEvent(shop.id, { type: 'complete' })
    }
  }

  const openItem = (it) => {
    api.shopEvent(shop.id, { type: 'tap', listing_id: it.id })
    navigate(it.path)
  }
  const write = async (it) => {
    if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(`/shops?start=${shop.id}`)}`); return }
    api.shopEvent(shop.id, { type: 'chat', listing_id: it.id })
    try { const chat = await api.startChat(it.id, i18n.language); navigate(`/chat/${chat.id}`) } catch { navigate(it.path) }
  }

  const shown = shop.items.filter((it) => (it.appear_at || 0) <= time + 0.05)
  const src = lowData() && shop.video_low_url ? shop.video_low_url : shop.video_url
  const dur = shop.duration || 1

  return (
    <section ref={ref} className="sh-slide" aria-label={shop.caption || shop.author?.name}>
      <video ref={video} className="sh-video" playsInline loop muted={muted} poster={shop.poster_url || undefined}
        preload={active ? 'auto' : near ? 'auto' : 'none'} src={near ? src : undefined} onTimeUpdate={onTime}
        onClick={() => setPaused((p) => !p)} />
      {paused && <div className="sh-paused" aria-hidden="true"><svg viewBox="0 0 24 24" width="56" height="56" fill="#fff"><path d="M8 5v14l11-7z" /></svg></div>}
      <div className="sh-progress"><span style={{ width: `${Math.min(100, (time / dur) * 100)}%` }} /></div>
      <div className="sh-meta">
        <div className="sh-author">
          <span className="sh-ava">{shop.author?.avatar ? <img src={shop.author.avatar} alt="" /> : (shop.author?.name || '?')[0]}</span>
          <span>{shop.author?.name}</span>
          {shop.is_ad && <span className="sh-ad">{t('shops.ad')}</span>}
        </div>
        {shop.caption && <p className="sh-caption">{shop.caption}</p>}
        <div className="sh-items">
          {shown.slice(-2).map((it) => (
            <div key={it.item_id} className={`sh-item${it.status !== 'active' ? ' sold' : ''}`}>
              <button type="button" className="sh-item-main" onClick={() => openItem(it)}>
                {it.photo && <img src={it.photo} alt="" />}
                <span className="sh-item-text"><span className="sh-item-title">{it.title}</span>
                  <span className="sh-item-price">{it.status !== 'active' ? t('shops.sold') : price(it)}</span></span>
              </button>
              {it.status === 'active' && <button type="button" className="sh-item-write" onClick={() => write(it)}>{t('shops.write')}</button>}
            </div>
          ))}
          {shop.items.length > 1 && (
            <button type="button" className="sh-all" onClick={() => setSheet(true)}>{t('shops.all_items', { count: shop.items.length })}</button>
          )}
        </div>
      </div>
      {sheet && (
        <div className="jr-overlay" onClick={() => setSheet(false)}>
          <div className="jr-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="jr-grab" />
            <div className="jr-title">{t('shops.in_video')}</div>
            {shop.items.map((it) => (
              <div key={it.item_id} className={`sh-item light${it.status !== 'active' ? ' sold' : ''}`}>
                <button type="button" className="sh-item-main" onClick={() => openItem(it)}>
                  {it.photo && <img src={it.photo} alt="" />}
                  <span className="sh-item-text"><span className="sh-item-title">{it.title}</span>
                    <span className="sh-item-price">{it.status !== 'active' ? t('shops.sold') : price(it)}</span></span>
                </button>
                {it.status === 'active' && <button type="button" className="sh-item-write" onClick={() => write(it)}>{t('shops.write')}</button>}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
