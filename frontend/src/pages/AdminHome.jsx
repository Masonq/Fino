import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { KpiGrid } from './AdminStats'

/**
 * Панель команды — вход во всю админку одним экраном (по образцу домашней страницы Stripe):
 * 1) четыре главных числа с изменением к прошлой неделе; 2) «Требует внимания» — только то, где есть очередь,
 * крупными карточками с числом; 3) все разделы плитками. Раньше разделы были длинным списком в профиле.
 */
const SECTIONS = [
  { to: '/moderation', key: 'moderation', tint: '#E2F1E6', icon: 'M9 12l2 2 4-4M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z' },
  { to: '/admin/support', key: 'support', tint: '#E3ECFA', icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' },
  { to: '/admin/users', key: 'users', tint: '#FAE5EE', icon: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8' },
  { to: '/admin/stats', key: 'stats', tint: '#EAE7FA', icon: 'M3 3v18h18M7 15l4-4 3 3 5-6' },
  { to: '/admin/alerts', key: 'alerts', tint: '#FFF0D2', icon: 'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01' },
  { to: '/admin/flagged', key: 'flagged_chats', tint: '#FCEADB', icon: 'M4 22V4a1 1 0 0 1 1-1h12l-2 4 2 4H5' },
  { to: '/admin/shops', key: 'shops', tint: '#DDF0F3', icon: 'M15.5 10.5l6-3.5v10l-6-3.5M2.5 6h13v12h-13z' },
  { to: '/admin/jobs', key: 'jobs', tint: '#F3EBDB', icon: 'M12 7v5l3 2 M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z' },
  { to: '/admin/team-chats', key: 'team_chats', tint: '#ECF0DD', icon: 'M8 10h8M8 14h5M21 12a9 9 0 0 1-13.4 7.9L3 21l1.1-4.6A9 9 0 1 1 21 12z' },
  { to: '/admin/volunteers', key: 'volunteers', tint: '#F7E4F1', admin: true, icon: 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z' },
  { to: '/admin/audit', key: 'audit', tint: '#E5EAF0', admin: true, icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5' },
  { to: '/admin/settings', key: 'settings', tint: '#F1E8DE', admin: true, icon: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z' },
]

export default function AdminHome() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [c, setC] = useState(null)
  const [stats, setStats] = useState(null)
  useEffect(() => {
    api.modCounters().then(setC).catch(() => setC({}))
    api.adminStats(7).then(setStats).catch(() => {})
  }, [])
  if (!user || (user.role !== 'admin' && user.role !== 'moderator')) {
    return <div className="page"><PageHeader title={t('adminhub.title')} /><p className="empty-hint">{t('admin.no_access')}</p></div>
  }
  const isAdmin = user.role === 'admin'
  // очереди: только где есть что разбирать — пустые не отвлекают
  const queues = [
    { to: '/moderation', n: c?.moderation, label: t('adminhub.q_moderation') },
    { to: '/admin/support', n: c?.support, label: t('adminhub.q_support') },
    { to: '/admin/team-chats', n: c?.team_chats, label: t('adminhub.q_team') },
    { to: '/admin/flagged', n: c?.flagged_chats, label: t('adminhub.q_flagged') },
    { to: '/admin/volunteers', n: c?.volunteers, label: t('adminhub.q_volunteers') },
  ].filter((q) => q.n > 0)
  return (
    <div className="page admin-home">
      <PageHeader title={t('adminhub.title')} kicker={isAdmin ? t('adminhub.kicker_admin') : t('adminhub.kicker_mod')} />

      {isAdmin && (stats
        ? <KpiGrid days={7} active={stats.listings.active} pending={stats.listings.pending} />
        : <div className="kpi-grid">{[0, 1, 2, 3].map((i) => <div key={i} className="kpi sk-block" style={{ height: 112 }} />)}</div>)}

      <div className="ah-title">{t('adminhub.attention')}</div>
      {c === null ? <div className="ah-queues"><div className="ah-queue sk-block" style={{ height: 76 }} /></div>
        : queues.length === 0 ? (
          <div className="ah-calm">
            <span className="ah-calm-ico">✓</span>
            <span><b>{t('adminhub.calm')}</b><br />{t('adminhub.calm_sub')}</span>
          </div>
        ) : (
          <div className="ah-queues">
            {queues.map((q) => (
              <Link key={q.to} to={q.to} className="ah-queue">
                <span className="ah-queue-n">{q.n}</span>
                <span className="ah-queue-label">{q.label}</span>
                <svg className="ah-queue-go" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="m9 6 6 6-6 6" /></svg>
              </Link>
            ))}
          </div>
        )}

      <div className="ah-title">{t('adminhub.sections')}</div>
      <div className="ah-grid">
        {SECTIONS.filter((s) => !s.admin || isAdmin).map((s) => (
          <Link key={s.to} to={s.to} className="ah-tile" style={{ background: s.tint }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d={s.icon} /></svg>
            <span>{t(`adminhub.s_${s.key}`)}</span>
            {c?.[s.key] > 0 && <b className="ah-tile-n">{c[s.key]}</b>}
          </Link>
        ))}
      </div>
    </div>
  )
}
