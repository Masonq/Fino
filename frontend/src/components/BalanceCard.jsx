import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

// Готовые суммы — быстрее тыкнуть, чем каждый раз набирать вручную.
// Суммы в динарах: поднятие стоит 150, выделение 300, крупная
// карточка 450 — набор подобран так, чтобы каждой кнопки хватало на
// что-то целое, а не «почти хватило».
const PRESETS = [500, 1000, 2000, 5000]

export default function BalanceCard() {
  const { t } = useTranslation()
  const [wallet, setWallet] = useState(null)      // { balance, money, bonus } или null, пока грузится
  const [open, setOpen] = useState(false)
  const [amount, setAmount] = useState(PRESETS[1])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getBalance().then(setWallet).catch(() => setWallet({ balance: 0, money: 0, bonus: 0 }))
  }, [])

  const topup = async () => {
    setBusy(true); setError('')
    try {
      const { confirmation_url } = await api.startTopup(amount)
      // Уводим на оплату целиком — сама оплата на стороне ЮKassa.
      window.location.href = confirmation_url
    } catch (e) {
      setError(e.code === 'promotion_not_configured'
        ? t('promo.err_unavailable') : t('promo.err_generic'))
      setBusy(false)
    }
  }

  return (
    <div className="balance-card">
      <div className="balance-row">
        <div>
          <div className="balance-label">{t('balance.title')}</div>
          <div className="balance-amount">
            {wallet === null ? '…' : t('promo.price', { price: wallet.balance })}
          </div>
          {/* Подарочная часть — отдельной строкой: её нельзя вывести и вернуть,
              только потратить на продвижение. Видеть это надо до траты, а не после. */}
          {wallet?.bonus > 0 && (
            <div className="balance-bonus">{t('balance.of_which_bonus', { amount: wallet.bonus })}</div>
          )}
        </div>
        <button className="balance-topup-btn" onClick={() => setOpen((v) => !v)}>
          {t('balance.topup')}
        </button>
      </div>

      {open && (
        <div className="balance-topup-form">
          <div className="balance-presets">
            {PRESETS.map((p) => (
              <button
                key={p}
                className={amount === p ? 'balance-preset active' : 'balance-preset'}
                onClick={() => setAmount(p)}
              >
                {t('promo.price', { price: p })}
              </button>
            ))}
          </div>
          {error && <p className="auth-error">{error}</p>}
          <button className="promo-cta" disabled={busy} onClick={topup}>
            {busy ? '…' : t('balance.topup_cta', { amount })}
          </button>
        </div>
      )}
    </div>
  )
}
