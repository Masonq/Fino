/**
 * «Мой год на PLONK» — итог года, как Spotify Wrapped: крупные цифры на цветных плитках (выложил, продал,
 * заработал, смотрели, сохранили, любимый раздел, самое популярное объявление) и «Поделиться» — готовая картинка
 * 1080×1350, нарисованная прямо в браузере, для сторис и постов.
 */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import { api } from '../api/client'

const nf = (n) => Math.round(n || 0).toLocaleString('ru-RU').replace(/\u00a0/g, ' ')

function drawCard(d, t) {
  const c = document.createElement('canvas')
  c.width = 1080; c.height = 1350
  const g = c.getContext('2d')
  const bg = g.createLinearGradient(0, 0, 1080, 1350)
  bg.addColorStop(0, '#CDEFE0'); bg.addColorStop(1, '#ECF4CE')
  g.fillStyle = bg; g.fillRect(0, 0, 1080, 1350)
  g.fillStyle = '#0F1512'
  g.font = '800 64px Onest, system-ui, sans-serif'; g.fillText(t('year.share_title', { year: d.year }), 80, 150)
  const tiles = [[nf(d.posted), t('year.posted')], [nf(d.sold), t('year.sold')], [`€${nf(d.earned_eur)}`, t('year.earned')], [nf(d.views), t('year.views')]]
  tiles.forEach(([v, l], i) => {
    const x = 80 + (i % 2) * 470, y = 230 + Math.floor(i / 2) * 330
    g.fillStyle = 'rgba(255,255,255,.75)'; g.beginPath(); g.roundRect(x, y, 450, 300, 40); g.fill()
    g.fillStyle = '#0F1512'; g.font = '900 110px Onest, system-ui, sans-serif'; g.fillText(v, x + 40, y + 160)
    g.fillStyle = '#434B46'; g.font = '700 40px Onest, system-ui, sans-serif'; g.fillText(l, x + 40, y + 235)
  })
  if (d.top_category) { g.fillStyle = '#0F1512'; g.font = '700 44px Onest, system-ui, sans-serif'; g.fillText(`${t('year.top_category')}: ${d.top_category}`, 80, 1000) }
  g.fillStyle = '#085041'; g.font = '900 56px Onest, system-ui, sans-serif'; g.fillText('PLONK', 80, 1250)
  g.fillStyle = '#434B46'; g.font = '700 40px Onest, system-ui, sans-serif'; g.fillText('plonk.rs', 300, 1250)
  return new Promise((res) => c.toBlob(res, 'image/png'))
}

export default function MyYear() {
  const { t, i18n } = useTranslation()
  const [d, setD] = useState(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => { api.myYear(i18n.language).then(setD).catch(() => setFailed(true)) }, [i18n.language])

  const share = async () => {
    const blob = await drawCard(d, t)
    const file = new File([blob], `plonk-${d.year}.png`, { type: 'image/png' })
    try {
      if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], text: t('year.share_text', { year: d.year }) + ' https://plonk.rs' }); return }
    } catch { return }
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = file.name; a.click()
  }

  const tiles = d ? [
    { v: nf(d.posted), l: t('year.posted'), bg: '#E3ECFA' },
    { v: nf(d.sold), l: t('year.sold'), bg: '#E2F1E6' },
    { v: `€${nf(d.earned_eur)}`, l: t('year.earned'), bg: '#FFF1C9' },
    { v: nf(d.views), l: t('year.views'), bg: '#EDE7FA' },
    { v: nf(d.saves), l: t('year.saves'), bg: '#FAE5EE' },
  ].filter((x, i) => i === 0 || (i === 1 ? d.sold : i === 2 ? d.earned_eur : i === 3 ? d.views : d.saves) > 0) : []   // нули не показываем — итог про то, что было

  return (
    <div className="page year-page">
      <PageHeader title={t('year.title', { year: d?.year || new Date().getFullYear() })} kicker={t('year.kicker')} />
      {failed && <p className="empty-hint">{t('support.failed')}</p>}
      {!d && !failed && <div className="year-grid">{[0, 1, 2, 3].map((i) => <div key={i} className="year-tile sk-block" />)}</div>}
      {d && (
        <>
          <div className="year-hero">
            <span>{t('year.hero_kicker')}</span>
            <b>{d.sold > 0 ? t('year.hero_sold', { n: d.sold }) : d.posted > 0 ? t('year.hero_posted', { n: d.posted }) : t('year.hero_start')}</b>
          </div>
          <div className="year-grid">
            {tiles.map((x) => (
              <div key={x.l} className="year-tile" style={{ background: x.bg }}><b>{x.v}</b><span>{x.l}</span></div>
            ))}
          </div>
          {d.top_category && <div className="year-row"><span>{t('year.top_category')}</span><b>{d.top_category}</b></div>}
          {d.top_listing && (
            <Link to={`/go/${d.top_listing.id}`} className="year-row is-link">
              <span>{t('year.top_listing')}</span><b>{d.top_listing.title || '—'}</b><i>{t('year.top_views', { n: d.top_listing.views })}</i>
            </Link>
          )}
          <button type="button" className="year-share" onClick={share}>{t('year.share')}</button>
        </>
      )}
    </div>
  )
}
