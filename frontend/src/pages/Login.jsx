import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

// Имя бота: через него идёт вход, и держать его в одном месте
// надёжнее, чем повторять в разметке.
const TELEGRAM_BOT = 'Baraholka_plonk_bot'

// Ящики, до которых наши письма сейчас не доходят.
//
// Apple отклоняет письма с нашего домена целиком («554 5.7.1 [HM07]»,
// «rejected due to local policy») — не из-за содержимого и не из-за
// подписей: проверено и то, и другое. Он просто не доверяет молодому
// домену, а репутация набирается месяцами.
//
// Пока это так, честнее сказать человеку правду сразу, а не заставлять
// ждать код, который не придёт. Тем более выход есть — вход через
// Telegram работает.
const APPLE_MAIL = ['@icloud.com', '@me.com', '@mac.com']

function isAppleMail(address) {
  const value = (address || '').trim().toLowerCase()
  return APPLE_MAIL.some((domain) => value.endsWith(domain))
}

const CODE_LEN = 6
const RESEND_SEC = 60

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { signIn } = useAuth()

  const returnTo = params.get('returnTo') || '/'

  // iOS выгружает вкладку из памяти, когда уходишь в другое приложение за кодом.
  // Поэтому шаг и введённый адрес держим в хранилище сессии и восстанавливаем.
  const saved = (() => {
    try { return JSON.parse(sessionStorage.getItem('plonk_login') || '{}') } catch { return {} }
  })()

  const [step, setStep] = useState(saved.step || 'choose')   // choose → enter → code
  const [channel, setChannel] = useState(saved.channel || 'email')
  const [destination, setDestination] = useState(saved.destination || '')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [left, setLeft] = useState(() => {
    if (!saved.sentAt) return 0
    const passed = Math.floor((Date.now() - saved.sentAt) / 1000)
    return Math.max(0, RESEND_SEC - passed)
  })

  const destRef = useRef(null)
  const codeRef = useRef(null)

  useEffect(() => {
    if (step === 'choose') sessionStorage.removeItem('plonk_login')
    else sessionStorage.setItem('plonk_login', JSON.stringify({ step, channel, destination, sentAt: saved.sentAt }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, channel, destination])

  // обратный отсчёт до повторной отправки
  useEffect(() => {
    if (left <= 0) return
    const id = setTimeout(() => setLeft((s) => s - 1), 1000)
    return () => clearTimeout(id)
  }, [left])

  useEffect(() => {
    if (step === 'enter') destRef.current?.focus()
    if (step === 'code') codeRef.current?.focus()
  }, [step])

  const errorText = (e) => {
    const map = {
      too_many_requests: t('auth.err_too_often'),
      too_many_attempts: t('auth.err_too_many'),
      invalid_code: t('auth.err_wrong_code'),
      code_expired: t('auth.err_expired'),
      user_blocked: t('auth.err_blocked'),
    }
    return map[e?.code] || t('auth.err_generic')
  }

  const sendCode = async () => {
    const dest = destination.trim()
    if (!dest) return
    if (channel === 'email' && !/^\S+@\S+\.\S+$/.test(dest)) {
      setError(t('auth.err_email')); return
    }
    setBusy(true); setError('')
    try {
      await api.requestCode(dest, channel)
      const sentAt = Date.now()
      sessionStorage.setItem('plonk_login', JSON.stringify({ step: 'code', channel, destination: dest, sentAt }))
      setStep('code')
      setLeft(RESEND_SEC)
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const submitCode = async (value) => {
    setBusy(true); setError('')
    try {
      const res = await api.verifyCode(destination.trim(), value, channel, name.trim() || null)
      sessionStorage.removeItem('plonk_login')
      signIn(res.token, res.user)
      navigate(returnTo, { replace: true })
    } catch (e) {
      setError(errorText(e))
      setCode('')
      codeRef.current?.focus()
    } finally {
      setBusy(false)
    }
  }

  const onCodeChange = (v) => {
    const digits = v.replace(/\D/g, '').slice(0, CODE_LEN)
    setCode(digits)
    if (digits.length === CODE_LEN) submitCode(digits)
  }

  // ——— выбор способа ———
  if (step === 'choose') {
    return (
      <div className="auth-page">
        {/* replace, а не push: иначе экран входа оставался в истории, и
            «назад» с объявления возвращал на него — получался круг, из
            которого нельзя было выйти. Успешный вход это уже делал верно. */}
        <button className="auth-close" onClick={() => navigate(returnTo, { replace: true })} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>

        <img className="auth-logo" src="/logo-mark.png" alt="PLONK" />
        <h1>{t('auth.title')}</h1>
        <p className="auth-sub">{t('auth.subtitle')}</p>

        <button className="auth-method primary" onClick={() => { setChannel('email'); setStep('enter') }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><rect x="2.5" y="4.5" width="19" height="15" rx="3" /><path d="m3 7 9 6 9-6" /></svg>
          {t('auth.by_email')}
        </button>

        {/* Вход через бота: он и так знает, кто перед ним. Просить
            человека набирать своё имя пользователя — лишний шаг, на
            котором ошибаются и бросают. */}
        <a
          className="auth-method telegram"
          href={`https://t.me/${TELEGRAM_BOT}?start=login`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.3 18.7 19c-.2 1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.3 12.9l-4.8-1.5c-1-.3-1-1 .2-1.5l18.8-7.2c.9-.3 1.6.2 1.4 1.6Z" /></svg>
          {t('auth.by_telegram')}
        </a>

        {error && <p className="auth-error">{error}</p>}
        <p className="auth-terms">
          {t('auth.terms_prefix')}{' '}
          <Link to="/terms" target="_blank" rel="noopener">{t('auth.terms_link')}</Link>
          {' '}{t('auth.terms_and')}{' '}
          <Link to="/privacy" target="_blank" rel="noopener">{t('auth.privacy_link')}</Link>
        </p>
      </div>
    )
  }

  // ——— ввод адреса ———
  if (step === 'enter') {
    return (
      <div className="auth-page">
        <button className="auth-close" onClick={() => { setStep('choose'); setError('') }} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>

        <div className="auth-icon">
          {channel === 'email' ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><rect x="2.5" y="4.5" width="19" height="15" rx="3" /><path d="m3 7 9 6 9-6" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.3 18.7 19c-.2 1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.3 12.9l-4.8-1.5c-1-.3-1-1 .2-1.5l18.8-7.2c.9-.3 1.6.2 1.4 1.6Z" /></svg>
          )}
        </div>

        <h1>{channel === 'email' ? t('auth.enter_email') : t('auth.enter_telegram')}</h1>
        <p className="auth-sub">
          {channel === 'email' ? t('auth.enter_email_hint') : t('auth.enter_telegram_hint')}
        </p>

        <div className="auth-input-wrap">
          {channel === 'email' ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><rect x="2.5" y="4.5" width="19" height="15" rx="3" /><path d="m3 7 9 6 9-6" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 3.6-6 8-6s8 2 8 6" /></svg>
          )}
          <input
            ref={destRef}
            type={channel === 'email' ? 'email' : 'text'}
            inputMode={channel === 'email' ? 'email' : 'text'}
            autoComplete={channel === 'email' ? 'email' : 'off'}
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') sendCode() }}
            placeholder={channel === 'email' ? 'name@example.com' : '@username'}
          />
        </div>

        {error && <p className="auth-error">{error}</p>}

        {/* Предупреждаем до нажатия, а не после: человек иначе отправит
            запрос, уйдёт проверять почту и вернётся ни с чем. Кнопку
            «получить код» при этом не убираем и в Telegram не тащим —
            человек сам решит, ввести другой адрес или войти иначе. */}
        {channel === 'email' && isAppleMail(destination) && (
          <p className="auth-warning">{t('auth.icloud_blocked')}</p>
        )}

        <button className="auth-submit" onClick={sendCode} disabled={busy || !destination.trim()}>
          {busy ? '…' : t('auth.get_code')}
        </button>
      </div>
    )
  }

  // ——— ввод кода ———
  return (
    <div className="auth-page">
      <button className="auth-close" onClick={() => { setStep('enter'); setCode(''); setError('') }} aria-label={t('actions.back')}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
      </button>

      <div className="auth-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><rect x="3" y="10" width="18" height="11" rx="2.5" /><path d="M7 10V7a5 5 0 0 1 10 0v3" /></svg>
      </div>

      <h1>{t('auth.enter_code')}</h1>
      <p className="auth-sub">{t('auth.code_sent')} <b>{destination}</b></p>

      <input
        ref={codeRef}
        className="auth-code"
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        value={code}
        onChange={(e) => onCodeChange(e.target.value)}
        placeholder="······"
        maxLength={CODE_LEN}
      />

      {error && <p className="auth-error">{error}</p>}

      <button
        className="auth-resend"
        onClick={() => { setCode(''); sendCode() }}
        disabled={left > 0 || busy}
      >
        {left > 0 ? `${t('auth.resend_in')} ${left}` : t('auth.resend')}
      </button>
    </div>
  )
}
