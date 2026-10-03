import SheetFrame from './SheetFrame'
import { tr } from '../i18n'
import type { ReactNode } from 'react'
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { colors, font } from '../theme'

/** Шторка снизу: затемнение, ручка, заголовок. Закрывается нажатием мимо. */
export default function Sheet({ visible, title, onClose, children }: { visible: boolean; title?: string; onClose: () => void; children: ReactNode }) {
  const insets = useSafeAreaInsets()
  return (
    <SheetFrame visible={visible} onClose={onClose}>
      <View style={[styles.sheet, { paddingBottom: insets.bottom + 10 }]}>
        <View style={styles.handle} />
        {!!title && <Text style={styles.title}>{title}</Text>}
        {children}
      </View>
    </SheetFrame>
  )
}

export function SheetAction({ label, onPress, danger, icon }: { label: string; onPress: () => void; danger?: boolean; icon?: ReactNode }) {
  return (
    <Pressable style={styles.action} onPress={onPress} accessibilityRole="button">
      {icon}
      <Text style={[styles.actionText, danger && { color: '#B42318' }]}>{label}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(17,22,19,0.42)' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8 },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: '#D8DCD8', marginBottom: 8 },
  title: { fontSize: 18, fontFamily: font[800], color: colors.ink, paddingHorizontal: 20, paddingBottom: 8 },
  action: { height: 54, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', gap: 12 },
  actionText: { fontSize: 16.5, color: colors.ink, fontFamily: font[600] },
})
