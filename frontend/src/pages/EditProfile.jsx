import { useEffect, useState } from 'react'
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
  const { user, loading: authLoading, updateUser } = useAuth()

  const [name, setName] = useState('')
  const [avatar, setAvatar] = useState('')
  const [company, setCompany] = useState('')
  const [companyDescription, setCompanyDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  const [verify, setVerify] = useState(null)
  const [verifyBusy, setVerifyBusy] = useState(false)
  const [verifyError, setVerifyError] = useState('')

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }
    api.myProfile().then((me) => {
      setName(me.display_name || '')
      setAvatar(me.avatar_url || '')
      setCompany(me.company_name || '')
      setCompanyDescription(me.company_description || '')
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
      alert(e.code === 'verify_identity_first'
        ? t('edit_profile.verify_first') : t('edit_profile.failed'))
    } finally { setSaving(false) }
  }

  const pickPhoto = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const { url } = await api.uploadPhoto(file)
      setAvatar(url)
    } catch {
      alert(t('edit_profile.photo_failed'))
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

  return (
    <div className="page edit-profile">
      <PageHeader title={t('edit_profile.title')} />

      <div className="edit-avatar">
        <div className="profile-avatar">
          {avatar ? <img src={avatar} alt="" />
            : (name || '?').trim().charAt(0).toUpperCase()}
        </div>
        <label className="edit-avatar-pick">
          {t('edit_profile.photo')}
          <input type="file" accept="image/*" onChange={pickPhoto} hidden />
        </label>
      </div>

      <div className="support-form">
        <label className="edit-label">{t('edit_profile.name')}</label>
        <input
          className="admin-search"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('edit_profile.name_hint')}
        />

        <label className="edit-label">{t('edit_profile.company')}</label>
        <input
          className="admin-search"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder={t('edit_profile.company_hint')}
        />
        {/* Уже бизнес-аккаунт — правит своё же название, проверка тут
            не при чём. Иначе, пока не пройдена проверка личности,
            подсказываем сразу, не дожидаясь неудачной попытки сохранить. */}
        {company.trim() && user?.role !== 'seller_business' && verify && verify.status !== 'verified' && (
          <p className="edit-hint-warn">{t('edit_profile.verify_first')}</p>
        )}

        {company.trim() && (
          <>
            <label className="edit-label">{t('edit_profile.company_description')}</label>
            <textarea
              className="admin-search edit-company-desc"
              value={companyDescription}
              onChange={(e) => setCompanyDescription(e.target.value)}
              placeholder={t('edit_profile.company_description_hint')}
              rows={4}
              maxLength={2000}
            />
          </>
        )}

        <button className="support-send" disabled={saving} onClick={save}>
          {done ? t('edit_profile.saved') : t('edit_profile.save')}
        </button>
      </div>

      {/* Проверка документа — отдельное действие от правки профиля,
          со своим статусом и загрузкой, поэтому вне общей формы и
          кнопки «Сохранить». */}
      <div className="profile-section-title">{t('verify.title')}</div>
      <div className="verify-card">
        {!verify ? (
          <p className="verify-hint">{t('actions.loading')}</p>
        ) : verify.status === 'verified' ? (
          <div className="verify-status verified">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
            {t('verify.verified')}
          </div>
        ) : verify.status === 'pending' ? (
          <div className="verify-status pending">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></svg>
            {t('verify.pending')}
          </div>
        ) : (
          <>
            {verify.status === 'rejected' && (
              <div className="verify-status rejected">
                {t('verify.rejected')}
                {verify.reason && <div className="verify-reason">{verify.reason}</div>}
              </div>
            )}
            <p className="verify-hint">{t('verify.hint')}</p>
            <button className={verifyBusy ? 'verify-upload disabled' : 'verify-upload'} disabled={verifyBusy} onClick={submitDoc}>
              {verifyBusy ? '…' : t('verify.upload')}
            </button>
            {verifyError && <p className="auth-error">{verifyError}</p>}
          </>
        )}
      </div>
    </div>
  )
}
