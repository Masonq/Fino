import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

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
        <button className="auth-close" onClick={() => navigate(returnTo)} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>

        <img className="auth-logo" src="/logo-mark.png" alt="PLONK" />
        <h1>{t('auth.title')}</h1>
        <p className="auth-sub">{t('auth.subtitle')}</p>

        <button className="auth-method primary" onClick={() => { setChannel('email'); setStep('enter') }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><rect x="2.5" y="4.5" width="19" height="15" rx="3" /><path d="m3 7 9 6 9-6" /></svg>
          {t('auth.by_email')}
        </button>

        <button className="auth-method" onClick={() => { setChannel('telegram'); setStep('enter') }}>
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.3 18.7 19c-.2 1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.3 12.9l-4.8-1.5c-1-.3-1-1 .2-1.5l18.8-7.2c.9-.3 1.6.2 1.4 1.6Z" /></svg>
          {t('auth.by_telegram')}
        </button>

        <div className="auth-divider"><span>{t('auth.or')}</span></div>

        <div className="auth-socials">
          <button className="auth-social" onClick={() => setError(t('auth.soon'))}>
            <svg viewBox="0 0 24 24"><path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.9h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.7 3-4.3 3-7.4Z"/><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.6-2.4l-3.2-2.5c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.4 14c-.2-.6-.3-1.3-.3-2s.1-1.4.3-2V7.4H3.1a10 10 0 0 0 0 9.2L6.4 14Z"/><path fill="#EA4335" d="M12 6c1.5 0 2.8.5 3.8 1.5l2.8-2.8A10 10 0 0 0 3.1 7.4L6.4 10c.8-2.3 3-4 5.6-4Z"/></svg>
            Google
          </button>
          <button className="auth-social" onClick={() => setError(t('auth.soon'))}>
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.05 12.6c0-2.2 1.8-3.3 1.9-3.3-1-1.5-2.6-1.7-3.2-1.7-1.4-.1-2.7.8-3.4.8-.7 0-1.8-.8-2.9-.8-1.5 0-2.9.9-3.7 2.2-1.6 2.7-.4 6.8 1.1 9 .7 1.1 1.6 2.3 2.8 2.3 1.1 0 1.5-.7 2.9-.7 1.3 0 1.7.7 2.9.7 1.2 0 2-1.1 2.7-2.2.9-1.2 1.2-2.5 1.2-2.5s-2.3-.9-2.3-3.8ZM14.8 5.9c.6-.7 1-1.8.9-2.9-.9 0-2 .6-2.7 1.4-.6.6-1.1 1.7-.9 2.7 1 .1 2-.5 2.7-1.2Z" /></svg>
            Apple
          </button>
          <button className="auth-social" onClick={() => setError(t('auth.soon'))}>
            <svg viewBox="0 0 24 24" fill="#7360F2"><path d="M11.4 0C9.473.028 5.333.344 3.02 2.467 1.302 4.187.696 6.7.633 9.817.57 12.933.488 18.776 6.12 20.36h.003l-.004 2.416s-.037.977.61 1.177c.777.242 1.234-.5 1.98-1.302.407-.44.972-1.084 1.397-1.58 3.85.326 6.812-.416 7.15-.525.776-.252 5.176-.816 5.892-6.657.74-6.02-.36-9.83-2.34-11.546-.596-.55-3.006-2.3-8.375-2.323 0 0-.395-.025-1.037-.017zm.058 1.693c.545-.004.88.017.88.017 4.542.02 6.717 1.388 7.222 1.846 1.675 1.435 2.53 4.868 1.906 9.897v.002c-.604 4.878-4.174 5.184-4.832 5.395-.28.09-2.882.737-6.153.524 0 0-2.436 2.94-3.197 3.704-.12.12-.26.167-.352.144-.13-.033-.166-.188-.165-.414l.02-4.018c-4.762-1.32-4.485-6.292-4.43-8.895.054-2.604.543-4.738 1.996-6.173 1.96-1.773 5.474-2.018 7.11-2.03zm.38 2.602c-.167 0-.303.135-.304.302 0 .167.133.303.3.305 1.624.01 2.946.537 4.028 1.592 1.073 1.046 1.62 2.468 1.633 4.334.002.167.14.3.307.3.166-.002.3-.138.3-.304-.014-1.984-.618-3.596-1.816-4.764-1.19-1.16-2.692-1.753-4.447-1.765zm-3.96.695c-.19-.032-.4.005-.616.117l-.01.002c-.43.247-.816.562-1.146.932-.002.004-.006.004-.008.008-.267.323-.42.638-.46.948-.008.046-.01.093-.007.14 0 .136.022.27.065.4l.013.01c.135.48.473 1.276 1.205 2.604.42.768.903 1.5 1.446 2.186.27.344.56.673.87.984l.132.132c.31.308.64.6.984.87.686.543 1.418 1.027 2.186 1.447 1.328.733 2.126 1.07 2.604 1.206l.01.014c.13.042.265.064.402.063.046.002.092 0 .138-.008.31-.036.627-.19.948-.46.004 0 .003-.002.008-.005.37-.33.683-.72.93-1.148l.003-.01c.225-.432.15-.842-.18-1.12-.004 0-.698-.58-1.037-.83-.36-.255-.73-.492-1.113-.71-.51-.285-1.032-.106-1.248.174l-.447.564c-.23.283-.657.246-.657.246-3.12-.796-3.955-3.955-3.955-3.955s-.037-.426.248-.656l.563-.448c.277-.215.456-.737.17-1.248-.217-.383-.454-.756-.71-1.115-.25-.34-.826-1.033-.83-1.035-.137-.165-.31-.265-.502-.297zm4.49.88c-.158.002-.29.124-.3.282-.01.167.115.312.282.324 1.16.085 2.017.466 2.645 1.15.63.688.93 1.524.906 2.57-.002.168.13.306.3.31.166.003.305-.13.31-.297.025-1.175-.334-2.193-1.067-2.994-.74-.81-1.777-1.253-3.05-1.346h-.024zm.463 1.63c-.16.002-.29.127-.3.287-.008.167.12.31.288.32.523.028.875.175 1.113.422.24.245.388.62.416 1.164.01.167.15.295.318.287.167-.008.295-.15.287-.317-.03-.644-.215-1.178-.58-1.557-.367-.378-.893-.574-1.52-.607h-.018z" /></svg>
            Viber
          </button>
        </div>

        {error && <p className="auth-error">{error}</p>}
        <p className="auth-terms">{t('auth.terms')}</p>
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

        <h1>{channel === 'email' ? t('auth.enter_email') : t('auth.enter_telegram')}</h1>
        <p className="auth-sub">
          {channel === 'email' ? t('auth.enter_email_hint') : t('auth.enter_telegram_hint')}
        </p>

        <div className="post-field">
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
