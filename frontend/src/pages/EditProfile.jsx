import { confirmSheet } from '../utils/confirm'
import { showIsland } from '../utils/island'
import { useEffect, useState } from 'react'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

/**
 * Правка своих данных.
 *
 * Имя и фотография — то, что видит покупатель в карточке продавца.
 * Без возможности их поменять человек остаётся с тем, что подставилось
 * при первом входе.
 */
export default function EditProfile() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading, updateUser, signOut } = useAuth()

  const [name, setName] = useState('')
  const [avatar, setAvatar] = useState('')
  const [company, setCompany] = useState('')
  const [companyDescription, setCompanyDescription] = useState('')
  // Только цифры после кода страны — сам код зашит в самой строке
  // ввода (+381), не отдельное поле выбора: сайт работает в Сербии,
  // спрашивать код у каждого просто лишний шаг.
  const [phoneLocal, setPhoneLocal] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  const [verify, setVerify] = useState(null)
  const [verifyBusy, setVerifyBusy] = useState(false)
  const [verifyError, setVerifyError] = useState('')

  // Смена почты — отдельный, самостоятельный поток, не часть общего
  // «Сохранить» ниже: у неё свой цикл (запрос кода на новый адрес →
  // подтверждение), пока код не подтверждён, менять по сути нечего.
  const [email, setEmail] = useState('')
  const [emailStep, setEmailStep] = useState('view')   // view | enter | code
  // Имя сбросил модератор: пока не введено новое, ни выложить, ни
  // написать нельзя — говорим об этом прямо, а не молчим до отказа.
  const [mustRename, setMustRename] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [emailCode, setEmailCode] = useState('')
  const [emailBusy, setEmailBusy] = useState(false)
  const [emailError, setEmailError] = useState('')

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }
    api.myProfile().then((me) => {
      setName(me.display_name || '')
      setMustRename(Boolean(me.must_rename))
      setAvatar(me.avatar_url || '')
      setCompany(me.company_name || '')
      setCompanyDescription(me.company_description || '')
      setEmail(me.email || '')
      // Если номер уже сохранён с кодом +381 — показываем только
      // остаток, префикс и так на своём месте в самой строке ввода.
      // Мало ли номер сохранён без него (старые записи, до этого поля
      // вообще не было) — тогда просто как есть.
      setPhoneLocal((me.phone || '').replace(/^\+381/, ''))
    }).catch(() => {})
    api.getVerificationStatus().then(setVerify).catch(() => {})
  }, [authLoading, user, navigate])

  const save = async () => {
    if (name.trim().length < 2) return
    setSaving(true)
    try {
      const updated = await api.editProfile({
        display_name: name.trim(),
        avatar_url: avatar.trim(),
        company_name: company.trim(),
        company_description: companyDescription.trim(),
        default_language: i18n.language,
        phone: phoneLocal.trim() ? `+381${phoneLocal.trim()}` : '',
      })
      // Сервер в ответе на сохранение уже отдаёт обновлённый профиль
      // целиком — используем его же, а не собираем заново из полей
      // формы: так кэш входа точно совпадает с тем, что реально
      // сохранилось (например, company_verified сервер мог сбросить
      // сам, если название компании поменялось).
      updateUser(updated)
      setDone(true)
      setTimeout(() => navigate('/profile'), 700)
    } catch (e) {
      showIsland({ text: e.code === 'verify_identity_first'
        ? t('edit_profile.verify_first')
        : e.code === 'phone_already_used'
        ? t('edit_profile.phone_taken')
        : t('edit_profile.failed'), kind: 'warn' })
    } finally { setSaving(false) }
  }

  const requestEmailCode = async () => {
    const trimmed = newEmail.trim().toLowerCase()
    if (!trimmed || trimmed === email.toLowerCase()) return
    setEmailBusy(true); setEmailError('')
    try {
      await api.requestEmailChange(trimmed)
      setEmailStep('code')
    } catch (e) {
      setEmailError(
        e.code === 'email_taken' ? t('edit_profile.email_taken')
        : e.code === 'too_many_requests' ? t('edit_profile.email_too_soon')
        : t('edit_profile.failed')
      )
    } finally { setEmailBusy(false) }
  }

  // Привязка Telegram: сайт выдаёт одноразовый ключ, бот по нему
  // говорит, кто человек в Telegram.
  //
  // Переходим в том же окне, а не открываем новое. Новое окно
  // открывалось уже после ответа сервера — то есть не в момент
  // нажатия, — и браузер на телефоне считал его всплывающим и
  // молча закрывал. Со стороны это выглядело как «кнопка не
  // работает», что ты и увидел.
  const linkTelegram = async () => {
    setEmailError('')
    try {
      const res = await api.linkTelegramStart()
      if (res.url) {
        window.location.href = res.url
      } else if (res.status === 'already_linked') {
        updateUser({ telegram_linked: true })
      }
    } catch {
      setEmailError(t('edit_profile.tg_failed'))
    }
  }

  // Отвязать можно, только если есть чем войти вместо телеграма.
  const canUnlinkTelegram = Boolean(user?.email && user?.email_verified)

  const unlinkTelegram = async () => {
    setEmailError('')
    try {
      await api.unlinkTelegram()
      updateUser({ telegram_linked: false })
    } catch (err) {
      setEmailError(err?.code === 'no_other_login'
        ? t('edit_profile.tg_need_email')
        : t('edit_profile.tg_failed'))
    }
  }

  const confirmEmailCode = async () => {
    if (!emailCode.trim()) return
    setEmailBusy(true); setEmailError('')
    try {
      const updated = await api.verifyEmailChange(newEmail.trim().toLowerCase(), emailCode.trim())
      updateUser(updated)
      setEmail(updated.email || newEmail.trim().toLowerCase())
      setEmailStep('view')
      setNewEmail(''); setEmailCode('')
    } catch (e) {
      setEmailError(
        e.code === 'wrong_code' ? t('edit_profile.email_wrong_code')
        : e.code === 'code_expired' ? t('edit_profile.email_code_expired')
        : e.code === 'email_taken' ? t('edit_profile.email_taken')
        : t('edit_profile.failed')
      )
    } finally { setEmailBusy(false) }
  }

  const pickPhoto = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const { url } = await api.uploadPhoto(file)
      setAvatar(url)
    } catch {
      showIsland({ text: t('edit_profile.photo_failed'), kind: 'warn' })
    }
  }

  const submitDoc = async () => {
    setVerifyBusy(true); setVerifyError('')
    try {
      const { url } = await api.startVerification()
      // Уводим на сторону Didit целиком — снимок документа и селфи
      // происходят там, не на нашей странице.
      window.location.href = url
    } catch (e) {
      setVerifyError(e.code === 'verification_not_configured'
        ? t('verify.err_unavailable') : t('verify.err_generic'))
      setVerifyBusy(false)
    }
  }

  // Пока не пройдена проверка личности, поле «Компания» недоступно
  // для ввода вовсе — заполнить его и всё равно не сохранить (см.
  // edit_profile() на сервере), так честнее показать сразу, чем
  // разрешить печатать и только на «Сохранить» отказать. Уже
  // бизнес-аккаунт — правит своё же название, замок к нему не
  // относится: ждём, пока verify не загрузится, только для тех, кто
  // им ещё не стал.
  const isBusiness = user?.role === 'seller_business'
  const locked = !isBusiness && (!verify || verify.status !== 'verified')

  return (
    <div className="page edit-profile">
      <PageHeader title={t('edit_profile.title')} />

      {mustRename && (
        <p className="admin-note admin-note-warn">{t('edit_profile.must_rename')}</p>
      )}

      {/* Фото и имя — первой карточкой: это то, что видит покупатель
          в объявлении и переписке. Остальное ниже, по назначению. */}
      <div className="form-card form-card-avatar">
        <Avatar src={avatar} name={name} className="profile-avatar" />
        <div className="form-avatar-text">
          <div className="form-avatar-title">{t('edit_profile.photo_title')}</div>
          <label className="form-avatar-pick">
            {t('edit_profile.photo')}
            <input type="file" accept="image/*" onChange={pickPhoto} hidden />
          </label>
        </div>
      </div>

      {/* Поля одной карточкой со строками, а не россыпью подписей и
          полей: так это выглядит настройками, а не анкетой, и видно,
          что всё относится к одному — к тому, как с вами связаться. */}
      <div className="form-card">
        <label className="field-row">
          <span className="field-label">{t('edit_profile.name')}</span>
          <input
            className="field-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('edit_profile.name_hint')}
          />
        </label>

        {/* Код страны зашит в саму строку: сайт работает в Сербии,
            спрашивать код у каждого — лишний шаг. */}
        <label className="field-row">
          <span className="field-label">{t('edit_profile.phone')}</span>
          <span className="field-phone">
            <span className="field-prefix">+381</span>
            <input
              className="field-input"
              type="tel"
              inputMode="numeric"
              value={phoneLocal}
              onChange={(e) => setPhoneLocal(e.target.value.replace(/[^\d]/g, ''))}
              placeholder={t('edit_profile.phone_hint')}
            />
          </span>
        </label>

        <div className="field-row">
          <span className="field-label">{t('edit_profile.email')}</span>
          {emailStep === 'view' ? (
            <div className="field-value-row">
              <span className={email ? 'field-value' : 'field-value empty'}>
                {email || t('edit_profile.email_none')}
              </span>
              <button type="button" className="field-action" onClick={() => setEmailStep('enter')}>
                {t('edit_profile.email_change')}
              </button>
            </div>
          ) : emailStep === 'enter' ? (
            <div className="field-sub">
              <input
                className="field-input"
                type="email"
                inputMode="email"
                autoCapitalize="none"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder={t('edit_profile.email_new_ph')}
                autoFocus
              />
              <div className="field-sub-actions">
                <button type="button" disabled={emailBusy || !newEmail.trim()} onClick={requestEmailCode}>
                  {t('edit_profile.email_send_code')}
                </button>
                <button type="button" className="ghost"
                        onClick={() => { setEmailStep('view'); setNewEmail(''); setEmailError('') }}>
                  {t('actions.cancel')}
                </button>
              </div>
            </div>
          ) : (
            <div className="field-sub">
              <div className="field-note">{t('edit_profile.email_code_sent', { email: newEmail.trim() })}</div>
              <input
                className="field-input"
                type="text"
                inputMode="numeric"
                value={emailCode}
                onChange={(e) => setEmailCode(e.target.value.replace(/\D/g, ''))}
                placeholder={t('edit_profile.email_code_ph')}
                autoFocus
              />
              <div className="field-sub-actions">
                <button type="button" disabled={emailBusy || !emailCode.trim()} onClick={confirmEmailCode}>
                  {t('edit_profile.email_confirm')}
                </button>
                <button type="button" className="ghost"
                        onClick={() => { setEmailStep('view'); setNewEmail(''); setEmailCode(''); setEmailError('') }}>
                  {t('actions.cancel')}
                </button>
              </div>
            </div>
          )}
          {emailError && <p className="auth-error">{emailError}</p>}
        </div>

        {/* Telegram. Человек, размещавший объявления через бота, и
            человек, вошедший сюда по почте, — для нас до сих пор двое
            разных. Привязка сводит их в одного: объявления, переписки
            и отзывы оказываются в одном месте. */}
        <div className="field-row">
          <span className="field-label">Telegram</span>
          <div className="field-value-row">
            <span className={user?.telegram_linked ? 'field-value' : 'field-value empty'}>
              {user?.telegram_linked
                ? t('edit_profile.tg_linked')
                : t('edit_profile.tg_none')}
            </span>
            {!user?.telegram_linked ? (
              <button type="button" className="field-action" onClick={linkTelegram}>
                {t('edit_profile.tg_link')}
              </button>
            ) : canUnlinkTelegram && (
              <button type="button" className="field-action" onClick={unlinkTelegram}>
                {t('edit_profile.tg_unlink')}
              </button>
            )}
          </div>
          {/* Пока другого входа нет, отвязка заперла бы человека
              снаружи: нажал — и войти больше нечем. Поэтому кнопки нет,
              а вместо неё сказано, что нужно сделать раньше. */}
          <span className="field-sub-hint">
            {!user?.telegram_linked
              ? t('edit_profile.tg_hint')
              : !canUnlinkTelegram
                ? t('edit_profile.tg_need_email')
                : t('edit_profile.tg_linked_hint')}
          </span>
        </div>
      </div>

      {/* Бизнес — отдельной карточкой: это не «ещё одно поле анкеты», а
          другой способ продавать. Пока проверка не пройдена, поле
          закрыто, и сказано это одной строкой рядом, а не плашкой в
          три строки, как было. */}
      <div className="form-card">
        <div className="form-card-title">{t('edit_profile.company_title')}</div>
        <label className="field-row">
          <span className="field-label">{t('edit_profile.company')}</span>
          <span className="field-phone">
            <input
              className="field-input"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder={locked ? t('edit_profile.company_locked_ph') : t('edit_profile.company_hint')}
              disabled={locked}
              readOnly={locked}
            />
            {locked && (
              <svg className="field-lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
                <rect x="4.5" y="10.5" width="15" height="10" rx="2.5" />
                <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
              </svg>
            )}
          </span>
        </label>

        {company.trim() && !locked && (
          <label className="field-row">
            <span className="field-label">{t('edit_profile.company_description')}</span>
            <textarea
              className="field-input field-textarea"
              value={companyDescription}
              onChange={(e) => setCompanyDescription(e.target.value)}
              placeholder={t('edit_profile.company_description_hint')}
              rows={4}
              maxLength={2000}
            />
          </label>
        )}
      </div>

      <button className="form-save" disabled={saving} onClick={save}>
        {done ? t('edit_profile.saved') : t('edit_profile.save')}
      </button>

      {/* Проверка личности — отдельное действие со своим статусом,
          поэтому вне формы и кнопки «Сохранить». Длинное объяснение
          показываем только тем, кто ещё не начал: прошедшему проверку
          достаточно строки со статусом. */}
      <div className="form-card">
        <div className="form-card-title">{t('verify.title')}</div>
        {!verify ? (
          <p className="field-note"><span className="sk-block" style={{ display: 'inline-block', width: 180, height: 14, borderRadius: 6 }} aria-hidden="true" /></p>
        ) : verify.status === 'verified' ? (
          <div className="verify-line ok">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
            {t('verify.verified')}
          </div>
        ) : verify.status === 'pending' ? (
          <div className="verify-line wait">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></svg>
            {t('verify.pending')}
          </div>
        ) : (
          <>
            {verify.status === 'rejected' && (
              <div className="verify-line bad">
                {t('verify.rejected')}
                {verify.reason && <div className="field-note">{verify.reason}</div>}
              </div>
            )}
            <p className="field-note">{t('verify.hint')}</p>
            <button className="form-secondary" disabled={verifyBusy} onClick={submitDoc}>
              {verifyBusy ? '…' : t('verify.upload')}
            </button>
            {verifyError && <p className="auth-error">{verifyError}</p>}
          </>
        )}
      </div>

      {/* удаление аккаунта — по просьбе самого человека (в приложении было, на сайте не было) */}
      <button type="button" className="edit-delete-account" onClick={async () => {
        if (!(await confirmSheet({ title: t('profile.delete_confirm'), danger: true }))) return
        try { await api.deleteMe(); signOut?.(); window.location.href = '/' } catch { confirmSheet({ title: t('support.failed'), confirm: 'OK' }) }
      }}>{t('profile.delete_account')}</button>
    </div>
  )
}
