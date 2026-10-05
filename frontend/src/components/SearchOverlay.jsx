import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { hasLanding } from '../data/landings'
import ListingCard from './ListingCard'

const RECENT_KEY = 'plonk_recent_searches'
const RECENT_MAX = 6

function readRecent() {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
    return Array.isArray(raw) ? raw.slice(0, RECENT_MAX) : []
  } catch { return [] }
}

function saveRecent(q) {
  try {
    const next = [q, ...readRecent().filter((v) => v !== q)].slice(0, RECENT_MAX)
    localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  } catch { /* приватный режим — обойдёмся без истории */ }
}

function clearRecent() {
  try { localStorage.removeItem(RECENT_KEY) } catch { /* см. выше */ }
}

export default function SearchOverlay({ open, onClose }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const [text, setText] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [recent, setRecent] = useState([])
  const [categories, setCategories] = useState([])
  const [popular, setPopular] = useState([])
  // подсказки на лету: исправление опечатки, продолжения запроса, разделы
  const [sug, setSug] = useState(null)

  // Фокус ставится сразу при открытии — мы остаёмся на той же странице,
  // поэтому iOS считает это продолжением жеста и показывает клавиатуру.
  useEffect(() => {
    if (open) {
      inputRef.current?.focus()
      setRecent(readRecent())
      api.searchPopular(i18n.language).then((r) => setPopular((r.items || []).slice(0, 8))).catch(() => {})
      if (!categories.length) {
        api.getCategories().then((res) => setCategories(res || [])).catch(() => {})
      }
    } else { setText(''); setItems([]); setSug(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (!open || !text.trim()) { setItems([]); return }
    setLoading(true)
    const id = setTimeout(() => {
      api.searchListings({ q: text.trim(), lang: i18n.language, limit: 20 })
        .then((res) => setItems(res.items || []))
        .catch(() => setItems([]))
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(id)
  }, [text, open, i18n.language])

  useEffect(() => {
    const q = text.trim()
    if (!open || q.length < 2) { setSug(null); return undefined }
    const id = setTimeout(() => { api.searchSuggest(q, i18n.language).then(setSug).catch(() => setSug(null)) }, 180)
    return () => clearTimeout(id)
  }, [text, open, i18n.language])

  const submit = (value = text) => {
    const q = value.trim()
    if (!q) return
    saveRecent(q)
    onClose()
    navigate(`/search?q=${encodeURIComponent(q)}`)
  }

  if (!open) return null

  return (
    <div className="search-overlay">
      <div className="search-topbar">
        <button className="search-back" onClick={onClose} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="search-field">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            ref={inputRef}
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
            placeholder={t('search.placeholder_full')}
            autoComplete="off"
            enterKeyHint="search"
          />
          {text && (
            <button className="search-clear" onClick={() => { setText(''); inputRef.current?.focus() }} aria-label={t('actions.clear')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
      </div>

      <div className="search-suggest">
        {/* Пустой запрос раньше показывал пустой экран — человек открывал
            поиск и упирался в белое поле. Показываем то, с чего можно
            начать: свои прошлые запросы и категории. */}
        {!text.trim() && (
          <>
            {recent.length > 0 && (
              <div className="suggest-block">
                <div className="suggest-head">
                  <span>{t('search.recent')}</span>
                  <button onClick={() => { clearRecent(); setRecent([]) }}>{t('actions.clear')}</button>
                </div>
                {recent.map((q) => (
                  <button key={q} className="recent-row" onClick={() => submit(q)}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
                    </svg>
                    {q}
                  </button>
                ))}
              </div>
            )}

            {popular.length > 0 && (
              <div className="suggest-block">
                <div className="suggest-head"><span>{t('search.popular')}</span></div>
                <div className="suggest-cats">
                  {popular.filter((q) => !recent.includes(q)).map((q) => (
                    <button key={q} type="button" className="suggest-cat" onClick={() => submit(q)}>{q}</button>
                  ))}
                </div>
              </div>
            )}

            {categories.length > 0 && (
              <div className="suggest-block">
                <div className="suggest-head"><span>{t('common.all_categories')}</span></div>
                <div className="suggest-cats">
                  {categories.map((c) => (
                    <button
                      key={c.id}
                      className="suggest-cat"
                      onClick={() => {
                        onClose()
                        navigate(hasLanding(c.slug) ? `/c/${c.slug}` : `/search?category=${c.slug}`)
                      }}
                    >
                      {c.name?.[i18n.language] || c.name?.ru}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* подсказки на лету: «возможно, вы искали» (опечатка), продолжения запроса и разделы */}
        {text.trim().length >= 2 && sug && (sug.fix || sug.completions?.length > 0 || sug.categories?.length > 0) && (
          <div className="suggest-block live-suggest">
            {sug.fix && (
              <button type="button" className="ls-row ls-fix" onClick={() => setText(sug.fix)}>
                <span className="ls-ico">✎</span>
                <span>{t('search.did_you_mean')} <b>{sug.fix}</b></span>
              </button>
            )}
            {(sug.completions || []).slice(0, 4).map((c) => {
              const typed = text.trim().toLowerCase()
              const rest = c.toLowerCase().startsWith(typed) ? c.slice(typed.length) : c
              return (
                <button key={c} type="button" className="ls-row" onClick={() => submit(c)}>
                  <svg className="ls-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
                  <span>{c.toLowerCase().startsWith(typed) ? <>{text.trim()}<b>{rest}</b></> : c}</span>
                  <span className="ls-fill" role="button" tabIndex={-1} aria-label={t('search.fill')} onClick={(e) => { e.stopPropagation(); setText(`${c} `); inputRef.current?.focus() }}>↖</span>
                </button>
              )
            })}
            {(sug.categories || []).slice(0, 3).map((c) => (
              <button key={c.slug} type="button" className="ls-row ls-cat" onClick={() => { const q = text.trim(); saveRecent(q); onClose(); navigate(`/search?q=${encodeURIComponent(q)}&category=${c.slug}`) }}>
                <svg className="ls-ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="4" width="7" height="7" rx="2" /><rect x="13" y="4" width="7" height="7" rx="2" /><rect x="4" y="13" width="7" height="7" rx="2" /><rect x="13" y="13" width="7" height="7" rx="2" /></svg>
                <span><b>{text.trim()}</b> {t('search.in_section')} <span className="ls-path">{c.name}</span></span>
              </button>
            ))}
          </div>
        )}

        {loading && <p className="empty-hint">{t('search.searching')}</p>}

        {!loading && text.trim() && items.length === 0 && (
          <p className="empty-hint">{t('search.nothing')}</p>
        )}

        {/* Раньше здесь был список строчками, а привычные карточки
            появлялись только после «Показать ещё» — то есть нормальный
            поиск начинался со второго шага. Показываем их сразу. */}
        {items.length > 0 && (
          <>
            <div className="results-head">
              <span className="results-count">{`${t('search.found')}: ${items.length}`}</span>
            </div>
            <div className="infinite-grid no-pad">
              {items.map((l) => <ListingCard key={l.id} listing={l} />)}
            </div>
            <button className="suggest-all" onClick={() => submit()}>
              {t('search.open_filters')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
