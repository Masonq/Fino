/**
 * Свайп строки, как в «Сообщениях» iPhone и на сайте: влево — кнопки справа («Без звука», «Удалить»),
 * вправо — слева («Закрепить», «Непрочитано»). Длинный свайп влево сразу выполняет последнее действие справа.
 * Вертикальная прокрутка списка не перехватывается — строка реагирует, только если палец идёт вбок.
 */
import * as Haptics from 'expo-haptics'
import { type ReactNode, useRef } from 'react'
import { Animated, Dimensions, PanResponder, Pressable, StyleSheet, Text, View } from 'react-native'
import { font } from '../theme'

export type SwipeAction = { label: string; color: string; onPress: () => void }
const BTN = 78
const W = Dimensions.get('window').width

export default function SwipeRow({ left = [], right = [], children }: { left?: SwipeAction[]; right?: SwipeAction[]; children: ReactNode }) {
  const x = useRef(new Animated.Value(0)).current
  const base = useRef(0)
  const buzzed = useRef(false)
  const maxL = left.length * BTN
  const maxR = right.length * BTN

  const snap = (to: number) => { base.current = to; Animated.spring(x, { toValue: to, useNativeDriver: true, damping: 22, stiffness: 260 }).start() }
  const run = (a: SwipeAction) => { snap(0); a.onPress() }

  const pan = useRef(PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 10 && Math.abs(g.dx) > Math.abs(g.dy) * 1.5,
    onPanResponderGrant: () => { buzzed.current = false },
    onPanResponderMove: (_, g) => {
      let v = base.current + g.dx
      v = Math.max(-(maxR + W * 0.35), Math.min(maxL + 40, v))
      if (!maxL && v > 0) v = 0
      if (!maxR && v < 0) v = 0
      x.setValue(v)
      if (v < -(maxR + 90) && !buzzed.current) { buzzed.current = true; Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {}) }
    },
    onPanResponderRelease: (_, g) => {
      const v = base.current + g.dx
      if (right.length && v < -(maxR + 90)) { const a = right[right.length - 1]; Animated.timing(x, { toValue: -W, duration: 180, useNativeDriver: true }).start(() => { x.setValue(0); base.current = 0; a.onPress() }); return }
      if (v < -maxR / 2) snap(-maxR)
      else if (v > maxL / 2 && maxL) snap(maxL)
      else snap(0)
    },
    onPanResponderTerminate: () => snap(0),
  })).current

  return (
    <View style={st.wrap}>
      <View style={[st.side, { left: 0 }]}>
        {left.map((a) => <Pressable key={a.label} style={[st.btn, { backgroundColor: a.color }]} onPress={() => run(a)}><Text style={st.btnT} numberOfLines={2}>{a.label}</Text></Pressable>)}
      </View>
      <View style={[st.side, { right: 0 }]}>
        {right.map((a) => <Pressable key={a.label} style={[st.btn, { backgroundColor: a.color }]} onPress={() => run(a)}><Text style={st.btnT} numberOfLines={2}>{a.label}</Text></Pressable>)}
      </View>
      <Animated.View {...pan.panHandlers} style={{ transform: [{ translateX: x }] }}>{children}</Animated.View>
    </View>
  )
}

const st = StyleSheet.create({
  wrap: { overflow: 'hidden' },
  side: { position: 'absolute', top: 0, bottom: 0, flexDirection: 'row' },
  btn: { width: BTN, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 },
  btnT: { color: '#FFFFFF', fontFamily: font[800], fontSize: 12.5, textAlign: 'center' },
})
