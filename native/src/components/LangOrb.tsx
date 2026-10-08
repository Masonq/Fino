/**
 * Язык в шапке главной — «барабан», как на сайте: скруглённая кнопка с кодом; нажатие прокручивает код вверх
 * (SR → RU → EN → SR) и меняет язык. Кружок с кольцом убран по решению владельца.
 */
import { useRef, useState } from 'react'
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native'
import { select } from '../haptics'
import { useLang } from '../i18n'
import { colors, font } from '../theme'

const ORDER = ['sr', 'ru', 'en'] as const
const H = 46

export default function LangOrb() {
  const { lang, setLang } = useLang()
  const cur = (ORDER as readonly string[]).includes(lang) ? lang : 'sr'
  const next = ORDER[(ORDER.indexOf(cur as typeof ORDER[number]) + 1) % ORDER.length]
  const y = useRef(new Animated.Value(0)).current
  const [busy, setBusy] = useState(false)
  const roll = () => {
    if (busy) return
    setBusy(true); select()
    Animated.timing(y, { toValue: -H, duration: 380, easing: Easing.bezier(0.3, 1.45, 0.5, 1), useNativeDriver: true }).start(() => {
      setLang(next, '/'); y.setValue(0); setBusy(false)
    })
  }
  return (
    <Pressable onPress={roll} style={({ pressed }) => [st.drum, pressed && { transform: [{ scale: 0.95 }] }]} accessibilityRole="button" accessibilityLabel={`Language: ${cur.toUpperCase()} → ${next.toUpperCase()}`}>
      <Animated.View style={{ transform: [{ translateY: y }] }}>
        <View style={st.cell}><Text style={st.code}>{cur.toUpperCase()}</Text></View>
        <View style={st.cell}><Text style={st.code}>{next.toUpperCase()}</Text></View>
      </Animated.View>
    </Pressable>
  )
}

const st = StyleSheet.create({
  drum: { width: 52, height: H, borderRadius: 15, overflow: 'hidden', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.1, shadowRadius: 10, shadowOffset: { width: 0, height: 3 }, elevation: 3 },
  cell: { height: H, alignItems: 'center', justifyContent: 'center' },
  code: { fontFamily: font[800], fontSize: 14, letterSpacing: 0.4, color: colors.ink },
})
