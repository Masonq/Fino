import { promptSheet, confirmSheet } from '../utils/confirm'
import SheetCard from '../components/SheetCard'
import Presence from '../components/Presence'
import Stars from '../components/Stars'
import PriceGauge from '../components/PriceGauge'
import MarketChart from '../components/MarketChart'
import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import RichText from '../components/RichText'
import Avatar from '../components/Avatar'
import AttrChips from '../components/AttrChips'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'
// Карта — по требованию: библиотека карт весит около 150 КБ и лежала
// в первом файле, хотя карта открывается только по нажатию, и далеко
// не каждым. Подгружается в момент открытия — это доли секунды, и они
// теряются на самой отрисовке карты.
const LocationMap = lazy(() => import('../components/LocationMap'))
import { addToHistory } from '../data/history'
import { useAuth } from '../context/AuthContext'
import JobRespond from '../components/JobRespond'
import StorefrontLink from '../components/StorefrontLink'
import { useFavorites } from '../context/FavoritesContext'
import ReportButton from '../components/ReportButton'
import PromoteButton from '../components/PromoteButton'
import SimilarListings from '../components/SimilarListings'
import SellerListings from '../components/SellerListings'
import HScroll from '../components/HScroll'
import { lastListPage } from '../utils/lastList'
import { rememberRemoved } from '../utils/removedListings'
import { formatPrice } from '../utils/money'
import { relativeDate, sinceMonth } from '../utils/time'
import { hasLanding } from '../data/landings'
import { showIsland } from '../utils/island'
import VerifiedMark from '../components/VerifiedMark'

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
  // Карта открывается только по нажатию на «Узнать подробности» — и на
  // телефоне, и на десктопе. Разница лишь в том, КАК она выглядит
  // после открытия: на телефоне отдельный полноэкранный экран, на
  // десктопе — блок прямо в потоке страницы под «Местоположением»
  // (см. .map-page в десктопной секции styles.css).
  const [mapOpen, setMapOpen] = useState(false)
  const [mapAddress, setMapAddress] = useState('')
  const [addressCopied, setAddressCopied] = useState(false)
  // Широкий экран — не просто «другие отступы»: заголовок стоит над
  // фотографией слева (а не в правой колонке над ценой), и готовые
  // вопросы продавцу показываются прямо в колонке, а не всплывающей
  // панелью. Один и тот же узел разметки нельзя переставить между
  // колонками средствами CSS, а дублировать заголовок в разметке —
  // два h1 на странице, поэтому решаем в JS. 900px — та же точка
  // перелома, что и во всех медиазапросах styles.css.
  const [wide, setWide] = useState(() => window.matchMedia('(min-width: 900px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 900px)')
    const onChange = (e) => setWide(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  const lang = i18n.language

  const copyAddress = () => {
    if (!mapAddress) return
    navigator.clipboard.writeText(mapAddress).then(() => {
      setAddressCopied(true)
      setTimeout(() => setAddressCopied(false), 1500)
    }).catch(() => {})
  }

  // При открытом просмотре страница под ним не должна прокручиваться:
  // иначе закрываешь снимок и оказываешься в другом месте объявления.
  useEffect(() => {
    if (fullscreen === null) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [fullscreen])

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
  // Звук у видео: по умолчанию выключен — иначе объявление начинает
  // говорить, едва человек его открыл, и это пугает.
  const [videoMuted, setVideoMuted] = useState(true)

  // Запоминаем просмотр — чтобы человек мог вернуться к тому, что
  // смотрел.
  //
  // Берём идентификатор из загруженного объявления, а не из адреса. В
  // красивом адресе (/beograd/mebel/stol-45e17e58) последняя часть — это
  // лишь восемь знаков от полного номера, и в историю попадал обрезок.
  // Страница «Вы смотрели» запрашивала объявления по нему, сервер
  // отвечал отказом, и список оставался пустым — открытое объявление в
  // него не попадало вовсе.
  useEffect(() => {
    if (listing?.id) addToHistory(listing.id)
  }, [listing?.id])

  const [schema, setSchema] = useState([])

  // Адрес текстом — координаты у нас есть, а самой строки «улица, дом»
  // в базе нет вовсе (только город), так что переводим координаты в
  // читаемый адрес тем же бесплатным Nominatim, что уже используется
  // в LocationPicker для обратной задачи (поиск адреса по тексту).
  //
  // Место вставки далось не с первого раза (три подряд промаха на
  // одном и том же блоке) — сюда, сразу после useState(listing), а
  // не выше (там listing ещё не объявлен — temporal dead zone на
  // чтение в массиве зависимостей) и не ниже, после if (!listing)
  // return (там же — React #310, другой хук на разных рендерах).
  // Правильное место — строго между объявлением каждой переменной,
  // которую использует хук, и любым условным return в компоненте,
  // без исключений в обе стороны.
  useEffect(() => {
    if (!mapOpen || !listing?.location_lat) return
    setMapAddress('')
    const controller = new AbortController()
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${listing.location_lat}&lon=${listing.location_lng}&zoom=17&addressdetails=1`
    fetch(url, { signal: controller.signal, headers: { 'Accept-Language': lang } })
      .then((r) => r.json())
      .then((data) => {
        const parts = (data?.display_name || '').split(',').map((s) => s.trim())
        setMapAddress(parts.slice(0, 3).join(', ') || displayCity(listing?.city, lang))
      })
      .catch(() => setMapAddress(displayCity(listing?.city, lang)))
    return () => controller.abort()
  }, [mapOpen, listing?.location_lat, listing?.location_lng, listing?.city, lang])


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

    // Жест может не закончиться вовсе: система забирает касание себе —
    // свайп от края экрана, входящий звонок, шторка уведомлений, — и
    // тогда браузер шлёт touchcancel, а touchend не приходит совсем.
    // Обработчика на этот случай не было, и просмотр оставался ровно
    // там, где его бросил палец: сдвинутым вниз и почти прозрачным
    // (touchmove доводит прозрачность до 0.3, а сдвиг легко уносит
    // картинку за нижний край). Со стороны экран выглядит обычной
    // страницей объявления, но поверх неё во всю высоту лежит
    // невидимый слой (position:fixed, z-index 80) и забирает себе все
    // нажатия — корзина, «поделиться», «в избранное» перестают
    // работать, и помогает только перезагрузка страницы. Именно этот
    // случай и ловили как «иногда не нажимается кнопка удалить».
    //
    // Возвращаем просмотр на место, как при недотянутом свайпе: жест
    // прерван, а не завершён, закрывать по нему нельзя.
    const onCancel = () => {
      lightboxTouch.current = null
      el.style.transition = 'transform .25s ease, opacity .25s ease'
      el.style.transform = ''
      el.style.opacity = ''
      setTimeout(() => { if (el) el.style.transition = '' }, 250)
    }
    el.addEventListener('touchcancel', onCancel)
    return () => {
      el.removeEventListener('touchmove', onMove)
      el.removeEventListener('touchcancel', onCancel)
    }
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
      showIsland({ text: t('detail.link_copied'), kind: 'ok' })
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
    setConfirmDelete(false)
    setDeleteError('')
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
      setDeleteError(t('detail.own_listing'))
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
  // разделы объявления одной строкой и примерный CO₂, сбережённый покупкой б/у (по средним оценкам для новых вещей)
  const paths = (listing?.category_path || []).map((c) => c.slug).join(' ')
  // животное отдают даром — «Ищет дом»: своя кнопка связи и блок
  const petHome = !!listing?.is_free && /(^|\s)pets(-dogs|-cats|-birds|-other|-farm)?(\s|$)/.test(paths) && !/pets-supplies/.test(paths) && listing?.attributes?.listing_kind !== 'supplies'
  const co2 = !listing ? 0 : /phones|smartphone/.test(paths) ? 60 : /laptop|computers|notebook/.test(paths) ? 200 : /electronics/.test(paths) ? 80
    : /furniture|furn-|home-garden/.test(paths) ? 90 : /fashion|clothes|shoes|kids-clothes/.test(paths) ? 15 : /kids|toys/.test(paths) ? 20
    : /bikes|bicycle|hobby-sport|sport/.test(paths) ? 40 : 0
  // команда исправляет цену: «18000 EUR», «18000 €», «2 500 000 дин», «0» или «даром» — бесплатно
  const fixPrice = async () => {
    const cur = listing.is_free ? '0' : `${listing.price ?? ''} ${listing.currency || 'EUR'}`.trim()
    const raw = await promptSheet({ title: t('mod.fix_price'), value: cur, placeholder: '18000 EUR' })
    if (raw == null) return
    const txt = String(raw).toLowerCase()
    const free = /^(0|даром|бесплатно|besplatno|free)$/.test(txt.trim())
    const num = parseFloat(txt.replace(/[^\d.,]/g, '').replace(/[.,](?=\d{3}\b)/g, '').replace(',', '.'))
    const currency = /€|eur|евро/.test(txt) ? 'EUR' : /rsd|дин|din/.test(txt) ? 'RSD' : (listing.currency || 'EUR')
    if (!free && !(num > 0)) return
    try {
      const r = await api.modPrice(listing.id, { price: free ? null : num, currency, is_free: free })
      setListing((l) => ({ ...l, price: r.price, currency: r.currency, is_free: r.is_free }))
    } catch { confirmSheet({ title: t('support.failed'), confirm: 'OK' }) }
  }
  // Продвигать может только сам владелец, и только пока объявление
  // реально в выдаче — снятое или ждущее модерации продвигать бы
  // впустую, покупатель его всё равно не увидит (та же проверка,
  // что и на бэкенде).
  const isOwner = user?.id && listing?.owner?.id === user.id && listing?.status === 'active'
  const [deleting, setDeleting] = useState(false)
  // Перенос в другой раздел — служебное действие: из чатов объявления
  // приезжают с разделом, угаданным по тексту, и ошибается он нередко.
  // Раньше такое можно было только снять с публикации, то есть
  // выбросить настоящий товар вместе с ошибкой разбора.
  const [movingOpen, setMovingOpen] = useState(false)
  const [moveQuery, setMoveQuery] = useState('')
  // Оценка цены приходит вместе с карточкой: отдельным запросом блок
  // появлялся через секунду после загрузки и сдвигал вниз всё под
  // собой — заголовок, продавца, описание.
  const [priceOpen, setPriceOpen] = useState(false)
  const [moveTree, setMoveTree] = useState([])
  const [moving, setMoving] = useState(false)
  const [showReasons, setShowReasons] = useState(false)
  // false | true (обычное подтверждение) | 'force' (с историей)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteError, setDeleteError] = useState('')
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

  // Название раздела на языке интерфейса: с сервера оно приходит
  // словарём {ru, en, sr}.
  const catName = (c) => (c ? (c.name?.[i18n.language] || c.name?.ru || c.slug) : '')

  // Плоский список всех разделов для поиска: слаг и название на всех
  // трёх языках, чтобы «rukavice» находилось так же, как «перчатки», и
  // путь родителей — по одному названию «Обувь» не понять, детская она
  // или мужская.
  const moveMatches = (() => {
    const q = moveQuery.trim().toLowerCase()
    if (!q) return []
    const out = []
    const walk = (node, trail) => {
      const path = [...trail, catName(node)]
      const hay = [node.slug, node.name?.ru, node.name?.en, node.name?.sr]
        .filter(Boolean).join(' ').toLowerCase()
      const leaf = !(node.children || []).length
      // В раздел верхнего уровня класть нельзя — предлагаем только то,
      // куда перенос разрешён.
      if (hay.includes(q) && trail.length > 0) {
        out.push({ ...node, path: path.slice(0, -1).join(' → '), leaf })
      }
      ;(node.children || []).forEach((c) => walk(c, path))
    }
    moveTree.forEach((root) => walk(root, []))
    return out.slice(0, 40)
  })()

  const openMove = async () => {
    setMovingOpen(true)
    if (moveTree.length) return
    try {
      setMoveTree(await api.getCategories())
    } catch {
      setMoveTree([])
    }
  }

  const doMove = async (categoryId) => {
    setMoving(true)
    try {
      await api.modMove(listing.id, categoryId)
      // Перечитываем объявление: раздел показан на самой странице, и
      // человек должен увидеть новый, а не тот, что был.
      const fresh = await api.getListing(listing.id)
      setListing(fresh)
      setMovingOpen(false)
    } catch (e) {
      // Разбираем ответ сами: общей функции для этого на странице нет,
      // а errorText живёт только на странице входа и знает лишь её
      // ошибки. Взял её по привычке — линт остановил деплой, и верно
      // сделал.
      const message = {
        pick_subcategory: t('move.pick_sub'),
        category_not_found: t('move.no_category'),
        not_found: t('move.gone'),
      }[e?.code] || t('move.failed')
      setDeleteError(message)
    } finally {
      setMoving(false)
    }
  }

  // Куда уходить после удаления: на ту же страницу-список, с которой
  // пришли, со всеми условиями поиска. Раздел удалённого объявления —
  // запасной вариант на случай прямого захода по ссылке.
  const afterDelete = () => {
    const back = lastListPage()
    navigate(back !== '/' ? back
      : (listing?.category_slug ? `/search?category=${listing.category_slug}` : '/'),
      { replace: true })
  }

  const doDelete = async (force = false) => {
    setConfirmDelete(false)
    setShowReasons(false)
    setDeleting(true)
    try {
      await api.deleteListing(listing.id, force)
      // Списки держатся в памяти несколько минут — без этой отметки
      // удалённое объявление возвращалось на экран при возврате назад.
      rememberRemoved(listing.id)
      afterDelete()
    } catch (e) {
      if (e.code === 'listing_has_history' && isStaff && !force) {
        // Такое удаление стирает настоящую переписку, жалобы и отзывы —
        // спрашиваем второй раз, отдельно и явно.
        setConfirmDelete('force')
      } else {
        setDeleteError(e.code === 'listing_has_history' ? t('my.delete_has_history') : t('auth.err_generic'))
      }
    } finally { setDeleting(false) }
  }

  const handleDelete = () => {
    // Объявление ещё не загрузилось — говорим об этом вслух.
    if (!listing) { setDeleteError(t('detail.not_loaded_yet')); return }
    // Ни confirm, ни alert: страницу открывают из Telegram, а его
    // встроенный браузер такие окна иногда просто не показывает —
    // нажатие на корзину выглядело как «ничего не произошло», и
    // помогала только перезагрузка в обычном браузере. Спрашиваем
    // своей панелью, которая рисуется на странице и видна всегда.
    if (canReturnToEdit) { setShowReasons(true); return }
    setConfirmDelete(true)
  }

  const returnToEdit = async (reason) => {
    if (!listing) return
    setShowReasons(false)
    setDeleting(true)
    try {
      await api.modReject(listing.id, reason)
      rememberRemoved(listing.id)
      afterDelete()
    } catch { /* оставляем как было */ }
    finally { setDeleting(false) }
  }

  if (!listing) {
    // Скелетон повторяет реальную раскладку страницы блок в блок и по
    // высотам (см. .detail-price/.detail-title/.seller-row/.attr-row в
    // styles.css), а не четыре условные полоски: раньше настоящее
    // содержимое при подстановке было заметно выше скелетона, и
    // страница резко прыгала вниз в момент загрузки — особенно
    // бросалось в глаза на карточке продавца, которой в скелетоне не
    // было вовсе.
    return (
      // key нужен, чтобы React не превратил узел листа из скелета («detail-sheet», стоит на 371 точке) в галерею
      // (стоит на 0): пользователь ничего не видит, а браузер и Google засчитывают это как сдвиг 0,65 в Core Web Vitals.
      <div className="detail-page" key="detail-skeleton">
        <div className="detail-photo sk-block" />
        <div className="detail-sheet">
          {/* цена — 25px */}
          <div className="sk-block sk-line" style={{ height: 25, width: '48%' }} />
          {/* заголовок — 17.5px, line-height 1.3, marginTop 12 */}
          <div className="sk-block sk-line" style={{ height: 23, width: '90%', marginTop: 12 }} />
          <div className="sk-block sk-line" style={{ height: 23, width: '65%', marginTop: 4 }} />
          {/* карточка продавца — .seller-row: 46px аватар + padding 15px, marginTop 20 */}
          <div className="sk-block" style={{ height: 76, borderRadius: 17, marginTop: 20 }} />
          {/* кнопки связи — .sticky-cta */}
          <div className="sk-block" style={{ height: 48, borderRadius: 14, marginTop: 12 }} />
          {/* «Местоположение» — заголовок 13.5px + строка города 12px */}
          <div className="sk-block sk-line" style={{ height: 14, width: '38%', marginTop: 22 }} />
          <div className="sk-block sk-line" style={{ height: 12, width: '30%', marginTop: 8 }} />
          {/* «Характеристики» + две строки .attr-row по 11px padding */}
          <div className="sk-block sk-line" style={{ height: 14, width: '42%', marginTop: 22 }} />
          <div className="sk-block" style={{ height: 88, borderRadius: 14, marginTop: 8 }} />
        </div>
      </div>
    )
  }

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
  // Оценка цены приходит внутри самой карточки — см. price_check в
  // listings.py. Отдельным запросом блок появлялся через секунду после
  // загрузки и сдвигал вниз всё под собой.
  const priceCheck = listing?.price_check || null

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
      // Через строку: поле могло быть числом до того, как стало списком,
      // и 2 !== '2' оставляло бы голую цифру без подписи.
      const opt = field.options?.find((o) => String(o.value) === String(value))
      return opt?.label?.[lang] || opt?.label?.ru || value
    }
    // Атрибуты, заполненные словами («Вид услуги»), переводятся вместе с
    // объявлением — берём перевод, если он есть на нужном языке.
    // перевод есть у любого поля, написанного словами (цвет, материал…), — не только у помеченных translatable
    return listing?.attributes_i18n?.[lang]?.[key] || value
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
      // На широком экране готовые вопросы уже стоят в правой колонке
      // («Спросите у продавца») — всплывающая панель с тем же
      // содержимым была бы вторым списком тех же кнопок поверх
      // первого. Кнопка «Написать» там открывает чат сразу.
      if (isResume || wide) startChatWith()
      else setQuickReplyOpen(true)
    } else {
      navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
    }
  }

  return (
    <div className="detail-page" key="detail-loaded">
      {/* Хлебные крошки — на десктопе первой строкой во всю ширину, над
          фотографией и правой колонкой (на телефоне скрыты в CSS: там
          для возврата есть кнопка «назад»). Раньше лежали внутри
          .detail-aside и потому начинались с середины страницы, от
          края правой колонки. */}
      {listing.category_path?.length > 0 && (
        <nav className="breadcrumbs">
          <Link to="/">{t('nav.home')}</Link>
          {listing.category_path.map((c) => (
            <span key={c.slug}>
              <span className="breadcrumbs-sep">›</span>
              <Link to={hasLanding(c.slug) ? `/c/${c.slug}` : `/search?category=${c.slug}`}>
                {c.name?.[lang] || c.name?.ru || c.slug}
              </Link>
            </span>
          ))}
        </nav>
      )}
      {/* Левая колонка на широком экране — заголовок, фотография и
          миниатюры одним блоком. Обёртка не для красоты: без неё эти
          три узла были отдельными элементами сетки и их приходилось
          расставлять по номерам строк, а правая колонка растягивалась
          на span в три строки — под фотографией от этого оставалась
          пустая полоса в 160px (нашёл на снимке, не в коде). С
          обёрткой сетка простая: две колонки, три строки, всё
          раскладывается само. На телефоне обёртка ничего не меняет —
          обычный блок во всю ширину вокруг фотографии. */}
      <div className="detail-gallery">
      {/* Заголовок: на широком экране — над фотографией, слева, а цена
          остаётся первой строкой правой колонки, ровно на одной линии
          с ним. На телефоне заголовок идёт под ценой, как и был. */}
      {wide && <div className="detail-title detail-title-wide">{translation?.title}</div>}
      {/* То же имя, что у фотографии в карточке ленты: браузер переносит
          снимок с одной страницы на другую, а не гасит и показывает
          заново. */}
      <div
        className="detail-photo"
        style={listing ? { viewTransitionName: `photo-${listing.id}` } : undefined}
      >
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
                onClick={ph.is_video ? undefined : () => setFullscreen(i)}
              >
                {ph.is_video ? (
                  // Видео играет само, без звука и по кругу — как живое
                  // фото. Кнопок браузера здесь нет намеренно: они
                  // рисуются поверх видео крупными кружками — пауза, две
                  // перемотки, раскрытие в углу — и закрывают наши
                  // кнопки сверху, да и само видео. Видно на снимке
                  // объявления с видео.
                  //
                  // Вместо них: своя кнопка звука в углу и тап по видео,
                  // открывающий полный экран. Там кнопки браузера
                  // остаются — на весь экран они уместны и никому не
                  // мешают.
                  <>
                    <video
                      className="photo-main"
                      src={ph.url}
                      poster={ph.thumbnail_url}
                      autoPlay
                      muted={videoMuted}
                      loop
                      playsInline
                      onClick={() => setFullscreen(i)}
                    />
                    <button
                      className="photo-sound"
                      onClick={(e) => { e.stopPropagation(); setVideoMuted((m) => !m) }}
                      aria-label={videoMuted ? t('listing.sound_on') : t('listing.sound_off')}
                    >
                      {videoMuted ? (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 5 6 9H3v6h3l5 4V5z" /><path d="m17 9 4 6" /><path d="m21 9-4 6" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 5 6 9H3v6h3l5 4V5z" /><path d="M16 8a5 5 0 0 1 0 8" />
                        </svg>
                      )}
                    </button>
                  </>
                ) : (
                  <>
                    <img className="photo-blur" src={ph.url} alt="" aria-hidden="true" />
                    <img className="photo-main" src={ph.url} alt="" loading={i === 0 ? 'eager' : 'lazy'} />
                  </>
                )}
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
              <button className="topbar-btn" onClick={openMove} aria-label={t('move.title')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7h7l2 2h9v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /><path d="m12 12 3 3-3 3" /><path d="M15 15H9" /></svg>
              </button>
            )}
            {isStaff && (
              <button className="topbar-btn danger" onClick={handleDelete} disabled={deleting || !listing} aria-label={t('my.delete')}>
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
              <button className="circle-btn" onClick={openMove} aria-label={t('move.title')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7h7l2 2h9v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /><path d="m12 12 3 3-3 3" /><path d="M15 15H9" /></svg>
              </button>
            )}
            {isStaff && (
              <button className="circle-btn danger" onClick={handleDelete} disabled={deleting || !listing} aria-label={t('my.delete')}>
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
        {/* Телефон: мини-кадры поверх низа фотографии — видно, сколько снимков и что на них, можно сразу
            перейти к нужному (Baymard: 76% мобильных сайтов не показывают миниатюры, и люди пропускают фото). */}
        {!wide && photos.length > 2 && (
          <div className="photo-minis" aria-hidden="true">
            {photos.slice(0, 5).map((ph, i) => (
              <button type="button" tabIndex={-1} key={ph.url || i} className={i === photoIdx ? 'photo-mini on' : 'photo-mini'} onClick={() => goToPhoto(i)}>
                {ph.thumbnail_url || ph.url ? <img src={ph.thumbnail_url || ph.url} alt="" loading="lazy" /> : null}
                {i === 4 && photos.length > 5 && <span className="photo-mini-more">+{photos.length - 5}</span>}
              </button>
            ))}
          </div>
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

      {/* Миниатюры — под фотографией и только на широком экране: там
          мышью листать стрелками по одной неудобно, а места под ряд
          снимков хватает. На телефоне их нет намеренно — свайп и так
          естественный, а ряд отнял бы высоту у самой фотографии. */}
      {wide && photos.length > 1 && (
        <HScroll className="photo-thumbs">
          {photos.map((ph, i) => (
            <button
              type="button"
              key={ph.url || i}
              className={i === photoIdx ? 'photo-thumb on' : 'photo-thumb'}
              onClick={() => goToPhoto(i)}
              aria-label={`${i + 1} / ${photos.length}`}
            >
              <img src={ph.is_video ? ph.thumbnail_url : ph.url} alt="" loading="lazy" decoding="async" />
              {ph.is_video && (
                <span className="photo-thumb-play">
                  <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
                </span>
              )}
            </button>
          ))}
        </HScroll>
      )}
      </div>

      {/* Подтверждение только для запасного пути (копия в буфер) —
          там, где сработало системное меню navigator.share, у
          телефона уже есть своё «отправлено», добавлять здесь ещё
          одно поверх — задваивать. */}

      <div className="detail-sheet">
        {/* Правая колонка — «шапка» объявления: цена, продавец, кнопки,
            местоположение. Левая (.detail-main ниже) — содержимое:
            характеристики, описание, объявления продавца. На телефоне
            обе идут одна под другой обычным потоком (flex только в
            десктопном медиазапросе). */}
        <div className="detail-aside">
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
        {/* Путь по разделам на телефоне — над ценой, мелко (Baymard: без полного пути разделов на мобильной
            странице товара люди теряются; 36% сайтов его не дают). На широком экране путь — отдельной строкой сверху. */}
        {!wide && listing.category_path?.length > 0 && (
          <nav className="m-crumbs" aria-label={t('detail.section')}>
            {listing.category_path.map((c, i) => (
              <span key={c.slug}>
                {i > 0 && <span className="m-crumbs-sep">›</span>}
                <Link to={hasLanding(c.slug) ? `/c/${c.slug}` : `/search?category=${c.slug}`}>{c.name?.[lang] || c.name?.ru || c.slug}</Link>
              </span>
            ))}
          </nav>
        )}
        <div className="detail-price">
          {listing.price != null
            ? formatPrice(listing.price, listing.currency, lang)
            : listing.is_free
              ? <span className="price-free">{/(^|\s)pets(-dogs|-cats|-birds|-other|-farm)?(\s|$)/.test(paths) && !/pets-supplies/.test(paths) && listing.attributes?.listing_kind !== 'supplies' ? t('pets.home') : t('detail.free')}</span>
              : t(isResume ? 'detail.no_salary' : 'detail.no_price')}
          {listing.previous_price && (
            <span className="price-old">
              {formatPrice(listing.previous_price.price, listing.previous_price.currency, lang)}
            </span>
          )}
          {/* команда: исправить цену — разбор цены из Telegram ошибается («18 000 €» → «18 000 RSD») */}
          {isStaff && (
            <button type="button" className="price-fix" onClick={fixPrice} aria-label={t('mod.fix_price')}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
            </button>
          )}
        </div>
        {isResume && listing.price != null && (
          <div className="price-note">{t('detail.desired_salary')}</div>
        )}

        {listing.price_negotiable && <div className="neg-pill">{t('detail.negotiable')}</div>}
        {listing.is_reserved && (
          <div className="reservation-banner">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
            {listing.reserved_for_me ? t('detail.reserved_for_me') : t('detail.reserved_other')}
          </div>
        )}

        {!wide && <div className="detail-title">{translation?.title}</div>}
        {/* PLONK 2.0: главные факты одной строкой значками — где, когда, сколько смотрели */}
        <div className="fact-chips">
          {listing.city && (
            <span className="fact-chip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 21s-7-6.1-7-11.5A7 7 0 0 1 19 9.5C19 14.9 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></svg>
              {displayCity(listing.city, lang)}
            </span>
          )}
          {(listing.published_at || listing.created_at) && (
            <span className="fact-chip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              {relativeDate(listing.published_at || listing.created_at, t, lang)}
            </span>
          )}
          {listing.views_count > 0 && (
            <span className="fact-chip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></svg>
              {listing.views_count}
            </span>
          )}
        </div>
        {/* Помечаем явно: иначе продавец с нашего сайта конкурирует с
            перепечаткой и не понимает, почему объявление ведёт себя иначе. */}
        {listing.external_source === 'telegram' && (
          <div className="from-telegram">{t('detail.from_telegram')}</div>
        )}
        {/* Главные характеристики значками — для квартир и машин их
            смотрят раньше описания и раньше цены соседей. */}
        <AttrChips
          rootSlug={listing.category_path?.[0]?.slug}
          attributes={listing.attributes}
          schema={schema}
          attrLabel={attrLabel}
          attrValue={attrValue}
        />

        {/* Оценка цены. Покупатель всё равно делает это сам — открывает
            десяток похожих и смотрит, из чего выбирать. Считаем за него,
            и по нажатию честно показываем, на чём считали. */}
        {priceCheck?.verdict && !isResume && (
          <button className={`price-check ${priceCheck.verdict}`} onClick={() => setPriceOpen(true)}>
            {/* Картинка, а не значок: оценку читают мельком, и цветная
                монета узнаётся быстрее контурной стрелки. Все три
                приведены к одному размеру плашки, чтобы при разных
                оценках ничего не прыгало. */}
            <img
              className="price-check-icon"
              src={`/price/price-${priceCheck.verdict}.png`}
              alt=""
              width="44"
              height="44"
            />
            <span className="price-check-text">
              <b>{t(`price_check.${priceCheck.verdict}`)}</b>
              <span>{t('price_check.subtitle')}</span>
            </span>
            <svg className="price-check-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
          </button>
        )}

        {listing.owner && (
          <Link to={`/seller/${listing.owner.id}`} className="seller-row">
            <Avatar
              src={listing.owner.avatar_url}
              name={listing.owner.company_name || listing.owner.display_name}
              className={listing.owner.is_company ? 'seller-avatar is-company' : 'seller-avatar'}
            />
            <div>
              <div className="seller-name">
                <span className="name-text">{listing.owner.company_name || listing.owner.display_name}</span>
                <VerifiedMark official={listing.owner.official} verified={listing.owner.company_verified || listing.owner.document_verified} />
                {/* Подпись к галочке — рядом с ней, а не отдельной
                    строкой ниже: иначе непонятно, к чему относится
                    сама галочка, а карточка растёт на целую строку. */}
                {(listing.owner.official || listing.owner.document_verified) && (
                  <span className="seller-verified-note">{listing.owner.official ? t('verify.official') : t('seller.fact_verified')}</span>
                )}
              </div>
              <div className="seller-meta">
                {listing.owner.is_company && (
                  <span className="seller-badge-inline">{t('seller.company_badge')} · </span>
                )}
                {listing.owner.rating_count > 0
                  ? <><Stars value={listing.owner.rating_avg} />{`${listing.owner.rating_avg?.toFixed(1)} · ${t('rev.count', { count: listing.owner.rating_count })}`}</>
                  : t('rev.none_yet')}
              </div>

              {/* Факты, по которым человек решает, верить ли продавцу.
                  Не выдуманный «рейтинг доверия» из формулы, которую
                  никто не проверит, а то, что проверяется само: сколько
                  он здесь, подтверждена ли личность, как быстро
                  отвечает. Вывод человек делает сам. */}
              <div className="seller-facts">
                {listing.owner.since && (
                  <span className="seller-fact">
                    {t('seller.fact_since', { date: sinceMonth(listing.owner.since, i18n.language) })}
                  </span>
                )}
                {listing.owner.reply_speed && (
                  <span className="seller-fact">{listing.owner.reply_speed}</span>
                )}
                {listing.owner.listings_count > 1 && (
                  <span className="seller-fact">
                    {t('seller.fact_listings', { count: listing.owner.listings_count })}
                  </span>
                )}
              </div>
            </div>
            {/* шеврон: без него строка не читается как ведущая куда-то */}
            <svg className="seller-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </Link>
        )}

        {/* машины (65): цена на рынке за год — медиана таких же по месяцам и где на этой вилке эта машина */}
        {/(^|\s)(auto|cars|moto)(\s|$)/.test(paths) && listing.price != null && <MarketChart listingId={listing.id} />}
        {/* пристрой животных (123): животное отдают даром — блок «Ищет дом» с тем, что известно, и памяткой для того, кто берёт */}
        {/(^|\s)pets(-dogs|-cats|-birds|-other|-farm)?(\s|$)/.test(paths) && !/pets-supplies/.test(paths) && listing.is_free && listing.attributes?.listing_kind !== 'supplies' && (
          <div className="pet-home">
            <div className="pet-home-head">
              <span className="pet-home-ico" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><circle cx="5.5" cy="10" r="2.2" /><circle cx="9.5" cy="6" r="2.2" /><circle cx="14.5" cy="6" r="2.2" /><circle cx="18.5" cy="10" r="2.2" /><path d="M12 11.5c-3 0-5.5 3.6-5.5 5.6 0 1.6 1.2 2.4 2.7 2.4 1.1 0 1.8-.5 2.8-.5s1.7.5 2.8.5c1.5 0 2.7-.8 2.7-2.4 0-2-2.5-5.6-5.5-5.6Z" /></svg>
              </span>
              <div><b>{t('pets.title')}</b><span>{t('pets.sub')}</span></div>
            </div>
            <div className="pet-home-facts">
              <span className={listing.attributes?.vaccinated ? 'is-yes' : ''}>
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5z" />{listing.attributes?.vaccinated && <path d="m9 12 2 2 4-4" />}</svg>
                {listing.attributes?.vaccinated ? t('pets.vaccinated') : t('pets.vaccinated_unknown')}
              </span>
              {listing.attributes?.age && (
                <span>
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M3 10h18M8 3v4M16 3v4" /></svg>
                  {t('pets.age')}: {listing.attributes.age}
                </span>
              )}
            </div>
            <div className="pet-home-tips-title">{t('pets.tips_title')}</div>
            <ol className="pet-home-tips">
              <li><i>1</i><span>{t('pets.tip_meet')}</span></li>
              <li><i>2</i><span>{t('pets.tip_ask')}</span></li>
              <li className="is-warn"><i>!</i><span>{t('pets.tip_pay')}</span></li>
            </ol>
          </div>
        )}
        {/* благотворительность (102): продавец отметил «деньги идут на доброе дело» */}
        {listing?.attributes?.charity && (
          <div className="detail-charity"><span aria-hidden="true">💚</span><div><b>{t('extras.charity_title')}</b><span>{listing.attributes.charity_note || t('extras.charity_text')}</span></div></div>
        )}
        {/* аренда жилья (60): памятка о документах — главный вопрос приезжих */}
        {/flats|houses|rooms|real-estate/.test(paths) && /rent|najam|arend|daily/.test(`${listing.category_path?.map((c) => c.slug).join(' ')} ${listing.attributes?.deal_type || ''}`) && (
          <Link to="/vodic" className="detail-memo">
            <b>{t('extras.rent_memo_title')}</b>
            <span>{t('extras.rent_memo_text')}</span>
          </Link>
        )}
        {/* б/у вместо нового (101): сколько CO₂ не выбросили — повод гордиться покупкой */}
        {co2 > 0 && listing.condition !== 'new' && (
          <div className="detail-co2"><span aria-hidden="true">🌱</span>{t('extras.co2', { kg: co2 })}</div>
        )}
        {listing?.owner?.id && listing?.attributes?.listing_kind !== 'vacancy' && listing?.attributes?.listing_kind !== 'resume' && (
          <StorefrontLink ownerId={listing.owner.id} listingId={listing.id} initial={listing.owner_storefront} />
        )}
        {listing?.attributes?.listing_kind === 'vacancy' && listing?.status === 'active' && listing.external_source !== 'telegram' && (
          <div className="jr-slot"><JobRespond listing={listing} /></div>
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
          {/* Не вошёл — сперва вход, потом Telegram.
              Прямая ссылка была открыта всем, и блокировка обходилась в
              один клик: заблокированный не мог написать через сайт, но
              спокойно писал тому же человеку в Telegram. Раз доступ
              закрыт — значит закрыт весь, а не наполовину.
              Гостю вход тоже полезен: продавцу приятнее отвечать
              человеку с аккаунтом, а не безымянной ссылке. */}
          {!user ? (
            <button
              className="cta-btn primary telegram"
              onClick={() => navigate(
                `/login?returnTo=${encodeURIComponent(window.location.pathname)}`)}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21.9 4.3 18.8 19c-.2 1-.9 1.3-1.7.8l-4.7-3.5-2.3 2.2c-.3.3-.5.5-1 .5l.4-4.9 9-8.1c.4-.3-.1-.5-.6-.2L7 10.7 2.4 9.2c-1-.3-1-1 .2-1.5l18-6.9c.8-.3 1.5.2 1.3 1.5Z" />
              </svg>
              {t('detail.open_telegram')}
            </button>
          ) : (
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
          )}
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
          {starting ? '...' : t(isResume ? 'detail.write_person' : petHome ? 'pets.want' : 'detail.write_seller')}
        </button>
      </div>
      )}

        {/* «Спросите у продавца» — на широком экране готовые вопросы
            стоят прямо под кнопками, а не прячутся во всплывающей
            панели: место в колонке есть, и первый вопрос уходит одним
            нажатием. На телефоне остаётся панель (см. handleWriteToSeller):
            там этот список занял бы пол-экрана над описанием. */}
        {wide && !gone && !isOwner && !isResume && listing.owner
          && listing.external_source !== 'telegram' && (
          <div className="quick-ask">
            <div className="quick-ask-title">{t('detail.quick_title')}</div>
            {quickReplies.map((text) => (
              <button
                key={text}
                type="button"
                className="quick-ask-option"
                disabled={starting}
                onClick={() => {
                  if (user?.id) startChatWith(text)
                  else navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
                }}
              >
                {text}
              </button>
            ))}
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

        </div>

        <div className="detail-main">
        {/* Местоположение и карта — на широком экране идут под фотографией
            и правой колонкой, во всю ширину страницы (карта в узкой
            колонке была шириной с кнопку). Порядок на телефоне не
            меняется: .detail-main лежит сразу за колонкой и в обычном
            потоке продолжает её. */}
        {/* Город и координаты — независимые поля в базе, может быть
            только одно из двух: показываем блок, если есть хоть что-то,
            и каждую часть — по своему условию. */}
        {(listing.city || listing.location_lat != null) && (
          <div className="loc-block">
            <div className="desc-title loc-title">{t('detail.map_location_label')}</div>
            <div className="detail-loc-row">
              {listing.city && (
                <div className="detail-loc">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" />
                  </svg>
                  {displayCity(listing.city, lang)}
                </div>
              )}
              {/* Ссылка на карту — справа от города, в той же строке.
                  Сама карта открывается отдельным полноэкранным
                  экраном, не разворачивается тут же. */}
              {listing.location_lat != null && (
                <button type="button" className="detail-map-link" onClick={() => setMapOpen(true)}>
                  {t('detail.map_learn_more')}
                </button>
              )}
            </div>
            {mapOpen && listing.location_lat != null && (
          <div className="map-page">
            <div className="map-page-head">
              <button type="button" className="topbar-btn" onClick={() => setMapOpen(false)} aria-label={t('actions.back')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
              </button>
              <span className="map-page-title">{translation?.title}</span>
            </div>
            <Suspense fallback={<div className="map-loading" />}>
              <LocationMap
                lat={listing.location_lat}
                lng={listing.location_lng}
                approximate={listing.location_approximate}
                height="100%"
              />
            </Suspense>
            <div className="map-page-address">
              <span className="map-page-address-label">{t('detail.map_location_label')}</span>
              <div className="map-page-address-row">
                <span className="map-page-address-text">{mapAddress || displayCity(listing.city, lang)}</span>
                <button type="button" className="map-page-copy-btn" onClick={copyAddress} aria-label={t('actions.copy')}>
                  {addressCopied ? (
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 13l5 5L19 7" /></svg>
                  ) : (
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M4 16V5a1 1 0 0 1 1-1h11" /></svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
          </div>
        )}

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
            <RichText
              className={`desc-text${
                !descOpen && (translation.description || '').length > 320
                  ? ' clipped' : ''}`}
              text={translation.description}
            />
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

        {/* Подсказки перед первым сообщением — пустой чат заставлял
          придумывать, с чего начать, с нуля. Готовый вопрос уходит
          сразу при касании; «Своё сообщение» — прежнее поведение,
          открывает пустой чат как раньше. */}
      <Presence show={Boolean(quickReplyOpen)}>{(Boolean(quickReplyOpen)) && (<div className="quick-reply-layer">
          <div className="quick-reply-backdrop" onClick={() => setQuickReplyOpen(false)} />
          <SheetCard base="quick-reply-sheet" onClose={() => setQuickReplyOpen(false)}>
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
          </SheetCard>
        </div>)}</Presence>

        {/* Другие объявления продавца — до похожих товаров и жалобы,
            а не после: на десктопе именно это место (после кнопки
            «Написать продавцу») оставалось пустым белым фоном под
            высоту фото слева, если описание короткое. На мобильном
            просто ещё один блок в общей ленте, ничего не меняется. */}
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
          {wide && listing.views_count > 0 && (
            <span>{t('detail.views', { count: listing.views_count })}</span>
          )}
          {listing.favorites_count > 0 && (
            <span>{t('detail.favorited_count', { count: listing.favorites_count })}</span>
          )}
          {wide && listing.published_at && <span>{relativeDate(listing.published_at, t, i18n.language)}</span>}
          {listing.number && <span>{t('detail.id', { id: listing.number })}</span>}
        </div>

        {/* «Другие объявления продавца» и «Похожие» — после жалобы и справочной строки, в самом конце. Оба блока
            молчат, пока не загрузятся, а стояли выше: приходили через полсекунды и толкали «Пожаловаться» и
            строку с просмотрами вниз (замер: на 244 точки, у объявления из истории — прямо на экране).
            Внизу они дописываются и ничего над собой не двигают. */}
        <SellerListings sellerId={listing.owner?.id} excludeListingId={listing.id} />
        <SimilarListings listingId={listing.id} />
        </div>
      </div>


      {/* Выбор раздела для переноса.
          Тем же видом, что окно причин возврата, — служебные действия
          должны выглядеть одинаково. Список разделов с подразделами:
          в раздел верхнего уровня класть нельзя, там объявления никто
          не ищет, поэтому такие строки только раскрывают вложенные. */}
      <Presence show={movingOpen}>{(movingOpen) && (
        <div className="reasons-sheet" onClick={() => setMovingOpen(false)}>
          <SheetCard onClose={() => setMovingOpen(false)}>
            <div className="reasons-title">{t('move.title')}</div>
            <div className="move-current">
              {t('move.now')}: <b>{
                listing.category_name?.[i18n.language]
                || listing.category_name?.ru
                || listing.category_slug || '—'
              }</b>
            </div>

            {/* Поиск по разделам. Их больше сотни в три уровня, и
                листать весь список ради «перчаток» — это минута
                прокрутки на каждое объявление. */}
            <input
              className="move-search"
              value={moveQuery}
              onChange={(e) => setMoveQuery(e.target.value)}
              placeholder={t('move.search')}
              autoComplete="off"
            />

            {moveQuery.trim() ? (
              <div className="move-list">
                {moveMatches.length === 0 && <p className="empty-hint">{t('move.nothing')}</p>}
                {moveMatches.map((m) => (
                  <button
                    key={m.id}
                    className="reasons-item move-found"
                    disabled={moving}
                    onClick={() => doMove(m.id)}
                  >
                    <b>{catName(m)}</b>
                    <span>{m.path}</span>
                  </button>
                ))}
              </div>
            ) : (
            <div className="move-list">
              {moveTree.map((root) => (
                <div key={root.id} className="move-group">
                  {/* Название приходит словарём с тремя языками, а не
                      строкой: рисовать его как есть нельзя, страница
                      падает. Берём язык интерфейса, запасной — русский. */}
                  <div className="move-group-title">{catName(root)}</div>
                  {/* Дерево трёхуровневое: раздел → подраздел →
                      вложенный. Показывали только два, и мультиварка
                      уезжала в «Бытовую технику» целиком, хотя внутри
                      есть свои разделы. Теперь видно всё, вложенные —
                      с отступом. */}
                  {(root.children || []).length > 0 ? (
                    (root.children || []).map((sub) => (
                      <div key={sub.id}>
                        <button
                          className="reasons-item"
                          disabled={moving}
                          onClick={() => doMove(sub.id)}
                        >
                          {catName(sub)}
                        </button>
                        {(sub.children || []).map((deep) => (
                          <button
                            key={deep.id}
                            className="reasons-item move-deep"
                            disabled={moving}
                            onClick={() => doMove(deep.id)}
                          >
                            {catName(deep)}
                          </button>
                        ))}
                      </div>
                    ))
                  ) : (
                    <button
                      className="reasons-item"
                      disabled={moving}
                      onClick={() => doMove(root.id)}
                    >
                      {catName(root)}
                    </button>
                  )}
                </div>
              ))}
            </div>
            )}

            <button className="reasons-cancel" onClick={() => setMovingOpen(false)}>
              {t('actions.cancel')}
            </button>
          </SheetCard>
        </div>
      )}</Presence>

      <Presence show={showReasons}>{(showReasons) && (
        <div className="reasons-sheet" onClick={() => { setShowReasons(false); setCustomReason(false); setReasonText('') }}>
          <SheetCard onClose={() => { setShowReasons(false); setCustomReason(false); setReasonText('') }}>
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
                {/* Прямое удаление — здесь же.
                    Кнопка называется «Удалить», а открывается окно
                    «Вернуть на доработку»: человек жмёт удаление и не
                    получает удаления. Это и была жалоба «иногда не
                    срабатывает» — на объявлениях, поданных на сайте,
                    вместо удаления предлагался возврат автору.
                    Возврат остаётся первым и главным: чужое объявление
                    честнее вернуть с причиной, чем стереть. Но если
                    решение — удалить, дорога для этого должна быть. */}
                <button
                  className="reasons-delete"
                  disabled={deleting}
                  onClick={() => { setShowReasons(false); setConfirmDelete(true) }}
                >
                  {t('my.delete')}
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
          </SheetCard>
        </div>
      )}</Presence>

      {/* Подтверждение удаления — своей панелью, а не окном браузера. */}
      <Presence show={confirmDelete}>{(confirmDelete) && (
        <div className="reasons-sheet" onClick={() => setConfirmDelete(false)}>
          <SheetCard onClose={() => setConfirmDelete(false)}>
            <div className="reasons-title">
              {confirmDelete === 'force' ? t('my.delete_has_history_force_confirm') : t('my.confirm_delete')}
            </div>
            <div className="reasons-actions-row">
              <button className="reasons-cancel" onClick={() => setConfirmDelete(false)}>
                {t('actions.cancel')}
              </button>
              <button
                className="reasons-item primary"
                disabled={deleting}
                onClick={() => doDelete(confirmDelete === 'force')}
              >
                {t('my.delete')}
              </button>
            </div>
          </SheetCard>
        </div>
      )}</Presence>

      <Presence show={Boolean(deleteError)}>{(Boolean(deleteError)) && (
        <div className="reasons-sheet" onClick={() => setDeleteError('')}>
          <SheetCard onClose={() => setDeleteError('')}>
            <div className="reasons-title">{deleteError}</div>
            <button className="reasons-cancel" onClick={() => setDeleteError('')}>
              {t('actions.close')}
            </button>
          </SheetCard>
        </div>
      )}</Presence>

      <Presence show={Boolean(priceOpen && priceCheck)}>{(Boolean(priceOpen && priceCheck)) && (
        <div className="reasons-sheet" onClick={() => setPriceOpen(false)}>
          <SheetCard onClose={() => setPriceOpen(false)}>
            <div className="reasons-title">{t(`price_check.${priceCheck.verdict}`)}</div>
            <PriceGauge mine={priceCheck.mine_eur} low={priceCheck.low_eur} high={priceCheck.high_eur} label={t(`price_check.${priceCheck.verdict}`)} />
            <p className="price-check-explain">
              {t(`price_check.explain_${priceCheck.verdict}`)}
            </p>
            <p className="price-check-explain">
              {t(priceCheck.scope === 'city' ? 'price_check.how_city' : 'price_check.how_country', {
                count: priceCheck.based_on,
                low: formatPrice(priceCheck.low_eur, 'EUR', lang),
                high: formatPrice(priceCheck.high_eur, 'EUR', lang),
              })}
            </p>
            <button className="reasons-cancel" onClick={() => setPriceOpen(false)}>
              {t('actions.close')}
            </button>
          </SheetCard>
        </div>
      )}</Presence>

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
              ph.is_video
                ? <video key={ph.url || i} src={ph.url} poster={ph.thumbnail_url} controls playsInline />
                : <img key={ph.url || i} src={ph.url} alt="" />
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
