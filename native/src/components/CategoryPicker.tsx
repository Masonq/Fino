import { Ionicons } from '@expo/vector-icons'
import { useEffect, useState } from 'react'
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type Category, fetchCategories } from '../api'
import { colors } from '../theme'

const nameOf = (c: Category) => (typeof c.name === 'string' ? c.name : c.name?.ru || c.slug)

/** Выбор раздела по дереву: раздел → подраздел → … до конечного. Наверху — путь и «назад» на уровень выше. */
export default function CategoryPicker({ visible, onPick, onClose }: {
  visible: boolean; onPick: (c: Category, path: string) => void; onClose: () => void
}) {
  const insets = useSafeAreaInsets()
  const [roots, setRoots] = useState<Category[] | null>(null)
  const [stack, setStack] = useState<Category[]>([])
  useEffect(() => { if (visible && !roots) fetchCategories().then(setRoots).catch(() => setRoots([])) }, [visible, roots])
  useEffect(() => { if (visible) setStack([]) }, [visible])

  const level = stack.length ? (stack[stack.length - 1].children ?? []) : (roots ?? [])
  const choose = (c: Category) => {
    if (c.children && c.children.length) { setStack((s) => [...s, c]); return }
    onPick(c, [...stack, c].map(nameOf).join(' › '))
    onClose()
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Закрыть" />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + 8 }]}>
        <View style={styles.handle} />
        <View style={styles.head}>
          {stack.length > 0 ? (
            <Pressable onPress={() => setStack((s) => s.slice(0, -1))} hitSlop={10} style={styles.back} accessibilityLabel="Назад">
              <Ionicons name="chevron-back" size={22} color={colors.ink} />
            </Pressable>
          ) : null}
          <Text style={styles.title} numberOfLines={1}>{stack.length ? nameOf(stack[stack.length - 1]) : 'Раздел'}</Text>
        </View>
        {roots === null ? <ActivityIndicator style={{ margin: 30 }} color={colors.primary} /> : (
          <ScrollView style={{ maxHeight: 480 }}>
            {level.map((c) => (
              <Pressable key={c.id} style={styles.row} onPress={() => choose(c)} accessibilityRole="button">
                <Text style={styles.rowText}>{nameOf(c)}</Text>
                {c.children && c.children.length ? <Ionicons name="chevron-forward" size={18} color={colors.muted} /> : null}
              </Pressable>
            ))}
          </ScrollView>
        )}
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(17,22,19,0.42)' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8 },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: '#D8DCD8', marginBottom: 6 },
  head: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingBottom: 8, minHeight: 40 },
  back: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  title: { flex: 1, fontSize: 18, fontWeight: '800', color: colors.ink, paddingHorizontal: 8 },
  row: { minHeight: 52, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  rowText: { fontSize: 16.5, color: colors.ink, flex: 1, paddingRight: 8 },
})
