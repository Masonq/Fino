import { Ionicons } from '@expo/vector-icons'
import { useRef } from 'react'
import { Animated, Pressable, StyleSheet } from 'react-native'

import { useFavorites } from '../favorites'
import { colors } from '../theme'

/**
 * Сердечко: белый круг поверх фото, как на сайте. При добавлении — короткий «хлопок» (пружина).
 * Нажатие не открывает объявление — только отмечает. Гостя ведёт во вход.
 */
export default function HeartButton({ id, size = 36, style }: { id: string; size?: number; style?: object }) {
  const { isFav, toggle } = useFavorites()
  const on = isFav(id)
  const scale = useRef(new Animated.Value(1)).current

  const press = () => {
    if (!on) {
      scale.setValue(0.6)
      Animated.spring(scale, { toValue: 1, useNativeDriver: true, speed: 14, bounciness: 14 }).start()
    }
    toggle(id)
  }

  return (
    <Pressable onPress={press} hitSlop={6} style={[styles.btn, { width: size, height: size, borderRadius: size / 2 }, style]}
      accessibilityRole="button" accessibilityLabel={on ? 'Убрать из избранного' : 'В избранное'} accessibilityState={{ selected: on }}>
      <Animated.View style={{ transform: [{ scale }] }}>
        <Ionicons name={on ? 'heart' : 'heart-outline'} size={Math.round(size * 0.56)} color={on ? colors.accent : colors.ink} />
      </Animated.View>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  btn: {
    backgroundColor: 'rgba(255,255,255,0.94)', alignItems: 'center', justifyContent: 'center',
    shadowColor: '#14201A', shadowOpacity: 0.12, shadowRadius: 5, shadowOffset: { width: 0, height: 1 }, elevation: 2,
  },
})
