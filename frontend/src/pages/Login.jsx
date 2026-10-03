import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

// Имя бота: через него идёт вход, и держать его в одном месте
// надёжнее, чем повторять в разметке.
const TELEGRAM_BOT = 'Baraholka_plonk_bot'

// Длина кода и пауза до повторной отправки.
//
// Пропали однажды вместе с блоком про адреса iCloud: убирая его, я
// вырезал кусок файла целиком и захватил заодно эти две строки. Страница
// входа после этого падала с «Can't find variable: RESEND_SEC» — то
// есть войти нельзя было вовсе, а сборка и проверки этого не заметили.
const CODE_LEN = 6
const RESEND_SEC = 60

const GOOGLE_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

export default function Login() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { signIn } = useAuth()

  const returnTo = params.get('returnTo') || '/'
  // Вход для мобильного приложения (/login?app=google): приложение открывает эту страницу в защищённом окне
  // браузера; здесь — только Google, а готовый вход уходит обратно в приложение по его ссылке plonk://auth.
  // Ключи Google у нас — только для сайта, поэтому приложение входит через Google именно так.
  const appMode = params.get('app') === 'google'
  const [appDone, setAppDone] = useState(false)
  const googleRef = useRef(null)
  const [googleReady, setGoogleReady] = useState(false)
  const observerRef = useRef(null)
  // Высота кнопки Google с прошлого раза: место под неё резервируем
  // сразу правильное, чтобы ничего не дёрнулось.
  const knownH = (() => {
    try { return Number(localStorage.getItem('plonk_google_h')) || 0 } catch { return 0 }
  })()

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
  // Исправленный адрес, если в домене похоже на опечатку.
  const [suggestion, setSuggestion] = useState('')
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

  // Обратный отсчёт до повторной отправки.
  //
  // Считаем от времени отправки, а не «минус секунда каждую секунду».
  // Браузер притормаживает таймеры в свёрнутой вкладке и в фоне: человек
  // уходил в почту за кодом, возвращался — а счётчик всё это время стоял
  // и заставлял ждать заново, хотя минута давно прошла.
  //
  // Пересчитываем ещё и при возвращении на страницу: одного тика мало,
  // ждать до него — та же пауза на ровном месте.
  useEffect(() => {
    if (left <= 0) return

    const tick = () => {
      const sentAt = (() => {
        try { return JSON.parse(sessionStorage.getItem('plonk_login') || '{}').sentAt }
        catch { return null }
      })()
      if (!sentAt) { setLeft(0); return }
      setLeft(Math.max(0, RESEND_SEC - Math.floor((Date.now() - sentAt) / 1000)))
    }

    const id = setInterval(tick, 500)
    document.addEventListener('visibilitychange', tick)
    window.addEventListener('pageshow', tick)
    window.addEventListener('focus', tick)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', tick)
      window.removeEventListener('pageshow', tick)
      window.removeEventListener('focus', tick)
    }
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
      email_malformed: t('auth.email_malformed'),
      email_domain_unknown: t('auth.email_domain_unknown'),
      // Письмо не ушло — говорим прямо и показываем выход.
      // Человек пришёл регистрироваться; если он увидит «что-то пошло
      // не так» и не получит код, второй раз он может не прийти.
      apple_mail_unavailable: t('auth.err_apple_mail'),
      code_not_sent: t('auth.err_not_sent'),
    }
    return map[e?.code] || t('auth.err_generic')
  }

  const sendCode = async (force = false) => {
    const dest = destination.trim()
    if (!dest) return
    if (channel === 'email' && !/^\S+@\S+\.\S+$/.test(dest)) {
      setError(t('auth.err_email')); return
    }
    setBusy(true); setError('')
    try {
      const res = await api.requestCode(dest, channel)

      // Похоже на опечатку в домене: «gmial.com» вместо «gmail.com».
      //
      // Не отказываем — домен существует, и человек может быть правда
      // там. Показываем исправленный адрес и даём выбрать: письмо
      // отправится только после его решения.
      // Сравниваем именно с true.
      //
      // Эту функцию вызывает и кнопка «Получить код», а React передаёт
      // ей событие нажатия — оно считалось бы признаком «отправить всё
      // равно», и подсказка не показывалась бы никогда. Поймал на
      // снимке: сайт сразу переходил к вводу кода для ivan@gmial.com.
      if (force !== true && res?.status === 'typo_suspected' && res.suggestion) {
        setSuggestion(res.suggestion)
        setBusy(false)
        return
      }

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
  // Кнопку рисует сам Google — свою нарисовать нельзя, правила
  // Google этого не разрешают. Токен приходит сюда и уходит на сервер,
  // где проверяется его подпись: браузеру в этом вопросе доверия нет.
  useEffect(() => {
    if (!GOOGLE_ID || step !== 'choose' || !googleRef.current) return
    let cancelled = false

    const draw = () => {
      if (cancelled || !window.google?.accounts?.id || !googleRef.current) return
      window.google.accounts.id.initialize({
        client_id: GOOGLE_ID,
        // Всплывающее окошко «войти одним касанием» не показываем: мы
        // его и не вызываем, но библиотека умеет поднимать его сама.
        auto_select: false,
        cancel_on_tap_outside: true,
        callback: async ({ credential }) => {
          try {
            const res = await api.googleLogin(credential)
            if (appMode) {
              setAppDone(true)
              window.location.replace(`plonk://auth?token=${encodeURIComponent(res.token)}`)
              return
            }
            signIn(res.token, res.user)
            navigate(returnTo, { replace: true })
          } catch (e) {
            setError(e.code === 'user_blocked' ? t('auth.err_blocked') : t('auth.err_generic'))
          }
        },
      })
      // Ширину берём у самого места под кнопку, а не числом: Google
      // рисует кнопку ровно той ширины, что ей передали, и 320 на
      // экране 394 давало кнопку уже двух соседних — своя линия слева
      // и справа. Потолок 400 — предел, который принимает Google.
      // Ширину просим чуть меньше колонки: Google добавляет к заданному
      // числу свою рамку, и кнопка ровно по колонке вылезала за край —
      // справа было видно срез. Меньше и по центру спокойнее, чем
      // впритык.
      const box = Math.round(googleRef.current.getBoundingClientRect().width)
      const slot = Math.max(240, Math.min(400, box - 8)) || 320
      // Подгоняем место под кнопку по факту. Google не держит обещанного
      // размера: размер «large» — это 40 точек у обычной кнопки, но
      // персонализированная («Войти как Максим») выше, а запрошенная
      // ширина не соблюдается — просишь 400, получаешь 420. Поэтому
      // слушаем фактический размер того, что он вставил, и задаём его
      // блоку. Последний известный размер храним: со второго захода
      // место сразу правильное, и дёргаться нечему.
      const remember = (h) => {
        if (!h || !googleRef.current) return
        googleRef.current.parentElement?.style.setProperty('--google-h', `${Math.round(h)}px`)
        try { localStorage.setItem('plonk_google_h', String(Math.round(h))) } catch { /* приват */ }
      }
      const watch = new ResizeObserver((entries) => {
        const h = entries[0]?.target?.getBoundingClientRect().height
        if (h > 20) remember(h)
      })
      watch.observe(googleRef.current)
      observerRef.current = watch

      window.google.accounts.id.renderButton(googleRef.current, {
        theme: 'outline', size: 'large', width: slot,
        // Прямоугольная со скруглением — ближе к нашим кнопкам, чем
        // «таблетка» по умолчанию.
        text: 'continue_with', shape: 'rectangular',
        locale: i18n.language,
      })
      setGoogleReady(true)
    }

    // Уходя со страницы, убираем за Google. Его скрипт оставляет на
    // body свои слои — окно выбора аккаунта и подложку под ним. Они
    // прозрачные и растянуты на весь экран: пока они висят, нажатия по
    // сайту уходят в них, и кажется, что кнопки перестали работать.
    const cleanup = () => {
      cancelled = true
      observerRef.current?.disconnect()
      try { window.google?.accounts?.id?.cancel() } catch { /* скрипт мог не доехать */ }
      document.querySelectorAll(
        '#credential_picker_container, #credential_picker_iframe, ' +
        '[id^="gsi_"], iframe[src*="accounts.google.com/gsi"]',
      ).forEach((el) => {
        // Кнопку, которую мы сами нарисовали, не трогаем — только то,
        // что Google положил мимо нашего места под неё.
        if (!googleRef.current || !googleRef.current.contains(el)) el.remove()
      })
    }

    if (window.google?.accounts?.id) { draw(); return cleanup }
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = draw
    document.head.appendChild(script)
    return cleanup
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step])

  if (step === 'choose') {
    return (
      <div className="auth-page">
        {/* replace, а не push: иначе экран входа оставался в истории, и
            «назад» с объявления возвращал на него — получался круг, из
            которого нельзя было выйти. Успешный вход это уже делал верно. */}
        <button className="auth-close" onClick={() => (appMode ? window.location.replace('plonk://auth?cancel=1') : navigate(returnTo, { replace: true }))} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>

        <img className="auth-logo" src="/logo-mark.png" alt="PLONK" />
        <h1>{t('auth.title')}</h1>
        <p className="auth-sub">{appMode ? t(appDone ? 'auth.app_done' : 'auth.app_google_sub') : t('auth.subtitle')}</p>

        {!appMode && (<>
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
        </>)}

        {/* Вход через Google — кнопка появляется, только если
            идентификатор приложения задан в сборке: без него Google
            ничего не покажет, а пустая кнопка хуже её отсутствия.
            Скрипт Google подгружается один раз и только на этом
            экране — на остальных страницах он не нужен и только
            смотрел бы за человеком зря. */}
        {/* Место под кнопку занято с самого начала: раньше она
            появлялась, когда доезжал скрипт Google, и всё под ней —
            баннер и подпись о правилах — подпрыгивало вниз. Пока
            кнопки нет, в том же месте стоит её серый силуэт. */}
        {/* Кнопку рисует сам Google, её вид нам не подчиняется. Пробовали
            накрыть своей и пустить нажатие сквозь — на телефоне кнопка
            перестала нажиматься вовсе, так что показываем настоящую:
            рабочая кнопка важнее одинакового вида. Ширину она берёт по
            месту, чтобы стоять в одной колонке с соседями. */}
        {GOOGLE_ID && (
          <div
            className={googleReady ? 'auth-google' : 'auth-google loading'}
            style={knownH ? { '--google-h': `${knownH}px` } : undefined}
          >
            <div ref={googleRef} className="auth-google-slot" />
          </div>
        )}

        {error && <p className="auth-error">{error}</p>}

        {/* Подарка новичку здесь больше нет — он остался в профиле.
            Экран входа с полем для кода, кнопкой Google и обещанием
            денег за регистрацию на молодом домене — ровно тот набор, по
            которому Safari повторно пометил сайт мошенническим через
            два дня после снятия первой пометки. */}

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

        {/* Похоже на опечатку в домене почты.
            Не отказ, а вопрос: домен существует, и человек может быть
            правда там. Настоять на своём можно одним нажатием — иначе
            мы бы просто не пустили того, у кого почта на редком
            домене. */}
        {suggestion && (
          <div className="auth-typo">
            <span>{t('auth.typo_question', { address: suggestion })}</span>
            <div className="auth-typo-actions">
              <button
                className="auth-typo-yes"
                onClick={() => { setDestination(suggestion); setSuggestion(''); }}
              >
                {t('auth.typo_fix')}
              </button>
              <button
                className="auth-typo-no"
                onClick={() => { setSuggestion(''); sendCode(true); }}
              >
                {t('auth.typo_keep')}
              </button>
            </div>
          </div>
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
