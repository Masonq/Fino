import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

// Тревоги — то, что стоит посмотреть сегодня, в одном месте.
//
// Всё это можно было найти и раньше, но надо было знать, где искать и
// зачем. Здесь четыре вопроса, ответы на которые обычно и означают
// неприятность: регистрируют аккаунты пачкой с одного адреса, кому-то
// отклоняют всё подряд, одни и те же фото у разных людей, и как давно
// стоит очередь.

const LINKS = {
  many_rejected: (a) => (a.user_id ? `/admin/users/${a.user_id}` : null),
  queue_stale: () => '/moderation',
}

export default function AdminAlerts() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()
  const [items, setItems] = useState(null)
  const [denied, setDenied] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }
    api.adminAlerts()
      .then((r) => setItems(r.items || []))
      .catch((e) => { if (e.status === 403) setDenied(true); else setItems([]) })
  }, [authLoading, user?.id, navigate])

  if (denied) {
    return (
      <div className="page admin-users">
        <PageHeader title={t('admin.alerts')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-users">
      <PageHeader title={t('admin.alerts')} />

      {items === null && <p className="empty">{t('admin.loading')}</p>}

      {items?.length === 0 && (
        <div className="admin-calm">
          <b>{t('admin.calm_title')}</b>
          <span>{t('admin.calm_text')}</span>
        </div>
      )}

      <div className="admin-list">
        {(items || []).map((a, i) => {
          const to = LINKS[a.kind]?.(a)
          const body = (
            <>
              <span className={`admin-alert-dot ${a.level}`} aria-hidden="true" />
              <span className="admin-alert-text">
                <b>{t(`admin.alert_${a.kind}`, { count: a.count, value: a.value || '' })}</b>
                <span>{t(`admin.alert_${a.kind}_hint`, { value: a.value || '' })}</span>
              </span>
            </>
          )
          return to ? (
            <Link key={i} to={to} className={`admin-alert ${a.level}`}>{body}</Link>
          ) : (
            <div key={i} className={`admin-alert ${a.level}`}>{body}</div>
          )
        })}
      </div>
    </div>
  )
}
