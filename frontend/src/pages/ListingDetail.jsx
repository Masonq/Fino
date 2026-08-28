import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'
import { addToHistory } from '../data/history'
import { useAuth } from '../context/AuthContext'
import { useFavorites } from '../context/FavoritesContext'
import ReportButton from '../components/ReportButton'
import PromoteButton from '../components/PromoteButton'
import SimilarListings from '../components/SimilarListings'
import { formatPrice } from '../utils/money'

const REASON_KEYS = [
  'wrong_category', 'bad_photos', 'unclear_description',
  'duplicate', 'prohibited', 'suspicious_price',
]

export default function ListingDetail() {
  const { slug } = useParams()

  // Ключ объявления — хвост адреса: у «stol-ikea-45e17e58» это
  // «45e17e58». Название могли поправить, и адрес разойдётся с
  // нынешним — но хвост остаётся.
  //
  // Короткая ссылка /go/:slug (админка) передаёт сюда объявление
  // целиком по UUID, а не по хвосту — split('-').pop() на полном UUID
  // («e63e2224-...-543bbc7d2b31») давал «543bbc7d2b31» (12 знаков),
  // не подходящее ни под UUID, ни под 8-значный хвост, который ждёт
  // бэкенд, — ссылка вела на несуществующее объявление. Полный UUID
  // передаём как есть, не трогая.
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  const listingId = UUID_RE.test(slug || '') ? slug : (slug || '').split('-').pop()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const [scrolled, setScrolled] = useState(false)
  const [photoIdx, setPhotoIdx] = useState(0)
  // Просмотр во весь экран: в галерее фото вписано целиком и потому мелкое,
  // а разглядеть вещь перед покупкой — половина смысла объявления.
  const [fullscreen, setFullscreen] = useState(null)

  // При открытом просмотре страница под ним не должна прокручиваться:
  // иначе закрываешь снимок и оказываешься в другом месте объявления.
  useEffect(() => {
    if (fullscreen === null) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [fullscreen])

  // запоминаем просмотр — чтобы человек мог вернуться к тому, что смотрел
  useEffect(() => {
    if (listingId) addToHistory(listingId)
  }, [listingId])

  // Шапка появляется, когда фото уехало вверх — как у Avito:
  // сначала кнопки полупрозрачными кружками на фото, потом панель на белом.
  useEffect(() => {
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        setScrolled(window.scrollY > 210)
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); if (raf) cancelAnimationFrame(raf) }
  }, [])
  const [searchParams] = useSearchParams()

  const [listing, setListing] = useState(null)
  const [schema, setSchema] = useState([])

  const lightboxRef = useRef(null)
  const stripRef = useRef(null)
  const imgRefs = useRef([])

  // Переключение между фото — снова через нативную прокрутку ленты
  // (scroll-x + scroll-snap), как было изначально: проверенно
  // работает, браузер сам умеет это лучше самодельного кода. Щипок,
  // зум, панорама при увеличении, свайп-закрытие вниз/вверх и двойной
  // тап — отдельный слой поверх, включается только когда действительно
  // нужен (два пальца, либо уже увеличено), не спорит с прокруткой.
  //
  // Более ранняя версия пробовала подвинуть и переключение между фото
  // тоже через свой JS (transform вместо scroll) — итог был печальным:
  // счётчик наверху обновлялся верно, а само изображение переставало
  // показываться, чёрный экран вместо фото. Свой код для того, что
  // браузер и так умеет надёжно, — плохой размен.
  const gesture = useRef({
    mode: null, startDist: 0, startScale: 1, startMidX: 0, startMidY: 0,
    panStartX: 0, panStartY: 0, zoomStartX: 0, zoomStartY: 0,
    closeStartX: 0, closeStartY: 0,
    lastTap: 0, lastTapX: 0, lastTapY: 0, suppressClick: false,
  })
  const zoom = useRef({ scale: 1, x: 0, y: 0 })

  const currentImg = () => imgRefs.current[photoIdx]

  const applyZoom = (animate) => {
    const el = currentImg()
    if (!el) return
    if (animate) {
      el.style.transition = 'transform .2s ease'
      setTimeout(() => { if (el) el.style.transition = '' }, 200)
    }
    const { scale, x, y } = zoom.current
    el.style.transform = `translate(${x}px, ${y}px) scale(${scale})`
  }

  const resetZoom = (animate) => {
    zoom.current = { scale: 1, x: 0, y: 0 }
    applyZoom(animate)
    // Пока было увеличено, нативную прокрутку ленты держали
    // выключенной (см. onStart ниже) — возвращаем её на 1×.
    const strip = stripRef.current
    if (strip) strip.style.overflowX = ''
  }

  // При смене фото зум предыдущего снимка не должен переезжать на
  // следующий — каждое открывается заново на 1×.
  useEffect(() => { resetZoom(false) }, [photoIdx])

  useEffect(() => {
    if (fullscreen === null) return
    const el = lightboxRef.current
    const strip = stripRef.current
    if (!el || !strip) return
    const g = gesture.current
    const dist = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)
    const mid = (a, b) => ({ x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 })

    const onStart = (e) => {
      const touches = e.touches
      if (touches.length === 2) {
        g.mode = 'pinch'
        g.startDist = dist(touches[0], touches[1])
        g.startScale = zoom.current.scale
        const m = mid(touches[0], touches[1])
        g.startMidX = m.x; g.startMidY = m.y
        g.zoomStartX = zoom.current.x; g.zoomStartY = zoom.current.y
        // На время щипка нативная прокрутка мешала бы — временно гасим,
        // resetZoom() включит обратно, когда вернёмся к 1×.
        strip.style.overflowX = 'hidden'
        return
      }
      if (touches.length === 1) {
        const t = touches[0]
        if (zoom.current.scale > 1.02) {
          g.mode = 'pan'
          g.panStartX = t.clientX; g.panStartY = t.clientY
          g.zoomStartX = zoom.current.x; g.zoomStartY = zoom.current.y
          strip.style.overflowX = 'hidden'
        } else {
          // Не увеличено — горизонталь целиком достаётся нативной
          // прокрутке ленты между фото, мы только следим за вертикалью,
          // чтобы понять, не тянут ли вниз/вверх для закрытия.
          g.mode = null
          g.closeStartX = t.clientX; g.closeStartY = t.clientY
        }
      }
    }

    const onMove = (e) => {
      const touches = e.touches
      // Число пальцев сменилось посреди жеста (отпустили один из двух
      // при щипке) — не дёргаем позицию рывком, берём точкой отсчёта
      // то, что осталось, едем дальше тем же плавным движением.
      if ((g.mode === 'pinch' && touches.length !== 2) || (g.mode === 'pan' && touches.length !== 1)) {
        onStart(e)
      }

      if (g.mode === 'pinch' && touches.length === 2) {
        e.preventDefault()
        const d = dist(touches[0], touches[1])
        const m = mid(touches[0], touches[1])
        const scale = Math.max(1, Math.min(4, g.startScale * (d / g.startDist)))
        zoom.current = {
          scale,
          x: g.zoomStartX + (m.x - g.startMidX),
          y: g.zoomStartY + (m.y - g.startMidY),
        }
        applyZoom(false)
        return
      }

      if (g.mode === 'pan' && touches.length === 1) {
        e.preventDefault()
        const t = touches[0]
        zoom.current = {
          scale: zoom.current.scale,
          x: g.zoomStartX + (t.clientX - g.panStartX),
          y: g.zoomStartY + (t.clientY - g.panStartY),
        }
        applyZoom(false)
        return
      }

      // Не увеличено, один палец — свайп-закрытие. Срабатывает только
      // если движение явно вертикальное: иначе это самое обычное
      // перелистывание между фото, которое ведёт браузер сам через
      // нативный scroll, мы его руками не трогаем вовсе.
      if (touches.length !== 1) return
      if (g.mode !== null && g.mode !== 'v-close') return
      const t = touches[0]
      const dx = t.clientX - g.closeStartX
      const dy = t.clientY - g.closeStartY

      if (g.mode === null) {
        if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return
        if (Math.abs(dy) <= Math.abs(dx) * 1.3) return // горизонталь — не наше дело
        g.mode = 'v-close'
      }

      e.preventDefault()
      const progress = Math.min(Math.abs(dy) / 300, 1)
      el.style.transform = `translateY(${dy}px)`
      el.style.opacity = String(1 - progress * 0.7)
    }

    const onEnd = (e) => {
      // Любой настоящий жест — клик после него не должен закрывать
      // панель сам по себе, даже если движение не дотянуло до порога.
      if (g.mode !== null) g.suppressClick = true

      // Двойной тап — переключатель зума. Только если жест не
      // превратился в перетаскивание (mode остался null).
      if (g.mode === null && e.touches.length === 0) {
        const now = Date.now()
        const t = e.changedTouches[0]
        const closeTap = Math.hypot(t.clientX - g.lastTapX, t.clientY - g.lastTapY) < 40
        if (now - g.lastTap < 300 && closeTap) {
          g.suppressClick = true
          if (zoom.current.scale > 1.02) resetZoom(true)
          else { zoom.current = { scale: 2.5, x: 0, y: 0 }; applyZoom(true) }
          g.lastTap = 0
        } else {
          g.lastTap = now; g.lastTapX = t.clientX; g.lastTapY = t.clientY
        }
      }

      if (g.mode === 'pinch' || g.mode === 'pan') {
        if (zoom.current.scale <= 1.02) resetZoom(true)
        if (e.touches.length === 0) g.mode = null
        return
      }

      if (g.mode === 'v-close') {
        const t = e.changedTouches[0]
        const dy = t.clientY - g.closeStartY
        if (Math.abs(dy) > 80) {
          el.style.transition = 'transform .2s ease, opacity .2s ease'
          el.style.transform = `translateY(${dy > 0 ? '100%' : '-100%'})`
          el.style.opacity = '0'
          setTimeout(() => setFullscreen(null), 200)
        } else {
          el.style.transition = 'transform .25s ease, opacity .25s ease'
          el.style.transform = ''
          el.style.opacity = ''
          setTimeout(() => { if (el) el.style.transition = '' }, 250)
        }
      }
      g.mode = null
    }

    el.addEventListener('touchstart', onStart, { passive: true })
    el.addEventListener('touchmove', onMove, { passive: false })
    el.addEventListener('touchend', onEnd, { passive: true })
    return () => {
      el.removeEventListener('touchstart', onStart)
      el.removeEventListener('touchmove', onMove)
      el.removeEventListener('touchend', onEnd)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullscreen, photoIdx])
  const { isFavorite, toggle } = useFavorites()
  const fav = isFavorite(listingId)

  const onFav = async () => {
    const res = await toggle(listingId)
    if (res?.needAuth) navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
  }
  const [starting, setStarting] = useState(false)
  const [descOpen, setDescOpen] = useState(false)
  const [attrsOpen, setAttrsOpen] = useState(false)

  useEffect(() => {
    api.getListing(listingId).then(setListing).catch(() => setListing(null))
  }, [listingId])

  useEffect(() => {
    if (!listing?.category_slug) return
    api.getCategorySchema(listing.category_slug)
      .then((res) => setSchema(res.attribute_schema || []))
      .catch(() => setSchema([]))
  }, [listing?.category_slug])

  const startChatWith = async () => {
    if (!listing) return
    setStarting(true)
    try {
      const chat = await api.startChat(listing.id, i18n.language)
      navigate(`/chat/${chat.id}`)
    } catch (e) {
      alert(t('detail.own_listing'))
    } finally {
      setStarting(false)
    }
  }

  useEffect(() => {
    if (searchParams.get('identified') === '1' && listing) {
      const myId = user?.id
      if (myId) startChatWith()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing])

  const isStaff = user?.role === 'admin' || user?.role === 'moderator'
  // Продвигать может только сам владелец, и только пока объявление
  // реально в выдаче — снятое или ждущее модерации продвигать бы
  // впустую, покупатель его всё равно не увидит (та же проверка,
  // что и на бэкенде).
  const isOwner = user?.id && listing?.owner?.id === user.id && listing?.status === 'active'
  const [deleting, setDeleting] = useState(false)
  const [showReasons, setShowReasons] = useState(false)
  const [customReason, setCustomReason] = useState(false)
  const [reasonText, setReasonText] = useState('')
  // Перенесённое из телеграм-чата объявление принадлежит служебному
  // аккаунту чата — реального человека, которому можно вернуть его на
  // доработку, тут нет. Такие просто удаляем, как раньше. У обычного
  // объявления владелец — тот, кто его разместил, и ему есть куда его
  // вернуть — через отклонение с причиной, как в очереди модерации.
  const canReturnToEdit = listing?.external_source !== 'telegram'

  const handleDelete = async () => {
    if (!listing) return
    if (canReturnToEdit) { setShowReasons(true); return }
    if (!window.confirm(t('my.confirm_delete'))) return
    setDeleting(true)
    try {
      await api.deleteListing(listing.id)
      navigate(listing.category_slug ? `/search?category=${listing.category_slug}` : '/', { replace: true })
    } catch (e) {
      // Раньше тут любая ошибка проглатывалась молча — модератор
      // видел, что кнопка просто перестала крутиться, без объяснения.
      alert(e.code === 'listing_has_history' ? t('my.delete_has_history') : t('auth.err_generic'))
    }
    finally { setDeleting(false) }
  }

  const returnToEdit = async (reason) => {
    if (!listing) return
    setShowReasons(false)
    setDeleting(true)
    try {
      await api.modReject(listing.id, reason)
      navigate(listing.category_slug ? `/search?category=${listing.category_slug}` : '/', { replace: true })
    } catch { /* оставляем как было */ }
    finally { setDeleting(false) }
  }

  if (!listing) {
    // Скелетон вместо надписи: страница объявления загружается заметно,
    // и пустой экран с текстом выглядит как ошибка.
    return (
      <div className="detail-page">
        <div className="detail-photo sk-block" />
        <div className="detail-sheet">
          <div className="sk-block sk-line" style={{ height: 26, width: '45%', marginTop: 4 }} />
          <div className="sk-block sk-line" style={{ height: 17, width: '85%', marginTop: 14 }} />
          <div className="sk-block sk-line" style={{ height: 17, width: '60%', marginTop: 8 }} />
          <div className="sk-block sk-line" style={{ height: 13, width: '35%', marginTop: 18 }} />
        </div>
      </div>
    )
  }

  const lang = i18n.language
  const translation = listing.translations[lang] || Object.values(listing.translations)[0]
  // обложка идёт первой, остальные — следом
  const photos = (() => {
    const all = listing.photos || []
    const cov = all.find((ph) => ph.is_cover)
    return cov ? [cov, ...all.filter((ph) => ph !== cov)] : all
  })()

  const attrLabel = (key) => {
    const field = schema.find((f) => f.key === key)
    if (!field) return key
    return field.label?.[lang] || field.label?.ru || key
  }
  // Резюме — не товар: человек не продаёт себя, у него нет цены и он не
  // «продавец». Отличается только подачей, поэтому отдельной категории не
  // заводим, а правим формулировки там, где они не годятся.
  const isResume = listing?.attributes?.listing_kind === 'resume'
  // Вещи больше нет: продана или снята. Показываем это, но объявление
  // оставляем — по нему смотрят цены и на него стоят ссылки.
  const gone = listing?.status === 'sold' || listing?.status === 'archived'

  // Куда вести кнопку «назад».
  //
  // navigate(-1) возвращает в историю браузера, а у пришедшего по
  // прямой ссылке — из поиска, из телеграма — её нет: кнопка не делает
  // ничего, и человек застревает. Тогда ведём в раздел объявления: это
  // ближайшее осмысленное место.
  const goBack = () => {
    if (window.history.state?.idx > 0) {
      navigate(-1)
      return
    }
    // Раздел открывается поиском с отбором — отдельной страницы у
    // него нет. Веду туда: человек увидит другие вещи из того же
    // раздела, а не пустой экран.
    navigate(listing?.category_slug
      ? `/search?category=${listing.category_slug}`
      : '/', { replace: true })
  }

  const attrValue = (key, value) => {
    const field = schema.find((f) => f.key === key)
    if (field?.type === 'boolean') return value ? t('common.yes') : t('common.no')
    // Зарплата без валюты — просто число: «1800» не отличить от чего угодно.
    // Разделитель тысяч ставим только деньгам: «Год» превратился бы в «2 016».
    if (field?.unit === 'currency' && value !== '' && value != null) {
      return formatPrice(value, listing.currency, lang)
    }
    if (field?.type === 'select') {
      const opt = field.options?.find((o) => o.value === value)
      return opt?.label?.[lang] || opt?.label?.ru || value
    }
    // Атрибуты, заполненные словами («Вид услуги»), переводятся вместе с
    // объявлением — берём перевод, если он есть на нужном языке.
    if (field?.translatable) {
      return listing?.attributes_i18n?.[lang]?.[key] || value
    }
    return value
  }

  const handleWriteToSeller = () => {
    const myId = user?.id
    if (myId) {
      startChatWith()
    } else {
      navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
    }
  }

  return (
    <div className="detail-page">
      <div className="detail-photo">
        {photos.length > 0 ? (
          <div
            className="photo-strip"
            onScroll={(e) => {
              const el = e.currentTarget
              setPhotoIdx(Math.round(el.scrollLeft / el.clientWidth))
            }}
          >
            {photos.map((ph, i) => (
              /* Снимок показываем целиком, а поля по бокам заполняем его же
                 размытой копией: обрезка по высоте съедала половину
                 вертикальных фото — а их в объявлениях большинство. */
              <div
                className="photo-slide"
                key={ph.url || i}
                onClick={() => setFullscreen(i)}
              >
                <img className="photo-blur" src={ph.url} alt="" aria-hidden="true" />
                <img className="photo-main" src={ph.url} alt="" loading={i === 0 ? 'eager' : 'lazy'} />
              </div>
            ))}
          </div>
        ) : <div className="photo-placeholder" />}
        <div className={scrolled ? 'detail-topbar shown' : 'detail-topbar'}>
          <button className="topbar-btn" onClick={goBack} aria-label={t('actions.back')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <div className="topbar-right">
            {isStaff && (
              <button className="topbar-btn danger" onClick={handleDelete} disabled={deleting} aria-label={t('my.delete')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7h16M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7m2 0-.7 12.4A2 2 0 0 1 14.3 21H9.7a2 2 0 0 1-2-1.6L7 7" /></svg>
              </button>
            )}
            <button className={fav ? 'topbar-btn on' : 'topbar-btn'} onClick={onFav} aria-label={t('misc.in_favorites')}>
              <svg viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
              </svg>
            </button>
          </div>
        </div>

        <div className="detail-nav">
          <button className="circle-btn" onClick={goBack} aria-label={t('actions.back')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>
          <div className="detail-nav-right">
            {isStaff && (
              <button className="circle-btn danger" onClick={handleDelete} disabled={deleting} aria-label={t('my.delete')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7h16M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7m2 0-.7 12.4A2 2 0 0 1 14.3 21H9.7a2 2 0 0 1-2-1.6L7 7" /></svg>
              </button>
            )}
            <button className={fav ? 'circle-btn on' : 'circle-btn'} onClick={onFav} aria-label={t('misc.in_favorites')}>
              <svg viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
              </svg>
            </button>
          </div>
        </div>
        {/* Один указатель, а не два: счётчик в углу и точки по центру
            показывали одно и то же, и оба упирались в край карточки. */}
        {photos.length > 1 && (
          <div className="photo-count">{photoIdx + 1} / {photos.length}</div>
        )}
      </div>

      <div className="detail-sheet">
        {/* Снятое объявление не исчезает: по нему смотрят, за сколько
            ушла похожая вещь, и на него уже стоят ссылки. Но человек
            должен видеть, что вещи больше нет, а не писать впустую. */}
        {gone && (
          <div className="gone-banner">
            <div className="gone-banner-title">
              {t(listing.status === 'sold' ? 'detail.sold' : 'detail.gone')}
            </div>
            <div className="gone-banner-note">{t('detail.gone_note')}</div>
          </div>
        )}
        <div className="detail-price">
          {listing.price != null
            ? formatPrice(listing.price, listing.currency, lang)
            : listing.is_free
              ? <span className="price-free">{t('detail.free')}</span>
              : t(isResume ? 'detail.no_salary' : 'detail.no_price')}
          {listing.previous_price && (
            <span className="price-old">
              {formatPrice(listing.previous_price.price, listing.previous_price.currency, lang)}
            </span>
          )}
        </div>
        {isResume && listing.price != null && (
          <div className="price-note">{t('detail.desired_salary')}</div>
        )}
        {listing.price_negotiable && <div className="neg-pill">{t('detail.negotiable')}</div>}

        <div className="detail-title">{translation?.title}</div>
        {/* Помечаем явно: иначе продавец с нашего сайта конкурирует с
            перепечаткой и не понимает, почему объявление ведёт себя иначе. */}
        {listing.external_source === 'telegram' && (
          <div className="from-telegram">{t('detail.from_telegram')}</div>
        )}
        {listing.city && (
          <div className="detail-loc">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" />
            </svg>
            {displayCity(listing.city, lang)}
          </div>
        )}

        <div className="badge-row">
          {listing.safe_deal_available && (
            <div className="info-badge green">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6 9 17l-5-5" /></svg>
              {t('detail.safe_deal')}
            </div>
          )}
          {listing.delivery_available && <div className="info-badge grey">{t('detail.delivery')}</div>}
        </div>

        {/* Показываем только то, что описано в схеме категории. Иначе на
            странице появлялась строка с сырым ключом вроде «condition» —
            так и случилось, когда признак заполнили там, где поля нет. */}
        {(() => {
          const rows = Object.entries(listing.attributes || {})
            .filter(([key, value]) =>
              value !== null && value !== '' &&
              schema.some((f) => f.key === key))
          if (!rows.length) return null
          // Длинный список сворачиваем — как на Авито: сразу видно
          // главное, а не стену из пятнадцати строк характеристик.
          const LIMIT = 6
          const visible = attrsOpen ? rows : rows.slice(0, LIMIT)
          return (
            <div className="attrs-block">
              <div className="desc-title">{t('detail.characteristics')}</div>
              <div className="attr-card">
                {visible.map(([key, value]) => (
                  <div className="attr-row" key={key}>
                    <span className="k">{attrLabel(key)}</span>
                    <span className="v">{String(attrValue(key, value))}</span>
                  </div>
                ))}
              </div>
              {!attrsOpen && rows.length > LIMIT && (
                <button className="desc-more" onClick={() => setAttrsOpen(true)}>
                  {t('detail.show_all')}
                </button>
              )}
            </div>
          )
        })()}

        {translation?.description && (
          <div className="desc-block">
            <div className="desc-title">{t('detail.description')}</div>
            {/* Длинное описание сворачиваем: в объявлениях из чата их
                пишут на пол-экрана, и до продавца человек не
                доскроллит. Короткие показываем целиком — прятать в них
                нечего. */}
            <div className={`desc-text${
              !descOpen && (translation.description || '').length > 320
                ? ' clipped' : ''}`}>
              {translation.description}
            </div>
            {(translation.description || '').length > 320 && !descOpen && (
              <button className="desc-more" onClick={() => setDescOpen(true)}>
                {t('detail.read_more')}
              </button>
            )}
          </div>
        )}

        {listing.owner && (
          <Link to={`/seller/${listing.owner.id}`} className="seller-row">
            <div className={listing.owner.is_company ? 'seller-avatar is-company' : 'seller-avatar'}>
              {listing.owner.avatar_url
                ? <img src={listing.owner.avatar_url} alt="" />
                : (listing.owner.company_name || listing.owner.display_name)?.[0] || '?'}
            </div>
            <div>
              <div className="seller-name">
                {listing.owner.company_name || listing.owner.display_name}
                {(listing.owner.phone_verified || listing.owner.company_verified || listing.owner.document_verified) && (
                  <div className="seal seal-sm">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><path d="M20 6 9 17l-5-5" /></svg>
                  </div>
                )}
              </div>
              <div className="seller-meta">
                {listing.owner.is_company && (
                  <span className="seller-badge-inline">{t('seller.company_badge')} · </span>
                )}
                {listing.owner.rating_count > 0
                  ? `${listing.owner.rating_avg?.toFixed(1)} · ${t('rev.count', { count: listing.owner.rating_count })}`
                  : t('rev.none_yet')}
              </div>
            </div>
            {/* шеврон: без него строка не читается как ведущая куда-то */}
            <svg className="seller-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </Link>
        )}

        {isOwner && (
          <div className="detail-promote-slot">
            <PromoteButton listingId={listing.id} />
          </div>
        )}

        <SimilarListings listingId={listing.id} />

        <ReportButton listingId={listing.id} ownerId={listing.owner?.id} />
      </div>

      {/* Объявление перенесено из телеграм-чата: писать и звонить через сайт
          некому — автор у нас не зарегистрирован. Вместо двух погашенных
          кнопок даём одну рабочую, иначе экран выглядит сломанным. */}
      {gone ? (
        <div className="sticky-cta">
          {/* Не обещаем похожие: подбор пока слабый, и пустая надежда
              хуже честного «смотрите раздел». */}
          {/* Ведём в поиск по подразделу этого объявления, а не на /c/,
              который рассчитан только на разделы верхнего уровня —
              category_slug тут почти всегда подраздел («phones»), и
              /c/phones упал бы: LANDINGS ключуется по верхнему уровню. */}
          <button
            className="cta-btn primary"
            onClick={() => navigate(`/search?category=${listing.category_slug}`)}
          >
            {t('detail.gone_to_category')}
          </button>
        </div>
      ) : listing.external_source === 'telegram' && listing.external_author ? (
        <div className="sticky-cta">
          <a
            className="cta-btn primary telegram"
            href={`https://t.me/${listing.external_author}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21.9 4.3 18.8 19c-.2 1-.9 1.3-1.7.8l-4.7-3.5-2.3 2.2c-.3.3-.5.5-1 .5l.4-4.9 9-8.1c.4-.3-.1-.5-.6-.2L7 10.7 2.4 9.2c-1-.3-1-1 .2-1.5l18-6.9c.8-.3 1.5.2 1.3 1.5Z" />
            </svg>
            {t('detail.open_telegram')}
          </a>
        </div>
      ) : (
      <div className="sticky-cta">
        <button className="cta-btn icon">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
          </svg>
        </button>
        <button className="cta-btn primary" disabled={starting} onClick={handleWriteToSeller}>
          {starting ? '...' : t(isResume ? 'detail.write_person' : 'detail.write_seller')}
        </button>
      </div>
      )}

      {showReasons && (
        <div className="reasons-sheet" onClick={() => { setShowReasons(false); setCustomReason(false); setReasonText('') }}>
          <div className="reasons-card" onClick={(e) => e.stopPropagation()}>
            <div className="reasons-title">{t('mod.return_to_edit')}</div>
            {!customReason ? (
              <>
                {REASON_KEYS.map((key) => (
                  <button
                    key={key}
                    className="reasons-item"
                    disabled={deleting}
                    onClick={() => returnToEdit(t(`mod.reasons.${key}`))}
                  >
                    {t(`mod.reasons.${key}`)}
                  </button>
                ))}
                <button
                  className="reasons-item"
                  disabled={deleting}
                  onClick={() => setCustomReason(true)}
                >
                  {t('mod.reasons.other')}
                </button>
                <button className="reasons-cancel" onClick={() => setShowReasons(false)}>
                  {t('actions.cancel')}
                </button>
              </>
            ) : (
              <>
                <textarea
                  className="mod-reason-input"
                  placeholder={t('mod.reason_prompt')}
                  value={reasonText}
                  onChange={(e) => setReasonText(e.target.value)}
                  autoFocus
                />
                <div className="reasons-actions-row">
                  <button className="reasons-cancel" onClick={() => setCustomReason(false)}>
                    {t('actions.back')}
                  </button>
                  <button
                    className="reasons-item primary"
                    disabled={deleting || !reasonText.trim()}
                    onClick={() => returnToEdit(reasonText.trim())}
                  >
                    {t('mod.reject')}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {fullscreen !== null && (
        <div
          ref={lightboxRef}
          className="lightbox"
          onClick={() => {
            if (gesture.current.suppressClick) { gesture.current.suppressClick = false; return }
            if (zoom.current.scale <= 1.02) setFullscreen(null)
          }}
        >
          <button className="lightbox-close" aria-label={t('actions.close')}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
          <div
            className="lightbox-strip"
            ref={(el) => {
              stripRef.current = el
              // открываем сразу на том снимке, который смотрели в ленте
              if (el && el.dataset.ready !== '1') {
                el.scrollLeft = fullscreen * el.clientWidth
                el.dataset.ready = '1'
              }
            }}
            onClick={(e) => e.stopPropagation()}
            onScroll={(e) => {
              // Только пока не увеличено — при зуме прокрутка временно
              // выключена (overflowX:'hidden' в onStart), это событие
              // просто не придёт.
              const el = e.currentTarget
              setPhotoIdx(Math.round(el.scrollLeft / el.clientWidth))
            }}
          >
            {photos.map((ph, i) => (
              <img
                key={ph.url || i}
                ref={(el) => { imgRefs.current[i] = el }}
                src={ph.url}
                alt=""
                draggable="false"
              />
            ))}
          </div>
          {photos.length > 1 && (
            <div className="lightbox-count">{photoIdx + 1} / {photos.length}</div>
          )}
        </div>
      )}
    </div>
  )
}
