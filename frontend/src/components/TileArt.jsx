import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { artBoxFor, resetTileMeasure, tileMeasure } from '../utils/artFit'

// код раздела из адреса картинки (/cat/<код>.png) — по нему форма и заполненность из catArt.json
export const slugOf = (src) => (String(src).match(/\/cat\/([^/?]+)\.png/) || [])[1] || ''

// форма картинки (ширина / высота) — один раз на адрес, дальше из памяти
const aspects = new Map()
export function useAspect(src) {
  const [aspect, setAspect] = useState(() => aspects.get(src) || 1.3)
  useEffect(() => {
    if (aspects.has(src)) { setAspect(aspects.get(src)); return undefined }
    const im = new Image()
    let alive = true
    im.onload = () => { if (im.naturalWidth && im.naturalHeight) { const a = im.naturalWidth / im.naturalHeight; aspects.set(src, a); if (alive) setAspect(a) } }
    im.src = src
    return () => { alive = false }
  }, [src])
  return aspect
}

/**
 * Настоящие строки надписи плитки: правый край и низ каждой — внутри рамки плитки. Надпись — соседний элемент
 * (selector) в той же плитке, что и ref. Оценка по самому широкому шрифту в разы осторожнее настоящего текста
 * («Периферия для компьютера» считалась в три строки, а выходит в две) — картинка из-за неё была мельче, чем можно.
 * Пересчёт — после отрисовки, после загрузки шрифтов и при смене ширины плитки.
 */
export function useTextLines(ref, selector, deps) {
  const [lines, setLines] = useState(null)
  useLayoutEffect(() => {
    const el = ref.current
    const tile = el?.parentElement?.closest('.jl-tile, .cat-tile-2row') || el?.parentElement
    const text = tile?.querySelector(selector)
    if (!tile || !text) return undefined
    let alive = true
    const measure = () => {
      if (!alive || !text.firstChild) return
      const tr = tile.getBoundingClientRect()
      const ox = tr.left + tile.clientLeft, oy = tr.top + tile.clientTop
      const range = document.createRange()
      range.selectNodeContents(text)
      const rows = []
      for (const r of range.getClientRects()) {
        if (!r.width) continue
        const row = rows.find((x) => Math.abs(x.top - r.top) < 4)
        if (row) { row.right = Math.max(row.right, r.right); row.bottom = Math.max(row.bottom, r.bottom) } else rows.push({ top: r.top, right: r.right, bottom: r.bottom })
      }
      const next = rows.sort((a, b) => a.top - b.top).map((x) => ({ right: Math.ceil(x.right - ox), bottom: Math.ceil(x.bottom - oy) }))
      setLines((prev) => (prev && JSON.stringify(prev) === JSON.stringify(next) ? prev : next.length ? next : null))
    }
    measure()
    document.fonts?.ready?.then(measure)
    const ro = new ResizeObserver(measure)
    ro.observe(text)
    return () => { alive = false; ro.disconnect() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return lines
}

/** Замер надписей плиток; после загрузки шрифтов — заново (до неё браузер мерил запасным шрифтом). */
let fontsSeen = false
export function useTileMeasure() {
  const [, bump] = useState(0)
  useEffect(() => {
    if (fontsSeen || !document.fonts?.ready) return undefined
    let alive = true
    document.fonts.ready.then(() => { fontsSeen = true; resetTileMeasure(); if (alive) bump((n) => n + 1) })
    return () => { alive = false }
  }, [])
  return tileMeasure()
}

/** Картинка плитки: размер — по её форме и по настоящим строкам надписи, прижата к правому нижнему углу. */
export default function TileArt({ src, name, fit, className = 'jl-tile-img' }) {
  const aspect = useAspect(src)
  const ref = useRef(null)
  const measure = useTileMeasure()
  const lines = useTextLines(ref, '.jl-tile-text', [name, fit.text, fit.tile])
  const box = artBoxFor(name, fit, slugOf(src), measure, lines, aspect)
  return (
    <img ref={ref} className={className} src={src} alt="" loading="lazy"
      style={{ width: box.width, height: box.height, right: box.right, bottom: box.bottom }}
      onError={(e) => { e.currentTarget.style.display = 'none' }} />
  )
}
