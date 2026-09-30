import { intlLocale } from '../utils/time'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

// Порядок показа — от самого дешёвого к самому дорогому, цены сами
// приходят с сервера (одно место правды, не дублируем тут).
const TYPES = ['bump', 'highlight', 'xl_card']

// Картинка-иллюстрация каждого типа — если файла нет (ещё не
// загружен), просто остаётся крупная иконка на цветной подложке,
// ничего не ломается.
const IMAGES = {
  bump: '/promo/bump.jpg',
  highlight: '/promo/highlight.jpg',
  xl_card: '/promo/xl.jpg',
}

const ICONS = {
  bump: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19V5M6 11l6-6 6 6" />
    </svg>
  ),
  highlight: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m12 2 2.4 6.5L21 11l-6.6 2.5L12 20l-2.4-6.5L3 11l6.6-2.5z" />
    </svg>
  ),
  xl_card: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3m11-5v3a2 2 0 0 1-2 2h-3" />
    </svg>
  ),
}

/**
 * Кнопка «Поднять просмотры» — только для владельца активного объявления.
 *
 * Тот же управляемый режим, что и у ReportButton: renderMode='trigger'
 * рисует только кнопку (пригодится внутри тесного ряда других кнопок,
 * как в MyListings.jsx — панель туда не влезла бы), renderMode='sheet'
 * рисует только панель, когда open истинно. Обе половины — один
 * открытый диалог, просто в разных местах DOM, управляются снаружи
 * одним и тем же состоянием. Без controlled-пропов (open/onOpenChange)
 * компонент как раньше — сам себе хозяин, для мест, где панели есть
 * куда развернуться без конфликта (страница объявления).
 *
 * Выбор — радио, не чекбоксы: один платёж несёт одну сумму за один
 * тип, купить несколько разом одной кнопкой нельзя технически.
 * Совмещать можно — просто не в один заход: купил один, вернулся,
 * выбрал другой.
 *
 * Оплата — с баланса мгновенно (если хватает), либо картой через
 * ЮKassa с редиректом. Баланс приходит тем же запросом, что и цены —
 * не нужен отдельный поход за ним только чтобы решить, какую кнопку
 * показать.
 */
export default function PromoteButton({ listingId, renderMode = 'full', open: openProp, onOpenChange }) {
  const { t, i18n } = useTranslation()

  const [openState, setOpenState] = useState(false)
  const controlled = openProp !== undefined
  const open = controlled ? openProp : openState
  const setOpen = controlled ? onOpenChange : setOpenState

  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const carouselRef = useRef(null)

  // Одна карточка на весь экран, листается свайпом — по прокрутке
  // определяем, какая сейчас видна, и делаем её выбранной сама собой:
  // раз видно только одну, «выбор» и «пролистал до неё» — одно и то же.
  const onScroll = () => {
    const el = carouselRef.current
    if (!el) return
    const index = Math.round(el.scrollLeft / el.clientWidth)
    const type = TYPES[Math.max(0, Math.min(TYPES.length - 1, index))]
    if (type) setSelected((prev) => (prev === type ? prev : type))
  }

  const goTo = (index) => {
    const el = carouselRef.current
    if (!el) return
    el.scrollTo({ left: el.clientWidth * index, behavior: 'smooth' })
  }

  const load = () => {
    api.listingPromotions(listingId).then((res) => {
      setData(res)
      // Выбираем по умолчанию первый ещё не купленный тип — чтобы
      // кнопка внизу сразу была готова к нажатию, не заставляя сначала
      // тыкать в строку. Прокрутку карусели ставим туда же без
      // анимации — иначе первый показ дёргался бы к нужной карточке.
      const active = new Set((res.items || []).map((p) => p.type))
      const firstFree = TYPES.find((tp) => !active.has(tp))
      setSelected(firstFree || null)
      const index = firstFree ? TYPES.indexOf(firstFree) : 0
      requestAnimationFrame(() => {
        const el = carouselRef.current
        if (el) el.scrollLeft = el.clientWidth * index
      })
    }).catch(() => setData({ prices: {}, items: [], balance: 0 }))
  }

  const openSheet = () => {
    setOpen(true)
    if (!data) load()
  }

  // Управляемый режим (панель открывается внешним состоянием, не
  // своим openSheet) — данные подгружаем сами при первом появлении.
  useEffect(() => {
    if (controlled && open && !data) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controlled, open])

  const buy = async (payMethod) => {
    if (!selected) return
    setBusy(true); setError('')
    try {
      const res = await api.startPromotion(listingId, selected, payMethod)
      if (res.paid_from_balance) {
        // Списалось мгновенно — обновляем список активных и баланс,
        // никуда уходить не нужно.
        setDone(true)
        load()
        setTimeout(() => setDone(false), 1800)
      } else {
        // Уводим на оплату целиком, как и с проверкой документа —
        // сама оплата происходит на стороне ЮKassa, не у нас.
        window.location.href = res.confirmation_url
      }
    } catch (e) {
      setError(e.code === 'promotion_not_configured'
        ? t('promo.err_unavailable') : t('promo.err_generic'))
    } finally {
      setBusy(false)
    }
  }

  const trigger = () => (
    <button className="promo-trigger" onClick={openSheet}>
      {t('promo.button')}
    </button>
  )

  const sheet = () => {
    const activeTypes = new Set((data?.items || []).map((p) => p.type))
    const price = selected ? data?.prices?.[selected] : null
    const balance = data?.balance || 0
    const canUseBalance = price != null && balance >= price

    return (
      <div className="promo-sheet">
        <div className="promo-sheet-head">
          <div>
            <div className="promo-title">{t('promo.title')}</div>
            <div className="promo-sub">{t('promo.subtitle')}</div>
          </div>
          {data && (
            <div className="promo-balance">
              {t('promo.balance', { amount: balance })}
              {data.bonus > 0 && <div className="promo-balance-bonus">{t('balance.of_which_bonus', { amount: data.bonus })}</div>}
            </div>
          )}
        </div>

        {!data ? (
          <p className="verify-hint">{t('actions.loading')}</p>
        ) : (
          <>
            <div className="promo-carousel-wrap">
              {/* Стрелки — только на широком экране (см. CSS), где
                  нет тачскрина и пролистать свайпом нечем. На телефоне
                  скрыты, там и так работает жест. */}
              <button
                className="promo-arrow prev"
                aria-label={t('actions.back')}
                disabled={TYPES.indexOf(selected) <= 0}
                onClick={() => goTo(Math.max(0, TYPES.indexOf(selected) - 1))}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
              </button>
              <div className="promo-carousel" ref={carouselRef} onScroll={onScroll}>
                {TYPES.map((type) => {
                const activePromo = (data.items || []).find((p) => p.type === type)
                const isActive = activeTypes.has(type)
                return (
                  <div key={type} className="promo-card-full">
                    <div className={`promo-card-image ${type === 'xl_card' ? 'xl' : type}`}>
                      <img
                        src={IMAGES[type]} alt=""
                        onError={(e) => { e.currentTarget.style.display = 'none' }}
                      />
                      <div className="promo-card-icon">{ICONS[type]}</div>
                    </div>
                    <div className="promo-card-name">{t(`promo.type_${type}`)}</div>
                    <div className="promo-card-desc">{t(`promo.desc_${type}`)}</div>
                    <div className="promo-card-bottom">
                      {isActive ? (
                        <span className="promo-active-tag">
                          {activePromo?.expires_at
                            ? t('promo.active_until', { date: new Date(activePromo.expires_at).toLocaleDateString(intlLocale(i18n.language), { day: "numeric", month: "long", year: "numeric" }) })
                            : t('promo.active_now')}
                        </span>
                      ) : (
                        <span className="promo-price">{t('promo.price', { price: data.prices?.[type] })}</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
              <button
                className="promo-arrow next"
                aria-label={t('promo.next')}
                disabled={TYPES.indexOf(selected) >= TYPES.length - 1}
                onClick={() => goTo(Math.min(TYPES.length - 1, TYPES.indexOf(selected) + 1))}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m9 6 6 6-6 6" /></svg>
              </button>
            </div>

            <div className="promo-dots">
              {TYPES.map((type, i) => (
                <button
                  key={type}
                  className={selected === type ? 'promo-dot active' : 'promo-dot'}
                  aria-label={t(`promo.type_${type}`)}
                  onClick={() => goTo(i)}
                />
              ))}
            </div>
            {error && <p className="auth-error">{error}</p>}
            {done && <p className="promo-done">{t('promo.paid_ok')}</p>}

            {selected && (
              canUseBalance ? (
                <>
                  <button className="promo-cta" disabled={busy} onClick={() => buy('balance')}>
                    {busy ? '…' : t('promo.pay_balance', { price })}
                  </button>
                  <button className="promo-alt-pay" disabled={busy} onClick={() => buy('yookassa')}>
                    {t('promo.pay_card')}
                  </button>
                </>
              ) : (
                <>
                  <button className="promo-cta" disabled={busy} onClick={() => buy('yookassa')}>
                    {busy ? '…' : t('promo.cta', { price })}
                  </button>
                  {price != null && (
                    <p className="promo-balance-hint">
                      {t('promo.not_enough_balance', { amount: balance })}
                    </p>
                  )}
                </>
              )
            )}
            {!selected && (
              <button className="promo-cta" disabled>{t('promo.all_active')}</button>
            )}
          </>
        )}

        <button className="review-cancel" onClick={() => { setOpen(false); setError('') }}>
          {t('rev.cancel')}
        </button>
      </div>
    )
  }

  if (renderMode === 'trigger') return trigger()
  if (renderMode === 'sheet') return open ? sheet() : null
  return open ? sheet() : trigger()
}
