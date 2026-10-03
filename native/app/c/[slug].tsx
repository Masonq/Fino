import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type Category, fetchCategories, fetchFeed, type FeedItem, type Filters } from '../../src/api'
import Icon from '../../src/components/Icon'
import ListingCard from '../../src/components/ListingCard'
import { SITE } from '../../src/config'
import { select } from '../../src/haptics'
import { getLang, plural, tr } from '../../src/i18n'
import { colors, font, space } from '../../src/theme'

const SORTS: [Filters['sort'], string][] = [['', 'По умолчанию'], ['new', 'Сначала новые'], ['cheap', 'Дешевле'], ['expensive', 'Дороже']]
const nameOf = (c?: Category | null) => (!c ? '' : typeof c.name === 'string' ? c.name : c.name?.[getLang()] || c.name?.ru || c.slug)
function findNode(list: Category[], slug: string): Category | null {
  for (const c of list) {
    if (c.slug === slug) return c
    const hit = c.children ? findNode(c.children, slug) : null
    if (hit) return hit
  }
  return null
}

/**
 * Страница раздела — как CategoryLanding сайта: название и число предложений, подразделы с картинками
 * (вглубь — своя страница), поиск внутри раздела, цена от/до, сортировка, объявления сеткой с подгрузкой.
 */
export default function CategoryScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [node, setNode] = useState<Category | null>(null)
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [min, setMin] = useState('')
  const [max, setMax] = useState('')
  const [sort, setSort] = useState<Filters['sort']>('')
  const [applied, setApplied] = useState({ q: '', min: '', max: '', sort: '' as Filters['sort'] })
  const [more, setMore] = useState(false)
  const req = useRef(0)

  useEffect(() => { fetchCategories().then((list) => setNode(findNode(list, String(slug)))).catch(() => {}) }, [slug])

  const load = useCallback(async () => {
    const id = ++req.current
    setItems(null)
    try {
      const res = await fetchFeed({ tab: 'all', offset: 0, q: applied.q, category: String(slug), filters: { currency: 'EUR', priceMin: applied.min, priceMax: applied.max, sort: applied.sort } })
      if (id === req.current) { setItems(res.items); setTotal(res.total) }
    } catch { if (id === req.current) setItems([]) }
  }, [slug, applied])
  useEffect(() => { load() }, [load])

  const loadMore = async () => {
    if (!items || more || items.length >= total) return
    setMore(true)
    try {
      const res = await fetchFeed({ tab: 'all', offset: items.length, q: applied.q, category: String(slug), filters: { currency: 'EUR', priceMin: applied.min, priceMax: applied.max, sort: applied.sort } })
      setItems((prev) => [...(prev ?? []), ...res.items.filter((n) => !(prev ?? []).some((p) => p.id === n.id))])
    } finally { setMore(false) }
  }

  const dirty = q !== applied.q || min !== applied.min || max !== applied.max || sort !== applied.sort
  const subs = node?.children ?? []
  const head = (
    <View>
      <View style={[styles.top, { paddingTop: insets.top + 6 }]}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.title} numberOfLines={1}>{nameOf(node) || ' '}</Text>
          <Text style={styles.count}>{items ? `${total} ${plural(total, { ru: ['предложение', 'предложения', 'предложений'], en: ['offer', 'offers'], sr: ['ponuda', 'ponude', 'ponuda'] })}` : ' '}</Text>
        </View>
      </View>

      {subs.length > 0 && (
        <View style={styles.subs}>
          {subs.map((c) => (
            <Pressable key={c.id} style={styles.sub} onPress={() => { select(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
              <Image source={{ uri: `${SITE}/cat/${c.slug}.png` }} style={styles.subArt} contentFit="contain" />
              <Text style={styles.subName} numberOfLines={2}>{nameOf(c)}</Text>
              <Icon name="forward" size={14} color={colors.muted} />
            </Pressable>
          ))}
        </View>
      )}

      <View style={styles.form}>
        <View style={styles.search}>
          <Icon name="search" size={17} color={colors.muted} />
          <TextInput value={q} onChangeText={setQ} placeholder={tr('Поиск в разделе')} placeholderTextColor={colors.muted} style={styles.searchInput} returnKeyType="search" onSubmitEditing={() => setApplied({ q, min, max, sort })} />
        </View>
        <View style={styles.priceRow}>
          <TextInput value={min} onChangeText={(v) => setMin(v.replace(/\D/g, '').slice(0, 9))} placeholder={tr('Цена от, €')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.priceInput} />
          <TextInput value={max} onChangeText={(v) => setMax(v.replace(/\D/g, '').slice(0, 9))} placeholder={tr('до, €')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.priceInput} />
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.sorts}>
          {SORTS.map(([k, l]) => (
            <Pressable key={k || 'def'} onPress={() => { select(); setSort(k) }} style={[styles.sortChip, sort === k && styles.sortOn]}>
              <Text style={[styles.sortText, sort === k && styles.sortTextOn]}>{tr(l)}</Text>
            </Pressable>
          ))}
        </ScrollView>
        {dirty && (
          <Pressable style={styles.show} onPress={() => setApplied({ q, min, max, sort })}><Text style={styles.showText}>{tr('Показать')}</Text></Pressable>
        )}
      </View>
      {items === null && <ActivityIndicator style={{ marginTop: 20 }} color={colors.primary} />}
    </View>
  )

  return (
    <View style={styles.page}>
      <FlatList
        data={items ?? []}
        keyExtractor={(i) => i.id}
        numColumns={2}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        columnWrapperStyle={styles.row}
        contentContainerStyle={{ gap: space.gap, paddingBottom: 32 }}
        ListHeaderComponent={head}
        keyboardShouldPersistTaps="handled"
        onEndReachedThreshold={0.6}
        onEndReached={loadMore}
        ListEmptyComponent={items ? <Text style={styles.empty}>{tr('В этом разделе пока ничего нет. Попробуйте изменить условия.')}</Text> : null}
        ListFooterComponent={more ? <ActivityIndicator style={{ marginVertical: 16 }} color={colors.primary} /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingBottom: 10 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 21, fontFamily: font[800], letterSpacing: -0.3, color: colors.ink },
  count: { fontSize: 13, fontFamily: font[600], color: colors.muted, marginTop: 1 },
  subs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingHorizontal: space.page, marginBottom: 12 },
  sub: { width: '48.8%', flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 56, paddingLeft: 6, paddingRight: 10, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  subArt: { width: 42, height: 42 },
  subName: { flex: 1, fontSize: 13, lineHeight: 16, fontFamily: font[700], color: colors.ink },
  form: { paddingHorizontal: space.page, gap: 8, marginBottom: 12 },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13 },
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontSize: 15, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  priceRow: { flexDirection: 'row', gap: 8 },
  priceInput: { flex: 1, flexBasis: 0, minWidth: 0, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13, fontSize: 15, fontFamily: font[500], color: colors.ink },
  sorts: { gap: 6 },
  sortChip: { height: 34, paddingHorizontal: 12, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  sortOn: { backgroundColor: colors.primary },
  sortText: { fontSize: 13, fontFamily: font[700], color: colors.inkSoft },
  sortTextOn: { color: '#fff' },
  show: { height: 48, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  showText: { color: '#fff', fontSize: 15.5, fontFamily: font[800] },
  row: { gap: space.gap, paddingHorizontal: space.page },
  empty: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 24, paddingHorizontal: 32 },
})
