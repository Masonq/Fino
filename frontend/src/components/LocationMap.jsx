import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const pinIcon = L.divIcon({
  className: 'map-pin-icon',
  html: '<svg viewBox="0 0 24 24" width="34" height="34"><path fill="#1F8F5F" stroke="#fff" stroke-width="1.5" d="M12 2C7.5 2 4 5.5 4 10c0 6 8 12 8 12s8-6 8-12c0-4.5-3.5-8-8-8z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>',
  iconSize: [34, 34],
  iconAnchor: [17, 34],
})

// approximate=true — метка с размытыми координатами (продавец скрыл
// точный адрес): чуть больше приближение и полупрозрачный круг вокруг,
// чтобы было видно «где-то здесь», а не «ровно тут» — сами координаты
// уже размыты на сервере (см. _fuzz_coord в listings.py), тут только
// визуальная подсказка, что это не точка, а район.
export default function LocationMap({ lat, lng, approximate = false, height = 200 }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || lat == null || lng == null) return
    const map = L.map(containerRef.current, {
      center: [lat, lng], zoom: approximate ? 13 : 15,
      attributionControl: false, zoomControl: false, dragging: true,
      scrollWheelZoom: false,
    })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map)

    if (approximate) {
      L.circle([lat, lng], { radius: 400, color: '#1F8F5F', fillOpacity: 0.12, weight: 1 }).addTo(map)
    } else {
      L.marker([lat, lng], { icon: pinIcon }).addTo(map)
    }

    setTimeout(() => map.invalidateSize(), 80)
    return () => map.remove()
  }, [lat, lng, approximate])

  if (lat == null || lng == null) return null
  return <div ref={containerRef} className="location-view-map" style={{ height }} />
}
