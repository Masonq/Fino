import SlidePill from '../components/SlidePill'
import { intlLocale } from '../utils/time'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminStatsSkeleton } from '../components/Skeletons'
import BarsChart from '../components/BarsChart'

const PERIODS = [7, 14, 30]

export default function AdminStats() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [days, setDays] = useState(14)
  const [data, setData] = useState(null)
  const [daily, setDaily] = useState([])
  const [categories, setCategories] = useState([])
  const [sources, setSources] = useState([])
  const [quality, setQuality] = useState(null)
  const [funnel, setFunnel] = useState(null)
  const [denied, setDenied] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }

    setLoaded(false)
    Promise.all([
      api.adminStats(days),
      api.adminStatsDaily(days),
      api.adminStatsCategories().catch(() => ({ items: [] })),
      api.adminStatsSources().catch(() => ({ items: [] })),
      api.adminStatsQuality().catch(() => null),
      api.adminStatsFunnel(days).catch(() => null),
    ])
      .then(([overview, byDay, cats, srcs, qual, fun]) => {
        setData(overview)
        setDaily(byDay.items || [])
        setCategories(cats.items || [])
        setSources(srcs.items || [])
        setQuality(qual)
        setFunnel(fun)
        setDenied(false)
      })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [authLoading, user, days, navigate])

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('stats.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  const share = (part, whole) => (whole ? Math.round((part / whole) * 100) : 0)

  return (
    <div className="page admin-stats">
      <PageHeader title={t('stats.title')} />

      {/* Тот же ряд отборов, что на остальных экранах админки. */}
      <div className="admin-bar">
        <div className="admin-chips">
        <div className="pill-track pill-row">
          <SlidePill />
          {PERIODS.map((d) => (
            <button
              key={d}
              className={`chip ${days === d ? 'chip-active' : ''}`}
              onClick={() => setDays(d)}
            >
              {t('stats.days', { count: d })}
            </button>
          ))}
        </div>
      </div>
      </div>

      {!loaded && <AdminStatsSkeleton />}

      {data && (
        <>
          {/* Иерархия вместо шести одинаковых плиток.
              Раньше все числа были равны по весу, и на вопрос «как
              дела» страница не отвечала: приходилось читать все шесть
              и сравнивать самому. Теперь сверху два главных — сколько
              всего в ленте и сколько прибавилось за выбранный срок, —
              а остальное строками под ними: они нужны, но не первыми.

              Подпись срока стоит у того числа, которое от срока
              зависит: «320» без «за 14 дней» ничего не значит. */}
          {/* Главные два числа — лента и то, сколько принесли живые
              люди.
              Прежде наверху стояло «Добавлено», но в него входит и то,
              что перенесено из чатов: цифра выглядит бодро, а растёт
              от работы конвейера, а не от людей. Сколько разместили
              сами — единственное, что говорит, живёт ли площадка. */}
          {/* 4 главных показателя карточками (по исследованиям дашбордов — Stripe, NN/g: 4–5 крупных чисел наверху,
              у каждого сравнение с прошлым периодом и мини-график по дням; подробности — ниже) */}
          <KpiGrid days={days} active={data.listings.active} pending={data.listings.pending} />

          <div className="stats-list">
            <div className="stats-list-row">
              <span>
                {t('stats.added_total')}
                <span className="stats-row-hint">{t('stats.added_total_hint')}</span>
              </span>
              <b>+{data.listings.fresh}</b>
            </div>
            <div className="stats-list-row">
              <span>{t('stats.pending')}</span>
              <b>{data.listings.pending}</b>
            </div>
            <div className="stats-list-row">
              <span>{t('stats.sellers')}</span>
              <b>{data.people.sellers}</b>
            </div>
            <div className="stats-list-row">
              <span>{t('stats.new_people')}</span>
              <b>+{data.people.fresh}</b>
            </div>
          </div>

          {/* Воронка — первым блоком после чисел: по ней судят, работает
              площадка или просто наполняется. Показ в ленте → открытие
              карточки → контакт; проценты между ступенями важнее самих
              чисел. */}
          {funnel && funnel.funnel.impressions > 0 && (
            <div className="stats-block">
              <div className="stats-block-title">{t('stats.funnel')}</div>
              <div className="funnel">
                {[
                  ['impressions', funnel.funnel.impressions, null],
                  ['views', funnel.funnel.views, share(funnel.funnel.views, funnel.funnel.impressions)],
                  ['contacts', funnel.funnel.contacts, share(funnel.funnel.contacts, funnel.funnel.views)],
                ].map(([key, value, pct]) => (
                  <div key={key} className="funnel-step">
                    <div className="funnel-bar" style={{ width: `${Math.max(share(value, funnel.funnel.impressions), 4)}%` }} />
                    <div className="funnel-text">
                      <span className="funnel-name">{t(`stats.step_${key}`)}</span>
                      <b>{value.toLocaleString(intlLocale(i18n.language))}</b>
                      {pct !== null && <span className="funnel-pct">{pct}%</span>}
                    </div>
                  </div>
                ))}
              </div>
              <div className="stats-split">
                <span>{t('stats.by_message')}: <b>{funnel.funnel.messages}</b></span>
                <span>{t('stats.by_phone')}: <b>{funnel.funnel.phone_reveals}</b></span>
              </div>
            </div>
          )}

          {/* Ликвидность: доля объявлений, получивших хоть один контакт,
              и сколько до него ждать. Ради этого продавец возвращается —
              или не возвращается. */}
          {funnel && funnel.liquidity.listings > 0 && (
            <div className="stats-block">
              <div className="stats-block-title">{t('stats.liquidity')}</div>
              <div className="stats-rows">
                <div className="stats-row">
                  <span>{t('stats.with_contact')}</span>
                  <span>
                    {funnel.liquidity.with_contact} · {share(funnel.liquidity.with_contact, funnel.liquidity.listings)}%
                  </span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.time_to_contact')}</span>
                  <span>
                    {funnel.liquidity.median_hours_to_contact == null
                      ? '—'
                      : t('stats.hours', { count: Math.round(funnel.liquidity.median_hours_to_contact) })}
                  </span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.sold_share')}</span>
                  <span>
                    {funnel.liquidity.sold} · {share(funnel.liquidity.sold, funnel.liquidity.listings)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_day')}</div>
            <div className="stats-legend">
              <span className="dot dot-all" /> {t('stats.all')}
              <span className="dot dot-own" /> {t('stats.own')}
            </div>
            <BarsChart key={days} items={daily} valueKey="listings" secondKey="own" />
          </div>

          {/* Посещаемость отдельным графиком, а не вторым рядом в
              предыдущем: числа разного порядка — объявлений за день
              десятки, заходов сотни, — и в одном графике столбики
              объявлений превратились бы в незаметную полоску у нуля. */}
          <div className="stats-block">
            <div className="stats-block-title">{t('stats.visits')}</div>
            {/* Порядок подписей повторяет порядок рядов в графике:
                светлым рисуется первый ряд (заходы), тёмным — второй
                (люди). Подписал их наоборот и увидел на снимке. */}
            <div className="stats-legend">
              <span className="dot dot-all" /> {t('stats.hits')}
              <span className="dot dot-own" /> {t('stats.visitors')}
            </div>
            <BarsChart
              key={`visits-${days}`}
              items={daily}
              valueKey="hits"
              secondKey="visitors"
              unitKey="stats.hits_count"
              secondLabelKey="stats.visitors_short"
            />
            {/* Новые и вернувшиеся: общее число посетителей само по себе
                мало что говорит. Новые показывают, работает ли реклама;
                вернувшиеся — стоит ли сайт того, чтобы к нему
                возвращаться. Для площадки объявлений второе важнее. */}
            {daily.length > 0 && (
              <div className="stats-split">
                <span>{t('stats.newcomers')}: <b>{daily[daily.length - 1].newcomers ?? 0}</b></span>
                <span>{t('stats.returning')}: <b>{daily[daily.length - 1].returning ?? 0}</b></span>
              </div>
            )}
          </div>

          {/* Входы и регистрации — отдельным графиком: заходят сотни, а
              входят единицы, и в одном графике вход был бы неразличимой
              полоской у нуля. Разница между «зашли» и «вошли» и есть
              главное, что тут видно. */}
          <div className="stats-block">
            <div className="stats-block-title">{t('stats.logins')}</div>
            <div className="stats-legend">
              <span className="dot dot-all" /> {t('stats.logins_count_label')}
              <span className="dot dot-own" /> {t('stats.signups')}
            </div>
            <BarsChart
              key={`logins-${days}`}
              items={daily}
              valueKey="logins"
              secondKey="signups"
              unitKey="stats.logins_unit"
              secondLabelKey="stats.signups_short"
            />
          </div>

          {quality && (
            <div className="stats-block">
              <div className="stats-block-title">{t('stats.quality')}</div>
              <div className="stats-rows">
                <div className="stats-row">
                  <span>{t('stats.no_price')}</span>
                  <span>{quality.no_price} · {share(quality.no_price, quality.active)}%</span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.no_photo')}</span>
                  <span>{quality.no_photo} · {share(quality.no_photo, quality.active)}%</span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.no_city')}</span>
                  <span>{quality.no_city} · {share(quality.no_city, quality.active)}%</span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.not_translated')}</span>
                  <span>
                    {quality.not_translated} · {share(quality.not_translated, quality.active)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_category')}</div>
            <div className="stats-rows">
              {categories.map((c) => (
                <div key={c.slug} className={`stats-row ${c.count ? '' : 'stats-row-empty'}`}>
                  {/* Название берём из базы: там оно есть на всех трёх
                      языках у любого раздела, даже заведённого вручную.
                      Перевод по служебному имени оставлен запасным —
                      без него в списке всплывали строки вида
                      «appliances» и «pets-supplies». */}
                  <span>{c.name?.[i18n.language] || c.name?.ru
                         || t(`categories.${c.slug}`, c.slug)}</span>
                  <span>{c.count}</span>
                </div>
              ))}
            </div>
          </div>

          <SearchReport days={days} />

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_source')}</div>
            <div className="stats-rows">
              {sources.map((s) => (
                <div key={s.source} className="stats-row">
                  <span>{s.source === 'own' ? t('stats.own_source') : (s.title || s.source)}</span>
                  <span>{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

/** Поиск: сколько искали, доля пустых, что ищут, что не находят, какие опечатки исправили. Пустые поиски —
 * главный список того, каких вещей и слов не хватает сайту (смотреть раз в неделю). */
function SearchReport({ days }) {
  const { t } = useTranslation()
  const [r, setR] = useState(null)
  useEffect(() => { api.searchReport(days).then(setR).catch(() => setR(null)) }, [days])
  if (!r) return null
  const share = r.total ? Math.round((r.empty / r.total) * 100) : 0
  return (
    <div className="stats-block">
      <div className="stats-block-title">{t('stats.search_title')} · {r.total} · {t('stats.search_empty')} {share}%</div>
      <div className="stats-rows">
        {r.zero.length > 0 && <div className="stats-row stats-subhead"><span>{t('stats.search_zero')}</span><span /></div>}
        {r.zero.map((x) => <div key={`z${x.q}`} className="stats-row"><span>«{x.q}»</span><span>{x.n}</span></div>)}
        {r.fixed.length > 0 && <div className="stats-row stats-subhead"><span>{t('stats.search_fixed')}</span><span /></div>}
        {r.fixed.map((x) => <div key={`f${x.q}${x.to}`} className="stats-row"><span>«{x.q}» → «{x.to}»</span><span>{x.n}</span></div>)}
        {r.top.length > 0 && <div className="stats-row stats-subhead"><span>{t('stats.search_top')}</span><span /></div>}
        {r.top.map((x) => <div key={`t${x.q}`} className="stats-row"><span>«{x.q}» · {x.results}</span><span>{x.n}</span></div>)}
      </div>
    </div>
  )
}

/** Карточка показателя: крупное число, подпись, изменение к прошлому такому же периоду и мини-график по дням. */
export function KpiGrid({ days, active, pending }) {
  const { t } = useTranslation()
  const [rows, setRows] = useState(null)
  useEffect(() => { api.adminStatsDaily(Math.min(days * 2, 90)).then((r) => setRows(r.items || [])).catch(() => setRows([])) }, [days])
  if (!rows) return <div className="kpi-grid">{[0, 1, 2, 3].map((i) => <div key={i} className="kpi sk-block" style={{ height: 112 }} />)}</div>
  const cur = rows.slice(-days)
  const prev = rows.slice(-days * 2, -days)
  const sum = (arr, k) => arr.reduce((n, r) => n + (Number(r[k]) || 0), 0)
  const card = (key, label, k) => {
    const now = sum(cur, k)
    const before = prev.length === days ? sum(prev, k) : null
    // в прошлом периоде был ноль — процент роста бессмыслен («+100%» при любом числе), пишем как есть
    const delta = before === null || before === 0 ? null : Math.round(((now - before) / before) * 100)
    const note = before === 0 ? t('stats.kpi_was_zero') : null
    return <Kpi key={key} label={label} value={now} delta={delta} note={note} series={cur.map((r) => Number(r[k]) || 0)} />
  }
  return (
    <div className="kpi-grid">
      {card('v', t('stats.kpi_visitors'), 'visitors')}
      {card('l', t('stats.kpi_listings'), 'own')}
      {card('p', t('stats.kpi_people'), 'signups')}
      <Kpi label={t('stats.kpi_active')} value={active} note={pending ? t('stats.kpi_pending', { count: pending }) : t('stats.now')} />
    </div>
  )
}

function Kpi({ label, value, delta, series, note }) {
  const { t } = useTranslation()
  const pts = (() => {
    if (!series || series.length < 2) return null
    const max = Math.max(...series, 1)
    return series.map((v, i) => `${(i / (series.length - 1)) * 100},${28 - (v / max) * 24}`).join(' ')
  })()
  const up = delta > 0, down = delta < 0
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{Number(value).toLocaleString('ru-RU')}</div>
      <div className="kpi-foot">
        {delta === null || delta === undefined
          ? <span className="kpi-note">{note || t('stats.kpi_no_prev')}</span>
          : <span className={`kpi-delta${up ? ' up' : down ? ' down' : ''}`}>{up ? '↑' : down ? '↓' : '→'} {Math.abs(delta)}%</span>}
        {pts && (
          <svg className="kpi-spark" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
            <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          </svg>
        )}
      </div>
    </div>
  )
}
