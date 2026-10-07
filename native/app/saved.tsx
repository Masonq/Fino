import { tr } from '../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Alert, FlatList, Pressable, StyleSheet, Switch, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { deleteSavedSearch, type SavedSearch, savedSearches, type SearchFilters, toggleSavedSearch } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { cityName } from '../src/format'
import { colors, font } from '../src/theme'

/** Подпись поиска по фильтрам: «велосипед · Белград · до 300». */
export function describeSearch(f: SearchFilters, name?: string | null): string {
  if (name) return name
  const parts = [f.q, f.city ? cityName(f.city) : '', f.price_min ? tr('от {n}', { n: f.price_min }) : '', f.price_max ? tr('до {n}', { n: f.price_max }) : '', f.with_photo ? tr('с фото') : '']
  return parts.filter(Boolean).join(' · ') || tr('Все объявления')
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
  const remove = (s: SavedSearch) => Alert.alert(tr('Удалить поиск?'), describeSearch(s.filters, s.name), [
    { text: tr('Отмена'), style: 'cancel' },
    { text: tr('Удалить'), style: 'destructive', onPress: async () => { await deleteSavedSearch(token as string, s.id).catch(() => {}); load() } },
  ])

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.head}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}>
          <Icon name="back" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.h1}>{tr('Сохранённые поиски')}</Text>
        {!!items?.length && <Text style={styles.count}>{items.length}</Text>}
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <FlatList
          data={items}
          keyExtractor={(s) => s.id}
          contentContainerStyle={items.length === 0 ? { flexGrow: 1 } : { paddingHorizontal: 16, paddingBottom: 24 }}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <Pressable onPress={() => open(item)} style={{ gap: 2 }}>
                <Text style={styles.title} numberOfLines={2}>{item.name || describeSearch(item.filters, item.name)}</Text>
                <Text style={styles.sub} numberOfLines={2}>{describeSearch(item.filters, item.name)}</Text>
              </Pressable>
              <View style={styles.rowFoot}>
                <Pressable style={styles.check} onPress={() => toggle(item, !item.notify_enabled)} accessibilityRole="checkbox" accessibilityState={{ checked: item.notify_enabled }} hitSlop={6}>
                  <View style={[styles.box, item.notify_enabled && styles.boxOn]}>{item.notify_enabled && <Icon name="check" size={12} color="#fff" />}</View>
                  <Text style={styles.checkText}>{tr('Уведомлять')}</Text>
                </Pressable>
                <Pressable onPress={() => remove(item)} hitSlop={8}><Text style={styles.del}>{tr('Удалить')}</Text></Pressable>
              </View>
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <View style={styles.circle}><Ionicons name="bookmark-outline" size={28} color={colors.primaryDeep} /></View>
              <Text style={styles.emptyTitle}>{tr('Нет сохранённых поисков')}</Text>
              <Text style={styles.emptyText}>{tr('Найдите что-нибудь на главной и нажмите «Сохранить поиск» — пришлём уведомление, когда появится новое.')}</Text>
            </View>
          }
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  // как .saved-row сайта: строки с разделителем, «Уведомлять» галочкой, «Удалить» красным текстом
  count: { fontSize: 12, fontFamily: font[800], color: colors.primaryDeep, backgroundColor: colors.primarySoft, borderRadius: 8, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 3, marginLeft: 8 },
  row: { paddingVertical: 12, gap: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  rowFoot: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  check: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  box: { width: 20, height: 20, borderRadius: 5, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  boxOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkText: { fontSize: 13.5, fontFamily: font[700], color: colors.ink },
  del: { fontSize: 13.5, fontFamily: font[700], color: '#E5533D' },
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  h1: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  card: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  sub: { fontSize: 13, fontFamily: font[500], color: colors.muted },
  trash: { width: 32, alignItems: 'center' },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  emptyText: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
})
