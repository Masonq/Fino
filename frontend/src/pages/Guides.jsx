import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import { RowSkeletons } from '../components/Skeletons'

// Темы статей — в том же порядке, что фильтры наверху. Цвет плашки обложки — по теме,
// чтобы список читался блоками, а не сплошной лентой одинаковых карточек.
const TOPICS = ['home', 'docs', 'auto', 'deals', 'family']

function dateLabel(iso, lang) {
  try {
    return new Intl.DateTimeFormat(lang === 'sr' ? 'sr-Latn' : lang, { day: 'numeric', month: 'long', year: 'numeric' })
      .format(new Date(iso))
  } catch { return iso }
}

function GuideCard({ g, big = false }) {
  const { t } = useTranslation()
  return (
    <Link to={`/vodic/${g.slug}`} className={`gcard${big ? ' gcard--big' : ''}`}>
      <span className={`gcard-art topic-${g.topic}`}><img src={g.cover} alt="" loading={big ? 'eager' : 'lazy'} /></span>
      <span className="gcard-body">
        <span className="gcard-meta">
          <span>{t(`guides.topic_${g.topic}`)}</span>
        </span>
        <span className="gcard-title">{g.title}</span>
        <span className="gcard-lead">{g.lead}</span>
      </span>
    </Link>
  )
}

/** «Полезное» — статьи-путеводители: поиск, темы, главная статья сверху и сетка остальных. */
export function GuidesList() {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState(null)
  const [topic, setTopic] = useState('all')
  const [q, setQ] = useState('')
  useEffect(() => { api.guides(i18n.language).then((r) => setItems(r.items || [])).catch(() => setItems([])) }, [i18n.language])
  useEffect(() => { document.title = `${t('guides.title')} — PLONK` }, [t])

  const shown = useMemo(() => {
    if (!items) return []
    const needle = q.trim().toLowerCase()
    return items.filter((g) => (topic === 'all' || g.topic === topic)
      && (!needle || `${g.title} ${g.lead}`.toLowerCase().includes(needle)))
  }, [items, topic, q])
  // Главная статья — только в общем виде: при поиске или фильтре важнее ровный список.
  // Главная статья — каждый раз другая: по очереди при каждом открытии раздела (номер — в памяти устройства),
  // чтобы наверху не стояла всегда одна и та же.
  const [turn] = useState(() => {
    try { const n = (Number(localStorage.getItem('plonk_guide_turn')) || 0) + 1; localStorage.setItem('plonk_guide_turn', String(n)); return n } catch { return Math.floor(Math.random() * 1000) }
  })
  const featured = topic === 'all' && !q.trim() && shown.length ? shown[turn % shown.length] : null
  const rest = featured ? shown.filter((g) => g !== featured) : shown

  return (
    <div className="page guides-page">
      <PageHeader title={t('guides.title')} />
      <section className="guides-hero">
        <p className="guides-intro">{t('guides.intro')}</p>
        <label className="guides-search">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" /><path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('guides.search')} aria-label={t('guides.search')} />
        </label>
        <div className="guides-topics" role="tablist">
          {['all', ...TOPICS].map((key) => (
            <button key={key} type="button" role="tab" aria-selected={topic === key}
              className={`guides-topic${topic === key ? ' is-on' : ''}`} onClick={() => setTopic(key)}>
              {key === 'all' ? t('guides.all') : t(`guides.topic_${key}`)}
            </button>
          ))}
        </div>
      </section>
      {items === null ? <RowSkeletons count={4} /> : (
        <>
          {featured && <div className="guides-featured"><GuideCard g={featured} big /></div>}
          {rest.length > 0 && <div className="guides-grid">{rest.map((g) => <GuideCard key={g.slug} g={g} />)}</div>}
          {shown.length === 0 && <p className="empty-hint guides-empty">{t('guides.empty')}</p>}
        </>
      )}
    </div>
  )
}

// Абзац «Проверено: …» в конце статьи — отдельная плашка: это источник и дата, а не часть рассказа.
const CHECKED = /^(Provereno|Проверено|Checked)\s*:/

export function GuideArticle() {
  const { slug } = useParams()
  const { t, i18n } = useTranslation()
  const [g, setG] = useState(null)
  const [missing, setMissing] = useState(false)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    setG(null); setMissing(false)
    api.guide(slug, i18n.language).then(setG).catch(() => setMissing(true))
  }, [slug, i18n.language])
  useEffect(() => { if (g) document.title = `${g.title} — PLONK` }, [g])

  const heads = useMemo(() => (g ? g.blocks.filter((b) => b.t === 'h2').map((b) => b.v) : []), [g])

  const share = async () => {
    const url = window.location.href
    try {
      if (navigator.share) { await navigator.share({ title: g.title, url }); return }
      await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 1800)
    } catch { /* закрыли окно «Поделиться» — ничего не делаем */ }
  }
  const jump = (i) => (e) => {
    e.preventDefault()
    document.getElementById(`s${i}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (missing) return <div className="page"><PageHeader title={t('guides.title')} /><p className="empty-hint">{t('guides.missing')}</p></div>
  let h = -1
  return (
    <div className="page guide-page">
      <PageHeader title={t('guides.title')} />
      {!g ? <RowSkeletons count={3} variant="plain" /> : (
        <article className="guide">
          <div className="guide-top">
            <span className={`guide-topic topic-${g.topic}`}>{t(`guides.topic_${g.topic}`)}</span>
            <span className="guide-meta">{t('guides.updated', { date: dateLabel(g.date, i18n.language) })}</span>
          </div>
          <h1 className="guide-title">{g.title}</h1>
          <p className="guide-lead">{g.lead}</p>
          <div className={`guide-hero topic-${g.topic}`}><img src={g.cover} alt="" /></div>

          {heads.length >= 3 && (
            <nav className="guide-toc" aria-label={t('guides.contents')}>
              <div className="guide-toc-title">{t('guides.contents')}</div>
              <ol>{heads.map((x, i) => <li key={x}><a href={`#s${i}`} onClick={jump(i)}>{x}</a></li>)}</ol>
            </nav>
          )}

          <div className="guide-body">
            {g.blocks.map((b, i) => {
              if (b.t === 'h2') { h += 1; return <h2 key={i} id={`s${h}`} className="guide-h2">{b.v}</h2> }
              if (b.t === 'p' && CHECKED.test(b.v)) {
                return (
                  <aside key={i} className="guide-note">
                    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="currentColor" opacity=".14" /><path d="m7.5 12.5 3 3 6-6.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    <p>{b.v}</p>
                  </aside>
                )
              }
              if (b.t === 'p') return <p key={i} className="guide-p">{b.v}</p>
              if (b.t === 'ul') return <ul key={i} className="guide-ul">{b.v.map((x) => <li key={x}>{x}</li>)}</ul>
              if (b.t === 'cta') {
                return (
                  <Link key={i} to={b.v[1]} className="guide-cta">
                    <span>{b.v[0]}</span>
                    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M5 12h13m-5-6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  </Link>
                )
              }
              return null
            })}
          </div>

          <div className="guide-actions">
            <button type="button" className="guide-share" onClick={share}>
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 3v12m0-12-4 4m4-4 4 4M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              {copied ? t('guides.copied') : t('guides.share')}
            </button>
            <Link to="/vodic" className="guide-all">{t('guides.back_all')}</Link>
          </div>

          {g.others?.length > 0 && (
            <section className="guide-more">
              <h2 className="guide-more-title">{t('guides.more')}</h2>
              <div className="guides-grid guides-grid--related">{g.others.map((o) => <GuideCard key={o.slug} g={o} />)}</div>
            </section>
          )}
        </article>
      )}
    </div>
  )
}
