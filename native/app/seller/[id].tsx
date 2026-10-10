import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, FlatList, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type FeedItem, type Review, type Seller, sellerListings, sellerProfile, subscribeSeller, userReviews } from '../../src/api'
import { useAuth } from '../../src/auth'
import Icon, { Star } from '../../src/components/Icon'
import ListingCard from '../../src/components/ListingCard'
import ReportSheet from '../../src/components/ReportSheet'
import { mediaUrl } from '../../src/config'
import { monthYear, parseTime } from '../../src/format'
import { getLang, plural, tr } from '../../src/i18n'
import { colors, font, space } from '../../src/theme'
import VerifiedMark from '../../src/components/VerifiedMark'

// «Обычно отвечает…» — тексты сайта (seller.reply_*)
const REPLY: Record<string, string> = {"minutes": "Обычно отвечает за несколько минут", "hour": "Обычно отвечает в течение часа", "hours": "Обычно отвечает в течение дня", "day": "Обычно отвечает за сутки", "days": "Отвечает не сразу"}

const MONTH_NOM: Record<'ru' | 'en' | 'sr', string[]> = {
  ru: ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'],
  en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
  sr: ['januar', 'februar', 'mart', 'april', 'maj', 'jun', 'jul', 'avgust', 'septembar', 'oktobar', 'novembar', 'decembar'],
}
/** «сентябрь 2026 г.» — как дата отзыва на сайте. */
const reviewDate = (iso: string) => {
  const d = parseTime(iso); if (!d) return ''
  const l = getLang(); const m = MONTH_NOM[l][d.getMonth()]
  return l === 'ru' ? `${m} ${d.getFullYear()} г.` : l === 'sr' ? `${m} ${d.getFullYear()}.` : `${m} ${d.getFullYear()}`
}
const reviewsWord = (n: number) => plural(n, { ru: ['отзыв', 'отзыва', 'отзывов'], en: ['review', 'reviews'], sr: ['recenzija', 'recenzije', 'recenzija'] })

/**
 * Продавец — как /seller/:id сайта: шапка «Продавец» с жалобой; строка — аватар, имя с галочкой, рейтинг
 * и число отзывов, «На PLONK с …», «Подписаться»; отзывы одной карточкой (имя, звёзды, дата, текст),
 * первые 4 и «Показать все отзывы · N»; объявления продавца сеткой.
 */
export default function SellerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const { token, user } = useAuth()
  const [seller, setSeller] = useState<Seller | null>(null)
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [total, setTotal] = useState<number | null>(null)   // всего объявлений у продавца (в ленте — первые 20)
  const [reviews, setReviews] = useState<{ avg: number; count: number; items: Review[] } | null>(null)
  const [subscribed, setSubscribed] = useState(false)
  const [allReviews, setAllReviews] = useState(false)
  const [allListings, setAllListings] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    sellerProfile(String(id)).then((x) => { setSeller(x); setSubscribed(!!x.is_subscribed) }).catch(() => setFailed(true))
    sellerListings(String(id)).then((r) => { setItems(r.items); setTotal(r.total) }).catch(() => setItems([]))
    userReviews(String(id)).then((r) => setReviews({ avg: r.rating_avg, count: r.rating_count, items: r.items })).catch(() => {})
  }, [id])

  const top = (
    <View style={[styles.top, { paddingTop: insets.top + 6 }]}>
      <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
      <Text style={styles.topTitle}>{tr('Продавец')}</Text>
      {!!seller && user?.id !== seller.id && (
        <Pressable onPress={() => (token ? setReportOpen(true) : router.push('/login'))} hitSlop={8} style={styles.flag} accessibilityLabel={tr('Пожаловаться')}>
          <Icon name="flag" size={17} color={colors.inkSoft} />
        </Pressable>
      )}
    </View>
  )
  if (failed) return <View style={styles.page}>{top}<Text style={styles.empty}>{tr('Профиль недоступен')}</Text></View>
  if (!seller) return <View style={styles.page}>{top}<ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /></View>

  const name = seller.company_name || seller.display_name || tr('Продавец')
  const since = parseTime(seller.created_at)
  const avatar = mediaUrl(seller.avatar_url)
  const shown = reviews ? (allReviews ? reviews.items : reviews.items.slice(0, 4)) : []

  const header = (
    <View>
      <View style={styles.head}>
        <View style={styles.avatar}>
          {avatar ? <Image source={{ uri: avatar }} style={styles.avatarImg} contentFit="cover" /> : <Text style={styles.avatarLetter}>{name.slice(0, 1).toUpperCase()}</Text>}
        </View>
        <View style={{ alignItems: 'center', gap: 3 }}>
          <View style={styles.nameRow}>
            <Text style={styles.name} numberOfLines={1}>{name}</Text>
            <VerifiedMark official={seller.official} verified={seller.document_verified} size={18} />
          </View>
          {(seller.rating_count ?? 0) > 0
            ? <Text style={styles.rating}><Text style={styles.ratingNum}>{(seller.rating_avg ?? 0).toFixed(1)}</Text>  {seller.rating_count} {reviewsWord(seller.rating_count ?? 0)}</Text>
            : <Text style={styles.meta}>{tr('Пока нет отзывов')}</Text>}
          {since && <Text style={styles.meta}>{tr('На PLONK с {date}', { date: monthYear(since) })}</Text>}
          {seller.active_seller && <View style={styles.active}><Icon name="check" size={12} color={colors.primaryDeep} /><Text style={styles.activeText}>{tr('Активный продавец')}</Text></View>}
          {!!seller.reply_speed?.label && REPLY[seller.reply_speed.label] && <View style={styles.reply}><Icon name="history" size={13} color={colors.muted} /><Text style={styles.meta}>{tr(REPLY[seller.reply_speed.label])}</Text></View>}
        </View>
        {user?.id !== seller.id && (
          <Pressable style={[styles.sub, subscribed && styles.subOn]} onPress={async () => {
            if (!token) { router.push('/login'); return }
            const next = !subscribed; setSubscribed(next)
            try { await subscribeSeller(token, seller.id, next) } catch { setSubscribed(!next) }
          }}>
            <Text style={[styles.subText, subscribed && styles.subTextOn]}>{tr(subscribed ? 'Вы подписаны' : 'Подписаться')}</Text>
          </Pressable>
        )}
      </View>

      {/* отзывы — всегда, как на сайте: нет отзывов — пустые звёзды и «Пока нет отзывов» */}
      {!!reviews && reviews.count === 0 && (
        <View style={styles.reviews}>
          <Text style={styles.reviewsTitle}>{tr('Отзывы')}</Text>
          <View style={styles.summary}>
            <View style={{ flexDirection: 'row', gap: 1 }}>{[1, 2, 3, 4, 5].map((k) => <Star key={k} size={14} color={colors.sunken} />)}</View>
            <Text style={styles.meta}>— {tr('Пока нет отзывов')}</Text>
          </View>
        </View>
      )}
      {!!reviews && reviews.count > 0 && (
        <View style={styles.reviews}>
          <Text style={styles.reviewsTitle}>{tr('Отзывы')}</Text>
          <View style={styles.summary}>
            <View style={{ flexDirection: 'row', gap: 1 }}>{[1, 2, 3, 4, 5].map((k) => <Star key={k} size={14} color={k <= Math.round(reviews.avg) ? '#E0A526' : colors.sunken} />)}</View>
            <Text style={styles.ratingNum}>{reviews.avg.toFixed(1)}</Text>
            <Text style={styles.meta}>{reviews.count} {reviewsWord(reviews.count)}</Text>
          </View>
          {shown.map((r, i) => (
            <View key={r.id} style={[styles.review, i === 0 && { borderTopWidth: 0 }]}>
              <View style={styles.reviewTop}>
                <Text style={styles.reviewName} numberOfLines={1}>{r.author_name || tr('Покупатель')}</Text>
                <View style={{ flexDirection: 'row', gap: 1 }}>{[1, 2, 3, 4, 5].map((k) => <Star key={k} size={11} color={k <= r.rating ? '#E0A526' : colors.sunken} />)}</View>
                <Text style={styles.reviewDate}>{reviewDate(r.created_at)}</Text>
              </View>
              {!!r.comment && <Text style={styles.reviewText}>{r.comment}</Text>}
            </View>
          ))}
          {!allReviews && reviews.items.length > 4 && (
            <Pressable style={styles.more} onPress={() => setAllReviews(true)}><Text style={styles.moreText}>{tr('Показать все отзывы · {n}', { n: reviews.count })}</Text></Pressable>
          )}
        </View>
      )}
      <Text style={styles.h2}>{tr('Объявления')}{items ? ` · ${total ?? items.length}` : ''}</Text>
    </View>
  )

  return (
    <View style={styles.page}>
      {top}
      <FlatList
        data={(items ?? []).slice(0, allListings ? undefined : 6)}
        keyExtractor={(i) => i.id}
        numColumns={2}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        columnWrapperStyle={styles.row}
        contentContainerStyle={{ gap: space.gap, paddingBottom: 32 }}
        ListHeaderComponent={header}
        ListFooterComponent={!allListings && (items?.length ?? 0) > 6 ? <Pressable style={styles.showAll} onPress={() => setAllListings(true)}><Text style={styles.showAllText}>{tr('Показать все объявления · {n}', { n: items?.length ?? 0 })}</Text></Pressable> : null}
        ListEmptyComponent={items === null ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.empty}>{tr('Сейчас активных объявлений нет.')}</Text>}
      />
      <ReportSheet visible={reportOpen} userId={seller.id} token={token} onClose={() => setReportOpen(false)} />
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingBottom: 8 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  topTitle: { flex: 1, fontSize: 27, fontFamily: font[800], letterSpacing: -0.8, color: colors.ink, marginLeft: 8 },
  flag: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },   // как «назад»: кружок 40 без рамки, как на сайте
  head: { alignItems: 'center', gap: 8, marginHorizontal: 12, marginTop: 6, marginBottom: 22, paddingVertical: 22, paddingHorizontal: 18, borderRadius: 28, backgroundColor: colors.surface,
    shadowColor: '#0F1512', shadowOpacity: 0.06, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 2 },
  avatar: { width: 84, height: 84, borderRadius: 42, borderWidth: 4, borderColor: colors.bg, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  avatarImg: { width: 56, height: 56 },
  avatarLetter: { color: '#fff', fontSize: 34, fontFamily: font[800] },
  // как на сайте: галочка у правого края колонки с именем
  nameRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 6 },
  name: { fontSize: 24, letterSpacing: -0.6, textAlign: 'center', fontFamily: font[800], color: colors.ink, flexShrink: 1 },
  seal: { width: 17, height: 17, borderRadius: 9, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  rating: { fontSize: 12.5, fontFamily: font[600], color: colors.muted },
  ratingNum: { fontSize: 13.5, fontFamily: font[800], color: colors.ink },
  meta: { fontSize: 12.5, fontFamily: font[600], color: colors.muted },
  active: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', gap: 5, marginTop: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, backgroundColor: colors.primarySoft },
  activeText: { fontSize: 12.5, fontFamily: font[700], color: colors.primaryDeep },
  reply: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  showAll: { marginHorizontal: space.page, marginTop: 4, paddingVertical: 12, borderRadius: 12, borderWidth: 1, borderColor: 'rgba(20,30,25,0.09)', backgroundColor: colors.surface, alignItems: 'center' },
  showAllText: { fontSize: 13.5, fontFamily: font[700], color: colors.ink },
  sub: { alignSelf: 'center', minWidth: 200, alignItems: 'center', marginTop: 6, paddingVertical: 13, paddingHorizontal: 26, borderRadius: 16, backgroundColor: colors.inverse },
  subOn: { backgroundColor: colors.surface, borderWidth: 0 },
  subText: { color: colors.onInverse, fontSize: 15, fontFamily: font[800] },
  subTextOn: { color: colors.ink },
  reviews: { marginHorizontal: 12, marginBottom: 14, padding: 14, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 0 },
  reviewsTitle: { fontSize: 16, fontFamily: font[800], color: colors.ink },
  summary: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6, marginBottom: 4 },
  review: { paddingVertical: 11, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border, gap: 4 },
  reviewTop: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  reviewName: { fontSize: 14, fontFamily: font[800], color: colors.ink, flexShrink: 1 },
  reviewDate: { marginLeft: 'auto', fontSize: 12, fontFamily: font[500], color: colors.muted },
  reviewText: { fontSize: 14, lineHeight: 19, fontFamily: font[400], color: colors.ink },
  more: { marginTop: 8, height: 44, borderRadius: 12, borderWidth: 0, alignItems: 'center', justifyContent: 'center' },
  moreText: { fontSize: 14, fontFamily: font[800], color: colors.primaryDeep },
  h2: { fontSize: 18, fontFamily: font[800], color: colors.ink, paddingHorizontal: 16, marginBottom: 2 },
  row: { gap: space.gap, paddingHorizontal: space.page },
  empty: { fontSize: 14.5, color: colors.muted, textAlign: 'center', marginTop: 16, fontFamily: font[500] },
})
