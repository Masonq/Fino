import { Ionicons } from '@expo/vector-icons'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  FlatList, LayoutAnimation, Platform, Pressable, RefreshControl, StyleSheet, Text, UIManager, useWindowDimensions, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { favoriteList, type FeedItem } from '../../src/api'
import { useAuth } from '../../src/auth'
import ListingCard from '../../src/components/ListingCard'
import Skeleton from '../../src/components/Skeleton'
import { useFavorites } from '../../src/favorites'
import { colors, radius, space } from '../../src/theme'

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
    try {
      const res = await favoriteList(token)
      if (id === req.current) { setItems(res.items); setFailed(false) }
    } catch {
      if (id === req.current) setFailed(true)
    } finally {
      if (id === req.current) setRefreshing(false)
    }
  }, [token])

  useFocusEffect(useCallback(() => { load() }, [load]))
  useEffect(() => { if (!token) setItems(null) }, [token])

  // Сняли сердечко где угодно (здесь или в ленте) — карточка уходит плавно
  const visible = items && loaded ? items.filter((i) => isFav(i.id)) : items
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
        <View style={styles.circle}><Ionicons name="heart-outline" size={30} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>Сохраняйте понравившееся</Text>
        <Text style={styles.text}>Нажмите сердечко на объявлении — оно появится здесь. Для этого нужно войти.</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>Войти</Text></Pressable>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <Text style={styles.h1}>Избранное</Text>
      {visible === null ? (
        failed ? (
          <View style={styles.center}>
            <Text style={styles.title}>Не удалось загрузить</Text>
            <Pressable style={styles.cta} onPress={load}><Text style={styles.ctaText}>Повторить</Text></Pressable>
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
              <View style={styles.circle}><Ionicons name="heart-outline" size={30} color={colors.primaryDeep} /></View>
              <Text style={styles.title}>Пока пусто</Text>
              <Text style={styles.text}>Нажмите сердечко на объявлении — оно сохранится здесь.</Text>
              <Pressable style={styles.cta} onPress={() => router.navigate('/')}><Text style={styles.ctaText}>Смотреть ленту</Text></Pressable>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  h1: { fontSize: 26, fontWeight: '800', color: colors.ink, paddingHorizontal: space.page + 2, paddingTop: 8, paddingBottom: 12 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  text: { fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 32, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  list: { paddingBottom: 24, gap: space.gap },
  row: { gap: space.gap, paddingHorizontal: space.page },
  skelGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.gap, paddingHorizontal: space.page },
})
