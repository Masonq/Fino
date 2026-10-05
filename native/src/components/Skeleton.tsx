import { useEffect, useRef } from 'react'
import { Animated, StyleProp, View, ViewStyle } from 'react-native'

import { colors } from '../theme'

/** Заготовка на время загрузки — мягко «дышит», а не стоит мёртвым серым пятном. */
export default function Skeleton({ style }: { style?: StyleProp<ViewStyle> }) {
  const o = useRef(new Animated.Value(0.55)).current
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(o, { toValue: 1, duration: 650, useNativeDriver: true }),
      Animated.timing(o, { toValue: 0.55, duration: 650, useNativeDriver: true }),
    ]))
    loop.start()
    return () => loop.stop()
  }, [o])
  return <Animated.View style={[{ backgroundColor: colors.sunken, borderRadius: 10, opacity: o }, style]} />
}

/** Строки-заглушки для списков (отклики, шопсы, заказы): превью слева и две строки текста. */
export function RowSkeletons({ count = 3, thumb = 'square' }: { count?: number; thumb?: 'square' | 'round' | 'tall' }) {
  const t = thumb === 'round' ? { width: 44, height: 44, borderRadius: 22 } : thumb === 'tall' ? { width: 64, height: 96, borderRadius: 12 } : { width: 56, height: 56, borderRadius: 14 }
  return (
    <View style={{ gap: 10 }}>
      {Array.from({ length: count }).map((_, i) => (
        <View key={i} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 18, backgroundColor: colors.surface }}>
          <Skeleton style={t} />
          <View style={{ flex: 1, gap: 8 }}>
            <Skeleton style={{ height: 14, width: `${70 - i * 8}%`, borderRadius: 6 }} />
            <Skeleton style={{ height: 12, width: '40%', borderRadius: 6 }} />
          </View>
        </View>
      ))}
    </View>
  )
}

/** Подборка на главной: заголовок и ряд карточек 140×175 (как «Новое сегодня»). */
export function SectionSkeleton({ wide = false }: { wide?: boolean }) {
  return (
    <View style={{ marginTop: 16, paddingHorizontal: 12 }}>
      <Skeleton style={{ width: '44%', height: 24, borderRadius: 8, marginBottom: 10 }} />
      <View style={{ flexDirection: 'row', gap: 12 }}>
        {[0, 1, 2].map((i) => (
          <View key={i} style={{ width: wide ? 220 : 140 }}>
            <Skeleton style={{ height: wide ? 150 : 175, borderRadius: 18 }} />
            <Skeleton style={{ height: 16, width: '60%', borderRadius: 6, marginTop: 9 }} />
            <Skeleton style={{ height: 13, width: '85%', borderRadius: 6, marginTop: 6 }} />
          </View>
        ))}
      </View>
    </View>
  )
}
