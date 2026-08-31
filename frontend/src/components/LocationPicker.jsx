import { useEffect, useRef } from 'react'
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
 *
 * value — [lat, lng] или null (тогда метка не показана, только центр
 * по городу). onChange(lat, lng) зовётся при любом перемещении.
 */
export default function LocationPicker({ value, defaultCenter, onChange, height = 240 }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)

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

  return <div ref={containerRef} className="location-picker-map" style={{ height }} />
}
