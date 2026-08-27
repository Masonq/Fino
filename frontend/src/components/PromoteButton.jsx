import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

// Порядок показа — от самого дешёвого к самому дорогому, цены сами
// приходят с сервера (одно место правды, не дублируем тут).
const TYPES = ['bump', 'highlight', 'xl_card']

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
 */
export default function PromoteButton({ listingId, renderMode = 'full', open: openProp, onOpenChange }) {
  const { t } = useTranslation()

  const [openState, setOpenState] = useState(false)
  const controlled = openProp !== undefined
  const open = controlled ? openProp : openState
  const setOpen = controlled ? onOpenChange : setOpenState

  const [data, setData] = useState(null)
  const [busyType, setBusyType] = useState(null)
  const [error, setError] = useState('')

  const openSheet = () => {
    setOpen(true)
    if (!data) {
      api.listingPromotions(listingId).then(setData).catch(() => setData({ prices: {}, items: [] }))
    }
  }

  // Управляемый режим (панель открывается внешним состоянием, не
  // своим openSheet) — данные подгружаем сами при первом появлении.
  useEffect(() => {
    if (controlled && open && !data) {
      api.listingPromotions(listingId).then(setData).catch(() => setData({ prices: {}, items: [] }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controlled, open])

  const buy = async (type) => {
    setBusyType(type); setError('')
    try {
      const { confirmation_url } = await api.startPromotion(listingId, type)
      // Уводим на оплату целиком, как и с проверкой документа — сама
      // оплата происходит на стороне ЮKassa, не на нашей странице.
      window.location.href = confirmation_url
    } catch (e) {
      setError(e.code === 'promotion_not_configured'
        ? t('promo.err_unavailable') : t('promo.err_generic'))
      setBusyType(null)
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

        {!data ? (
          <p className="verify-hint">{t('actions.loading')}</p>
        ) : (
          TYPES.map((type) => {
            const activePromo = (data.items || []).find((p) => p.type === type)
            return (
              <div key={type} className="promo-option">
                <div className="promo-option-text">
                  <div className="promo-option-name">{t(`promo.type_${type}`)}</div>
                  <div className="promo-option-desc">{t(`promo.desc_${type}`)}</div>
                </div>
                {activeTypes.has(type) ? (
                  <span className="promo-option-active">
                    {activePromo?.expires_at
                      ? t('promo.active_until', { date: new Date(activePromo.expires_at).toLocaleDateString() })
                      : t('promo.active_now')}
                  </span>
                ) : (
                  <button
                    className="promo-buy"
                    disabled={busyType !== null}
                    onClick={() => buy(type)}
                  >
                    {busyType === type ? '…' : t('promo.price', { price: data.prices?.[type] })}
                  </button>
                )}
              </div>
            )
          })
        )}

        {error && <p className="auth-error">{error}</p>}
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
