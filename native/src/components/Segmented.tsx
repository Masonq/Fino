import { select } from '../haptics'
import { useEffect, useRef, useState } from 'react'
import { Animated, LayoutChangeEvent, Pressable, StyleSheet, Text, View } from 'react-native'

import { tr } from '../i18n'
import { colors, font } from '../theme'

type Option<K extends string> = { key: K; label: string }

/**
 * Переключатель с переезжающей белой плашкой — как «Все / Новое / Даром» на сайте.
 * Плашка едет к выбранному варианту с лёгкой пружиной; при первом показе встаёт на место без движения.
 */
export default function Segmented<K extends string>({ options, value, onChange, stretch = false, onSunken = false }: {
  options: Option<K>[]
  value: K
  onChange: (key: K) => void
  /** На всю ширину равными частями — как переключатель «Купить / Снять / Посуточно» на сайте */
  stretch?: boolean
  /** на серой карточке: дорожка темнее, иначе она сливается с фоном карточки */
  onSunken?: boolean
}) {
  const [frames, setFrames] = useState<Record<string, { x: number; w: number }>>({})
  const x = useRef(new Animated.Value(0)).current
  const w = useRef(new Animated.Value(0)).current
  const placed = useRef(false)

  useEffect(() => {
    const f = frames[value]
    if (!f) return
    if (!placed.current) {
      x.setValue(f.x)
      w.setValue(f.w)
      placed.current = true
      return
    }
    Animated.parallel([
      Animated.spring(x, { toValue: f.x, useNativeDriver: false, speed: 18, bounciness: 7 }),
      Animated.spring(w, { toValue: f.w, useNativeDriver: false, speed: 18, bounciness: 7 }),
    ]).start()
  }, [frames, value, x, w])

  const onItemLayout = (key: K) => (e: LayoutChangeEvent) => {
    const { x: fx, width } = e.nativeEvent.layout
    setFrames((prev) => (prev[key]?.x === fx && prev[key]?.w === width ? prev : { ...prev, [key]: { x: fx, w: width } }))
  }

  return (
    <View style={[styles.track, stretch && styles.trackStretch, onSunken && styles.trackOnSunken]} accessibilityRole="tablist">
      <Animated.View style={[styles.pill, { left: x, width: w, opacity: frames[value] ? 1 : 0 }]} />
      {options.map((o) => {
        const on = o.key === value
        return (
          <Pressable key={o.key} onLayout={onItemLayout(o.key)} onPress={() => { if (o.key !== value) select(); onChange(o.key) }} style={[styles.item, stretch && styles.itemStretch]}
            accessibilityRole="tab" accessibilityState={{ selected: on }} hitSlop={6}>
            <Text style={[styles.label, on && styles.labelOn, stretch && styles.labelStretch]} numberOfLines={1} adjustsFontSizeToFit={stretch} minimumFontScale={0.85}>{tr(o.label)}</Text>
          </Pressable>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  track: { flexDirection: 'row', padding: 3, borderRadius: 13, backgroundColor: colors.sunken, alignSelf: 'flex-start', overflow: 'hidden' },
  pill: {
    position: 'absolute', top: 3, bottom: 3, borderRadius: 10, backgroundColor: colors.surface,
    shadowColor: '#14201A', shadowOpacity: 0.12, shadowRadius: 4, shadowOffset: { width: 0, height: 1 }, elevation: 2,
  },
  item: { height: 36, paddingHorizontal: 16, alignItems: 'center', justifyContent: 'center' },
  trackStretch: { alignSelf: 'stretch' },
  trackOnSunken: { backgroundColor: colors.bg },
  itemStretch: { flex: 1, height: 40, paddingHorizontal: 6 },
  labelStretch: { fontSize: 13.5, fontFamily: font[600], letterSpacing: -0.1 },
  label: { fontSize: 14.5, fontFamily: font[800], color: colors.inkSoft },
  labelOn: { color: colors.ink },
})
