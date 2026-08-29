import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import CategoryArt from '../components/CategoryArt'
import ListingCard from '../components/ListingCard'
import { CardSkeletons } from '../components/Skeletons'
import { LANDINGS } from '../data/landings'
import { MODE_WORDS } from '../data/modeWords'
import { CAR_MODELS, CAR_MODEL_OTHER } from '../data/carBrands'

/**
 * Вход в раздел.
 *
 * Человек, зашедший в «Недвижимость», ищет не «что-нибудь» — он хочет
 * снять двушку до тысячи евро. Спрашиваем это сразу, а не заставляем
 * листать всё подряд.
 *
 * Ниже — подразделы плитками и свежие объявления: если ответить на
 * вопросы нечем, человек всё равно видит, что тут есть.
 */

// Цветная шапка раздела — тот же приём, что у промо-баннера на главной
// (свой градиент на категорию), а не голая белая полоса. Своей
// фотокомпозиции под каждый раздел ещё нет, поэтому вместо неё —
// крупный контурный значок раздела поверх градиента.
const BANNER_GRADIENTS = {
  'real-estate': 'linear-gradient(135deg, #0E9F6E 0%, #1DB388 55%, #5CE8CC 100%)',
  auto: 'linear-gradient(135deg, #3B5BF6 0%, #4F7BF7 55%, #93BAFF 100%)',
  electronics: 'linear-gradient(135deg, #2B6CE0 0%, #4A8AF0 55%, #8FC1FF 100%)',
  'home-garden': 'linear-gradient(135deg, #0E9F6E 0%, #34D8A8 55%, #B7F5E1 100%)',
  fashion: 'linear-gradient(135deg, #E0326B 0%, #F0507F 55%, #FFA8BF 100%)',
  kids: 'linear-gradient(135deg, #F2860C 0%, #F5A524 55%, #FFD98A 100%)',
  'hobby-sport': 'linear-gradient(135deg, #6D3DFC 0%, #8156FD 55%, #BEA4FF 100%)',
  pets: 'linear-gradient(135deg, #E0326B 0%, #F0507F 55%, #FFC2D3 100%)',
  beauty: 'linear-gradient(135deg, #C0399B 0%, #DD5DBB 55%, #FBC6EE 100%)',
  services: 'linear-gradient(135deg, #0A7A54 0%, #0E9F6E 55%, #7EE4C1 100%)',
  jobs: 'linear-gradient(135deg, #3B5BF6 0%, #6D9BFB 55%, #C6DBFF 100%)',
  business: 'linear-gradient(135deg, #1B2A4A 0%, #3B5BF6 55%, #93BAFF 100%)',
}

export default function CategoryLanding() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

  // Ручная липкость сайдбара — в дополнение к CSS position:sticky, не
  // вместо него: несколько попыток одним только CSS не помогли на
  // Safari у пользователя, при том что тот же самый приём работает
  // верно и в Chromium, и на соседней странице поиска — не нашли ни
  // одного оставшегося структурного отличия между двумя сайдбарами,
  // при этом один липнет, другой нет. Раз чистый CSS не поддаётся
  // диагностике без доступа к самому Safari, этот способ гарантированно
  // работает в любом браузере одинаково, не полагаясь на то, как
  // именно движок трактует sticky. Обычный обработчик scroll и прямое
  // сравнение координат — проще и предсказуемее, чем IntersectionObserver
  // с margin-математикой (первая версия так и не откалибровалась верно:
  // естественное положение сайдбара оказалось уже около 68px, ниже
  // порога в 82px, и срабатывало сразу, а не после настоящей прокрутки).
  const sidebarRef = useRef(null)
  const [sidebarStuck, setSidebarStuck] = useState(false)
  const [sidebarLeft, setSidebarLeft] = useState(0)
  const STICK_AT = 82

  const [category, setCategory] = useState(null)
  const [fresh, setFresh] = useState([])
  const [deal, setDeal] = useState('')
  const [values, setValues] = useState({})
  const [text, setText] = useState('')
  const [showAllSubs, setShowAllSubs] = useState(false)

  // category в зависимостях — сайдбар не существует в DOM, пока
  // категория не загрузилась; без этого обработчик мог бы читать
  // getBoundingClientRect() у ещё не отрисованного элемента.
  useEffect(() => {
    const handleScroll = () => {
      const el = sidebarRef.current
      if (!el) return
      // .parentElement — сам .landing-body, тот же ориентир, что и
      // раньше: не зависит от того, закреплён ли сейчас сам сайдбар
      // (position:fixed вынимает его из потока, но не родителя).
      const parentTop = el.parentElement.getBoundingClientRect().top
      setSidebarStuck((prevStuck) => {
        if (parentTop < STICK_AT && !prevStuck) {
          setSidebarLeft(el.getBoundingClientRect().left)
          return true
        }
        if (parentTop >= STICK_AT && prevStuck) return false
        return prevStuck
      })
    }
    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [category])

  // Результаты показываются прямо тут, под фильтрами, вместо перехода
  // на отдельную страницу поиска — раньше «Показать объявления» уводил
  // на /search с почти той же вёрсткой, и это читалось как две разные,
  // плохо связанные страницы.
  const [results, setResults] = useState([])
  const [resultsTotal, setResultsTotal] = useState(0)
  const [searched, setSearched] = useState(false)
  const [searching, setSearching] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const PAGE = 20
  const resultsRef = useRef(null)

  const landing = LANDINGS[slug]

  useEffect(() => {
    api.getCategories()
      .then((all) => setCategory(all.find((c) => c.slug === slug) || null))
      .catch(() => setCategory(null))

    api.searchListings({ category_slug: slug, limit: 8, lang: i18n.language })
      .then((res) => setFresh(res.items || []))
      .catch(() => setFresh([]))

    // Переход на другой раздел (напр. по «Все категории») не должен
    // оставлять открытым режим результатов прошлого раздела.
    setSearched(false)
  }, [slug, i18n.language])

  // Плитка подраздела задаёт свой слаг категории вместо родительского —
  // нужен и на первом запуске поиска (buildQuery), и на догрузке
  // (loadMore), поэтому держим его в состоянии, а не только в замыкании
  // клика.
  const [activeCategorySlug, setActiveCategorySlug] = useState(slug)

  const buildQuery = (categorySlug = activeCategorySlug) => {
    const params = { category_slug: categorySlug, lang: i18n.language, limit: PAGE, offset: 0 }
    if (text.trim()) params.q = text.trim()

    // «Купить/Снять/Посуточно» — структурный атрибут (attributes.deal_type),
    // отбирает по полю, а не по словам в тексте: раньше «Снять» словом
    // «аренда» находило и «ищу квартиру в аренду» — чужую заявку, а не
    // те, что реально сдают.
    if (deal) params.deal_type = deal

    // «2 комнаты» и т.п. структурного поля пока не имеют — уходит как
    // extra_terms с синонимами, так же, как на обычном /search.
    const ROOMS_TO_CHIP = { '1': 'rooms1', '2': 'rooms2', '3': 'rooms3', '4+': 'rooms3' }
    const groups = []
    // Остальные поля раздела (год, пробег, коробка передач и т.п.) —
    // общий механизм attr_eq/attr_range (см. listings.py): раньше
    // такое поле либо не фильтровало вовсе (было в интерфейсе, но
    // бэкенд его не принимал — так нашёлся нерабочий «Год выпуска» у
    // авто), либо под каждое заводили свой именованный параметр.
    const attrEq = {}
    const attrRange = {}
    Object.entries(values).forEach(([key, value]) => {
      if (!value) return
      if (key === 'rooms') {
        const chip = ROOMS_TO_CHIP[value]
        if (chip && MODE_WORDS[chip]) groups.push(MODE_WORDS[chip].join('|'))
        return
      }
      // «Другая» — это «не нашлось в списке», не реальное значение
      // фильтра; отправлять его как есть значило бы искать буквальную
      // марку «Другая» и получать пустую выдачу.
      if ((key === 'brand' || key === 'model') && value === CAR_MODEL_OTHER) return
      if (key === 'brand' || key === 'model') { params[key] = value; return }

      // *_min/*_max — поле типа range. price — уже готовая пара
      // параметров на самой колонке цены (работает и без этого
      // механизма), остальные — в общий числовой диапазон.
      const rangeMatch = key.match(/^(.+)_(min|max)$/)
      if (rangeMatch) {
        const [, baseKey, bound] = rangeMatch
        if (baseKey === 'price') { params[key] = value; return }
        attrRange[baseKey] = attrRange[baseKey] || [null, null]
        attrRange[baseKey][bound === 'min' ? 0 : 1] = value
        return
      }

      attrEq[key] = value
    })
    if (groups.length) params.extra_terms = groups.join(';;')
    if (Object.keys(attrEq).length) params.attr_eq = JSON.stringify(attrEq)
    if (Object.keys(attrRange).length) params.attr_range = JSON.stringify(attrRange)
    return params
  }

  // Принимает необязательный слаг подраздела: плитка подраздела кликает
  // сюда напрямую с sub.slug, а не сначала кладёт его в state — иначе
  // из-за асинхронности setState поиск на этом же клике ушёл бы со
  // старым слагом.
  const search = (categorySlug = slug) => {
    setActiveCategorySlug(categorySlug)
    setSearching(true)
    setSearched(true)
    setShowAllSubs(false)
    requestAnimationFrame(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    api.searchListings(buildQuery(categorySlug))
      .then((res) => { setResults(res.items || []); setResultsTotal(res.total || 0) })
      .catch(() => { setResults([]); setResultsTotal(0) })
      .finally(() => setSearching(false))
  }

  // Прокрутка к результатам при самом первом переходе в режим поиска —
  // requestAnimationFrame в search() этот случай не ловит, потому что
  // блок результатов ещё не существовал в DOM в момент вызова.
  useEffect(() => {
    if (searched && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [searched])

  const loadMore = () => {
    if (loadingMore || results.length >= resultsTotal) return
    setLoadingMore(true)
    api.searchListings({ ...buildQuery(activeCategorySlug), offset: results.length })
      .then((res) => setResults((prev) => [...prev, ...(res.items || [])]))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }

  const name = category?.name?.[i18n.language] || category?.name?.ru || ''

  // Раньше кнопка «назад» в шапке жёстко вела на /categories — если
  // человек пришёл сюда с главной (по плитке раздела), «назад» уводил
  // не туда, откуда он пришёл, а на «Все категории»: история браузера
  // росла (Главная → Раздел → Все категории → Раздел → Все категории…),
  // и «назад» с «Все категории» возвращал обратно в этот же раздел —
  // получался замкнутый круг. Тот же приём, что и в ListingDetail.jsx:
  // если есть настоящая история — идём по ней, а не мимо. «Все
  // категории» остаётся запасным для прямых ссылок, где истории нет.
  const goBack = () => {
    if (window.history.state?.idx > 0) {
      navigate(-1)
      return
    }
    navigate('/categories', { replace: true })
  }

  return (
    <div className="landing">
      {searched && (
        <div className="landing-head plain-head">
          <button className="landing-back" onClick={() => setSearched(false)}
                  aria-label={t('actions.back')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3"
                 strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <h1 className="landing-title">{name}</h1>
        </div>
      )}

      {!searched && (
      <>
      <div className="landing-body">
      {/* Распорка того же размера, что и сайдбар — появляется, только
          когда сайдбар переключён на position:fixed (см. sidebarStuck
          выше), чтобы освободившееся место не схлопывалось и соседняя
          колонка не «прыгала» вбок в момент переключения. */}
      {sidebarStuck && <div className="landing-sidebar-spacer" aria-hidden="true" />}
      <div
        ref={sidebarRef}
        className={sidebarStuck ? 'landing-sidebar is-stuck' : 'landing-sidebar'}
        style={sidebarStuck ? { left: sidebarLeft } : undefined}
      >
      <div className="landing-hero" style={{ background: BANNER_GRADIENTS[slug] || BANNER_GRADIENTS['real-estate'] }}>
        <div className="landing-head">
          <button className="landing-back on-hero" onClick={goBack}
                  aria-label={t('actions.back')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3"
                 strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <h1 className="landing-title on-hero">{name}</h1>
          {/* Число объявлений приходит отдельным запросом (getCategories),
              чуть позже самой страницы — раньше блок целиком рендерился
              только после этого, резко появляясь и сдвигая всё, что
              ниже (саму страницу «дёргало» при каждом заходе). Теперь
              блок стоит на месте с первого кадра — просто пустой, пока
              число не пришло, высота у него уже есть за счёт line-height
              в CSS, появление текста ничего не сдвигает. */}
          <div className="landing-count on-hero">
            {category?.count > 0 ? t('landing.offers', { count: category.count }) : '\u00A0'}
          </div>
        </div>

        {/* Раньше здесь были только фильтры (комнаты, цена) — можно было
            сузить раздел, но не поискать конкретную вещь словом. Теперь
            можно и то, и другое: слово уходит в q вместе с остальными
            отборами. */}
        <div className="landing-search">
          <div className="search-field">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
            <input
              type="search"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') search() }}
              placeholder={t('search.placeholder_full')}
              autoComplete="off"
            />
            {text && (
            <button className="search-clear" onClick={() => setText('')} aria-label={t('actions.clear')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
        </div>
      </div>

      {/* Первый вопрос делит раздел надвое: без ответа на него
          остальное бессмысленно. */}
      {landing?.deal && (
        <div className="cat-modes landing-deal">
          {landing.deal.options.map((opt) => (
            <button
              key={opt.value}
              className={`cat-mode${deal === opt.value ? ' on' : ''}`}
              onClick={() => setDeal(deal === opt.value ? '' : opt.value)}
            >
              {t(opt.label)}
            </button>
          ))}
        </div>
      )}

      {landing?.fields?.map((field) => {
        // Модель без выбранной марки бессмысленна — список моделей
        // зависит от того, что выбрано выше, а «Другая» модели не
        // предполагает вовсе.
        if (field.type === 'car-model' && (!values.brand || values.brand === CAR_MODEL_OTHER)) {
          return null
        }
        return (
        <div key={field.key} className="landing-field">
          <div className="landing-label">{t(field.label)}</div>

          {field.type === 'chips' && (
            <div className="cat-chips landing-chips">
              {field.options.map((opt) => {
                // Старые поля (комнаты, размер) — плоский массив строк,
                // значение и подпись совпадают. Новые (коробка передач
                // и подобное) — {value, label}: хранится по-английски
                // («automatic»), показывается переводом. Оба формата
                // рядом, чтобы не переписывать уже работающие поля.
                const value = typeof opt === 'object' ? opt.value : opt
                const label = typeof opt === 'object' ? t(opt.label) : opt
                return (
                  <button
                    key={value}
                    className={`cat-chip${values[field.key] === value ? ' on' : ''}`}
                    onClick={() => setValues({
                      ...values,
                      [field.key]: values[field.key] === value ? '' : value,
                    })}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          )}

          {field.type === 'select' && (
            <select
              className="landing-input landing-select"
              value={values[field.key] || ''}
              onChange={(e) => setValues({
                ...values,
                [field.key]: e.target.value,
                ...(field.key === 'brand' ? { model: '' } : {}),
              })}
            >
              <option value="">{field.placeholder ? t(field.placeholder) : ''}</option>
              {field.options.map((opt) => {
                const value = typeof opt === 'object' ? opt.value : opt
                const label = typeof opt === 'object' ? t(opt.label) : opt
                return <option key={value} value={value}>{label}</option>
              })}
            </select>
          )}

          {field.type === 'car-model' && (
            CAR_MODELS[values.brand] ? (
              <select
                className="landing-input landing-select"
                value={values.model || ''}
                onChange={(e) => setValues({ ...values, model: e.target.value })}
              >
                <option value="">{t('landing.model_placeholder')}</option>
                {CAR_MODELS[values.brand].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
                <option value={CAR_MODEL_OTHER}>{t('landing.model_other')}</option>
              </select>
            ) : (
              <input
                className="landing-input"
                placeholder={t('landing.model_placeholder')}
                value={values.model || ''}
                onChange={(e) => setValues({ ...values, model: e.target.value })}
              />
            )
          )}

          {field.type === 'text' && (
            <input
              className="landing-input"
              placeholder={field.hint ? t(field.hint) : ''}
              value={values[field.key] || ''}
              onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
            />
          )}

          {field.type === 'range' && (
            <div className="landing-range">
              <input
                className="landing-input"
                inputMode="numeric"
                placeholder={t('landing.from')}
                value={values[`${field.key}_min`] || ''}
                onChange={(e) => setValues({
                  ...values, [`${field.key}_min`]: e.target.value,
                })}
              />
              <input
                className="landing-input"
                inputMode="numeric"
                placeholder={t('landing.to')}
                value={values[`${field.key}_max`] || ''}
                onChange={(e) => setValues({
                  ...values, [`${field.key}_max`]: e.target.value,
                })}
              />
            </div>
          )}
        </div>
        )
      })}

      <button className="landing-go" onClick={() => search()}>
        {t('landing.show')}
      </button>
      </div>

      <div className="landing-main">
      {/* Пока категория (а вместе с ней — список подразделов) ещё не
          пришла, на её месте ничего не было вовсе — блок появлялся
          целиком одним скачком, стоило данным дойти, и «Свежие
          объявления» ниже резко уезжали вниз (замерил — 354px за
          один кадр). Скелетон той же сетки (2 колонки, те же 104px на
          плитку) держит место заранее — придут данные раньше или
          позже, соседние блоки не двигаются. Шесть плиток — самое
          частое число подразделов; у категорий с меньшим числом
          настоящих плиток скелетон будет чуть выше финального блока,
          это меньшее зло по сравнению с прежним скачком со всей
          высоты разом. */}
      {!category && (
        <div className="landing-subs">
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="landing-sub skeleton" key={i} />
          ))}
        </div>
      )}
      {/* Подразделы: если отвечать на вопросы нечем, человек всё равно
          видит, что тут есть. Как у Авито — несколько плиток с картинкой
          и «Все категории» последней, а не весь список сразу: длинный
          список подряд читается хуже, чем несколько картинок и явный
          переход дальше. */}
      {category?.children?.length > 0 && (() => {
        const subs = category.children
        const showLimit = subs.length > 6
        const visible = showLimit ? subs.slice(0, 5) : subs
        return (
          <div className="landing-subs">
            {visible.map((sub) => (
              <button
                key={sub.id}
                className="landing-sub"
                onClick={() => navigate(`/search?category=${sub.slug}`)}
              >
                <span className="landing-sub-name">
                  {sub.name?.[i18n.language] || sub.name?.ru}
                </span>
                <span className="landing-sub-art"><CategoryArt slug={sub.slug} /></span>
              </button>
            ))}
            {showLimit && (
              <button
                className="landing-sub landing-sub-all"
                onClick={() => setShowAllSubs(true)}
              >
                <span className="landing-sub-name">{t('common.all_categories')}</span>
                <svg className="landing-sub-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m9 6 6 6-6 6" /></svg>
              </button>
            )}
          </div>
        )
      })()}

      {showAllSubs && (
        <div className="subs-modal">
          <div className="subs-modal-head">
            <button className="subs-modal-close" onClick={() => setShowAllSubs(false)} aria-label={t('actions.close')}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
            <div className="subs-modal-title">{t('common.all_categories')}</div>
          </div>
          <div className="subs-modal-list">
            {category.children.map((sub) => (
              <button
                key={sub.id}
                className="subs-modal-row"
                onClick={() => navigate(`/search?category=${sub.slug}`)}
              >
                {sub.name?.[i18n.language] || sub.name?.ru}
              </button>
            ))}
          </div>
        </div>
      )}

      {fresh.length > 0 && (
        <div className="landing-fresh">
          <h2>{t('landing.fresh')}</h2>
          <div className="feed-grid">
            {fresh.map((l) => <ListingCard key={l.id} listing={l} />)}
          </div>
        </div>
      )}
      </div>
      </div>
      </>
      )}

      {searched && (
        <div className="landing-results" ref={resultsRef}>
          <div className="landing-results-head">
            <span className="results-count">
              {searching && !results.length ? t('search.searching') : `${t('search.found')}: ${resultsTotal}`}
            </span>
          </div>
          {searching && !results.length ? (
            <div className="feed-grid"><CardSkeletons count={4} /></div>
          ) : results.length === 0 ? (
            <div className="empty-state">
              <p className="empty-hint">{t('search.nothing')}</p>
              <button className="empty-reset" onClick={() => setSearched(false)}>
                {t('actions.edit_filters')}
              </button>
            </div>
          ) : (
            <>
              <div className="feed-grid">
                {results.map((l) => <ListingCard key={l.id} listing={l} />)}
              </div>
              {results.length < resultsTotal && (
                <button className="load-more" disabled={loadingMore} onClick={loadMore}>
                  {loadingMore ? t('actions.loading') : t('actions.show_more')}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
