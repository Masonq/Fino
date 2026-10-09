import * as Location from 'expo-location'
import { useEffect, useRef, useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'

import { getLang, tr } from '../i18n'
import { colors, font } from '../theme'
import Icon from './Icon'
import MapWeb from './MapWeb'

type Props = {
  lat: number | null; lng: number | null; hide: boolean; center?: [number, number]
  onChange: (lat: number | null, lng: number | null) => void; onHide: (v: boolean) => void
}
type Found = { place_id: number; display_name: string; lat: string; lon: string }

/**
 * «Точка на карте» — как LocationPicker сайта: раскрывающийся блок; поиск адреса (Nominatim, только Сербия,
 * 5 вариантов), «Моё местоположение», карта — нажатие или перетаскивание метки, «Не показывать точный адрес —
 * только район», «Убрать точку».
 */
export default function LocationPicker({ lat, lng, hide, center, onChange, onHide }: Props) {
  const [open, setOpen] = useState(lat != null)
  const [q, setQ] = useState('')
  const [found, setFound] = useState<Found[]>([])
  const [busy, setBusy] = useState(false)
  const [locating, setLocating] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    if (q.trim().length < 3) { setFound([]); return undefined }
    timer.current = setTimeout(async () => {
      setBusy(true)
      try {
        const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&countrycodes=rs&addressdetails=0&limit=5&q=${encodeURIComponent(q.trim())}`, { headers: { 'Accept-Language': getLang() } })
        const d = await r.json()
        setFound(Array.isArray(d) ? d : [])
      } catch { setFound([]) } finally { setBusy(false) }
    }, 450)
    return () => { if (timer.current) clearTimeout(timer.current) }
  }, [q])

  const mine = async () => {
    setLocating(true)
    try {
      const perm = await Location.requestForegroundPermissionsAsync()
      if (perm.status === 'granted') {
        const p = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced })
        onChange(p.coords.latitude, p.coords.longitude)
      }
    } catch { /* нет доступа — ничего не делаем */ } finally { setLocating(false) }
  }

  return (
    <View style={styles.wrap}>
      <Pressable style={styles.head} onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }}>
        <Text style={styles.headText}>{tr(lat != null ? 'Точка на карте указана' : 'Указать точку на карте')}</Text>
        <View style={open ? { transform: [{ rotate: '180deg' }] } : undefined}><Icon name="down" size={14} color={colors.inkSoft} /></View>
      </Pressable>
      {open && (
        <View style={styles.body}>
          <View style={styles.searchRow}>
            <TextInput value={q} onChangeText={setQ} placeholder={tr('Поиск по адресу')} placeholderTextColor={colors.muted} style={styles.search} autoCorrect={false} />
            <Pressable style={styles.mine} onPress={mine} disabled={locating} accessibilityLabel={tr('Моё местоположение')}>
              {locating ? <ActivityIndicator size="small" color={colors.primary} /> : <Icon name="send" size={18} color={colors.primaryDeep} />}
            </Pressable>
          </View>
          {busy && <Text style={styles.small}>{tr('Ищу…')}</Text>}
          {found.length > 0 && (
            <View style={styles.results}>
              {found.map((f, i) => (
                <Pressable key={f.place_id} style={[styles.result, i === found.length - 1 && { borderBottomWidth: 0 }]} onPress={() => { onChange(Number(f.lat), Number(f.lon)); setFound([]); setQ('') }}>
                  <Text style={styles.resultText} numberOfLines={2}>{f.display_name}</Text>
                </Pressable>
              ))}
            </View>
          )}
          <Text style={styles.small}>{tr('Нажмите на карту или перетащите метку, чтобы указать точное место')}</Text>
          <MapWeb mode="pick" lat={lat} lng={lng} center={center} onPick={(a, b) => onChange(a, b)} />
          <Pressable style={styles.check} onPress={() => onHide(!hide)} accessibilityRole="checkbox" accessibilityState={{ checked: hide }}>
            <View style={[styles.box, hide && styles.boxOn]}>{hide && <Icon name="check" size={12} color="#fff" />}</View>
            <Text style={styles.checkText}>{tr('Не показывать точный адрес — только район')}</Text>
          </Pressable>
          {lat != null && <Pressable onPress={() => onChange(null, null)} hitSlop={6}><Text style={styles.clear}>{tr('Убрать точку')}</Text></Pressable>}
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { marginTop: 14, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 0, overflow: 'hidden' },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14, height: 48 },
  headText: { fontSize: 14.5, fontFamily: font[700], color: colors.ink },
  body: { paddingHorizontal: 12, paddingBottom: 12, gap: 8 },
  searchRow: { flexDirection: 'row', gap: 8 },
  search: { flex: 1, height: 44, borderRadius: 12, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, fontSize: 15, fontFamily: font[500], color: colors.ink, backgroundColor: colors.surface },
  mine: { width: 44, height: 44, borderRadius: 12, borderWidth: 0, alignItems: 'center', justifyContent: 'center' },
  small: { fontSize: 12.5, lineHeight: 17, fontFamily: font[500], color: colors.muted },
  results: { borderRadius: 12, borderWidth: 0, overflow: 'hidden' },
  result: { paddingHorizontal: 12, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  resultText: { fontSize: 13.5, lineHeight: 18, fontFamily: font[500], color: colors.ink },
  check: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  box: { width: 20, height: 20, borderRadius: 5, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  boxOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkText: { flex: 1, fontSize: 13.5, fontFamily: font[600], color: colors.ink },
  clear: { fontSize: 13.5, fontFamily: font[700], color: '#E5533D' },
})
