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

  const [step, setStep] = useState('choose')   // choose → enter → code
  const [channel, setChannel] = useState('email')
  const [destination, setDestination] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [left, setLeft] = useState(0)

  const destRef = useRef(null)
  const codeRef = useRef(null)

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
            <svg viewBox="0 0 24 24" fill="#7360F2">
              <path d="M12 1.6c-3 0-5.5.5-7 1.7C3.6 4.5 2.9 6.6 2.9 9.5c0 2.8.6 4.9 1.8 6.2.5.6 1.2 1.1 2 1.5v3.6c0 .5.6.8 1 .5l2.9-2.6c.5 0 .9.1 1.4.1 3 0 5.5-.5 7-1.7 1.4-1.2 2.1-3.3 2.1-6.2 0-2.9-.7-5-2.1-6.2-1.5-1.2-4-1.7-7-1.7Z" />
              <path fill="#fff" d="M9.2 6.1c-.3-.1-.6 0-.9.2l-.6.5c-.4.3-.5.9-.3 1.4.5 1.3 1.3 2.5 2.3 3.5s2.2 1.8 3.5 2.3c.5.2 1 .1 1.4-.3l.5-.6c.2-.3.3-.6.2-.9-.1-.3-.3-.5-.6-.6l-1.3-.5c-.4-.2-.8 0-1.1.3l-.3.4c-.6-.3-1.1-.7-1.6-1.2s-.9-1-1.2-1.6l.4-.3c.3-.3.4-.7.3-1.1l-.5-1.3c-.1-.3-.3-.5-.6-.6Z" />
              <path fill="#fff" d="M12.4 5.2c0-.2.2-.4.4-.4 2.4.1 4.3 2 4.4 4.4 0 .2-.2.4-.4.4s-.4-.2-.4-.4a3.7 3.7 0 0 0-3.6-3.6c-.2 0-.4-.2-.4-.4Zm.2 1.9c0-.2.2-.4.4-.4a2.8 2.8 0 0 1 2.7 2.7c0 .2-.2.4-.4.4s-.4-.2-.4-.4a2 2 0 0 0-1.9-1.9c-.2 0-.4-.2-.4-.4Z" />
            </svg>
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
