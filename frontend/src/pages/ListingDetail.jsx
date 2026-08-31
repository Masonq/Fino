import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'
import LocationMap from '../components/LocationMap'
import { addToHistory } from '../data/history'
import { useAuth } from '../context/AuthContext'
import { useFavorites } from '../context/FavoritesContext'
import ReportButton from '../components/ReportButton'
import PromoteButton from '../components/PromoteButton'
import SimilarListings from '../components/SimilarListings'
import SellerListings from '../components/SellerListings'
import { formatPrice } from '../utils/money'
import { relativeDate } from '../utils/time'

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
  //
  // Нижняя кнопка «Написать продавцу» — по тому же принципу, что и
  // многие мобильные сайты: прячется, когда листаешь вниз (читаешь
  // описание — кнопка занимает место просто так), и тут же
  // возвращается, стоит прокрутить назад вверх — жест «хочу
  // вернуться» и «хочу написать» это, как правило, один и тот же
  // порыв. Не прячем возле самого верха (< 80px) — там дёргалась бы
  // от каждого мелкого покачивания при обычном чтении первого экрана.
  const lastScrollY = useRef(0)
  const [ctaHidden, setCtaHidden] = useState(false)
  useEffect(() => {
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        const y = window.scrollY
        setScrolled(y > 210)
        if (y > 80) {
          setCtaHidden(y > lastScrollY.current)
        } else {
          setCtaHidden(false)
        }
        lastScrollY.current = y
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); if (raf) cancelAnimationFrame(raf) }
  }, [])
  const [searchParams, setSearchParams] = useSearchParams()

  const [listing, setListing] = useState(null)
  const [schema, setSchema] = useState([])

  const lightboxRef = useRef(null)
  // Точка начала касания — для свайпа вниз/вверх, закрывающего просмотр.
  // Не стейт: пересчитывать компонент на каждое touchmove незачем.
  const lightboxTouch = useRef(null)
  // Стрелки для десктопа — на телефоне и с тачпадом фото листают
  // свайпом, обычной мышью без сенсора и тачпада горизонтальную
  // полосу прокрутить нечем: колесо мыши крутит только вертикально.
  const photoStripRef = useRef(null)
  const goToPhoto = (i) => {
    const el = photoStripRef.current
    if (!el) return
    const clamped = Math.max(0, Math.min(photos.length - 1, i))
    el.scrollTo({ left: clamped * el.clientWidth, behavior: 'smooth' })
  }

  // Сама анимация перетаскивания — через нативный touchmove, не через
  // JSX onTouchMove: синтетические обработчики React могут навесить
  // {passive:true}, и preventDefault() в них тогда бы просто не сработал,
  // а он нужен — иначе одновременно с перетаскиванием фото вверх-вниз
  // страница под ним попыталась бы прокрутиться сама.
  useEffect(() => {
    if (fullscreen === null) return
    const el = lightboxRef.current
    if (!el) return

    const onMove = (e) => {
      // Щипок двумя пальцами — не свайп закрытия вовсе, не вмешиваемся:
      // ни transform, ни preventDefault, отдаём жест целиком нативному
      // масштабированию.
      if (e.touches.length > 1) {
        lightboxTouch.current = null
        return
      }
      const start = lightboxTouch.current
      if (!start) return
      const t = e.touches[0]
      const dx = t.clientX - start.x
      const dy = t.clientY - start.y

      if (start.mode === null) {
        // Направление решаем один раз, по первым же заметным пикселям —
        // дальше жест держится того же режима до конца касания.
        if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return
        start.mode = Math.abs(dy) > Math.abs(dx) * 1.3 ? 'v' : 'h'
      }
      if (start.mode !== 'v') return

      e.preventDefault()
      const progress = Math.min(Math.abs(dy) / 300, 1)
      el.style.transform = `translateY(${dy}px)`
      el.style.opacity = String(1 - progress * 0.7)
    }

    el.addEventListener('touchmove', onMove, { passive: false })
    return () => el.removeEventListener('touchmove', onMove)
  }, [fullscreen])
  const { isFavorite, toggle } = useFavorites()
  // listingId — короткий хвост из адреса (см. комментарий выше про
  // UUID_RE), нужен только чтобы ЗАГРУЗИТЬ это объявление — бэкенд
  // для get_listing специально понимает такую сокращённую форму.
  // Остальные эндпоинты (в том числе избранное) строго ждут полный
  // UUID и никакого запасного варианта для короткого хвоста не имеют
  // — FastAPI отбрасывает такой запрос как невалидный молча для
  // человека, лайк просто не срабатывал. listing.id — настоящий
  // полный id уже загруженного объявления, им пользуются и все
  // соседние кнопки на этой же странице (PromoteButton, ReportButton,
  // SimilarListings) — тут та же логика, просто раньше забыли применить.
  const fav = isFavorite(listing?.id)

  // Тот же отскок, что и на карточках в ленте — только при добавлении.
  const [justFaved, setJustFaved] = useState(false)
  const onFav = async () => {
    const wasFav = fav
    const res = await toggle(listing?.id)
    if (res?.needAuth) navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
    else if (!wasFav) {
      setJustFaved(true)
      setTimeout(() => setJustFaved(false), 450)
    }
  }

  // «Поделиться» — системное меню (WhatsApp/Telegram/куда угодно),
  // где есть navigator.share (почти все мобильные браузеры); там, где
  // нет (десктоп, старые браузеры) — копируем ссылку в буфер и
  // показываем короткое подтверждение самостоятельно, раз системного
  // сообщения об успехе тут не будет. Адрес строим сами
  // (origin + listing.path), а не берём window.location.href как есть —
  // в строке браузера мог остаться случайный ?promoted=... или другой
  // служебный параметр, которому нечего делать в ссылке для чужого человека.
  const [shareCopied, setShareCopied] = useState(false)
  const onShare = async () => {
    const url = `${window.location.origin}${listing?.path || window.location.pathname}`
    if (navigator.share) {
      try {
        await navigator.share({ title: listing?.title, url })
      } catch {
        // человек просто закрыл системное меню — не ошибка, молчим
      }
      return
    }
    try {
      await navigator.clipboard.writeText(url)
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 2000)
    } catch {
      // буфер обмена недоступен — редкий случай, молча ничего не делаем
    }
  }

  const [starting, setStarting] = useState(false)
  const [descOpen, setDescOpen] = useState(false)
  const [attrsOpen, setAttrsOpen] = useState(false)
  // Сигнал шлём один раз за просмотр объявления, не на каждый скролл/
  // клик — иначе пролистывание туда-сюда по фото раздувало бы счётчик
  // одним и тем же посетителем. Ref, не state: не должен вызывать
  // лишний рендер сам по себе.
  const gallerySignalSent = useRef(false)
  const descSignalSent = useRef(false)

  useEffect(() => {
    // Тот же класс утечки, что и с photoIdx ниже, только серьёзнее —
    // не деталь интерфейса, а вся страница целиком. Проверил настоящим
    // переходом между двумя объявлениями с явно различимыми
    // заголовками: в момент клика (0мс) страница ещё показывала
    // заголовок ПРЕЖНЕГО объявления, менялся только через ~50мс,
    // когда приходил ответ сервера. На медленном соединении это было
    // бы куда заметнее и дольше. setListing(null) сразу — возвращает
    // на уже готовый скелетон загрузки (см. if (!listing) ниже),
    // не оставляя чужие заголовок/фото/цену висеть даже на мгновение.
    setListing(null)
    api.getListing(listingId).then(setListing).catch(() => setListing(null))
    // Тот же самый класс бага, что нашли на страницах категорий —
    // React Router переиспользует один и тот же компонент при переходе
    // между объявлениями (тот же маршрут /:city/:category/:slug,
    // просто другой :slug — например, клик по «Похожие объявления»
    // или «Ещё у этого продавца»). photoIdx (текущее фото в галерее)
    // не сбрасывался — проверил настоящим переходом: пролистал до
    // 4-го из 5 фото на одном объявлении, перешёл на другое с двумя
    // фото — счётчик показал «2 / 2» вместо честного «1 / 2» на новой
    // странице. Заодно сбрасываю развёрнутые блоки описания/характеристик
    // и полноэкранный просмотр — по той же причине, не должны
    // оставаться открытыми с прошлого объявления.
    setPhotoIdx(0)
    setDescOpen(false)
    setAttrsOpen(false)
    setFullscreen(null)
    gallerySignalSent.current = false
    descSignalSent.current = false
    // Тот же класс утечки, что и выше, только опаснее — не просто
    // деталь интерфейса, а модальная панель, невидимо перехватывающая
    // клики. Открыл «Причина отклонения» на одном объявлении, ушёл по
    // ссылке (например, «Похожие объявления») не закрыв её явно —
    // showReasons оставался true, и на новом объявлении первый тап по
    // корзине уходил в невидимый оверлей прежней панели, а не в
    // обработчик кнопки. Снаружи выглядело как «корзина не нажимается»,
    // чинилось только перезагрузкой страницы, которая пересоздаёт
    // компонент с нуля.
    setDeleting(false)
    setShowReasons(false)
    setCustomReason(false)
    setReasonText('')
    // Одного сброса состояния мало — сам DOM-элемент полосы фото
    // тоже переиспользуется, и его scrollLeft остаётся от прошлого
    // объявления. onScroll на нём тут же пересчитывает photoIdx
    // обратно из старой позиции прокрутки, перекрывая сброс выше
    // (проверил именно так — без этой строки счётчик всё равно
    // показывал «2 / 2» вместо «1 / 2»). Явно возвращаем и саму
    // прокрутку в начало, не только React-состояние.
    if (photoStripRef.current) photoStripRef.current.scrollLeft = 0
  }, [listingId])

  useEffect(() => {
    if (!listing?.category_slug) return
    api.getCategorySchema(listing.category_slug)
      .then((res) => setSchema(res.attribute_schema || []))
      .catch(() => setSchema([]))
  }, [listing?.category_slug])

  const startChatWith = async (initialText) => {
    if (!listing) return
    setStarting(true)
    try {
      const chat = await api.startChat(listing.id, i18n.language)
      // Подсказка — не обязательный первый шаг: если человек выбрал
      // готовый вопрос, отправляем его сразу, тем же приёмом, что и
      // обычное сообщение из самого чата. Если это неудача — чат уже
      // создан, и открыть его всё равно стоит, просто без подставленного
      // текста: молчать полностью хуже, чем прийти в чат без готовой фразы.
      if (initialText) {
        try { await api.sendMessage(chat.id, initialText) } catch { /* открываем чат всё равно */ }
      }
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

  // После оплаты продвижения картой ЮKassa возвращает сюда же —
  // молча высаживать человека на ту же страницу без единого знака,
  // что деньги вообще куда-то ушли, не годится. Вебхук от ЮKassa
  // приходит не мгновенно, поэтому не читаем один раз, а опрашиваем
  // несколько раз с паузой — как и с проверкой документа. promoCheck:
  // null (ничего не проверяем) | 'checking' | 'confirmed' | 'pending'
  // (не дождались за отведённое время — не обязательно провал, вебхук
  // мог просто задержаться дольше).
  const [promoCheck, setPromoCheck] = useState(null)
  useEffect(() => {
    const promotedType = searchParams.get('promoted')
    if (!promotedType || !listing) return
    setPromoCheck('checking')
    let attempts = 0
    const maxAttempts = 5
    const poll = () => {
      api.listingPromotions(listing.id).then((res) => {
        const found = (res.items || []).some((p) => p.type === promotedType)
        if (found) {
          setPromoCheck('confirmed')
        } else if (attempts < maxAttempts) {
          attempts += 1
          setTimeout(poll, 1600)
        } else {
          setPromoCheck('pending')
        }
      }).catch(() => setPromoCheck('pending'))
    }
    poll()
    // Убираем параметр из адреса сразу — иначе обновление страницы
    // (или просто повторный визит по этой же ссылке) снова запускало
    // бы проверку заново.
    searchParams.delete('promoted')
    setSearchParams(searchParams, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing?.id])

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
  // Подсказки перед первым сообщением продавцу — хук должен жить тут,
  // до раннего return скелетоном загрузки ниже (if (!listing)): после
  // него хуки условны (на первом кадре, пока listing ещё не пришёл,
  // return срабатывает раньше и хук просто не вызывается) — React на
  // это ругается «Rendered more hooks than during the previous render»
  // и роняет всю страницу целиком. Раньше уже наступал на эти же
  // грабли — не с первого раза, тестом в реальном браузере, а не
  // просто чтением кода.
  const [quickReplyOpen, setQuickReplyOpen] = useState(false)
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

  // Готовые вопросы — не всегда одни и те же: торг и доставка
  // спрашивают только если это вообще применимо к объявлению, иначе
  // вопрос был бы бессмысленным («Торг уместен?» под ценой, где
  // владелец уже сказал, что торга нет). Первые два — общие, подходят
  // почти любой вещи или услуге.
  const quickReplies = [
    t('detail.quick_available'),
    t('detail.quick_when_see'),
    ...(listing?.price_negotiable ? [t('detail.quick_negotiable')] : []),
    ...(listing?.delivery_available ? [t('detail.quick_delivery')] : []),
  ]

  const handleWriteToSeller = () => {
    const myId = user?.id
    if (myId) {
      // Резюме — не тот случай, когда «где и когда посмотреть» уместно;
      // сразу открываем чат, как и раньше. Для обычной вещи или услуги —
      // сначала подсказки: пустой чат заставляет придумывать первую
      // фразу с нуля, а тут есть с чего начать одним касанием.
      if (isResume) startChatWith()
      else setQuickReplyOpen(true)
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
            ref={photoStripRef}
            onScroll={(e) => {
              const el = e.currentTarget
              const idx = Math.round(el.scrollLeft / el.clientWidth)
              setPhotoIdx(idx)
              // Сигнал глубины — реально пролистал, не просто фото
              // подгрузилось. Дальше первой (idx>0) уже значит
              // намеренное действие, не случайность.
              if (idx > 0 && !gallerySignalSent.current) {
                gallerySignalSent.current = true
                api.sendListingSignal(listingId, 'gallery_view').catch(() => {})
              }
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
            <button className="topbar-btn" onClick={onShare} aria-label={t('detail.share')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
                <path d="M8.6 10.5 15.4 6.5M8.6 13.5 15.4 17.5" />
              </svg>
            </button>
            <button className={fav ? 'topbar-btn on' : 'topbar-btn'} onClick={onFav} aria-label={t('misc.in_favorites')}>
              <svg viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" className={justFaved ? 'fav-pop' : ''}>
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
            <button className="circle-btn" onClick={onShare} aria-label={t('detail.share')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
                <path d="M8.6 10.5 15.4 6.5M8.6 13.5 15.4 17.5" />
              </svg>
            </button>
            <button className={fav ? 'circle-btn on' : 'circle-btn'} onClick={onFav} aria-label={t('misc.in_favorites')}>
              <svg viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" className={justFaved ? 'fav-pop' : ''}>
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
        {/* Стрелки — видны только на десктопе (styles.css, скрыты через
            hover:none touch-медиазапрос на телефоне/планшете, там и
            так свайп). Без них у мыши без сенсора и тачпада не было
            вовсе способа пролистать фото — колесо крутит только
            вертикально, а горизонтальной полосе это не помогает. */}
        {photos.length > 1 && (
          <>
            <button
              className="photo-nav photo-nav-prev"
              onClick={() => goToPhoto(photoIdx - 1)}
              disabled={photoIdx === 0}
              aria-label={t('detail.prev_photo')}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
            </button>
            <button
              className="photo-nav photo-nav-next"
              onClick={() => goToPhoto(photoIdx + 1)}
              disabled={photoIdx === photos.length - 1}
              aria-label={t('detail.next_photo')}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
            </button>
          </>
        )}
      </div>

      {/* Подтверждение только для запасного пути (копия в буфер) —
          там, где сработало системное меню navigator.share, у
          телефона уже есть своё «отправлено», добавлять здесь ещё
          одно поверх — задваивать. */}
      {shareCopied && (
        <div className="share-toast">{t('detail.link_copied')}</div>
      )}

      <div className="detail-sheet">
        {/* Подтверждение оплаты продвижения — сразу после возврата
            с ЮKassa, пока не прочитано и не отброшено переходом на
            другую страницу. Три состояния: идёт проверка, подтвердилось,
            не успели дождаться за отведённое время (не обязательно
            провал — вебхук мог задержаться, но снова опрашивать вечно
            тоже не дело). */}
        {promoCheck && (
          <div className={`promo-check-banner ${promoCheck}`}>
            {promoCheck === 'checking' && t('promo.checking')}
            {promoCheck === 'confirmed' && t('promo.confirmed')}
            {promoCheck === 'pending' && t('promo.check_pending')}
          </div>
        )}
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
        {listing.location_lat != null && (
          <LocationMap
            lat={listing.location_lat}
            lng={listing.location_lng}
            approximate={listing.location_approximate}
          />
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
              <button
                className="desc-more"
                onClick={() => {
                  setDescOpen(true)
                  if (!descSignalSent.current) {
                    descSignalSent.current = true
                    api.sendListingSignal(listingId, 'desc_expand').catch(() => {})
                  }
                }}
              >
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
                {(listing.owner.company_verified || listing.owner.document_verified) && (
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

      {/* Кнопка «Написать продавцу» — на мобильном она же .sticky-cta,
          прибитая к низу экрана под палец. На десктопе так же жить не
          может: там негде «низу экрана» быть, кнопка просто повисала
          бы отдельной узкой плашкой посреди страницы, оторванной от
          остальной карточки. Раньше .sticky-cta была соседом
          .detail-sheet и всегда рендерилась вне его — теперь она
          внутри: на мобильном это ничего не меняет (position:fixed не
          зависит от места в DOM), а на десктопе .detail-sheet .sticky-cta
          в styles.css превращает её в обычную часть карточки, сразу
          под ценой и продавцом, а не в конце после похожих объявлений. */}
      {gone ? (
        <div className={ctaHidden ? 'sticky-cta hidden' : 'sticky-cta'}>
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
        <div className={ctaHidden ? 'sticky-cta hidden' : 'sticky-cta'}>
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
      <div className={ctaHidden ? 'sticky-cta hidden' : 'sticky-cta'}>
        {listing.owner?.has_phone && (
          <button
            className="cta-btn icon"
            onClick={() => {
              // Не через панель с готовыми вопросами (та — для текстовых
              // сообщений) — иконка телефона ведёт сразу в чат, где и
              // живёт вся механика запроса звонка (call-status-row).
              const myId = user?.id
              if (myId) startChatWith()
              else navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
            }}
            aria-label={t('detail.call_via_chat')}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
          </svg>
        </button>
        )}
        <button className="cta-btn primary" disabled={starting} onClick={handleWriteToSeller}>
          {starting ? '...' : t(isResume ? 'detail.write_person' : 'detail.write_seller')}
        </button>
      </div>
      )}

      {/* Подсказки перед первым сообщением — пустой чат заставлял
          придумывать, с чего начать, с нуля. Готовый вопрос уходит
          сразу при касании; «Своё сообщение» — прежнее поведение,
          открывает пустой чат как раньше. */}
      {quickReplyOpen && (
        <>
          <div className="quick-reply-backdrop" onClick={() => setQuickReplyOpen(false)} />
          <div className="quick-reply-sheet">
            <div className="quick-reply-title">{t('detail.quick_title')}</div>
            {quickReplies.map((text) => (
              <button
                key={text}
                className="quick-reply-option"
                disabled={starting}
                onClick={() => { setQuickReplyOpen(false); startChatWith(text) }}
              >
                {text}
              </button>
            ))}
            <button
              className="quick-reply-option quick-reply-own"
              disabled={starting}
              onClick={() => { setQuickReplyOpen(false); startChatWith() }}
            >
              {t('detail.quick_own')}
            </button>
            <button className="quick-reply-cancel" onClick={() => setQuickReplyOpen(false)}>
              {t('rev.cancel')}
            </button>
          </div>
        </>
      )}

        {/* Другие объявления продавца — до похожих товаров и жалобы,
            а не после: на десктопе именно это место (после кнопки
            «Написать продавцу») оставалось пустым белым фоном под
            высоту фото слева, если описание короткое. На мобильном
            просто ещё один блок в общей ленте, ничего не меняется. */}
        <SellerListings sellerId={listing.owner?.id} excludeListingId={listing.id} />

        <SimilarListings listingId={listing.id} />

        <ReportButton listingId={listing.id} ownerId={listing.owner?.id} />

        {/* Просмотры/дата/номер — в самом низу страницы, тем же
            порядком, что и у Avito (после жалобы, а не под ценой) —
            это справочная строка, не то, что нужно видеть в первую
            секунду. Раньше видел только владелец, в «Моих
            объявлениях». Номер сначала был первыми 8 символами UUID
            (…-f7642d6b) — буквы вперемешку с цифрами не читаются
            и не произносятся вслух. Теперь number — настоящий
            автоинкремент в базе (см. модель Listing), только для
            этой строки, никак не связан с id объявления в остальном
            коде. */}
        <div className="detail-meta">
          {listing.views_count > 0 && (
            <span>{t('detail.views', { count: listing.views_count })}</span>
          )}
          {listing.favorites_count > 0 && (
            <span>{t('detail.favorited_count', { count: listing.favorites_count })}</span>
          )}
          {listing.published_at && <span>{relativeDate(listing.published_at, t)}</span>}
          {listing.number && <span>{t('detail.id', { id: listing.number })}</span>}
        </div>
      </div>


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
          className="lightbox"
          ref={lightboxRef}
          onClick={() => setFullscreen(null)}
          onTouchStart={(e) => {
            // Второй палец лёг ещё до того, как первый успел сдвинуться
            // достаточно, чтобы определить направление, — это уже щипок,
            // не начало свайпа закрытия, отслеживать нечего.
            if (e.touches.length > 1) {
              lightboxTouch.current = null
              return
            }
            const t = e.touches[0]
            // mode: пока неизвестно, куда в итоге пойдёт жест — решаем
            // по первым же пикселям движения, не заранее.
            lightboxTouch.current = { x: t.clientX, y: t.clientY, mode: null }
          }}
          onTouchEnd={(e) => {
            const start = lightboxTouch.current
            lightboxTouch.current = null
            const el = lightboxRef.current
            // Если на экране всё ещё остался хотя бы один палец (снимали
            // один из двух после щипка) — точно не отпускание свайпа
            // закрытия, ничего не делаем.
            if (e.touches.length > 0) return
            if (!start || start.mode !== 'v' || !el) return
            const t = e.changedTouches[0]
            const dy = t.clientY - start.y
            if (Math.abs(dy) > 80) {
              // долистали — доводим уже начатое движение до конца, тем
              // же направлением, что и тянул палец, и только тогда
              // закрываем по-настоящему.
              el.style.transition = 'transform .2s ease, opacity .2s ease'
              el.style.transform = `translateY(${dy > 0 ? '100%' : '-100%'})`
              el.style.opacity = '0'
              setTimeout(() => setFullscreen(null), 200)
            } else {
              // не дотянули — плавно возвращаем на место, а не дёргаем обратно рывком
              el.style.transition = 'transform .25s ease, opacity .25s ease'
              el.style.transform = ''
              el.style.opacity = ''
              setTimeout(() => { if (el) el.style.transition = '' }, 250)
            }
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
              // открываем сразу на том снимке, который смотрели в ленте
              if (el && el.dataset.ready !== '1') {
                el.scrollLeft = fullscreen * el.clientWidth
                el.dataset.ready = '1'
              }
            }}
            onClick={(e) => e.stopPropagation()}
            onScroll={(e) => {
              const el = e.currentTarget
              setPhotoIdx(Math.round(el.scrollLeft / el.clientWidth))
            }}
          >
            {photos.map((ph, i) => (
              <img key={ph.url || i} src={ph.url} alt="" />
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
