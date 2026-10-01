import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
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

// 14 частиц конфетти: направления по кругу, три дальности, цвета бренда
const CONFETTI = Array.from({ length: 14 }, (_, i) => {
  const a = (i / 14) * Math.PI * 2
  const r = 70 + (i % 3) * 22
  const colors = ['#0E9F6E', '#FF6A3D', '#D9A857', '#4B554E', '#7C6CF0']
  return { '--dx': `${Math.round(Math.cos(a) * r)}px`, '--dy': `${Math.round(Math.sin(a) * r - 30)}px`, background: colors[i % colors.length], animationDelay: `${(i % 4) * 25}ms` }
})

export default function BalanceCard({ onReady }) {
  const { t, i18n } = useTranslation()
  const [wallet, setWallet] = useState(null)      // { balance, money, bonus, payments_enabled } или null, пока грузится
  const { user } = useAuth()
  // Сообщаем странице, что баланс готов: профиль показывает шапку, баланс и меню одной волной
  useEffect(() => { if (wallet && onReady) onReady() }, [wallet, onReady])
  const [shown, setShown] = useState(null)        // промежуточные суммы, пока они «набегают»
  const [plan, setPlan] = useState(null)          // { from, to, party } — что проиграть; null — ничего
  const decided = useRef('')                      // для каких сумм уже решили (React в разработке зовёт эффект дважды)

  // Пришёл подарок (бонус за первое объявление, за друга) или пополнение — суммы набегают от прежних к новым, а при
  // новом бонусе ещё и короткое конфетти. Прежние суммы помним на устройстве отдельно для каждого человека: иначе
  // чужой аккаунт на том же телефоне дал бы ложный праздник. Первый заход — без представления, просто запоминаем.
  // «Решить» и «проиграть» разделены: решение принимается один раз на эти суммы, а проигрыш можно перезапустить.
  useEffect(() => {
    if (!wallet || !user?.id) return
    const to = { money: Number(wallet.money), bonus: Number(wallet.bonus) }
    const key = `plonk_seen_wallet:${user.id}`
    const stamp = `${key}:${to.money}:${to.bonus}`
    if (decided.current === stamp) return
    decided.current = stamp
    let prev = null
    try { prev = JSON.parse(localStorage.getItem(key) || 'null') } catch { prev = null }
    try { localStorage.setItem(key, JSON.stringify(to)) } catch { /* без памяти — без представления */ }
    if (!prev || (to.bonus <= prev.bonus && to.money <= prev.money)) return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    setPlan({ from: { money: Math.min(prev.money, to.money), bonus: Math.min(prev.bonus, to.bonus) }, to, party: to.bonus > prev.bonus })
  }, [wallet, user?.id])

  useEffect(() => {
    if (!plan) return undefined
    const { from, to } = plan
    const start = performance.now()
    let raf = 0
    const step = (now) => {
      const p = Math.min(1, (now - start) / 900)
      const e = 1 - (1 - p) ** 3
      setShown({ money: from.money + (to.money - from.money) * e, bonus: from.bonus + (to.bonus - from.bonus) * e })
      if (p < 1) raf = requestAnimationFrame(step)
      else setShown(null)
    }
    raf = requestAnimationFrame(step)
    const done = setTimeout(() => setPlan(null), 1500)
    return () => { cancelAnimationFrame(raf); clearTimeout(done); setShown(null) }
  }, [plan])
  const party = Boolean(plan?.party)
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
  const realMoney = Number(wallet?.money ?? 0)
  const realBonus = Number(wallet?.bonus ?? 0)
  // Пока идёт «представление» (бонус пришёл с прошлого захода), на экране промежуточные числа; потом — настоящие
  const money = shown ? Math.round(shown.money) : realMoney
  const bonus = shown ? Math.round(shown.bonus) : realBonus
  const total = shown ? money + bonus : Number(wallet?.balance ?? realMoney + realBonus)
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
      {party && (
        <span className="balance-confetti" aria-hidden="true">
          {CONFETTI.map((style, i) => <span key={i} className="balance-bit" style={style} />)}
        </span>
      )}
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
