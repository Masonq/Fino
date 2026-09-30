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

  // Была ли у этого человека строка про бонус в прошлый раз. Пока баланс грузится, держим под неё место
  // (невидимую), иначе карточка вырастала бы на строку в момент прихода ответа и всё под ней прыгало.
  const [hadBonusLine] = useState(() => {
    try { return localStorage.getItem('plonk_bonus_line') === '1' } catch { return false }
  })

  useEffect(() => {
    // Не удалось узнать — считаем, что оплата картой недоступна: лучше не предложить кнопку, чем предложить и отказать.
    api.getBalance().then((w) => {
      setWallet(w)
      try { localStorage.setItem('plonk_bonus_line', w.bonus > 0 ? '1' : '0') } catch { /* память недоступна — не беда */ }
    }).catch(() => setWallet({ balance: 0, money: 0, bonus: 0, payments_enabled: false }))
  }, [])

  const topup = async () => {
    setBusy(true); setError('')
    try {
      const { confirmation_url } = await api.startTopup(amount)
      // Уводим на оплату целиком — сама оплата на стороне ЮKassa.
      window.location.href = confirmation_url
    } catch (e) {
      setError(e.code === 'promotion_not_configured' ? t('promo.err_unavailable')
        : e.code === 'payments_disabled' ? t('balance.topup_off') : t('promo.err_generic'))
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
          {wallet === null && hadBonusLine && (
            <div className="balance-bonus" style={{ visibility: 'hidden' }} aria-hidden="true">{t('balance.of_which_bonus', { amount: 0 })}</div>
          )}
        </div>
        {/* Три состояния, и до ответа сервера не рисуем ничего осмысленного: раньше пока баланс грузился,
            условие «выключено» ещё не выполнялось, и на долю секунды показывалась кнопка «Пополнить»,
            которую потом заменяла подпись. Место под кнопку держим невидимым, чтобы строка не прыгала. */}
        {wallet === null ? (
          <span className="balance-topup-btn balance-topup-ph" aria-hidden="true">{t('balance.topup')}</span>
        ) : wallet.payments_enabled === true ? (
          <button className="balance-topup-btn" onClick={() => setOpen((v) => !v)}>
            {t('balance.topup')}
          </button>
        ) : (
          // Оплату картой выключил владелец (админка → Настройки): просить деньги не у кого и не за что.
          <span className="balance-topup-off">{t('balance.topup_off')}</span>
        )}
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
