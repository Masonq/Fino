/**
 * Поиск на карте: объявления точками с ценой, близкие — кружком с числом (кластеры MapLibre, без лишних библиотек).
 * Те же отборы, что у поиска (q, раздел, город, цена) — из адреса страницы. Точка объявления: точный адрес, если
 * продавец его не скрыл; скрыт — с точностью ~1 км; нет вовсе — центр города, чуть разнесённый, чтобы объявления
 * одного города не ложились в одну точку.
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { CITY_COORDS } from '../data/cities'
import { createMap } from '../utils/maplibre'
import { formatPrice } from '../utils/money'
import { goBack } from '../utils/goBack'

const PAGES = 5           // по 100 объявлений — 500 свежих на карте
const BELGRADE = [44.7866, 20.4489]

function jitter(id) {
  // устойчивый разнос вокруг центра города (~до 1,5 км): одно и то же объявление всегда в одной точке
  let h = 0
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) | 0
  const a = ((h >>> 0) % 360) * Math.PI / 180
  const r = (((h >>> 9) % 1000) / 1000) * 0.012
  return [Math.cos(a) * r, Math.sin(a) * r]
}

export default function MapSearch() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const box = useRef(null)
  const mapRef = useRef(null)
  const [items, setItems] = useState(null)
  const [picked, setPicked] = useState(null)
  const [noMap, setNoMap] = useState(false)

  // объявления — теми же отборами, что у поиска
  useEffect(() => {
    const base = Object.fromEntries([...params.entries()].filter(([k]) => ['q', 'category_slug', 'city', 'price_min', 'price_max', 'currency', 'deal_type'].includes(k)))
    Promise.all(Array.from({ length: PAGES }, (_, i) => api.searchListings({ ...base, limit: 100, offset: i * 100, lang: i18n.language }).catch(() => ({ items: [] }))))
      .then((pages) => {
        const seen = new Set()
        setItems(pages.flatMap((p) => p.items || []).filter((l) => (seen.has(l.id) ? false : seen.add(l.id))))
      })
  }, [params, i18n.language])

  // карта
  useEffect(() => {
    let alive = true
    const city = params.get('city')
    const center = (city && CITY_COORDS[city]) || BELGRADE
    createMap(box.current, { center, zoom: city ? 11 : 10, scrollZoom: true }).then((res) => {
      if (!alive) return
      if (!res) { setNoMap(true); return }
      mapRef.current = res.map
    })
    return () => { alive = false; mapRef.current?.remove(); mapRef.current = null }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // точки на карту
  useEffect(() => {
    const map = mapRef.current
    if (!map || !items) return
    const features = items.map((l) => {
      let lat, lng
      if (Array.isArray(l.map_point) && l.map_point[0] != null) [lat, lng] = l.map_point   // сервер: адрес или центр города
      else {
        const c = CITY_COORDS[l.city] || BELGRADE
        const [dy, dx] = jitter(l.id)
        lat = c[0] + dy; lng = c[1] + dx
      }
      return { type: 'Feature', geometry: { type: 'Point', coordinates: [lng, lat] },
        properties: { id: l.id, label: l.is_free ? t('card.free') : formatPrice(l.price, l.currency, i18n.language) } }
    })
    const data = { type: 'FeatureCollection', features }
    const draw = () => {
      if (map.getSource('ads')) { map.getSource('ads').setData(data); return }
      map.addSource('ads', { type: 'geojson', data, cluster: true, clusterRadius: 46, clusterMaxZoom: 15 })
      map.addLayer({ id: 'clusters', type: 'circle', source: 'ads', filter: ['has', 'point_count'],
        paint: { 'circle-color': '#0FA36A', 'circle-opacity': 0.92, 'circle-stroke-color': '#fff', 'circle-stroke-width': 3,
          'circle-radius': ['step', ['get', 'point_count'], 17, 10, 21, 50, 26, 200, 32] } })
      map.addLayer({ id: 'cluster-n', type: 'symbol', source: 'ads', filter: ['has', 'point_count'],
        layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 13, 'text-font': ['Noto Sans Bold'] }, paint: { 'text-color': '#fff' } })
      map.addLayer({ id: 'price', type: 'symbol', source: 'ads', filter: ['!', ['has', 'point_count']],
        layout: { 'text-field': ['get', 'label'], 'text-size': 12.5, 'text-font': ['Noto Sans Bold'], 'text-allow-overlap': true, 'text-padding': 4 },
        paint: { 'text-color': '#0F1512', 'text-halo-color': '#FFFFFF', 'text-halo-width': 6 } })
      map.on('click', 'clusters', (e) => {
        const f = e.features[0]
        map.getSource('ads').getClusterExpansionZoom(f.properties.cluster_id).then((z) => map.easeTo({ center: f.geometry.coordinates, zoom: z }))
      })
      map.on('click', 'price', (e) => setPicked(items.find((l) => l.id === e.features[0].properties.id) || null))
      for (const id of ['clusters', 'price']) {
        map.on('mouseenter', id, () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', id, () => { map.getCanvas().style.cursor = '' })
      }
      map.on('click', (e) => { if (!map.queryRenderedFeatures(e.point, { layers: ['clusters', 'price'] }).length) setPicked(null) })
    }
    if (map.isStyleLoaded()) draw()
    else map.once('load', draw)
  }, [items, t, i18n.language])

  const backToList = () => navigate(`/search?${params.toString()}`)
  return (
    <div className="map-page">
      <div className="map-top">
        <button type="button" className="map-btn" onClick={() => goBack(navigate, '/search')} aria-label={t('common.back')}>
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="map-title">
          <b>{params.get('q') || t('map.title')}</b>
          <span>{items ? t('map.count', { count: items.length }) : '\u00a0'}</span>
        </div>
        <button type="button" className="map-btn map-list" onClick={backToList}>{t('map.list')}</button>
      </div>
      <div ref={box} className="map-box" />
      {noMap && <div className="map-nomap">{t('map.no_webgl')}</div>}
      {picked && (
        <Link className="map-card" to={picked.path || `/go/${picked.id}`}>
          {picked.cover_photo ? <img src={picked.cover_photo} alt="" /> : <span className="map-card-ph" />}
          <span className="map-card-body">
            <b>{picked.is_free ? t('card.free') : formatPrice(picked.price, picked.currency, i18n.language)}</b>
            <span className="map-card-title">{picked.title}</span>
            <small>{picked.city_label || ''}</small>
          </span>
        </Link>
      )}
    </div>
  )
}
