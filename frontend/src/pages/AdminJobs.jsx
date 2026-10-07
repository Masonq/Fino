import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import { useKeepPlace } from '../utils/keepPlace'

/**
 * Ночные работы: чем кончились.
 *
 * Конвейер, сводки, уборка, перевод работают сами и молча. Пока
 * работают. Когда перестают, узнаёшь об этом случайно — через день
 * замечаешь, что новых объявлений нет.
 *
 * Здесь главное не «сколько сделано», а «когда было в последний раз»:
 * работа, молчащая третьи сутки, видна сразу. И причина, если работа
 * прошла впустую: «ничего не отправлено» само по себе ничего не
 * говорит, а «по поискам за сутки ничего не появилось» — говорит.
 */
export default function AdminJobs() {
  useKeepPlace('admin-jobs')
  const { t, i18n } = useTranslation()
  const [data, setData] = useState(null)

  useEffect(() => {
    api.adminJobs(7).then(setData).catch(() => setData({ jobs: [] }))
  }, [])

  const ago = (iso) => {
    const hours = Math.round((Date.now() - new Date(iso)) / 3600000)
    if (hours < 1) return t('jobs.just_now')
    if (hours < 24) return t('jobs.hours_ago', { count: hours })
    return t('jobs.days_ago', { count: Math.round(hours / 24) })
  }

  return (
    <div className="page">
      <PageHeader title={t('jobs.title')} kicker={data?.jobs?.length ? t('jobs.kicker', { count: data.jobs.length }) : '\u00a0'} />

      {/* сводка сверху: сколько работ, сколько с ошибкой, сколько сделали за последний запуск — понятно за секунду */}
      {data?.jobs?.length > 0 && (
        <div className="jobs-sum">
          <div className="jobs-sum-item"><b>{data.jobs.filter((j) => !j.error).length}</b><span>{t('jobs.sum_ok')}</span></div>
          <div className={data.jobs.some((j) => j.error) ? 'jobs-sum-item bad' : 'jobs-sum-item'}><b>{data.jobs.filter((j) => j.error).length}</b><span>{t('jobs.sum_err')}</span></div>
          <div className="jobs-sum-item"><b>{data.jobs.reduce((n, j) => n + (j.done || 0), 0)}</b><span>{t('jobs.sum_done')}</span></div>
        </div>
      )}

      {!data ? (
        <div className="jobs-list">{[0, 1, 2, 3].map((i) => <div key={i} className="job-card sk-block" style={{ height: 104 }} />)}</div>
      ) : data.jobs.length === 0 ? (
        <p className="empty-hint">{t('jobs.empty')}</p>
      ) : (
        <div className="jobs-list">
          {data.jobs.map((job) => (
            <div className={job.error ? 'job-card bad' : 'job-card'} key={job.name}>
              <div className="job-head">
                <span className="job-name">{job.name}</span>
                <span className="job-when">{ago(job.at)}</span>
              </div>

              {/* Что сделала. Ноль — не ошибка сам по себе, поэтому
                  рядом с ним всегда стоит причина. */}
              <div className={job.done > 0 ? 'job-done some' : 'job-done'}>
                {job.done > 0
                  ? t('jobs.done', { count: job.done })
                  : t('jobs.nothing')}
              </div>
              {job.reason && (
                <div className={job.error ? 'job-reason bad' : 'job-reason'}>
                  {job.reason}
                </div>
              )}

              {Object.keys(job.numbers || {}).length > 0 && (
                <div className="job-numbers">
                  {Object.entries(job.numbers).map(([key, value]) => (
                    <span key={key}>{key}: <b>{String(value)}</b></span>
                  ))}
                </div>
              )}

              <div className="job-runs">
                {t('jobs.runs', { count: job.runs, days: data.days })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
