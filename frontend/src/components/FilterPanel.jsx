import { intlLocale } from '../utils/time'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { CITIES, cityLabel } from '../data/cities'
import useScrollFade from '../hooks/useScrollFade'

/*
 * Живая панель фильтров.
 *
 * Раньше: тап на поиск, отдельный экран, отдельная панель фильтров,
 * страница результатов — и узнать, сколько всего найдётся, можно было
 * только дойдя до конца. Здесь всё на одном месте, а число «Показать N
 * объявлений» пересчитывается, пока двигаешь ползунок. Не нашлось
 * ничего — видно сразу, до перехода.
 *
 * Цена — один ползунок «до», а не два поля «от / до»: на телефоне
 * набирать цифры дольше, чем двигать палец, а нижняя граница нужна
 * редко. Ступени неравномерные: от 25 до 10 000 — иначе на одной шкале
 * не уместить ни табурет, ни машину.
 */
const STEPS = [25, 50, 100, 200, 300, 500, 750, 1000, 2000, 3000, 5000, 10000, null]
const LAST = STEPS.length - 1

export default function FilterPanel({ open, onClose, city, onCity }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [categories, setCategories] = useState([])
  const [category, setCategory] = useState('')
  const [step, setStep] = useState(LAST)
  const [count, setCount] = useState(null)
  const [serial, setSerial] = useState(0)         // меняется с числом — перезапускает размытие
  const chipsRef = useScrollFade()
  const ticket = useRef(0)                          // отбрасывает ответы, пришедшие позже более свежего запроса

  const priceMax = STEPS[step]

  useEffect(() => {
    if (!open || categories.length) return
    api.getCategories().then(setCategories).catch(() => {})
  }, [open, categories.length])

  // Живой счётчик. Запрос — «дай один результат»: нужен только total.
  // Ждём четверть секунды после последнего движения, иначе ползунок
  // засыпал бы сервер десятком запросов в секунду.
  useEffect(() => {
    if (!open) return undefined
    const mine = ++ticket.current
    const timer = setTimeout(() => {
      api.searchListings({
        lang: i18n.language, limit: 1, offset: 0,
        category_slug: category || undefined,
        city: city || undefined,
        price_max: priceMax || undefined,
      })
        .then((res) => {
          if (mine !== ticket.current) return
          setCount(res.total ?? 0)
          setSerial((n) => n + 1)
        })
        .catch(() => { if (mine === ticket.current) setCount(null) })
    }, 250)
    return () => clearTimeout(timer)
  }, [open, category, city, priceMax, i18n.language])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const go = () => {
    const q = new URLSearchParams()
    if (category) q.set('category', category)
    if (city) q.set('city', city)
    if (priceMax) q.set('price_max', String(priceMax))
    onClose()
    navigate(`/search${q.toString() ? `?${q}` : ''}`)
  }

  const reset = () => { setCategory(''); setStep(LAST); onCity('') }
  const dirty = category || city || step !== LAST

  return (
    <div className={`fp ${open ? 'is-open' : ''}`} aria-hidden={!open}>
      <div className="fp-backdrop" onClick={onClose} />
      <div className="fp-panel" role="dialog" aria-label={t('fpanel.title')}>
        <div className="fp-head">
          <span className="fp-title">{t('fpanel.title')}</span>
          {dirty && <button className="fp-reset" onClick={reset}>{t('fpanel.reset')}</button>}
          <button className="fp-close" onClick={onClose} aria-label={t('actions.close')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </div>

        <div className="fp-block">
          <span className="fp-label">{t('fpanel.section')}</span>
          <div className="fp-chips" ref={chipsRef}>
            <button className={`fp-chip ${category === '' ? 'on' : ''}`} onClick={() => setCategory('')}>
              {t('fpanel.all_sections')}
            </button>
            {categories.map((c) => (
              <button key={c.id} className={`fp-chip ${category === c.slug ? 'on' : ''}`} onClick={() => setCategory(c.slug)}>
                {c.name?.[i18n.language] || c.name?.ru}
              </button>
            ))}
          </div>
        </div>

        <div className="fp-block">
          <span className="fp-label">{t('fpanel.city')}</span>
          <label className="fp-select">
            <select value={city} onChange={(e) => onCity(e.target.value)}>
              <option value="">{t('search.all_cities')}</option>
              {CITIES.map((c) => <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>)}
            </select>
          </label>
        </div>

        <div className="fp-block">
          <div className="fp-row">
            <span className="fp-label">{t('fpanel.price')}</span>
            <span className="fp-value">
              {priceMax ? `${t('fpanel.up_to')} ${priceMax.toLocaleString(intlLocale(i18n.language))} €` : t('fpanel.any_price')}
            </span>
          </div>
          <input
            className="fp-range" type="range" min="0" max={LAST} step="1" value={step}
            aria-label={t('fpanel.price')}
            onChange={(e) => setStep(Number(e.target.value))}
          />
        </div>

        <button className="fp-go" onClick={go}>
          <span key={serial} className="fp-go-text">
            {count === null ? t('fpanel.show') : t('landing.show_count', { count })}
          </span>
        </button>
      </div>
    </div>
  )
}
