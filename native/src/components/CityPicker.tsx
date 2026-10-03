import { Ionicons } from '@expo/vector-icons'
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { CITY_LIST } from '../format'
import { colors } from '../theme'

/** Выбор города — список снизу, как шторка на сайте: «Все города» и города Сербии, у выбранного галочка. */
export default function CityPicker({ visible, value, onPick, onClose }: {
  visible: boolean
  value: string | null
  onPick: (slug: string | null) => void
  onClose: () => void
}) {
  const insets = useSafeAreaInsets()
  const rows: { slug: string | null; label: string }[] = [{ slug: null, label: 'Все города' }, ...CITY_LIST]
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Закрыть" />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + 8 }]}>
        <View style={styles.handle} />
        <Text style={styles.title}>Город</Text>
        <ScrollView style={{ maxHeight: 460 }}>
          {rows.map((r) => {
            const on = r.slug === value
            return (
              <Pressable key={r.slug ?? 'all'} style={styles.row} onPress={() => { onPick(r.slug); onClose() }}
                accessibilityRole="button" accessibilityState={{ selected: on }}>
                <Text style={[styles.rowText, on && styles.rowOn]}>{r.label}</Text>
                {on && <Ionicons name="checkmark" size={22} color={colors.primary} />}
              </Pressable>
            )
          })}
        </ScrollView>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(17,22,19,0.42)' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8 },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: '#D8DCD8', marginBottom: 8 },
  title: { fontSize: 18, fontWeight: '800', color: colors.ink, paddingHorizontal: 20, paddingBottom: 8 },
  row: { height: 52, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  rowText: { fontSize: 16.5, color: colors.ink },
  rowOn: { fontWeight: '800', color: colors.primaryDeep },
})
