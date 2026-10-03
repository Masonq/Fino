import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type FeedItem, listingsByIds } from '../src/api'
import Icon from '../src/components/Icon'
import ListingCard from '../src/components/ListingCard'
import { clearViewed, viewedIds } from '../src/history'
import { tr } from '../src/i18n'
import { colors, font, space } from '../src/theme'

/** «Вы смотрели» — как на сайте: недавно открытые объявления сеткой, свежие первыми; «Очистить». */
export default function History() {
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [items, setItems] = useState<FeedItem[] | null>(null)

  const load = useCallback(async () => {
    const ids = await viewedIds()
    if (!ids.length) { setItems([]); return }
    try {
      const res = await listingsByIds(ids)
      const list = Array.isArray(res) ? res : res.items
      const order = new Map(ids.map((id, i) => [id, i]))
      setItems([...list].sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0)))
    } catch { setItems((v) => v ?? []) }
  }, [])
  useFocusEffect(useCallback(() => { load() }, [load]))

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Вы смотрели')}</Text>
        {!!items?.length && <Pressable onPress={async () => { await clearViewed(); setItems([]) }} hitSlop={8}><Text style={styles.clear}>{tr('Очистить')}</Text></Pressable>}
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <FlatList data={items} keyExtractor={(i) => i.id} numColumns={2} renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
          columnWrapperStyle={{ gap: space.gap, paddingHorizontal: space.page }} contentContainerStyle={items.length ? { gap: space.gap, paddingBottom: 24 } : { flexGrow: 1 }}
          ListEmptyComponent={<View style={styles.empty}><Text style={styles.emptyTitle}>{tr('Пока пусто')}</Text><Text style={styles.emptyText}>{tr('Здесь появятся объявления, которые вы открывали.')}</Text></View>} />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingLeft: 8, paddingRight: 16, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { flex: 1, fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  clear: { fontSize: 14.5, fontFamily: font[700], color: colors.primaryDeep },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 8 },
  emptyTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink },
  emptyText: { fontSize: 15, lineHeight: 21, fontFamily: font[400], color: colors.inkSoft, textAlign: 'center' },
})
