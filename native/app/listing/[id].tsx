import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import * as Linking from 'expo-linking'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  FlatList, NativeScrollEvent, NativeSyntheticEvent, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { fetchListing, type Listing, startChat, textOf } from '../../src/api'
import { useAuth } from '../../src/auth'
import HeartButton from '../../src/components/HeartButton'
import Skeleton from '../../src/components/Skeleton'
import { SITE, mediaUrl } from '../../src/config'
import { cityName, formatPrice, isFresh, parseTime, relTime } from '../../src/format'
import { colors, radius } from '../../src/theme'

const MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

/**
 * Объявление: галерея на всю ширину (листается, «1 / 5»), цена, название, город и время, метки, описание,
 * продавец с рейтингом и проверкой. Внизу всегда видна «Написать продавцу» — пока ведёт в переписку на сайте.
 */
export default function ListingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { width } = useWindowDimensions()
  const insets = useSafeAreaInsets()
  const [data, setData] = useState<Listing | null>(null)
  const [failed, setFailed] = useState(false)
  const [photo, setPhoto] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const { token, user } = useAuth()
  const [opening, setOpening] = useState(false)

  useEffect(() => {
    let alive = true
    setFailed(false)
    fetchListing(String(id)).then((d) => { if (alive) setData(d) }).catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [id, attempt])

  const photoH = Math.round(Math.min(width * 0.95, 560))
  const photos = (data?.photos ?? []).filter((p) => !p.is_video).map((p) => mediaUrl(p.url)).filter(Boolean) as string[]
  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => setPhoto(Math.round(e.nativeEvent.contentOffset.x / width))
  const back = (
    <Pressable style={[styles.back, { top: insets.top + 8 }]} onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
      accessibilityLabel="Назад" hitSlop={8}>
      <Ionicons name="chevron-back" size={24} color={colors.ink} />
    </Pressable>
  )

  if (failed) {
    return (
      <View style={[styles.page, styles.center, { paddingTop: insets.top }]}>
        {back}
        <Text style={styles.h2}>Объявление не открылось</Text>
        <Text style={styles.soft}>Возможно, его сняли с публикации или пропал интернет.</Text>
        <Pressable style={styles.retry} onPress={() => setAttempt((n) => n + 1)}><Text style={styles.retryText}>Повторить</Text></Pressable>
      </View>
    )
  }

  if (!data) {
    return (
      <View style={styles.page}>
        <Skeleton style={{ width, height: photoH, borderRadius: 0 }} />
        <View style={{ padding: 16, gap: 12 }}>
          <Skeleton style={{ width: 140, height: 28 }} />
          <Skeleton style={{ width: width * 0.8, height: 20 }} />
          <Skeleton style={{ width: width * 0.5, height: 14 }} />
          <Skeleton style={{ width: width - 32, height: 90, marginTop: 8 }} />
        </View>
        {back}
      </View>
    )
  }

  const { title, description } = textOf(data)
  const owner = data.owner
  const since = parseTime(owner?.since)
  const chips: { label: string; tone: 'accent' | 'primary' | 'gold' | 'plain' }[] = []
  if (isFresh(data.published_at)) chips.push({ label: 'Новое', tone: 'accent' })
  if (data.is_reserved) chips.push({ label: 'Забронировано', tone: 'gold' })
  if (owner?.is_company) chips.push({ label: 'Компания', tone: 'primary' })
  if (data.delivery_available) chips.push({ label: 'Доставка', tone: 'plain' })
  if (data.price_negotiable) chips.push({ label: 'Торг уместен', tone: 'plain' })

  return (
    <View style={styles.page}>
      <ScrollView contentContainerStyle={{ paddingBottom: 96 + insets.bottom }} showsVerticalScrollIndicator={false}>
        <View style={{ width, height: photoH, backgroundColor: colors.photo }}>
          {photos.length > 0 && (
            <FlatList
              data={photos}
              keyExtractor={(u, i) => `${i}-${u}`}
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={onScroll}
              renderItem={({ item }) => <Image source={{ uri: item }} style={{ width, height: photoH }} contentFit="cover" transition={200} />}
            />
          )}
          {photos.length > 1 && (
            <View style={styles.counter}><Text style={styles.counterText}>{photo + 1} / {photos.length}</Text></View>
          )}
        </View>

        <View style={styles.body}>
          <View style={styles.priceRow}>
            <Text style={styles.price}>{formatPrice(data.price, data.currency, data.is_free)}</Text>
            {!!data.previous_price && !data.is_free && (
              <Text style={styles.oldPrice}>{formatPrice(data.previous_price, data.currency)}</Text>
            )}
          </View>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.soft}>{[cityName(data.city), relTime(data.published_at)].filter(Boolean).join(' · ')}</Text>

          {chips.length > 0 && (
            <View style={styles.chips}>
              {chips.map((c) => <Text key={c.label} style={[styles.chip, toneStyle[c.tone]]}>{c.label}</Text>)}
            </View>
          )}

          {!!description && (
            <View style={styles.section}>
              <Text style={styles.h3}>Описание</Text>
              <Text style={styles.text}>{description}</Text>
            </View>
          )}

          {owner && (
            <View style={styles.seller}>
              <View style={styles.avatar}>
                {owner.avatar_url
                  ? <Image source={{ uri: mediaUrl(owner.avatar_url) ?? undefined }} style={styles.avatarImg} contentFit="cover" />
                  : <Text style={styles.avatarLetter}>{(owner.company_name || owner.display_name || '?').slice(0, 1).toUpperCase()}</Text>}
              </View>
              <View style={{ flex: 1, gap: 3 }}>
                <View style={styles.nameRow}>
                  <Text style={styles.name} numberOfLines={1}>{owner.company_name || owner.display_name || 'Продавец'}</Text>
                  {owner.document_verified && <Ionicons name="checkmark-circle" size={17} color={colors.primary} accessibilityLabel="Личность подтверждена" />}
                </View>
                {(owner.rating_count ?? 0) > 0 ? (
                  <View style={styles.starsRow}>
                    {[1, 2, 3, 4, 5].map((i) => (
                      <Ionicons key={i} name="star" size={13} color={i <= Math.round(owner.rating_avg ?? 0) ? '#E0A526' : '#E1E4E1'} />
                    ))}
                    <Text style={styles.small}>{(owner.rating_avg ?? 0).toFixed(1).replace('.', ',')} · отзывов: {owner.rating_count}</Text>
                  </View>
                ) : <Text style={styles.small}>Пока нет отзывов</Text>}
                {since && <Text style={styles.small}>На PLONK с {MONTHS_GEN[since.getMonth()]} {since.getFullYear()}</Text>}
              </View>
            </View>
          )}

          <Text style={styles.footnote}>
            {[data.number ? `Объявление №${data.number}` : '', data.views_count != null ? `просмотров: ${data.views_count}` : ''].filter(Boolean).join(' · ')}
          </Text>
        </View>
      </ScrollView>

      {back}
      <HeartButton id={data.id} size={40} style={[styles.heartTop, { top: insets.top + 8 }]} />
      <View style={[styles.bar, { paddingBottom: 10 + insets.bottom }]}>
        {user && owner && user.id === owner.id ? (
          <View style={[styles.cta, styles.ctaMine]}>
            <Text style={styles.ctaMineText}>Это ваше объявление</Text>
          </View>
        ) : (
          <Pressable style={[styles.cta, opening && { opacity: 0.7 }]} disabled={opening} accessibilityRole="button" onPress={async () => {
            if (!token) { router.push('/login'); return }
            setOpening(true)
            try {
              const chat = await startChat(token, data.id)
              router.push(`/chat/${chat.id}`)
            } catch {
              Linking.openURL(`${SITE}${data.path ?? ''}`)
            } finally {
              setOpening(false)
            }
          }}>
            <Ionicons name="chatbubble-ellipses" size={18} color="#fff" />
            <Text style={styles.ctaText}>Написать продавцу</Text>
          </Pressable>
        )}
      </View>
    </View>
  )
}

const toneStyle = StyleSheet.create({
  accent: { backgroundColor: colors.accent, color: '#fff' },
  primary: { backgroundColor: colors.primarySoft, color: colors.primaryDeep },
  gold: { backgroundColor: colors.goldDark, color: '#fff' },
  plain: { backgroundColor: colors.sunken, color: colors.inkSoft },
})

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 8 },
  back: {
    position: 'absolute', left: 12, width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.94)',
    alignItems: 'center', justifyContent: 'center', shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 6, shadowOffset: { width: 0, height: 1 }, elevation: 3,
  },
  heartTop: { position: 'absolute', right: 12 },
  counter: { position: 'absolute', right: 12, bottom: 12, backgroundColor: 'rgba(28,38,32,0.6)', borderRadius: radius.chip, paddingHorizontal: 10, paddingVertical: 4 },
  counterText: { color: '#fff', fontSize: 12.5, fontWeight: '700' },
  body: { paddingHorizontal: 16, paddingTop: 16, gap: 8 },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10 },
  price: { fontSize: 26, fontWeight: '800', color: colors.primaryDeep },
  oldPrice: { fontSize: 16, color: colors.muted, textDecorationLine: 'line-through' },
  title: { fontSize: 20, lineHeight: 26, fontWeight: '700', color: colors.ink },
  soft: { fontSize: 14, color: colors.inkSoft, textAlign: 'left' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  chip: { overflow: 'hidden', borderRadius: radius.chip, paddingHorizontal: 10, paddingVertical: 5, fontSize: 12, fontWeight: '800' },
  section: { marginTop: 14, gap: 6 },
  h2: { fontSize: 19, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  h3: { fontSize: 17, fontWeight: '800', color: colors.ink },
  text: { fontSize: 15.5, lineHeight: 22, color: colors.ink },
  seller: { marginTop: 18, flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  avatarImg: { width: 52, height: 52 },
  avatarLetter: { color: '#fff', fontSize: 20, fontWeight: '800' },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  name: { fontSize: 16, fontWeight: '800', color: colors.ink, flexShrink: 1 },
  starsRow: { flexDirection: 'row', alignItems: 'center', gap: 1 },
  small: { fontSize: 12.5, color: colors.inkSoft, marginLeft: 4 },
  footnote: { marginTop: 18, fontSize: 12.5, color: colors.muted },
  bar: {
    position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 16, paddingTop: 10, backgroundColor: 'rgba(250,250,249,0.96)',
    borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border,
  },
  cta: { height: 52, borderRadius: 16, backgroundColor: colors.primary, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  ctaMine: { backgroundColor: colors.sunken },
  ctaMineText: { color: colors.inkSoft, fontSize: 15.5, fontWeight: '700' },
  retry: { marginTop: 8, height: 44, paddingHorizontal: 20, borderRadius: 12, backgroundColor: colors.primary, justifyContent: 'center' },
  retryText: { color: '#fff', fontWeight: '800', fontSize: 15 },
})
