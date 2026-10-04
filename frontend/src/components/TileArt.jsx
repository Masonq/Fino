import { useEffect, useState } from 'react'
import { artLayout } from '../utils/artFit'

// код раздела из адреса картинки (/cat/<код>.png) — по нему форма и заполненность из catArt.json
export const slugOf = (src) => (String(src).match(/\/cat\/([^/]+)\.png$/) || [])[1] || ''

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

/** Картинка плитки: размер — по её форме (artBox, как в приложении), прижата к правому нижнему углу. */
export default function TileArt({ src, name, fit, className = 'jl-tile-img' }) {
  const aspect = useAspect(src)
  const { box } = artLayout(name, fit, slugOf(src), aspect)
  return (
    <img className={className} src={src} alt="" loading="lazy"
      style={{ width: box.width, height: box.height, right: box.right, bottom: box.bottom }}
      onError={(e) => { e.currentTarget.style.display = 'none' }} />
  )
}
