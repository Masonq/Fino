import { tr } from '../i18n'
import { useEffect, useState } from 'react'
import { Modal, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import type { Filters } from '../api'
import { colors } from '../theme'
import Segmented from './Segmented'

const SORTS: { key: NonNullable<Filters['sort']>; label: string }[] = [
  { key: '', label: 'По умолчанию' }, { key: 'new', label: 'Сначала новые' }, { key: 'cheap', label: 'Дешевле' }, { key: 'expensive', label: 'Дороже' },
]

export const activeCount = (f: Filters) =>
  [f.priceMin || f.priceMax, f.withPhoto, f.delivery, f.sort].filter(Boolean).length

/** Фильтры ленты — шторка снизу: цена от/до (в евро или динарах), только с фото, с доставкой, сортировка. */
export default function FiltersSheet({ visible, value, onApply, onClose }: {
  visible: boolean; value: Filters; onApply: (f: Filters) => void; onClose: () => void
}) {
  const insets = useSafeAreaInsets()
  const [f, setF] = useState<Filters>(value)
  useEffect(() => { if (visible) setF(value) }, [visible, value])
  const set = (patch: Partial<Filters>) => setF((prev) => ({ ...prev, ...patch }))
  const digits = (v: string) => v.replace(/\D/g, '').slice(0, 9)

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel={tr('Закрыть')} />
      <View style={[styles.sheet, { paddingBottom: insets.bottom + 12 }]}>
        <View style={styles.handle} />
        <View style={styles.titleRow}>
          <Text style={styles.title}>{tr('Фильтры')}</Text>
          <Pressable onPress={() => setF({ currency: 'EUR' })} hitSlop={10}><Text style={styles.reset}>{tr('Сбросить')}</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={{ gap: 18, paddingHorizontal: 20 }} keyboardShouldPersistTaps="handled">
          <View style={{ gap: 10 }}>
            <View style={styles.labelRow}>
              <Text style={styles.label}>{tr('Цена')}</Text>
              <Segmented options={[{ key: 'EUR', label: '€' }, { key: 'RSD', label: 'RSD' }]} value={f.currency ?? 'EUR'} onChange={(c) => set({ currency: c as 'EUR' | 'RSD' })} />
            </View>
            <View style={styles.priceRow}>
              <TextInput value={f.priceMin ?? ''} onChangeText={(v) => set({ priceMin: digits(v) })} placeholder={tr('от')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.input} />
              <Text style={styles.dash}>—</Text>
              <TextInput value={f.priceMax ?? ''} onChangeText={(v) => set({ priceMax: digits(v) })} placeholder={tr('до')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.input} />
            </View>
          </View>
          <View style={styles.switchRow}>
            <Text style={styles.switchText}>{tr('Только с фото')}</Text>
            <Switch value={!!f.withPhoto} onValueChange={(v) => set({ withPhoto: v })} trackColor={{ true: colors.primary, false: '#D8DCD8' }} />
          </View>
          <View style={styles.switchRow}>
            <Text style={styles.switchText}>{tr('С доставкой')}</Text>
            <Switch value={!!f.delivery} onValueChange={(v) => set({ delivery: v })} trackColor={{ true: colors.primary, false: '#D8DCD8' }} />
          </View>
          <View style={{ gap: 4 }}>
            <Text style={styles.label}>{tr('Сортировка')}</Text>
            {SORTS.map((s) => {
              const on = (f.sort ?? '') === s.key
              return (
                <Pressable key={s.key || 'default'} style={styles.sortRow} onPress={() => set({ sort: s.key })} accessibilityRole="radio" accessibilityState={{ selected: on }}>
                  <View style={[styles.radio, on && styles.radioOn]}>{on && <View style={styles.radioDot} />}</View>
                  <Text style={[styles.sortText, on && styles.sortOn]}>{tr(s.label)}</Text>
                </Pressable>
              )
            })}
          </View>
        </ScrollView>
        <Pressable style={styles.apply} onPress={() => { onApply(f); onClose() }}>
          <Text style={styles.applyText}>{tr('Показать')}</Text>
        </Pressable>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(17,22,19,0.42)' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8, maxHeight: '88%' },
  handle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: '#D8DCD8', marginBottom: 6 },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingBottom: 12 },
  title: { fontSize: 20, fontWeight: '800', color: colors.ink },
  reset: { fontSize: 15, fontWeight: '700', color: colors.primaryDeep },
  labelRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  label: { fontSize: 16, fontWeight: '800', color: colors.ink },
  priceRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  // flexBasis 0 и minWidth 0 — два поля делят ширину поровну и не вылезают за край
  input: { flex: 1, flexBasis: 0, minWidth: 0, height: 48, borderRadius: 13, backgroundColor: colors.sunken, paddingHorizontal: 14, fontSize: 16, color: colors.ink },
  dash: { color: colors.muted, fontSize: 16 },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 40 },
  switchText: { fontSize: 16, color: colors.ink },
  sortRow: { flexDirection: 'row', alignItems: 'center', gap: 12, height: 44 },
  radio: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: '#C9CEC9', alignItems: 'center', justifyContent: 'center' },
  radioOn: { borderColor: colors.primary },
  radioDot: { width: 11, height: 11, borderRadius: 6, backgroundColor: colors.primary },
  sortText: { fontSize: 16, color: colors.ink },
  sortOn: { fontWeight: '700' },
  apply: { marginHorizontal: 20, marginTop: 14, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  applyText: { color: '#fff', fontSize: 16, fontWeight: '800' },
})
