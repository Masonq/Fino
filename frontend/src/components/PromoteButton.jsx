import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

// Порядок показа — от самого дешёвого к самому дорогому, цены сами
// приходят с сервера (одно место правды, не дублируем тут).
const TYPES = ['bump', 'highlight', 'xl_card']

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
 * Кнопка «Продвинуть» — только для владельца активного объявления.
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
 * Выбор — радио, не чекбоксы: один платёж ЮKassa несёт одну сумму за
 * один тип, купить несколько разом одной кнопкой нельзя технически.
 * Совмещать можно — просто не в один заход: купил один, вернулся,
 * выбрал другой.
 */
export default function PromoteButton({ listingId, renderMode = 'full', open: openProp, onOpenChange }) {
  const { t } = useTranslation()

  const [openState, setOpenState] = useState(false)
  const controlled = openProp !== undefined
  const open = controlled ? openProp : openState
  const setOpen = controlled ? onOpenChange : setOpenState

  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    api.listingPromotions(listingId).then((res) => {
      setData(res)
      // Выбираем по умолчанию первый ещё не купленный тип — чтобы
      // кнопка внизу сразу была готова к нажатию, не заставляя сначала
      // тыкать в строку.
      const active = new Set((res.items || []).map((p) => p.type))
      const firstFree = TYPES.find((tp) => !active.has(tp))
      setSelected(firstFree || null)
    }).catch(() => setData({ prices: {}, items: [] }))
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

  const buy = async () => {
    if (!selected) return
    setBusy(true); setError('')
    try {
      const { confirmation_url } = await api.startPromotion(listingId, selected)
      // Уводим на оплату целиком, как и с проверкой документа — сама
      // оплата происходит на стороне ЮKassa, не на нашей странице.
      window.location.href = confirmation_url
    } catch (e) {
      setError(e.code === 'promotion_not_configured'
        ? t('promo.err_unavailable') : t('promo.err_generic'))
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
    return (
      <div className="promo-sheet">
        <div className="promo-title">{t('promo.title')}</div>
        <div className="promo-sub">{t('promo.subtitle')}</div>

        {!data ? (
          <p className="verify-hint">{t('actions.loading')}</p>
        ) : (
          <>
            <div className="promo-row-list">
              {TYPES.map((type) => {
                const activePromo = (data.items || []).find((p) => p.type === type)
                const isActive = activeTypes.has(type)
                const isSelected = !isActive && selected === type
                return (
                  <div
                    key={type}
                    className={isSelected ? 'promo-row selected' : 'promo-row'}
                    onClick={isActive ? undefined : () => setSelected(type)}
                    role={isActive ? undefined : 'button'}
                  >
                    <div className={`promo-icon ${type === 'xl_card' ? 'xl' : type}`}>
                      {ICONS[type]}
                    </div>
                    <div className="promo-body">
                      <div className="promo-name">{t(`promo.type_${type}`)}</div>
                      <div className="promo-desc">{t(`promo.desc_${type}`)}</div>
                    </div>
                    <div className="promo-row-bottom">
                      {isActive ? (
                        <span className="promo-active-tag">
                          {activePromo?.expires_at
                            ? t('promo.active_until', { date: new Date(activePromo.expires_at).toLocaleDateString() })
                            : t('promo.active_now')}
                        </span>
                      ) : (
                        <>
                          <span className="promo-price">{t('promo.price', { price: data.prices?.[type] })}</span>
                          <span className={isSelected ? 'promo-radio on' : 'promo-radio'} />
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {error && <p className="auth-error">{error}</p>}

            <button className="promo-cta" disabled={!selected || busy} onClick={buy}>
              {busy ? '…' : selected
                ? t('promo.cta', { price: data.prices?.[selected] })
                : t('promo.all_active')}
            </button>
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
