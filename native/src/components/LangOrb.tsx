/**
 * Переключатель языка в шапке главной — «шар», как на сайте: круглая кнопка с кодом языка в медленно вращающемся
 * цветном кольце; нажатие раскрывает капсулу SR · RU · EN с мятным бегунком под выбранным.
 */
import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native'
import Svg, { Circle, Defs, LinearGradient, Stop } from 'react-native-svg'
import { select } from '../haptics'
import { useLang } from '../i18n'
import { colors, font } from '../theme'

const SH = { shadowColor: '#0F1512', shadowOpacity: 0.1, shadowRadius: 10, shadowOffset: { width: 0, height: 3 }, elevation: 3 }

const LANGS = ['sr', 'ru', 'en'] as const
const W = 44

export default function LangOrb() {
  const { lang, setLang } = useLang()
  const [open, setOpen] = useState(false)
  const spin = useRef(new Animated.Value(0)).current
  const thumb = useRef(new Animated.Value(LANGS.indexOf(lang as typeof LANGS[number]))).current
  useEffect(() => {
    const a = Animated.loop(Animated.timing(spin, { toValue: 1, duration: 6000, easing: Easing.linear, useNativeDriver: true }))
    a.start(); return () => a.stop()
  }, [spin])
  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] })
  const pick = (l: typeof LANGS[number]) => {
    select()
    Animated.spring(thumb, { toValue: LANGS.indexOf(l), useNativeDriver: true, speed: 20, bounciness: 8 }).start()
    setTimeout(() => { setOpen(false); if (l !== lang) setLang(l, '/') }, 180)
  }
  if (!open) {
    return (
      <Pressable onPress={() => { select(); setOpen(true) }} style={({ pressed }) => [st.orb, pressed && { transform: [{ scale: 0.94 }] }]} accessibilityRole="button" accessibilityLabel="Language">
        <Animated.View style={[StyleSheet.absoluteFill, { transform: [{ rotate }] }]} pointerEvents="none">
          <Svg width="100%" height="100%" viewBox="0 0 46 46">
            <Defs><LinearGradient id="orb" x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor="#0FA36A" /><Stop offset="0.35" stopColor="#B7E35A" /><Stop offset="0.7" stopColor="#FF7A59" /><Stop offset="1" stopColor="#6FC3FF" /></LinearGradient></Defs>
            <Circle cx="23" cy="23" r="19.5" stroke="url(#orb)" strokeWidth="2.5" fill="none" />
          </Svg>
        </Animated.View>
        <Text style={st.code}>{lang.toUpperCase()}</Text>
      </Pressable>
    )
  }
  return (
    <View style={st.pill} accessibilityRole="radiogroup">
      <Animated.View style={[st.thumb, { transform: [{ translateX: thumb.interpolate({ inputRange: [0, 2], outputRange: [0, W * 2] }) }] }]} />
      {LANGS.map((l) => (
        <Pressable key={l} style={st.opt} onPress={() => pick(l)} accessibilityRole="radio" accessibilityState={{ checked: l === lang }}>
          <Text style={[st.optT, l === lang && { color: colors.onInverse }]}>{l.toUpperCase()}</Text>
        </Pressable>
      ))}
    </View>
  )
}

const st = StyleSheet.create({
  orb: { width: 46, height: 46, borderRadius: 23, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', ...SH },
  code: { fontFamily: font[800], fontSize: 13, color: colors.ink, letterSpacing: 0.3 },
  pill: { flexDirection: 'row', height: 46, padding: 4, borderRadius: 23, backgroundColor: colors.surface, ...SH },
  thumb: { position: 'absolute', top: 4, left: 4, width: W, height: 38, borderRadius: 19, backgroundColor: colors.inverse },
  opt: { width: W, height: 38, alignItems: 'center', justifyContent: 'center' },
  optT: { fontFamily: font[800], fontSize: 13.5, color: colors.inkSoft },
})
