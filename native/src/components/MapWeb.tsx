import { colors } from '../theme'
import { useEffect, useMemo, useRef } from 'react'
import { StyleSheet, View } from 'react-native'
import { WebView, type WebViewMessageEvent } from 'react-native-webview'

import { mapHtml as html, type MapProps as Props } from './mapHtml'

/**
 * Карта — та же, что на сайте: MapLibre, стиль OpenFreeMap «liberty», без поворота и наклона; метка — зелёная
 * капля сайта. В приложении — внутри WebView: одинаково на iPhone и Android, без ключей Apple и Google.
 * mode «pick» — выбор точки (нажатие или перетаскивание метки → onPick); «show» — показ: метка (масштаб 15)
 * или, если адрес скрыт, круг 400 м (масштаб 13), как LocationMap сайта.
 */

export default function MapWeb({ mode, lat, lng, center, approximate, height = 220, onPick }: Props) {
  const ref = useRef<WebView>(null)
  // карту строим один раз; дальнейшие сдвиги точки (поиск адреса, «моё местоположение») — командой в карту
  const source = useMemo(() => ({ html: html({ mode, lat: lat ?? null, lng: lng ?? null, center: center ?? [44.7866, 20.4489], approximate: !!approximate }) }), []) // eslint-disable-line react-hooks/exhaustive-deps
  const last = useRef<string>(`${lat},${lng}`)
  useEffect(() => {
    const key = `${lat},${lng}`
    if (key === last.current) return
    last.current = key
    if (lat == null || lng == null) ref.current?.injectJavaScript('window.clearPin&&window.clearPin();true;')
    else ref.current?.injectJavaScript(`window.moveTo&&window.moveTo(${lat},${lng});true;`)
  }, [lat, lng])
  const onMessage = (e: WebViewMessageEvent) => {
    try {
      const p = JSON.parse(e.nativeEvent.data)
      if (typeof p.lat === 'number' && typeof p.lng === 'number') { last.current = `${p.lat},${p.lng}`; onPick?.(p.lat, p.lng) }
    } catch { /* не наше сообщение */ }
  }
  return (
    <View style={[styles.box, { height }]}>
      <WebView ref={ref} source={source} originWhitelist={['*']} onMessage={onMessage} scrollEnabled={false} javaScriptEnabled
        style={styles.web} setSupportMultipleWindows={false} nestedScrollEnabled />
    </View>
  )
}

const styles = StyleSheet.create({
  box: { borderRadius: 14, overflow: 'hidden', backgroundColor: colors.sunken },
  web: { flex: 1, backgroundColor: 'transparent' },
})
