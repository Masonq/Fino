import { Image } from 'expo-image'
import type { ComponentType } from 'react'
import { Modal, Pressable, StyleSheet, View } from 'react-native'

/** Только веб-превью: у react-native-image-viewing нет браузерной версии — простой просмотр без увеличения. */
type Props = {
  images: { uri: string }[]; imageIndex: number; visible: boolean; onRequestClose: () => void
  onImageIndexChange?: (i: number) => void; presentationStyle?: string; backgroundColor?: string
  FooterComponent?: ComponentType<{ imageIndex: number }>
}
export default function PhotoViewer({ images, imageIndex, visible, onRequestClose, backgroundColor, FooterComponent }: Props) {
  if (!visible) return null
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onRequestClose}>
      <Pressable style={[StyleSheet.absoluteFill, { backgroundColor: backgroundColor ?? '#000' }]} onPress={onRequestClose} accessibilityLabel="Закрыть">
        <Image source={{ uri: images[imageIndex]?.uri }} style={StyleSheet.absoluteFill} contentFit="contain" />
      </Pressable>
      {FooterComponent && <View style={{ position: 'absolute', left: 0, right: 0, bottom: 0 }}><FooterComponent imageIndex={imageIndex} /></View>}
    </Modal>
  )
}
