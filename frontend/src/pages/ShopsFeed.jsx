import { promptSheet } from '../utils/confirm'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import Comments from '../components/ShopComments'
import { useFavorites } from '../context/FavoritesContext'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Sheet from '../components/Sheet'
import { toast } from 'sonner'
import VerifiedMark from '../components/VerifiedMark'

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
  const { user } = useAuth()   // для «+» «Снять шопс» сверху
  const { t, i18n } = useTranslation()
  const [params] = useSearchParams()
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(null)
  const [active, setActive] = useState(0)
  const [muted, setMuted] = useState(true)
  const loading = useRef(false)
  const start = params.get('start')

  const load = useCallback((offset) => {
    if (loading.current) return
    loading.current = true
    api.shopsFeed({ offset, limit: PAGE, lang: i18n.language, with_listings: true, ...(offset === 0 && start ? { start } : {}) })
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

  return (
    <div className="sh-feed">
      <div className="sh-top">
        <span className="sh-top-title">{t('shops.title')}</span>
        <Link className="sh-create" to={user ? '/shops/new' : '/login'} aria-label={t('shops.new_title')}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
        </Link>
      </div>
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
  const [following, setFollowing] = useState(!!shop.author?.is_subscribed)
  const [sheet, setSheet] = useState(false)
  const [comments, setComments] = useState(false)
  const [like, setLike] = useState({ on: shop.liked, n: shop.likes || 0 })
  const [nComments, setNComments] = useState(shop.comments || 0)
  const [burst, setBurst] = useState(0)
  const lastTap = useRef(0)
  const isShop = shop.kind !== 'listing'
  const sent = useRef({ view: false, complete: false })

  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting && e.intersectionRatio >= 0.6) onActive(index) }, { threshold: [0.6] })
    io.observe(el)
    return () => io.disconnect()
  }, [index, onActive])

  // iOS Safari запускает сам только видео без звука, и проверяет атрибут muted, а React его не ставит —
  // из-за этого видео на сайте не шли. Ставим и свойство, и атрибут, и запускаем, когда данные пришли.
  useEffect(() => {
    const v = video.current
    if (!v) return
    v.muted = muted
    v.defaultMuted = true
    if (muted) v.setAttribute('muted', ''); else v.removeAttribute('muted')
  }, [muted, near])
  useEffect(() => {
    const v = video.current
    if (!v) return undefined
    const tryPlay = () => { v.muted = muted; v.play().catch(() => setPaused(true)) }
    if (active && !paused) {
      if (v.readyState >= 2) tryPlay()
      else { v.addEventListener('loadeddata', tryPlay, { once: true }); v.load() }
      return () => v.removeEventListener('loadeddata', tryPlay)
    }
    v.pause()
    if (!active) { setPaused(false) }
    return undefined
  }, [active, paused, near]) // eslint-disable-line react-hooks/exhaustive-deps

  const { isFavorite, toggle: toggleFav } = useFavorites()
  const listingId = shop.items?.[0]?.id
  const faved = !isShop && listingId ? isFavorite(listingId) : false
  const toggleLike = (force) => {
    if (!isShop) {
      if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(`/shops?start=${shop.id}`)}`); return }
      if (listingId && (force !== true || !faved)) toggleFav(listingId)
      return
    }
    if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(`/shops?start=${shop.id}`)}`); return }
    const on = force ?? !like.on
    if (on === like.on) return
    setLike((l) => ({ on, n: l.n + (on ? 1 : -1) }))
    api.shopLike(shop.id, on).then((r) => setLike({ on: r.liked, n: r.likes })).catch(() => setLike((l) => ({ on: !on, n: l.n + (on ? -1 : 1) })))
  }
  // один тап — пауза, два быстрых — лайк с сердечком (как в TikTok)
  const onTap = () => {
    const now = Date.now()
    if (now - lastTap.current < 300) {
      lastTap.current = 0
      setPaused(false)
      toggleLike(true); setBurst((b) => b + 1)
      return
    }
    lastTap.current = now
    setTimeout(() => { if (lastTap.current === now) setPaused((p) => !p) }, 300)
  }
  const share = async () => {
    const url = `${window.location.origin}/shops?start=${shop.id}`
    const title = shop.caption || shop.items[0]?.title || 'PLONK'
    try { if (navigator.share) { await navigator.share({ title, url }); return } } catch { return }
    try { await navigator.clipboard.writeText(url); toast(t('shops.link_copied')) } catch { promptSheet({ title: t('shops.share'), value: url }) }
  }

  // просмотр — после 2 секунд на экране, досмотр — 90% ролика
  useEffect(() => {
    if (!active || sent.current.view || !isShop) return undefined
    const id = setTimeout(() => { sent.current.view = true; api.shopEvent(shop.id, { type: 'view' }) }, 2000)
    return () => clearTimeout(id)
  }, [active, shop.id, isShop])

  const onTime = (e) => {
    const v = e.currentTarget
    setTime(v.currentTime)
    if (isShop && !sent.current.complete && v.duration && v.currentTime / v.duration > 0.9) {
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
      <video ref={video} className="sh-video" playsInline webkit-playsinline="true" loop muted={muted} autoPlay={active} poster={shop.poster_url || undefined}
        preload={active ? 'auto' : near ? 'auto' : 'none'} src={near ? src : undefined} onTimeUpdate={onTime}
        onClick={onTap} />
      {burst > 0 && <div key={burst} className="sh-burst" aria-hidden="true"><svg viewBox="0 0 24 24" width="96" height="96"><path fill="#FF3B5C" d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg></div>}
      <div className="sh-side">
        <div className="sh-side-who">
          <Link className="sh-side-ava" to={`/seller/${shop.author?.id}`} aria-label={shop.author?.name}>
            {shop.author?.avatar ? <img src={shop.author.avatar} alt="" /> : (shop.author?.name || '?')[0]}
          </Link>
          {/* подписка на автора прямо с ролика — «+», после подписки «✓» (как у Reels / TikTok) */}
          {shop.author && !shop.mine && (
            <button type="button" className={`sh-follow${following ? ' on' : ''}`} aria-label={following ? t('shops.following') : t('shops.follow')}
              onClick={() => {
                if (!user) { navigate('/login'); return }
                const on = !following; setFollowing(on)
                ;(on ? api.subscribeToSeller(shop.author.id) : api.unsubscribeFromSeller(shop.author.id)).catch(() => setFollowing(!on))
              }}>{following ? '✓' : '+'}</button>
          )}
        </div>
        <button type="button" className={`sh-side-btn${(isShop ? like.on : faved) ? ' on' : ''}`} onClick={() => toggleLike()} aria-label={t('shops.like')} aria-pressed={isShop ? like.on : faved}>
          <svg viewBox="0 0 24 24" width="30" height="30" fill={(isShop ? like.on : faved) ? '#FF3B5C' : 'none'} stroke={(isShop ? like.on : faved) ? '#FF3B5C' : '#fff'} strokeWidth="2" strokeLinejoin="round"><path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
          <span>{isShop ? (like.n || t('shops.like')) : t('shops.r_save')}</span>
        </button>
        <button type="button" className="sh-side-btn" onClick={() => (isShop ? setComments(true) : shop.items?.[0] && write(shop.items[0]))} aria-label={isShop ? t('shops.comments') : t('shops.ask_seller')}>
          <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#fff" strokeWidth="2" strokeLinejoin="round"><path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" /></svg>
          <span>{isShop ? (nComments || t('shops.r_discuss')) : t('shops.r_ask')}</span>
        </button>
        <button type="button" className="sh-side-btn" onClick={share} aria-label={t('shops.share')}>
          <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" /><path d="m16 6-4-4-4 4" /><path d="M12 2v13" /></svg>
          <span>{t('shops.share')}</span>
        </button>
      </div>
      {comments && <Comments shop={shop} item={shop.items[0]} onClose={() => setComments(false)} onCount={setNComments} onAsk={write} />}
      {paused && <div className="sh-paused" aria-hidden="true"><svg viewBox="0 0 24 24" width="56" height="56" fill="#fff"><path d="M8 5v14l11-7z" /></svg></div>}
      <div className="sh-shade" aria-hidden="true" />
      <div className="sh-progress"><span style={{ width: `${Math.min(100, (time / dur) * 100)}%` }} /></div>
      <div className="sh-meta">
        <div className="sh-author">
          <Link to={`/seller/${shop.author?.id}`} className="sh-author-name">{shop.author?.name}</Link>
          <VerifiedMark official={shop.author?.official} verified={shop.author?.verified} size={16} />
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
      <Sheet open={sheet} onClose={() => setSheet(false)} title={t('shops.in_video')}>
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
      </Sheet>
    </section>
  )
}
