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
  const { user, loading: authLoading } = useAuth()

  const [name, setName] = useState('')
  const [avatar, setAvatar] = useState('')
  const [company, setCompany] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }
    api.myProfile().then((me) => {
      setName(me.display_name || '')
      setAvatar(me.avatar_url || '')
      setCompany(me.company_name || '')
    }).catch(() => {})
  }, [authLoading, user, navigate])

  const save = async () => {
    if (name.trim().length < 2) return
    setSaving(true)
    try {
      await api.editProfile({
        display_name: name.trim(),
        avatar_url: avatar.trim(),
        company_name: company.trim(),
        default_language: i18n.language,
      })
      setDone(true)
      setTimeout(() => navigate('/profile'), 700)
    } catch {
      alert(t('edit_profile.failed'))
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

        <button className="support-send" disabled={saving} onClick={save}>
          {done ? t('edit_profile.saved') : t('edit_profile.save')}
        </button>
      </div>
    </div>
  )
}
