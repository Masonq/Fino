/**
 * Движение в приложении — как на сайте: нажатие утапливает элемент до 0,97 быстро, отпускание пружинит обратно
 * (пружина ~ stiffness 400 / damping 17 — так делают Framer Motion и Material 3); карточки появляются волной.
 */
import { useRef } from 'react'
import { Animated, Easing } from 'react-native'

export function usePressScale(to = 0.97) {
  const s = useRef(new Animated.Value(1)).current
  return {
    style: { transform: [{ scale: s }] },
    onPressIn: () => Animated.timing(s, { toValue: to, duration: 90, easing: Easing.out(Easing.quad), useNativeDriver: true }).start(),
    onPressOut: () => Animated.spring(s, { toValue: 1, stiffness: 400, damping: 17, mass: 1, useNativeDriver: true }).start(),
  }
}

/** Появление: проявление + подъём на 10 px, с задержкой по номеру (первые 8). */
export function useAppear(index = 0) {
  const v = useRef(new Animated.Value(0)).current
  const started = useRef(false)
  if (!started.current) {
    started.current = true
    Animated.timing(v, { toValue: 1, duration: 340, delay: Math.min(index, 8) * 40, easing: Easing.bezier(0.2, 0.8, 0.2, 1), useNativeDriver: true }).start()
  }
  return { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) }] }
}
