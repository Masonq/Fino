import { type ReactNode, useEffect, useRef, useState } from 'react'
import { Animated, Easing, KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet } from 'react-native'

import { tr } from '../i18n'

/**
 * Рамка шторки — как на сайте (.cs-overlay): затемнение rgba(17,22,19,.42) плавно проявляется на месте за 0,22 с,
 * а снизу выезжает только сама шторка (лёгкая пружина). Раньше окно анимировалось целиком, и затемнение
 * «выезжало» снизу вместе со шторкой, как тень. Над клавиатурой шторка поднимается целиком.
 */
export default function SheetFrame({ visible, onClose, children }: { visible: boolean; onClose: () => void; children: ReactNode }) {
  const [mounted, setMounted] = useState(visible)
  const fade = useRef(new Animated.Value(0)).current
  const slide = useRef(new Animated.Value(1)).current

  useEffect(() => {
    if (visible) {
      setMounted(true)
      fade.setValue(0); slide.setValue(1)
      Animated.parallel([
        Animated.timing(fade, { toValue: 1, duration: 220, easing: Easing.out(Easing.quad), useNativeDriver: true }),
        // без перелёта: иначе шторка подлетала выше края и снизу проглядывал незатемнённый экран
        Animated.spring(slide, { toValue: 0, useNativeDriver: true, damping: 24, stiffness: 240, mass: 0.9, overshootClamping: true }),
      ]).start()
    } else if (mounted) {
      Animated.parallel([
        Animated.timing(fade, { toValue: 0, duration: 180, useNativeDriver: true }),
        Animated.timing(slide, { toValue: 1, duration: 200, easing: Easing.in(Easing.quad), useNativeDriver: true }),
      ]).start(() => setMounted(false))
    }
  }, [visible]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!mounted) return null
  return (
    <Modal visible transparent animationType="none" onRequestClose={onClose} statusBarTranslucent>
      <KeyboardAvoidingView style={styles.wrap} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Animated.View style={[styles.backdrop, { opacity: fade }]}>
          <Pressable style={{ flex: 1 }} onPress={onClose} accessibilityLabel={tr('Закрыть')} />
        </Animated.View>
        {/* Высота шторки — не больше 88 % экрана; ограничение здесь, а не у самой шторки: иначе проценты считались
            от этой же обёртки, и шторка не доставала до низа на 70 точек */}
        <Animated.View style={{ maxHeight: '88%', transform: [{ translateY: slide.interpolate({ inputRange: [0, 1], outputRange: [0, 700] }) }] }}>
          {children}
        </Animated.View>
      </KeyboardAvoidingView>
    </Modal>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(17,22,19,0.42)' },
})
