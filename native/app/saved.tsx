import { Ionicons } from '@expo/vector-icons'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Alert, FlatList, Pressable, StyleSheet, Switch, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { deleteSavedSearch, type SavedSearch, savedSearches, type SearchFilters, toggleSavedSearch } from '../src/api'
import { useAuth } from '../src/auth'
import { cityName } from '../src/format'
import { colors } from '../src/theme'

/** Подпись поиска по фильтрам: «велосипед · Белград · до 300». */
export function describeSearch(f: SearchFilters, name?: string | null): string {
  if (name) return name
  const parts = [f.q, f.city ? cityName(f.city) : '', f.price_min ? `от ${f.price_min}` : '', f.price_max ? `до ${f.price_max}` : '', f.with_photo ? 'с фото' : '']
  return parts.filter(Boolean).join(' · ') || 'Все объявления'
}

/** Сохранённые поиски: открыть (поиск применяется к ленте), оповещения о новых — вкл/выкл, удалить. */
export default function Saved() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [items, setItems] = useState<SavedSearch[] | null>(null)
  const load = useCallback(async () => {
    if (!token) return
    try { setItems((await savedSearches(token)).items) } catch { setItems((v) => v ?? []) }
  }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const open = (s: SavedSearch) => {
    const f = s.filters
    router.navigate({ pathname: '/', params: {
      q: f.q ?? '', city: f.city ?? '', category: f.category_slug ?? '', price_min: f.price_min ?? '', price_max: f.price_max ?? '',
      with_photo: f.with_photo ? '1' : '', applied: String(Date.now()),
    } })
  }
  const toggle = async (s: SavedSearch, on: boolean) => {
    setItems((all) => (all ?? []).map((x) => (x.id === s.id ? { ...x, notify_enabled: on } : x)))
    try { await toggleSavedSearch(token as string, s.id, on) } catch { load() }
  }
  const remove = (s: SavedSearch) => Alert.alert('Удалить поиск?', describeSearch(s.filters, s.name), [
    { text: 'Отмена', style: 'cancel' },
    { text: 'Удалить', style: 'destructive', onPress: async () => { await deleteSavedSearch(token as string, s.id).catch(() => {}); load() } },
  ])

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.head}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel="Назад">
          <Ionicons name="chevron-back" size={26} color={colors.ink} />
        </Pressable>
        <Text style={styles.h1}>Сохранённые поиски</Text>
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <FlatList
          data={items}
          keyExtractor={(s) => s.id}
          contentContainerStyle={items.length === 0 ? { flexGrow: 1 } : { padding: 16, gap: 10 }}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <Pressable style={{ flex: 1, gap: 3 }} onPress={() => open(item)}>
                <Text style={styles.title} numberOfLines={2}>{describeSearch(item.filters, item.name)}</Text>
                <Text style={styles.sub}>{item.notify_enabled ? 'Пришлём уведомление о новых' : 'Оповещения выключены'}</Text>
              </Pressable>
              <Switch value={item.notify_enabled} onValueChange={(v) => toggle(item, v)} trackColor={{ true: colors.primary, false: '#D8DCD8' }} />
              <Pressable onPress={() => remove(item)} hitSlop={8} style={styles.trash} accessibilityLabel="Удалить поиск">
                <Ionicons name="trash-outline" size={20} color={colors.muted} />
              </Pressable>
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.circle}><Ionicons name="bookmark-outline" size={28} color={colors.primaryDeep} /></View>
              <Text style={styles.emptyTitle}>Нет сохранённых поисков</Text>
              <Text style={styles.emptyText}>Найдите что-нибудь на главной и нажмите «Сохранить поиск» — пришлём уведомление, когда появится новое.</Text>
            </View>
          }
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  h1: { fontSize: 20, fontWeight: '800', color: colors.ink, marginLeft: 4 },
  card: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  title: { fontSize: 16, fontWeight: '700', color: colors.ink },
  sub: { fontSize: 13, color: colors.muted },
  trash: { width: 32, alignItems: 'center' },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { fontSize: 20, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  emptyText: { fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
})
