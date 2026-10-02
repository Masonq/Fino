import { useEffect, useRef } from 'react'
import { Animated, StyleProp, ViewStyle } from 'react-native'

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
