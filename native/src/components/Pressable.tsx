/**
 * Pressable с «живым» нажатием — как на сайте: нажал — элемент утапливается до 0,97 за 90 мс, отпустил — пружинит
 * обратно (stiffness 400 / damping 17). Подменяет обычный Pressable во всём приложении, поэтому так реагируют все кнопки,
 * строки меню, плитки и капсулы. scale={1} — без утапливания (подложки окон, большие области).
 */
import { forwardRef, useRef, useState } from 'react'
import { Animated, Easing, Pressable as RNPressable, type PressableProps, type StyleProp, type View, type ViewStyle } from 'react-native'

const APressable = Animated.createAnimatedComponent(RNPressable)

type Props = PressableProps & { scale?: number }

const Pressable = forwardRef<View, Props>(function Pressable({ scale = 0.97, style, onPressIn, onPressOut, disabled, ...rest }, ref) {
  const v = useRef(new Animated.Value(1)).current
  const anim = { transform: [{ scale: v }] }
  const on = scale < 1 && !disabled
  // Animated-обёртка не понимает style-функцию ({ pressed }) => …, поэтому «нажато» считаем сами и отдаём готовый стиль
  const [pressed, setPressed] = useState(false)
  const base = typeof style === 'function' ? style({ pressed, hovered: false } as never) : style
  const merged = [base as StyleProp<ViewStyle>, on ? anim : null]
  return (
    <APressable
      ref={ref as never}
      disabled={disabled}
      {...rest}
      style={merged as never}
      onPressIn={(e) => { if (typeof style === 'function') setPressed(true); if (on) Animated.timing(v, { toValue: scale, duration: 90, easing: Easing.out(Easing.quad), useNativeDriver: true }).start(); onPressIn?.(e) }}
      onPressOut={(e) => { if (typeof style === 'function') setPressed(false); if (on) Animated.spring(v, { toValue: 1, stiffness: 400, damping: 17, mass: 1, useNativeDriver: true }).start(); onPressOut?.(e) }}
    />
  )
})

export default Pressable
