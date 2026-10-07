import EmptyArt from '../src/components/EmptyArt'
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
      {(
        <FlatList data={items ?? []} keyExtractor={(i) => i.id} numColumns={2} renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
          ListHeaderComponent={<>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Вы смотрели')}</Text>
        {!!items?.length && <Pressable onPress={async () => { await clearViewed(); setItems([]) }} hitSlop={8}><Text style={styles.clear}>{tr('Очистить')}</Text></Pressable>}
      </View>

          </>}
          columnWrapperStyle={{ gap: space.gap, paddingHorizontal: space.page }} contentContainerStyle={(items ?? []).length ? { gap: space.gap, paddingBottom: 24 } : undefined}
          ListEmptyComponent={items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : <View style={styles.emptyBox}><EmptyArt name="history" /><Text style={styles.emptyMsg}>{tr('Здесь появятся объявления, которые вы открывали')}</Text><Pressable style={styles.emptyBtn} onPress={() => router.navigate('/')}><Text style={styles.emptyBtnText}>{tr('К объявлениям')}</Text></Pressable></View>} />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  emptyBox: { alignItems: 'center', gap: 14, paddingTop: 44, paddingHorizontal: 32 },
  emptyIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  emptyMsg: { fontSize: 13.5, lineHeight: 19, fontFamily: font[500], color: colors.muted, textAlign: 'center' },
  emptyBtn: { height: 42, paddingHorizontal: 20, borderRadius: 13, backgroundColor: colors.inverse, justifyContent: 'center' },
  emptyBtnText: { color: colors.onInverse, fontSize: 14.5, fontFamily: font[800] },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingTop: 6, paddingBottom: 12 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  clear: { fontSize: 14.5, fontFamily: font[700], color: colors.primaryDeep },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 8 },
  emptyTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink },
  emptyText: { fontSize: 15, lineHeight: 21, fontFamily: font[400], color: colors.inkSoft, textAlign: 'center' },
})
