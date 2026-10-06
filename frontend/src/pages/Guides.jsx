import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import { RowSkeletons } from '../components/Skeletons'

/** «Полезное» — статьи-путеводители: аренда без агента, продажа перед переездом, б/у мебель, безопасная покупка. */
export function GuidesList() {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState(null)
  useEffect(() => { api.guides(i18n.language).then((r) => setItems(r.items || [])).catch(() => setItems([])) }, [i18n.language])
  useEffect(() => { document.title = `${t('guides.title')} — PLONK` }, [t])
  return (
    <div className="page guides-page">
      <PageHeader title={t('guides.title')} />
      <p className="guides-intro">{t('guides.intro')}</p>
      {items === null ? <RowSkeletons count={4} /> : (
        <div className="guides-list">
          {items.map((g) => (
            <Link key={g.slug} to={`/vodic/${g.slug}`} className="guide-card">
              <span className="guide-card-art"><img src={g.cover} alt="" loading="lazy" /></span>
              <span className="guide-card-text">
                <span className="guide-card-title">{g.title}</span>
                <span className="guide-card-lead">{g.lead}</span>
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export function GuideArticle() {
  const { slug } = useParams()
  const { t, i18n } = useTranslation()
  const [g, setG] = useState(null)
  const [missing, setMissing] = useState(false)
  useEffect(() => {
    setG(null); setMissing(false)
    api.guide(slug, i18n.language).then(setG).catch(() => setMissing(true))
  }, [slug, i18n.language])
  useEffect(() => { if (g) document.title = `${g.title} — PLONK` }, [g])
  if (missing) return <div className="page"><PageHeader title={t('guides.title')} /><p className="empty-hint">{t('guides.missing')}</p></div>
  return (
    <div className="page guide-page">
      <PageHeader title={t('guides.title')} />
      {!g ? <RowSkeletons count={3} variant="plain" /> : (
        <article className="guide">
          <div className="guide-hero"><img src={g.cover} alt="" /></div>
          <h1 className="guide-title">{g.title}</h1>
          <p className="guide-lead">{g.lead}</p>
          {g.blocks.map((b, i) => {
            if (b.t === 'h2') return <h2 key={i} className="guide-h2">{b.v}</h2>
            if (b.t === 'p') return <p key={i} className="guide-p">{b.v}</p>
            if (b.t === 'ul') return <ul key={i} className="guide-ul">{b.v.map((x) => <li key={x}>{x}</li>)}</ul>
            if (b.t === 'cta') return <Link key={i} to={b.v[1]} className="guide-cta">{b.v[0]} →</Link>
            return null
          })}
          {g.others?.length > 0 && (
            <div className="guide-more">
              <div className="guide-more-title">{t('guides.more')}</div>
              {g.others.map((o) => <Link key={o.slug} to={`/vodic/${o.slug}`} className="guide-more-link">{o.title}</Link>)}
            </div>
          )}
        </article>
      )}
    </div>
  )
}
