import { Ionicons } from '@expo/vector-icons'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, useWindowDimensions, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { fetchFeed, type FeedItem, type FeedTab, type Filters, saveSearch } from '../../src/api'
import { useAuth } from '../../src/auth'
import { useChats } from '../../src/chats'
import CategoryTiles from '../../src/components/CategoryTiles'
import CityPicker from '../../src/components/CityPicker'
import FiltersSheet, { activeCount } from '../../src/components/FiltersSheet'
import ListingCard from '../../src/components/ListingCard'
import Segmented from '../../src/components/Segmented'
import Skeleton from '../../src/components/Skeleton'
import StoriesRow from '../../src/components/StoriesRow'
import { cityName } from '../../src/format'
import { prefs } from '../../src/prefs'
import { colors, radius, space } from '../../src/theme'

const TABS: { key: FeedTab; label: string }[] = [
  { key: 'all', label: 'Все' }, { key: 'new', label: 'Новое' }, { key: 'free', label: 'Даром' },
]

/**
 * Главная: поиск, «Все / Новое / Даром» с переезжающей плашкой и лента карточек в две колонки.
 * Подгружает дальше при прокрутке, обновляется жестом вниз. Пока грузится — заготовки карточек той же формы.
 */
export default function Feed() {
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [tab, setTab] = useState<FeedTab>('all')
  const [query, setQuery] = useState('')
  const [q, setQ] = useState('')
  const [city, setCity] = useState<string | null>(null)
  const [cityReady, setCityReady] = useState(false)
  const [category, setCategory] = useState<string | null>(null)
  const [cityOpen, setCityOpen] = useState(false)
  const [filters, setFilters] = useState<Filters>({ currency: 'EUR' })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const { token } = useAuth()
  const { notices } = useChats()
  const [savedState, setSavedState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const params = useLocalSearchParams<{ q?: string; city?: string; category?: string; price_min?: string; price_max?: string; with_photo?: string; applied?: string }>()

  // Открыли сохранённый поиск — применяем его к ленте
  useEffect(() => {
    if (!params.applied) return
    setQuery(params.q ?? ''); setQ(params.q ?? '')
    setCategory(params.category || null)
    if (params.city !== undefined) { setCity(params.city || null) }
    setFilters({ currency: 'EUR', priceMin: params.price_min || undefined, priceMax: params.price_max || undefined, withPhoto: params.with_photo === '1' })
  }, [params.applied]) // eslint-disable-line react-hooks/exhaustive-deps
  const searchActive = !!(q || category || filters.priceMin || filters.priceMax || filters.withPhoto)
  useEffect(() => { setSavedState('idle') }, [q, category, city, filters])
  const onSave = async () => {
    if (!token) { router.push('/login'); return }
    setSavedState('saving')
    try {
      await saveSearch(token, { q: q || undefined, category_slug: category || undefined, city: city || undefined, price_min: filters.priceMin || undefined, price_max: filters.priceMax || undefined, with_photo: filters.withPhoto || undefined })
      setSavedState('saved')
    } catch { setSavedState('idle') }
  }
  const [items, setItems] = useState<FeedItem[]>([])
  const [total, setTotal] = useState(0)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [more, setMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const req = useRef(0)
  const listRef = useRef<FlatList<FeedItem>>(null)

  // Город помним на телефоне: открыл приложение — лента сразу своего города
  useEffect(() => {
    prefs.get('plonk_city').then((v) => { setCity(v || null); setCityReady(true) })
  }, [])
  const pickCity = (slug: string | null) => { setCity(slug); prefs.set('plonk_city', slug ?? '') }

  useEffect(() => {
    const t = setTimeout(() => setQ(query.trim()), 350)
    return () => clearTimeout(t)
  }, [query])

  const load = useCallback(async (mode: 'first' | 'refresh') => {
    const id = ++req.current
    if (mode === 'first') setState('loading')
    try {
      const res = await fetchFeed({ tab, offset: 0, q, city, category, filters })
      if (id !== req.current) return
      setItems(res.items)
      setTotal(res.total)
      setState('ready')
    } catch {
      if (id === req.current) setState('error')
    } finally {
      if (mode === 'refresh') setRefreshing(false)
    }
  }, [tab, q, city, category, filters])

  useEffect(() => {
    if (!cityReady) return
    listRef.current?.scrollToOffset({ offset: 0, animated: false })
    load('first')
  }, [load, cityReady])

  const loadMore = async () => {
    if (more || state !== 'ready' || items.length >= total) return
    setMore(true)
    const id = req.current
    try {
      const res = await fetchFeed({ tab, offset: items.length, q, city, category, filters })
      if (id === req.current) setItems((prev) => [...prev, ...res.items.filter((n) => !prev.some((p) => p.id === n.id))])
    } catch {
      // подгрузка не удалась — следующая прокрутка попробует снова
    } finally {
      setMore(false)
    }
  }

  const empty = () => {
    if (state === 'loading') {
      return (
        <View style={styles.skelGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <View key={i} style={{ width: cardW, gap: 8 }}>
              <Skeleton style={{ width: cardW, height: Math.round(cardW * 0.95), borderRadius: radius.card }} />
              <Skeleton style={{ width: cardW * 0.85, height: 14 }} />
              <Skeleton style={{ width: cardW * 0.5, height: 18 }} />
            </View>
          ))}
        </View>
      )
    }
    if (state === 'error') {
      return (
        <View style={styles.center}>
          <Text style={styles.emptyTitle}>Не удалось загрузить ленту</Text>
          <Text style={styles.emptyText}>Проверьте интернет и попробуйте ещё раз.</Text>
          <Pressable style={styles.retry} onPress={() => load('first')}><Text style={styles.retryText}>Повторить</Text></Pressable>
        </View>
      )
    }
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>{q ? 'Ничего не нашлось' : 'Здесь пока пусто'}</Text>
        {!!q && <Text style={styles.emptyText}>Попробуйте сказать иначе или убрать часть слов.</Text>}
      </View>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <View style={[styles.head, styles.headRow]}>
        <View style={[styles.search, { flex: 1 }]}>
          <Pressable style={styles.city} onPress={() => setCityOpen(true)} accessibilityRole="button" accessibilityLabel="Выбрать город">
            <Ionicons name="location-outline" size={16} color={colors.ink} />
            <Text style={styles.cityText} numberOfLines={1}>{city ? cityName(city) : 'Все города'}</Text>
            <Ionicons name="chevron-down" size={14} color={colors.inkSoft} />
          </Pressable>
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Найти на PLONK"
            placeholderTextColor={colors.muted}
            style={styles.searchInput}
            returnKeyType="search"
            clearButtonMode="never"
            autoCorrect={false}
          />
          {!!query && (
            <Pressable onPress={() => setQuery('')} hitSlop={10} accessibilityLabel="Очистить поиск">
              <Ionicons name="close-circle" size={18} color={colors.muted} />
            </Pressable>
          )}
          <Pressable onPress={() => setFiltersOpen(true)} hitSlop={8} style={styles.filterBtn} accessibilityRole="button" accessibilityLabel="Фильтры">
            <Ionicons name="options-outline" size={21} color={colors.ink} />
            {activeCount(filters) > 0 && <View style={styles.filterDot}><Text style={styles.filterDotText}>{activeCount(filters)}</Text></View>}
          </Pressable>
        </View>
        <Pressable style={styles.bell} onPress={() => (token ? router.push('/notifications') : router.push('/login'))} accessibilityRole="button" accessibilityLabel="Уведомления">
          <Ionicons name="notifications-outline" size={23} color={colors.ink} />
          {notices > 0 && <View style={styles.bellDot}><Text style={styles.bellDotText}>{notices > 9 ? '9+' : notices}</Text></View>}
        </Pressable>
      </View>
      <CityPicker visible={cityOpen} value={city} onPick={pickCity} onClose={() => setCityOpen(false)} />
      <FiltersSheet visible={filtersOpen} value={filters} onApply={setFilters} onClose={() => setFiltersOpen(false)} />

      <FlatList
        ref={listRef}
        data={state === 'ready' ? items : []}
        keyExtractor={(it) => it.id}
        numColumns={2}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        columnWrapperStyle={styles.row}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.listHead}>
            {!q && cityReady && <StoriesRow city={city} />}
            {!q && <CategoryTiles value={category} onPick={setCategory} />}
            <View style={styles.tabsRow}>
              <Segmented options={TABS} value={tab} onChange={setTab} />
              {searchActive && (
                <Pressable style={[styles.saveBtn, savedState === 'saved' && styles.saveBtnOn]} disabled={savedState !== 'idle'} onPress={onSave} accessibilityRole="button">
                  <Ionicons name={savedState === 'saved' ? 'bookmark' : 'bookmark-outline'} size={16} color={savedState === 'saved' ? '#fff' : colors.primaryDeep} />
                  <Text style={[styles.saveText, savedState === 'saved' && { color: '#fff' }]}>{savedState === 'saved' ? 'Сохранено' : 'Сохранить поиск'}</Text>
                </Pressable>
              )}
            </View>
          </View>
        }
        ListEmptyComponent={empty}
        onEndReached={loadMore}
        onEndReachedThreshold={0.6}
        ListFooterComponent={more ? <ActivityIndicator style={{ marginVertical: 16 }} color={colors.primary} /> : null}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load('refresh') }} tintColor={colors.primary} colors={[colors.primary]} />}
        keyboardDismissMode="on-drag"
        removeClippedSubviews
        initialNumToRender={6}
        windowSize={7}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  head: { paddingHorizontal: space.page, paddingTop: 6, paddingBottom: 10 },
  listHead: { gap: 12, paddingBottom: 2 },
  headRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bell: { width: 44, height: 46, alignItems: 'center', justifyContent: 'center' },
  bellDot: { position: 'absolute', top: 6, right: 4, minWidth: 17, height: 17, borderRadius: 9, paddingHorizontal: 4, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: colors.bg },
  bellDotText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  tabsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, paddingHorizontal: space.page },
  saveBtn: { flexDirection: 'row', alignItems: 'center', gap: 5, height: 36, paddingHorizontal: 12, borderRadius: 18, backgroundColor: colors.primarySoft },
  saveBtnOn: { backgroundColor: colors.primary },
  saveText: { fontSize: 13.5, fontWeight: '800', color: colors.primaryDeep },
  filterBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  filterDot: { position: 'absolute', top: 2, right: 0, minWidth: 16, height: 16, borderRadius: 8, paddingHorizontal: 4, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  filterDotText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  city: { flexDirection: 'row', alignItems: 'center', gap: 4, height: 36, paddingHorizontal: 10, borderRadius: 11, backgroundColor: colors.surface, maxWidth: 150, flexShrink: 0 },
  cityText: { fontSize: 13.5, fontWeight: '800', color: colors.ink, flexShrink: 1 },
  search: {
    flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, paddingHorizontal: 14,
    borderRadius: radius.field, backgroundColor: colors.sunken, paddingLeft: 5,
  },
  // flexBasis 0 и minWidth 0 — поле сжимается, и кнопка фильтров остаётся внутри строки поиска
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontSize: 15.5, color: colors.ink, paddingVertical: 0 },
  list: { paddingHorizontal: 0, paddingBottom: 24, gap: space.gap },
  row: { gap: space.gap, paddingHorizontal: space.page },
  skelGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.gap, paddingHorizontal: space.page },
  center: { alignItems: 'center', paddingTop: 80, paddingHorizontal: 32, gap: 8 },
  emptyTitle: { fontSize: 18, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  emptyText: { fontSize: 14.5, color: colors.inkSoft, textAlign: 'center', lineHeight: 20 },
  retry: { marginTop: 8, height: 44, paddingHorizontal: 20, borderRadius: 12, backgroundColor: colors.primary, justifyContent: 'center' },
  retryText: { color: '#fff', fontWeight: '800', fontSize: 15 },
})
