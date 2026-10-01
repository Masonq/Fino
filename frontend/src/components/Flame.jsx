import PriceGauge from './PriceGauge'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

/*
 * Огонёк рядом с ценой: «цена заметно ниже». По нажатию — пояснение, что
 * это и почему он тут стоит.
 *
 * Пламя живёт снизу вверх: основание стоит на месте, а острие и язычок
 * плавно меняют положение между тремя позами (SMIL, морфинг пути — общая
 * структура пути одинакова во всех позах). Прошлая версия качала весь
 * значок целиком, и он выглядел как ветка на ветру.
 *
 * Размер задан в em от шрифта цены: не больше и не меньше самой цены.
 */
const OUTER = [
  'M8 21.2 C4.2 21.2 1.5 18.4 1.5 14.6 C1.5 11.6 3.2 9.8 4.6 7.6 C5.2 8.8 9.3 9.6 6.8 9.6 C6.6 6.4 7.4 3.2 9.0 0.9 C9.8 4.4 12.0 6.6 13.0 10.0 C14.2 13.4 14.6 15.4 14.0 16.4 C13.0 19.6 10.9 21.2 8 21.2Z',
  'M8 21.2 C4.2 21.2 1.5 18.4 1.5 14.6 C1.5 11.6 2.8 9.8 4.2 7.6 C4.8 8.8 9.1 9.6 6.3 10.6 C6.1 6.4 5.9 3.2 7.5 2.3 C8.3 4.4 12.6 6.6 13.6 10.0 C14.5 13.4 14.9 15.4 14.3 16.4 C13.3 19.6 10.9 21.2 8 21.2Z',
  'M8 21.2 C4.2 21.2 1.5 18.4 1.5 14.6 C1.5 11.6 3.5 9.8 4.9 7.6 C5.5 8.8 9.6 9.6 7.3 9.0 C7.1 6.4 8.4 3.2 10.0 0.2 C10.8 4.4 11.7 6.6 12.7 10.0 C14.0 13.4 14.4 15.4 13.8 16.4 C12.8 19.6 10.9 21.2 8 21.2Z',
  'M8 21.2 C4.2 21.2 1.5 18.4 1.5 14.6 C1.5 11.6 3.0 9.8 4.4 7.6 C5.0 8.8 9.2 9.6 6.6 10.2 C6.4 6.4 6.6 3.2 8.2 1.6 C9.0 4.4 12.2 6.6 13.2 10.0 C14.3 13.4 14.7 15.4 14.1 16.4 C13.1 19.6 10.9 21.2 8 21.2Z',
  'M8 21.2 C4.2 21.2 1.5 18.4 1.5 14.6 C1.5 11.6 3.2 9.8 4.6 7.6 C5.2 8.8 9.3 9.6 6.8 9.6 C6.6 6.4 7.4 3.2 9.0 0.9 C9.8 4.4 12.0 6.6 13.0 10.0 C14.2 13.4 14.6 15.4 14.0 16.4 C13.0 19.6 10.9 21.2 8 21.2Z'
]
const INNER = [
  'M8 20.8 C5.9 20.8 5.0 19.2 5.0 17.4 C5.0 15.0 7.0 14.0 8.0 11.2 C9.0 14.0 11.0 15.0 11.0 17.4 C11.0 19.2 10.1 20.8 8 20.8Z',
  'M8 20.8 C5.9 20.8 5.0 19.2 5.0 17.4 C5.0 15.0 7.0 14.0 7.5 12.2 C8.5 14.0 11.0 15.0 11.0 17.4 C11.0 19.2 10.1 20.8 8 20.8Z',
  'M8 20.8 C5.9 20.8 5.0 19.2 5.0 17.4 C5.0 15.0 7.0 14.0 8.5 10.6 C9.5 14.0 11.0 15.0 11.0 17.4 C11.0 19.2 10.1 20.8 8 20.8Z',
  'M8 20.8 C5.9 20.8 5.0 19.2 5.0 17.4 C5.0 15.0 7.0 14.0 7.9 11.8 C8.9 14.0 11.0 15.0 11.0 17.4 C11.0 19.2 10.1 20.8 8 20.8Z',
  'M8 20.8 C5.9 20.8 5.0 19.2 5.0 17.4 C5.0 15.0 7.0 14.0 8.0 11.2 C9.0 14.0 11.0 15.0 11.0 17.4 C11.0 19.2 10.1 20.8 8 20.8Z'
]
const SPLINES = Array(4).fill('.45 0 .55 1').join(';')
const KEYS = '0;.25;.5;.75;1'

function delayFor(id) {
  let h = 0
  const s = String(id)
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return -((h % 16) / 10)            // фаза своя у каждой карточки: огоньки не мигают хором
}

function reducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function FlameSvg({ id }) {
  const still = reducedMotion()
  const begin = `${delayFor(id)}s`
  const anim = (values, dur) => (still ? null : (
    <animate attributeName="d" dur={dur} begin={begin} repeatCount="indefinite"
      calcMode="spline" keyTimes={KEYS} keySplines={SPLINES} values={values.join(';')} />
  ))
  return (
    <svg className="flame-svg" viewBox="0 0 16 22" aria-hidden="true" focusable="false">
      <path fill="#F0432A" d={OUTER[0]}>{anim(OUTER, '1.7s')}</path>
      <path fill="#FFB020" d={INNER[0]}>{anim(INNER, '1.2s')}</path>
    </svg>
  )
}

export default function PriceFlame({ listing }) {
  const { t, i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const [check, setCheck] = useState(null)
  const kind = 'below'      // вид метки один: «дешевле похожих на PLONK»

  // Подробности (с чем сравнивали) подгружаем при открытии, а не
  // для каждой карточки ленты: их нужно только тому, кто нажал.
  useEffect(() => {
    if (!open || check) return undefined
    let alive = true
    api.priceCheck(listing.id, i18n.language)
      .then((res) => { if (alive) setCheck(res || {}) })
      .catch(() => { if (alive) setCheck({}) })
    return () => { alive = false }
  }, [open, check, listing.id, i18n.language])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const stop = (e) => { e.preventDefault(); e.stopPropagation() }

  return (
    <>
      <button
        type="button" className="flame-btn" aria-label={t(`flame.title_${kind}`)}
        aria-haspopup="dialog" onClick={(e) => { stop(e); setOpen(true) }}
      >
        <FlameSvg id={listing.id} />
      </button>

      {open && createPortal(
        <div className="reasons-sheet" onClick={(e) => { stop(e); setOpen(false) }}>
          <div className="reasons-card flame-sheet" role="dialog" aria-modal="true"
            aria-label={t(`flame.title_${kind}`)} onClick={(e) => e.stopPropagation()}>
            <div className="flame-sheet-head">
              <span className="flame-sheet-icon"><FlameSvg id={listing.id} /></span>
              <div className="reasons-title flame-sheet-title">{t(`flame.title_${kind}`)}</div>
            </div>
            {/* Пока числа грузятся — место под шкалу держим, чтобы окно не подрастало */}
            {check
              ? <PriceGauge mine={check.mine_eur} low={check.low_eur} high={check.high_eur} label={t(`flame.title_${kind}`)} />
              : <div className="pg pg-ph" aria-hidden="true" />}
            <p className="price-check-explain">{t(`flame.why_${kind}`)}</p>
            {check?.based_on > 0 && (
              <p className="price-check-explain">{t('flame.compared', { count: check.based_on })}</p>
            )}
            <p className="price-check-explain flame-careful">{t('flame.careful')}</p>
            <Link to={listing.path} className="flame-sheet-link" onClick={() => setOpen(false)}>
              {t('flame.open')}
            </Link>
            <button className="reasons-cancel" onClick={() => setOpen(false)}>
              {t('flame.ok')}
            </button>
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}
