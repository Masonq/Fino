import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { formatAmount } from '../utils/money'

/**
 * Баланс: деньги и бонусы отдельно.
 *
 * Условия обещают разное: внесённые деньги при необходимости возвращаются, подаренный бонус — нет, его можно
 * потратить только на продвижение. Поэтому на экране это две разные вещи с разными цветами: зелёный — деньги,
 * оранжевый — бонусы. Полоса под суммой показывает пропорцию, плитки ниже — суммы и то, для чего они годятся.
 * Тратятся сначала бонусы, потом деньги (app.core.wallet) — об этом отдельная строка.
 */

// Пресеты суммы пополнения — круглые, чтобы после покупки продвижения на балансе оставалось что-то целое,
// а не «почти хватило».
const PRESETS = [500, 1000, 2000, 5000]

const Icon = ({ children }) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.9"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
)
const WalletIcon = () => (
  <Icon>
    <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H17a2 2 0 0 1 2 2v1" />
    <path d="M4 7.5V17a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2H6.5A2.5 2.5 0 0 1 4 7.5Z" />
    <circle cx="16" cy="13.5" r="1.1" fill="currentColor" stroke="none" />
  </Icon>
)
const GiftIcon = () => (
  <Icon>
    <rect x="4" y="10" width="16" height="10" rx="2" />
    <path d="M12 10v10M4 14h16" />
    <path d="M12 10c-1.4-3.2-5-3.2-5-.9 0 1.6 2.6 1.5 5 .9Zm0 0c1.4-3.2 5-3.2 5-.9 0 1.6-2.6 1.5-5 .9Z" />
  </Icon>
)

export default function BalanceCard() {
  const { t, i18n } = useTranslation()
  const [wallet, setWallet] = useState(null)      // { balance, money, bonus, payments_enabled } или null, пока грузится
  const [open, setOpen] = useState(false)
  const [amount, setAmount] = useState(PRESETS[1])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // Не удалось узнать — считаем, что оплата картой недоступна: лучше не предложить кнопку, чем предложить и отказать.
    api.getBalance().then(setWallet).catch(() => setWallet({ balance: 0, money: 0, bonus: 0, payments_enabled: false }))
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

  const known = wallet !== null
  const money = Number(wallet?.money ?? 0)
  const bonus = Number(wallet?.bonus ?? 0)
  const total = Number(wallet?.balance ?? money + bonus)
  const rsd = (n) => t('promo.price', { price: formatAmount(n, i18n.language) })
  const bar = total > 0
    ? [money > 0 && ['money', money], bonus > 0 && ['bonus', bonus]].filter(Boolean)
    : [['empty', 1]]

  // Строка под плитками одна и всегда занимает ровно одну строку: пока баланс грузится, она невидима, но на месте.
  // Что в ней написано, зависит от данных — а высота нет, поэтому ничего под ней не прыгает.
  const hint = wallet?.payments_enabled === true
    ? (bonus > 0 ? t('balance.spend_order') : t('balance.separate_note'))
    : t('balance.topup_off')

  return (
    <div className="balance-card">
      {/* Правило блока: загрузка и готовый вид занимают одно и то же место. Скелет лежит ВНУТРИ настоящей строки
          (той же высоты), кнопка не меняет размера, подпись про оплату — в строке под плитками, а не сбоку от суммы,
          иначе крупная сумма выталкивала её вниз и вся карточка съезжала. */}
      <div className="balance-head">
        <div className="balance-head-text">
          <div className="balance-label">{t('balance.title')}</div>
          <div className="balance-total">
            {known ? rsd(total) : <span className="sk-block balance-sk-inline balance-sk-total" aria-hidden="true" />}
          </div>
        </div>
        <div className="balance-action">
          {wallet === null ? (
            <span className="balance-topup-btn balance-topup-ph" aria-hidden="true">{t('balance.topup')}</span>
          ) : wallet.payments_enabled === true ? (
            <button className="balance-topup-btn" onClick={() => setOpen((v) => !v)}>{t('balance.topup')}</button>
          ) : (
            // Оплату картой выключил владелец (админка → Настройки): кнопка на месте, но погашена; почему — в строке ниже.
            <button className="balance-topup-btn is-off" disabled aria-describedby="balance-foot">{t('balance.topup')}</button>
          )}
        </div>
      </div>

      <div
        className={known ? 'balance-bar is-ready' : 'balance-bar'}
        role="img"
        aria-label={known ? t('balance.aria', { total: rsd(total), money: rsd(money), bonus: rsd(bonus) }) : undefined}
      >
        {known && bar.map(([kind, value]) => (
          <span key={kind} className={`balance-seg ${kind}`} style={{ flexGrow: value }} />
        ))}
      </div>

      <div className="balance-parts">
        <div className={money > 0 || !known ? 'balance-part money' : 'balance-part money is-zero'}>
          <div className="balance-part-top"><WalletIcon /><span>{t('balance.money')}</span></div>
          <div className="balance-part-amount">
            {known ? rsd(money) : <span className="sk-block balance-sk-inline balance-sk-part" aria-hidden="true" />}
          </div>
          <div className="balance-part-note">{t('balance.money_note')}</div>
        </div>
        <div className={bonus > 0 || !known ? 'balance-part bonus' : 'balance-part bonus is-zero'}>
          <div className="balance-part-top"><GiftIcon /><span>{t('balance.bonus')}</span></div>
          <div className="balance-part-amount">
            {known ? rsd(bonus) : <span className="sk-block balance-sk-inline balance-sk-part" aria-hidden="true" />}
          </div>
          <div className="balance-part-note">{t('balance.bonus_note')}</div>
        </div>
      </div>

      <p id="balance-foot" className="balance-hint" style={known ? undefined : { visibility: 'hidden' }} aria-hidden={known ? undefined : 'true'}>
        {known ? hint : t('balance.spend_order')}
      </p>

      {open && (
        <div className="balance-topup-form">
          <div className="balance-presets">
            {PRESETS.map((p) => (
              <button
                key={p}
                className={amount === p ? 'balance-preset active' : 'balance-preset'}
                onClick={() => setAmount(p)}
              >
                {rsd(p)}
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
