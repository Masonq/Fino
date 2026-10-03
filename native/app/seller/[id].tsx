import { tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type FeedItem, type Review, type Seller, sellerListings, sellerProfile, subscribeSeller, userReviews } from '../../src/api'
import { useAuth } from '../../src/auth'
import { Star } from '../../src/components/Icon'
import ListingCard from '../../src/components/ListingCard'
import { mediaUrl } from '../../src/config'
import { monthYear, parseTime } from '../../src/format'
import { colors, space, font } from '../../src/theme'

/** Страница продавца: аватар, имя (компания), проверка, рейтинг, «на PLONK с …», все его объявления сеткой. */
export default function SellerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [seller, setSeller] = useState<Seller | null>(null)
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [failed, setFailed] = useState(false)
  const { token, user } = useAuth()
  const [reviews, setReviews] = useState<{ avg: number; count: number; items: Review[] } | null>(null)
  const [subscribed, setSubscribed] = useState(false)

  useEffect(() => {
    sellerProfile(String(id)).then((x) => { setSeller(x); setSubscribed(!!x.is_subscribed) }).catch(() => setFailed(true))
    userReviews(String(id)).then((r) => setReviews({ avg: r.rating_avg, count: r.rating_count, items: r.items })).catch(() => {})
    sellerListings(String(id)).then((r) => setItems(r.items)).catch(() => setItems([]))
  }, [id])

  const back = (
    <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} style={[styles.back, { top: insets.top + 8 }]} hitSlop={8} accessibilityLabel={tr('Назад')}>
      <Ionicons name="chevron-back" size={24} color={colors.ink} />
    </Pressable>
  )

  if (failed) return <View style={[styles.page, styles.center]}>{back}<Text style={styles.name}>{tr('Профиль недоступен')}</Text></View>
  if (!seller) return <View style={[styles.page, styles.center]}>{back}<ActivityIndicator color={colors.primary} /></View>

  const name = seller.company_name || seller.display_name || tr('Продавец')
  const since = parseTime(seller.created_at)
  const avatar = mediaUrl(seller.avatar_url)

  const header = (
    <View style={[styles.head, { paddingTop: insets.top + 60 }]}>
      <View style={styles.avatar}>
        {avatar ? <Image source={{ uri: avatar }} style={styles.avatarImg} contentFit="cover" /> : <Text style={styles.avatarLetter}>{name.slice(0, 1).toUpperCase()}</Text>}
      </View>
      <View style={styles.nameRow}>
        <Text style={styles.name} numberOfLines={2}>{name}</Text>
        {seller.document_verified && <Ionicons name="checkmark-circle" size={20} color={colors.primary} accessibilityLabel={tr('Личность подтверждена')} />}
      </View>
      {seller.is_company && <Text style={styles.company}>{tr('Компания')}</Text>}
      <View style={styles.facts}>
        {(seller.rating_count ?? 0) > 0 ? (
          <View style={styles.fact}>
            <Ionicons name="star" size={15} color="#E0A526" />
            <Text style={styles.factText}>{(seller.rating_avg ?? 0).toFixed(1).replace('.', ',')} · {tr('отзывов: {n}', { n: seller.rating_count ?? 0 })}</Text>
          </View>
        ) : <Text style={styles.factText}>{tr('Пока нет отзывов')}</Text>}
        {since && <Text style={styles.factText}>{tr('На PLONK с {date}', { date: monthYear(since) })}</Text>}
      </View>
      {!!seller.company_description && <Text style={styles.about}>{seller.company_description}</Text>}
      {user?.id !== seller.id && (
        <Pressable style={[styles.sub, subscribed && styles.subOn]} onPress={async () => {
          if (!token) { router.push('/login'); return }
          const next = !subscribed; setSubscribed(next)
          try { await subscribeSeller(token, seller.id, next) } catch { setSubscribed(!next) }
        }}>
          <Text style={[styles.subText, subscribed && styles.subTextOn]}>{tr(subscribed ? 'Вы подписаны' : 'Подписаться')}</Text>
        </Pressable>
      )}
      {!!reviews && reviews.count > 0 && (
        <View style={styles.reviews}>
          <Text style={styles.h2}>{tr('Отзывы')} · {reviews.count}</Text>
          {reviews.items.slice(0, 5).map((r) => (
            <View key={r.id} style={styles.review}>
              <View style={styles.reviewTop}>
                <Text style={styles.reviewName}>{r.author_name || tr('Покупатель')}</Text>
                <View style={{ flexDirection: 'row', gap: 1 }}>{[1, 2, 3, 4, 5].map((k) => <Star key={k} size={12} color={k <= r.rating ? '#E0A526' : '#D9DDD9'} />)}</View>
              </View>
              {!!r.comment && <Text style={styles.reviewText}>{r.comment}</Text>}
            </View>
          ))}
        </View>
      )}
      <Text style={styles.h2}>{tr('Объявления')}{items ? ` · ${items.length}` : ''}</Text>
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
        ListHeaderComponent={header}
        ListEmptyComponent={items === null ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.empty}>{tr('Сейчас активных объявлений нет.')}</Text>}
      />
      {back}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center' },
  back: {
    position: 'absolute', left: 12, width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.94)', alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 6, shadowOffset: { width: 0, height: 1 }, elevation: 3,
  },
  head: { alignItems: 'center', paddingHorizontal: 20, gap: 6, paddingBottom: 6 },
  avatar: { width: 84, height: 84, borderRadius: 42, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', marginBottom: 6 },
  avatarImg: { width: 84, height: 84 },
  avatarLetter: { color: '#fff', fontSize: 34, fontFamily: font[800] },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6, justifyContent: 'center' },
  name: { fontSize: 22, fontFamily: font[800], color: colors.ink, textAlign: 'center', flexShrink: 1 },
  company: { fontSize: 12.5, fontFamily: font[800], color: colors.primaryDeep, backgroundColor: colors.primarySoft, paddingHorizontal: 9, paddingVertical: 3, borderRadius: 999, overflow: 'hidden' },
  facts: { alignItems: 'center', gap: 4, marginTop: 2 },
  fact: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  factText: { fontFamily: font[400], fontSize: 14, color: colors.inkSoft },
  about: { fontFamily: font[400], fontSize: 14.5, lineHeight: 20, color: colors.ink, textAlign: 'center', marginTop: 6 },
  h2: { alignSelf: 'flex-start', fontSize: 19, fontFamily: font[800], color: colors.ink, marginTop: 18, marginBottom: 4 },
  row: { gap: space.gap, paddingHorizontal: space.page },
  // Как .seller-sub-btn сайта: зелёная 13/700, скругление 11; подписан — светлая с рамкой
  sub: { marginTop: 10, paddingVertical: 9, paddingHorizontal: 18, borderRadius: 11, backgroundColor: colors.primary },
  subOn: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  subText: { color: '#fff', fontSize: 13, fontFamily: font[700] },
  subTextOn: { color: colors.ink },
  reviews: { alignSelf: 'stretch', marginTop: 18, gap: 8 },
  review: { padding: 12, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, gap: 4 },
  reviewTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  reviewName: { fontSize: 14, fontFamily: font[800], color: colors.ink },
  reviewText: { fontSize: 14, lineHeight: 19, fontFamily: font[400], color: colors.inkSoft },
  empty: { fontFamily: font[400], fontSize: 14.5, color: colors.muted, textAlign: 'center', marginTop: 16 },
})
