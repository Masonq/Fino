import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { circlePolygon, createMap, osmLink, pinElement } from '../utils/maplibre'

// approximate=true — метка с размытыми координатами (продавец скрыл точный адрес): чуть дальше приближение и
// полупрозрачный круг вокруг, чтобы было видно «где-то здесь», а не «ровно тут». Сами координаты уже размыты на
// сервере (см. _fuzz_coord в listings.py), тут только подсказка, что это район, а не точка.
export default function LocationMap({ lat, lng, approximate = false, height = 200 }) {
  const { t } = useTranslation()
  const containerRef = useRef(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!containerRef.current || lat == null || lng == null) return undefined
    let map = null
    let ro = null
    let alive = true
    createMap(containerRef.current, { center: [lat, lng], zoom: approximate ? 13 : 15 }).then((made) => {
      if (!alive) { made?.map.remove(); return }
      if (!made) { setFailed(true); return }
      map = made.map
      if (approximate) {
        map.on('load', () => {
          map.addSource('area', { type: 'geojson', data: circlePolygon(lat, lng, 400) })
          map.addLayer({ id: 'area-fill', type: 'fill', source: 'area', paint: { 'fill-color': '#1F8F5F', 'fill-opacity': 0.12 } })
          map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': '#1F8F5F', 'line-width': 1 } })
        })
      } else {
        new made.maplibregl.Marker({ element: pinElement(), anchor: 'bottom' }).setLngLat([lng, lat]).addTo(map)
      }
      // Контейнер иногда получает окончательный размер позже (панель ещё раскрывается) — перерисовываем по факту
      ro = new ResizeObserver(() => map?.resize())
      ro.observe(containerRef.current)
    })
    return () => { alive = false; ro?.disconnect(); map?.remove() }
  }, [lat, lng, approximate])

  if (lat == null || lng == null) return null
  if (failed) {
    return (
      <a className="location-view-map map-fallback" style={{ height }} href={osmLink(lat, lng)} target="_blank" rel="noreferrer">
        {t('map.open_external')}
      </a>
    )
  }
  return <div ref={containerRef} className="location-view-map" style={{ height }} />
}
