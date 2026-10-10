/**
 * Нижняя шторка, как на сайте и в приложениях iPhone: выезжает снизу, закрывается смахиванием вниз за полоску
 * или заголовок, нажатием на затемнение. Прокручиваемые списки внутри листаются сами — шторку тянет только
 * верхняя часть (полоска и заголовок), поэтому листание и смахивание не мешают друг другу.
 */
import { type ReactNode, useEffect, useRef } from 'react'
import { Animated, Dimensions, Modal, PanResponder, StyleSheet, View } from 'react-native'
import Pressable from './Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { colors } from '../theme'

const H = Dimensions.get('window').height

export default function BottomSheet({ visible, onClose, header, children }: {
  visible: boolean; onClose: () => void; header?: ReactNode; children: ReactNode
}) {
  const insets = useSafeAreaInsets()
  const y = useRef(new Animated.Value(H)).current
  const fade = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (!visible) return
    y.setValue(H)
    Animated.parallel([
      Animated.spring(y, { toValue: 0, useNativeDriver: true, damping: 22, stiffness: 220, mass: 0.9 }),
      Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }),
    ]).start()
  }, [visible, y, fade])

  const close = () => {
    Animated.parallel([
      Animated.timing(y, { toValue: H, duration: 220, useNativeDriver: true }),
      Animated.timing(fade, { toValue: 0, duration: 200, useNativeDriver: true }),
    ]).start(() => onClose())
  }

  const pan = useRef(PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) => g.dy > 4 && Math.abs(g.dy) > Math.abs(g.dx),
    onPanResponderMove: (_, g) => { if (g.dy > 0) y.setValue(g.dy) },
    onPanResponderRelease: (_, g) => {
      if (g.dy > 110 || g.vy > 0.9) close()
      else Animated.spring(y, { toValue: 0, useNativeDriver: true, damping: 20, stiffness: 260 }).start()
    },
  })).current

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={close} statusBarTranslucent>
      <Animated.View style={[StyleSheet.absoluteFill, st.back, { opacity: fade }]}>
        <Pressable scale={1} style={StyleSheet.absoluteFill} onPress={close} accessibilityLabel="Закрыть" />
      </Animated.View>
      <Animated.View style={[st.sheet, { paddingBottom: Math.max(insets.bottom, 16), transform: [{ translateY: y }] }]}>
        <View {...pan.panHandlers} style={st.grabZone}>
          <View style={st.handle} />
          {header}
        </View>
        {children}
      </Animated.View>
    </Modal>
  )
}

const st = StyleSheet.create({
  back: { backgroundColor: 'rgba(15,21,18,0.4)' },
  sheet: { position: 'absolute', left: 0, right: 0, bottom: 0, maxHeight: '90%', backgroundColor: colors.surface, borderTopLeftRadius: 26, borderTopRightRadius: 26, paddingHorizontal: 16 },
  grabZone: { paddingTop: 8, paddingBottom: 4 },
  handle: { width: 40, height: 5, borderRadius: 3, backgroundColor: colors.sunken, alignSelf: 'center', marginBottom: 12 },
})
