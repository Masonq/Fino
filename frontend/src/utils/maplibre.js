/*
 * Карта на MapLibre GL с векторными плитками OpenFreeMap.
 *
 * Раньше Leaflet брал плитки прямо с tile.openstreetmap.org. Правила OSM прямо запрещают тяжёлое использование их
 * серверов (рабочий коммерческий сайт с картой туда относится) и разрешают блокировать без предупреждения — карта
 * однажды стала бы пустой. OpenFreeMap — бесплатно, без ключей, регистрации и cookies, векторные плитки под
 * MapLibre. Подпись источника (© OpenMapTiles, © OpenStreetMap) MapLibre ставит сам — лицензия OSM её требует,
 * а раньше она была отключена.
 *
 * MapLibre тяжёлый, поэтому грузится отдельным куском и только там, где карта на экране. Нет WebGL — вызывающий
 * получает null и показывает ссылку на карту вместо неё.
 */
// Стили MapLibre — обычным импортом: динамический импорт CSS их не применял, и холст карты вставал от верха
// документа, а не внутри своего контейнера (метка выбора точки оказывалась за пределами экрана).
import 'maplibre-gl/dist/maplibre-gl.css'

export const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'

let loading = null
export function loadMaplibre() {
  if (!loading) {
    loading = import('maplibre-gl').then((mod) => mod.default || mod)
  }
  return loading
}

/** Создаёт карту в контейнере; center — [lat, lng]. Возвращает { maplibregl, map } или null, если WebGL нет. */
export async function createMap(container, { center, zoom, interactive = true, scrollZoom = false }) {
  const maplibregl = await loadMaplibre()
  try {
    const map = new maplibregl.Map({
      container,
      style: STYLE_URL,
      center: [center[1], center[0]],          // MapLibre ждёт [долгота, широта]
      zoom,
      interactive,
      scrollZoom,
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
      attributionControl: { compact: true },
    })
    map.touchZoomRotate?.disableRotation()
    return { maplibregl, map }
  } catch {
    return null
  }
}

/** Метка-капля в цветах сайта (та же, что была у Leaflet). */
export function pinElement() {
  const el = document.createElement('div')
  el.className = 'map-pin'
  el.innerHTML = '<svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true"><path fill="#1F8F5F" stroke="#fff" stroke-width="1.5" d="M12 2C7.5 2 4 5.5 4 10c0 6 8 12 8 12s8-6 8-12c0-4.5-3.5-8-8-8z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>'
  return el
}

/** Круг радиусом meters вокруг точки — многоугольник для слоя «где-то здесь» (у MapLibre нет круга в метрах). */
export function circlePolygon(lat, lng, meters, steps = 64) {
  const coords = []
  const dLat = meters / 111320
  const dLng = meters / (111320 * Math.cos((lat * Math.PI) / 180))
  for (let i = 0; i <= steps; i += 1) {
    const a = (i / steps) * Math.PI * 2
    coords.push([lng + dLng * Math.cos(a), lat + dLat * Math.sin(a)])
  }
  return { type: 'Feature', geometry: { type: 'Polygon', coordinates: [coords] }, properties: {} }
}

export function osmLink(lat, lng, zoom = 16) {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=${zoom}/${lat}/${lng}`
}
