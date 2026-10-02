import { Ionicons } from '@expo/vector-icons'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, useWindowDimensions, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { fetchFeed, type FeedItem, type FeedTab } from '../../src/api'
import ListingCard from '../../src/components/ListingCard'
import Segmented from '../../src/components/Segmented'
import Skeleton from '../../src/components/Skeleton'
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
  const [items, setItems] = useState<FeedItem[]>([])
  const [total, setTotal] = useState(0)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [more, setMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const req = useRef(0)
  const listRef = useRef<FlatList<FeedItem>>(null)

  useEffect(() => {
    const t = setTimeout(() => setQ(query.trim()), 350)
    return () => clearTimeout(t)
  }, [query])

  const load = useCallback(async (mode: 'first' | 'refresh') => {
    const id = ++req.current
    if (mode === 'first') setState('loading')
    try {
      const res = await fetchFeed({ tab, offset: 0, q })
      if (id !== req.current) return
      setItems(res.items)
      setTotal(res.total)
      setState('ready')
    } catch {
      if (id === req.current) setState('error')
    } finally {
      if (mode === 'refresh') setRefreshing(false)
    }
  }, [tab, q])

  useEffect(() => {
    listRef.current?.scrollToOffset({ offset: 0, animated: false })
    load('first')
  }, [load])

  const loadMore = async () => {
    if (more || state !== 'ready' || items.length >= total) return
    setMore(true)
    const id = req.current
    try {
      const res = await fetchFeed({ tab, offset: items.length, q })
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
      <View style={styles.head}>
        <View style={styles.search}>
          <Ionicons name="search" size={18} color={colors.muted} />
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
        </View>
        <Segmented options={TABS} value={tab} onChange={setTab} />
      </View>

      <FlatList
        ref={listRef}
        data={state === 'ready' ? items : []}
        keyExtractor={(it) => it.id}
        numColumns={2}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        columnWrapperStyle={styles.row}
        contentContainerStyle={styles.list}
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
  head: { paddingHorizontal: space.page, paddingTop: 6, paddingBottom: 10, gap: 10 },
  search: {
    flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, paddingHorizontal: 14,
    borderRadius: radius.field, backgroundColor: colors.sunken,
  },
  searchInput: { flex: 1, fontSize: 15.5, color: colors.ink, paddingVertical: 0 },
  list: { paddingHorizontal: 0, paddingBottom: 24, gap: space.gap },
  row: { gap: space.gap, paddingHorizontal: space.page },
  skelGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.gap, paddingHorizontal: space.page },
  center: { alignItems: 'center', paddingTop: 80, paddingHorizontal: 32, gap: 8 },
  emptyTitle: { fontSize: 18, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  emptyText: { fontSize: 14.5, color: colors.inkSoft, textAlign: 'center', lineHeight: 20 },
  retry: { marginTop: 8, height: 44, paddingHorizontal: 20, borderRadius: 12, backgroundColor: colors.primary, justifyContent: 'center' },
  retryText: { color: '#fff', fontWeight: '800', fontSize: 15 },
})
