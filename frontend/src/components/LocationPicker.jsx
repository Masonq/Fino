import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { createMap, pinElement } from '../utils/maplibre'

/**
 * Карта с одной перетаскиваемой меткой — куда поставили, туда и
 * запишется lat/lng. Тап по карте тоже переставляет метку: на телефоне
 * перетаскивание короткой пометки пальцем неудобнее одного тычка.
 * Плюс поиск по адресу (Nominatim — геокодер того же OpenStreetMap,
 * без ключей API) и кнопка «моё местоположение» (геолокация браузера) —
 * ставить метку тычками по карте на телефоне долго, если точка не
 * рядом с центром города по умолчанию.
 *
 * value — [lat, lng] или null (тогда метка не показана, только центр
 * по городу). onChange(lat, lng) зовётся при любом перемещении.
 */
export default function LocationPicker({ value, defaultCenter, onChange, height = 240 }) {
  const { t } = useTranslation()
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)
  const abortRef = useRef(null)
  const debounceRef = useRef(null)

  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [geoError, setGeoError] = useState('')
  const [locating, setLocating] = useState(false)

  const [mapFailed, setMapFailed] = useState(false)

  const showMarker = (lat, lng) => {
    markerRef.current.setLngLat([lng, lat])
    markerRef.current.getElement().style.opacity = '1'
  }

  const moveTo = (lat, lng, zoom = 16) => {
    onChange(lat, lng)
    if (!mapRef.current || !markerRef.current) return
    showMarker(lat, lng)
    mapRef.current.flyTo({ center: [lng, lat], zoom, speed: 1.6 })
  }

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return undefined
    let alive = true
    let ro = null
    const center = value || defaultCenter || [44.7866, 20.4489]
    createMap(containerRef.current, { center, zoom: value ? 15 : 12 }).then((made) => {
      if (!alive) { made?.map.remove(); return }
      if (!made) { setMapFailed(true); return }
      const { maplibregl, map } = made
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
      const marker = new maplibregl.Marker({ element: pinElement(), anchor: 'bottom', draggable: true })
        .setLngLat([center[1], center[0]])
        .addTo(map)
      marker.getElement().style.opacity = value ? '1' : '0'
      marker.on('dragend', () => {
        const p = marker.getLngLat()
        onChange(p.lat, p.lng)
      })
      // Тап по карте тоже переставляет метку: на телефоне перетаскивать маленькую метку пальцем неудобно
      map.on('click', (e) => {
        marker.setLngLat(e.lngLat)
        marker.getElement().style.opacity = '1'
        onChange(e.lngLat.lat, e.lngLat.lng)
      })
      mapRef.current = map
      markerRef.current = marker
      // Карта внутри раскрывающейся панели получает настоящий размер позже — перерисовываем по факту
      ro = new ResizeObserver(() => map.resize())
      ro.observe(containerRef.current)
    })
    return () => { alive = false; ro?.disconnect(); mapRef.current?.remove(); mapRef.current = null; markerRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Внешняя правка value (например восстановление черновика) —
  // подвигаем метку и карту следом, не только на клик/перетаскивание.
  useEffect(() => {
    if (!mapRef.current || !markerRef.current) return
    if (value) {
      showMarker(value[0], value[1])
      mapRef.current.jumpTo({ center: [value[1], value[0]] })
    }
  }, [value])

  // Поиск адреса — с задержкой и отменой предыдущего запроса: без
  // этого каждая напечатанная буква била бы по Nominatim отдельным
  // запросом, и медленный ответ на «Кне» мог прийти позже быстрого
  // на «Кнез Михайлова», подставив на экран не тот, более старый
  // результат.
  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (query.trim().length < 3) { setResults([]); return }
    debounceRef.current = setTimeout(async () => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      setSearching(true)
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&countrycodes=rs&addressdetails=0&limit=5&q=${encodeURIComponent(query)}`
        const res = await fetch(url, { signal: controller.signal })
        const data = await res.json()
        setResults(Array.isArray(data) ? data : [])
      } catch {
        // AbortError — отменили сами, следующий запрос уже в пути;
        // остальное — сервис недоступен, молча оставляем список пустым.
      } finally {
        setSearching(false)
      }
    }, 500)
    return () => clearTimeout(debounceRef.current)
  }, [query])

  const pickResult = (r) => {
    moveTo(parseFloat(r.lat), parseFloat(r.lon))
    setQuery('')
    setResults([])
  }

  const useMyLocation = () => {
    setGeoError('')
    if (!navigator.geolocation) {
      setGeoError(t('post.location_geo_unsupported'))
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        moveTo(pos.coords.latitude, pos.coords.longitude)
      },
      () => {
        setLocating(false)
        setGeoError(t('post.location_geo_denied'))
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  return (
    <div className="location-picker" data-lat={value?.[0] ?? ''} data-lng={value?.[1] ?? ''}>
      <div className="location-search-row">
        <input
          type="text"
          className="location-search-input"
          placeholder={t('post.location_search_placeholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="button"
          className="location-geo-btn"
          onClick={useMyLocation}
          disabled={locating}
          title={t('post.location_use_mine')}
        >
          {locating ? (
            <span className="location-geo-spinner" />
          ) : (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 11l18-8-8 18-2-8-8-2z" />
            </svg>
          )}
        </button>
      </div>
      {searching && <div className="location-search-hint">{t('post.location_searching')}</div>}
      {geoError && <div className="location-search-hint error">{geoError}</div>}
      {results.length > 0 && (
        <div className="location-search-results">
          {results.map((r) => (
            <button
              type="button"
              key={r.place_id}
              className="location-search-result"
              onClick={() => pickResult(r)}
            >
              {r.display_name}
            </button>
          ))}
        </div>
      )}
      {mapFailed
        ? <div className="location-picker-map map-fallback" style={{ height }}>{t('map.no_webgl')}</div>
        : <div ref={containerRef} className="location-picker-map" style={{ height }} />}
    </div>
  )
}
