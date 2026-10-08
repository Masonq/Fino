import EmptyArt from '../src/components/EmptyArt'
import { plural, tr } from '../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { router, useFocusEffect } from 'expo-router'
import Icon from '../src/components/Icon'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  FlatList, LayoutAnimation, ScrollView, Platform, Pressable, RefreshControl, StyleSheet, Text, UIManager, useWindowDimensions, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { favoriteList, type FeedItem } from '../src/api'
import { useAuth } from '../src/auth'
import ListingCard from '../src/components/ListingCard'
import Skeleton from '../src/components/Skeleton'
import { useFavorites } from '../src/favorites'
import { readCache, writeCache } from '../src/cache'
import { onRetry } from '../src/net'
import { colors, radius, space, font } from '../src/theme'

if (Platform.OS === 'android') UIManager.setLayoutAnimationEnabledExperimental?.(true)

/**
 * Избранное: гостю — приглашение войти; вошедшему — сохранённые объявления той же сеткой, что лента.
 * Сняли сердечко — карточка плавно уходит, соседи съезжают. Обновляется при каждом открытии вкладки.
 */
export default function Favorites() {
  const { token, ready } = useAuth()
  const { isFav, version, loaded } = useFavorites()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const req = useRef(0)

  const load = useCallback(async () => {
    if (!token) return
    const id = ++req.current
    const cached = await readCache<FeedItem[]>('favorites')
    if (cached && id === req.current) setItems((v) => v ?? cached)
    try {
      const res = await favoriteList(token)
      if (id === req.current) { setItems(res.items); setFailed(false); writeCache('favorites', res.items) }
    } catch {
      if (id === req.current && !cached) setFailed(true)
    } finally {
      if (id === req.current) setRefreshing(false)
    }
  }, [token])

  useFocusEffect(useCallback(() => { load() }, [load]))
  useEffect(() => onRetry(() => { load() }), [load])
  useEffect(() => { if (!token) setItems(null) }, [token])

  // Сняли сердечко где угодно (здесь или в ленте) — карточка уходит плавно
  const shown = items && loaded ? items.filter((i) => isFav(i.id)) : items
  // PLONK 2.0: порядок — недавние / подешевели / дешевле / дороже (как на сайте)
  const [sort, setSort] = useState<'added' | 'drop' | 'cheap' | 'exp'>('added')
  const dropped = (l: FeedItem) => l.previous_price != null && l.price != null && Number(l.previous_price) > Number(l.price)
  const priceOf = (l: FeedItem) => (l.is_free ? 0 : l.price == null ? Infinity : Number(l.price) * (l.currency === 'RSD' ? 1 / 117 : 1))
  const visible = !shown || sort === 'added' ? shown
    : sort === 'drop' ? [...shown].sort((a, b) => Number(dropped(b)) - Number(dropped(a)))
      : [...shown].sort((a, b) => (sort === 'cheap' ? priceOf(a) - priceOf(b) : priceOf(b) - priceOf(a)))
  const nDropped = shown ? shown.filter(dropped).length : 0
  const prevCount = useRef(visible?.length ?? 0)
  useEffect(() => {
    const n = visible?.length ?? 0
    if (n !== prevCount.current) LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut)
    prevCount.current = n
  }, [visible?.length])
  useEffect(() => { if (token) load() }, [version]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!ready) return <SafeAreaView style={styles.page} />

  if (!token) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <EmptyArt name="favorites" />
        <Text style={styles.title}>{tr('Сохраняйте понравившееся')}</Text>
        <Text style={styles.text}>{tr('Нажмите сердечко на объявлении — оно появится здесь. Для этого нужно войти.')}</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>{tr('Войти')}</Text></Pressable>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <View style={styles.headRow}>
        {/* «Избранное» открывается сердечком с главной или из профиля — есть куда вернуться */}
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.navigate('/'))} hitSlop={10} accessibilityLabel={tr('Назад')} style={{ marginRight: 8, width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 }}>
          <Icon name="back" size={22} color={colors.ink} />
        </Pressable>
        {/* как на сайте: число вещей — подводкой над заголовком */}
        <View style={{ flex: 1 }}>
          <Text style={styles.kicker}>{visible && visible.length > 0 ? plural(visible.length, { ru: ['{n} вещь', '{n} вещи', '{n} вещей'], en: ['{n} item', '{n} items', '{n} items'], sr: ['{n} stvar', '{n} stvari', '{n} stvari'] }) : ' '}</Text>
          <Text style={styles.h1}>{tr('Избранное')}</Text>
        </View>
      </View>
      {!!visible && visible.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingHorizontal: space.page, paddingBottom: 12 }} style={{ flexGrow: 0 }}>
          {([['added', tr('Недавние')], ['drop', nDropped ? `${tr('Подешевели')} · ${nDropped}` : tr('Подешевели')], ['cheap', tr('Дешевле')], ['exp', tr('Дороже')]] as const).map(([k, label]) => (
            <Pressable key={k} onPress={() => setSort(k)} style={[styles.sortChip, sort === k && styles.sortChipOn]}>
              <Text style={[styles.sortText, sort === k && { color: colors.onInverse }]}>{label}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}
      {visible === null ? (
        failed ? (
          <View style={styles.center}>
            <Text style={styles.title}>{tr('Не удалось загрузить')}</Text>
            <Pressable style={styles.cta} onPress={load}><Text style={styles.ctaText}>{tr('Повторить')}</Text></Pressable>
          </View>
        ) : (
          <View style={styles.skelGrid}>
            {Array.from({ length: 4 }).map((_, i) => (
              <View key={i} style={{ width: cardW, gap: 8 }}>
                <Skeleton style={{ width: cardW, height: Math.round(cardW * 0.95), borderRadius: radius.card }} />
                <Skeleton style={{ width: cardW * 0.85, height: 14 }} />
                <Skeleton style={{ width: cardW * 0.5, height: 18 }} />
              </View>
            ))}
          </View>
        )
      ) : (
        <FlatList
          data={visible}
          keyExtractor={(it) => it.id}
          numColumns={2}
          renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
          columnWrapperStyle={styles.row}
          contentContainerStyle={[styles.list, visible.length === 0 && { flexGrow: 1 }]}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} tintColor={colors.primary} colors={[colors.primary]} />}
          ListEmptyComponent={
            <View style={styles.center}>
              <EmptyArt name="favorites" />
              <Text style={styles.title}>{tr('Пока пусто')}</Text>
              <Text style={styles.text}>{tr('Нажмите сердечко на объявлении — оно сохранится здесь.')}</Text>
              <Pressable style={styles.cta} onPress={() => router.navigate('/')}><Text style={styles.ctaText}>{tr('Смотреть ленту')}</Text></Pressable>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  kicker: { fontFamily: font[600], fontSize: 14, color: colors.inkSoft },
  page: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  sortChip: { height: 36, paddingHorizontal: 14, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, justifyContent: 'center' },
  sortChipOn: { backgroundColor: colors.inverse, borderColor: colors.inverse },
  sortText: { fontFamily: font[600], fontSize: 14, color: colors.ink },
  headRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: space.page + 4, paddingTop: 10, paddingBottom: 12 },
  // Как заголовок страницы и .fav-count сайта
  h1: { fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  count: { fontSize: 15, fontFamily: font[700], color: colors.muted, marginLeft: 2 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 32, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  list: { paddingBottom: 24, gap: space.gap },
  row: { gap: space.gap, paddingHorizontal: space.page },
  skelGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.gap, paddingHorizontal: space.page },
})
