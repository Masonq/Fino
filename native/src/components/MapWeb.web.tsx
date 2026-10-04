import { createElement, useEffect, useMemo, useRef } from 'react'
import { View } from 'react-native'

import { mapHtml, type MapProps } from './mapHtml'

/** Только веб-превью: у react-native-webview нет браузерной версии — та же карта в iframe. */
export default function MapWeb({ mode, lat, lng, center, approximate, height = 220, onPick }: MapProps) {
  const frame = useRef<HTMLIFrameElement | null>(null)
  const srcDoc = useMemo(() => mapHtml({ mode, lat: lat ?? null, lng: lng ?? null, center: center ?? [44.7866, 20.4489], approximate: !!approximate })
    .replace('function post(o){window.ReactNativeWebView&&window.ReactNativeWebView.postMessage(JSON.stringify(o))}', 'function post(o){parent.postMessage(JSON.stringify(o),"*")}'), []) // eslint-disable-line react-hooks/exhaustive-deps
  const last = useRef(`${lat},${lng}`)
  useEffect(() => {
    const on = (e: MessageEvent) => {
      if (e.source !== frame.current?.contentWindow) return
      try { const p = JSON.parse(e.data); if (typeof p.lat === 'number') { last.current = `${p.lat},${p.lng}`; onPick?.(p.lat, p.lng) } } catch { /* не наше */ }
    }
    window.addEventListener('message', on)
    return () => window.removeEventListener('message', on)
  }, [onPick])
  useEffect(() => {
    const key = `${lat},${lng}`
    if (key === last.current) return
    last.current = key
    const w = frame.current?.contentWindow as unknown as { moveTo?: (a: number, b: number) => void; clearPin?: () => void } | undefined
    if (lat == null || lng == null) w?.clearPin?.(); else w?.moveTo?.(lat, lng)
  }, [lat, lng])
  return (
    <View style={{ height, borderRadius: 14, overflow: 'hidden', backgroundColor: '#E9ECE8' }}>
      {createElement('iframe', { ref: frame, srcDoc, style: { border: 0, width: '100%', height: '100%' } })}
    </View>
  )
}
