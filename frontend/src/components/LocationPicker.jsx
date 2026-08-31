import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Стандартная иконка Leaflet ссылается на файлы через require, которых
// нет при сборке через Vite — без этого маркер был бы невидимым битым
// значком. Рисуем свою: простая капля, ничего не тащим лишнего.
const pinIcon = L.divIcon({
  className: 'map-pin-icon',
  html: '<svg viewBox="0 0 24 24" width="34" height="34"><path fill="#1F8F5F" stroke="#fff" stroke-width="1.5" d="M12 2C7.5 2 4 5.5 4 10c0 6 8 12 8 12s8-6 8-12c0-4.5-3.5-8-8-8z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>',
  iconSize: [34, 34],
  iconAnchor: [17, 34],
})

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

  const moveTo = (lat, lng, zoom = 16) => {
    if (!mapRef.current || !markerRef.current) return
    markerRef.current.setLatLng([lat, lng])
    markerRef.current.setOpacity(1)
    mapRef.current.setView([lat, lng], zoom)
    onChange(lat, lng)
  }

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const center = value || defaultCenter || [44.7866, 20.4489]
    const map = L.map(containerRef.current, {
      center, zoom: value ? 15 : 12, attributionControl: false, zoomControl: true,
    })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map)

    const marker = L.marker(center, { icon: pinIcon, draggable: true, opacity: value ? 1 : 0 })
      .addTo(map)
    marker.on('dragend', () => {
      const p = marker.getLatLng()
      onChange(p.lat, p.lng)
    })
    map.on('click', (e) => {
      marker.setLatLng(e.latlng)
      marker.setOpacity(1)
      onChange(e.latlng.lat, e.latlng.lng)
    })

    mapRef.current = map
    markerRef.current = marker

    // Тайлы иногда домеряются с опозданием — контейнер внутри
    // раскрывающейся панели получает реальный размер только после
    // того, как сама панель успела развернуться.
    setTimeout(() => map.invalidateSize(), 80)

    return () => { map.remove(); mapRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Внешняя правка value (например восстановление черновика) —
  // подвигаем метку и карту следом, не только на клик/перетаскивание.
  useEffect(() => {
    if (!mapRef.current || !markerRef.current) return
    if (value) {
      markerRef.current.setLatLng(value)
      markerRef.current.setOpacity(1)
      mapRef.current.setView(value, mapRef.current.getZoom())
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
    <div className="location-picker">
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
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" strokeLinecap="round" />
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
      <div ref={containerRef} className="location-picker-map" style={{ height }} />
    </div>
  )
}
