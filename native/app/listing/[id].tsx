import Icon, { Star } from '../../src/components/Icon'
import { tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import * as Linking from 'expo-linking'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  FlatList, NativeScrollEvent, NativeSyntheticEvent, Pressable, ScrollView, Share, StyleSheet, Text, useWindowDimensions, View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { attrRows, type AttrField, ru, categorySchema, type FeedItem, fetchListing, type Listing, sellerListings, similarListings, startChat, textOf } from '../../src/api'
import { useAuth } from '../../src/auth'
import { rememberViewed } from '../../src/history'
import CardsRow from '../../src/components/CardsRow'
import HeartButton from '../../src/components/HeartButton'
import ReportSheet from '../../src/components/ReportSheet'
import Skeleton from '../../src/components/Skeleton'
import { SITE, mediaUrl } from '../../src/config'
import { cityName, formatPrice, isFresh, monthYear, parseTime, relTime } from '../../src/format'
import { colors, font, mono, radius } from '../../src/theme'

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
  const [schema, setSchema] = useState<AttrField[]>([])
  const [similar, setSimilar] = useState<FeedItem[] | null>(null)
  const [more, setMore] = useState<FeedItem[] | null>(null)
  const [reportOpen, setReportOpen] = useState(false)

  useEffect(() => {
    let alive = true
    setFailed(false)
    fetchListing(String(id)).then((d) => {
      if (!alive) return
      setData(d)
      rememberViewed(d.id).catch(() => {})
      // Подписи характеристик, похожие и другие объявления продавца — следом, не задерживая сам экран
      if (d.category_slug) categorySchema(String(d.category_slug)).then((r) => alive && setSchema(r.attribute_schema ?? [])).catch(() => {})
      similarListings(d.id).then((r) => alive && setSimilar(r.items)).catch(() => {})
      if (d.owner?.id) sellerListings(d.owner.id).then((r) => alive && setMore(r.items)).catch(() => {})
    }).catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [id, attempt])

  // Видимая часть фото — как на сайте (≈ 0,66 ширины), плюс зона под строкой состояния и под наезжающим листом
  const photoH = Math.round(Math.min(width * 0.92, 520))
  const photos = (data?.photos ?? []).filter((p) => !p.is_video).map((p) => mediaUrl(p.url)).filter(Boolean) as string[]
  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => setPhoto(Math.round(e.nativeEvent.contentOffset.x / width))
  const back = (
    <Pressable style={[styles.back, { top: insets.top + 8 }]} onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
      accessibilityLabel={tr('Назад')} hitSlop={8}>
      <Icon name="back" size={22} color="#fff" />
    </Pressable>
  )

  if (failed) {
    return (
      <View style={[styles.page, styles.center, { paddingTop: insets.top }]}>
        {back}
        <Text style={styles.h2}>{tr('Объявление не открылось')}</Text>
        <Text style={styles.soft}>{tr('Возможно, его сняли с публикации или пропал интернет.')}</Text>
        <Pressable style={styles.retry} onPress={() => setAttempt((n) => n + 1)}><Text style={styles.retryText}>{tr('Повторить')}</Text></Pressable>
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
  const attrs = attrRows(data.attributes as Record<string, unknown> | undefined, schema)
  const keyFacts = factChips(rootSlug(data), data.attributes as Record<string, unknown> | undefined, schema)
  const verdict = VERDICTS[(data as unknown as { price_check?: { verdict?: string } }).price_check?.verdict ?? '']
  const mine = !!(user && owner && user.id === owner.id)
  // Звонок — как на сайте: трубка ведёт в переписку, где запрашивается звонок
  const openChat = async () => {
    if (!token) { router.push('/login'); return }
    setOpening(true)
    try { const chat = await startChat(token, data.id); router.push(`/chat/${chat.id}`) } catch { /* сеть */ } finally { setOpening(false) }
  }
  const stripH = photoH + insets.top + SHEET_OVERLAP

  return (
    <View style={styles.page}>
      <ScrollView contentContainerStyle={{ paddingBottom: 96 + insets.bottom }} showsVerticalScrollIndicator={false}>
        {/* Фото — как на сайте: снимок целиком (contain) на размытой подложке из того же снимка */}
        <View style={{ width, height: stripH, backgroundColor: '#1E2621' }}>
          {photos.length > 0 && (
            <FlatList
              data={photos}
              keyExtractor={(u, k) => `${k}-${u}`}
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={onScroll}
              renderItem={({ item }) => (
                <View style={{ width, height: stripH }}>
                  <Image source={{ uri: item }} style={[StyleSheet.absoluteFill, styles.blur]} contentFit="cover" blurRadius={22} />
                  <Image source={{ uri: item }} style={{ position: 'absolute', left: 0, right: 0, top: insets.top, height: photoH }} contentFit="contain" transition={200} />
                </View>
              )}
            />
          )}
          {photos.length > 1 && (
            <View style={[styles.counter, { bottom: SHEET_OVERLAP + 12 }]}><Text style={styles.counterText}>{photo + 1} / {photos.length}</Text></View>
          )}
        </View>

        {/* Белый лист со скруглением наезжает на фото — как .detail-sheet на сайте */}
        <View style={styles.sheet}>
          <View style={styles.priceRow}>
            <Text style={styles.price}>{formatPrice(data.price, data.currency, data.is_free)}</Text>
            {!!data.previous_price && !data.is_free && <Text style={styles.oldPrice}>{formatPrice(data.previous_price, data.currency)}</Text>}
          </View>
          <Text style={styles.title}>{title}</Text>
          {data.external_source === 'telegram' && <Text style={styles.fromTg}>{tr('Объявление из Telegram')}</Text>}
          {keyFacts.length > 0 && (
            <View style={styles.facts}>
              {keyFacts.map((f) => (
                <View key={f.key} style={styles.fact}>
                  <Icon name={`attr_${f.key}`} size={16} color={colors.inkSoft} />
                  <Text style={styles.factText}>{f.text}</Text>
                </View>
              ))}
            </View>
          )}
          {chips.length > 0 && (
            <View style={styles.chips}>
              {chips.map((c) => <Text key={c.label} style={[styles.chip, toneStyle[c.tone]]}>{tr(c.label)}</Text>)}
            </View>
          )}

          {!!verdict && (
            <View style={styles.priceCheck}>
              <View style={[styles.pcIcon, { backgroundColor: verdict.bg }]}><Ionicons name={verdict.icon} size={22} color={verdict.color} /></View>
              <View style={{ flex: 1 }}>
                <Text style={styles.pcTitle}>{tr(verdict.title)}</Text>
                <Text style={styles.pcSub}>{tr('Оценка PLONK')}</Text>
              </View>
            </View>
          )}

          {owner && (
            <Pressable style={styles.seller} onPress={() => router.push(`/seller/${owner.id}`)} accessibilityRole="button" accessibilityLabel={tr('Профиль продавца')}>
              <View style={styles.avatar}>
                {owner.avatar_url
                  ? <Image source={{ uri: mediaUrl(owner.avatar_url) ?? undefined }} style={styles.avatarImg} contentFit="cover" />
                  : <Text style={styles.avatarLetter}>{(owner.company_name || owner.display_name || '?').slice(0, 1).toUpperCase()}</Text>}
              </View>
              <View style={{ flex: 1, gap: 2 }}>
                <View style={styles.nameRow}>
                  <Text style={styles.name} numberOfLines={1}>{owner.company_name || owner.display_name || tr('Продавец')}</Text>
                  {owner.document_verified && (
                    <View style={styles.verified}>
                      <View style={styles.seal}><Icon name="check" size={10} color="#fff" /></View>
                      <Text style={styles.verifiedText}>{tr('Личность подтверждена')}</Text>
                    </View>
                  )}
                </View>
                {(owner.rating_count ?? 0) > 0 ? (
                  <View style={styles.starsRow}>
                    {[1, 2, 3, 4, 5].map((k) => <Star key={k} size={13} color={k <= Math.round(owner.rating_avg ?? 0) ? '#E0A526' : '#D9DDD9'} />)}
                    <Text style={[styles.sellerSub, { marginLeft: 4 }]}>{(owner.rating_avg ?? 0).toFixed(1).replace('.', ',')} · {tr('отзывов: {n}', { n: owner.rating_count ?? 0 })}</Text>
                  </View>
                ) : <Text style={styles.sellerSub}>{tr('Пока нет отзывов')}</Text>}
                <Text style={styles.sellerSub}>
                  {[since ? tr('Здесь с {date}', { date: monthYear(since) }) : '', (owner.listings_count ?? 0) > 1 ? tr('объявлений: {n}', { n: owner.listings_count ?? 0 }) : ''].filter(Boolean).join('  ·  ')}
                </Text>
              </View>
              <Icon name="forward" size={16} color={colors.muted} />
            </Pressable>
          )}

          {!!data.city && (
            <View style={styles.section}>
              <Text style={styles.h3}>{tr('Местоположение')}</Text>
              <View style={styles.locRow}>
                <Icon name="pin" size={16} color={colors.inkSoft} />
                <Text style={styles.loc}>{cityName(data.city)}</Text>
              </View>
            </View>
          )}

          {attrs.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.h3}>{tr('Характеристики')}</Text>
              <View style={styles.attrs}>
                {attrs.map((r, k) => (
                  <View key={r.label} style={[styles.attr, k === attrs.length - 1 && { borderBottomWidth: 0 }]}>
                    <Text style={styles.attrLabel}>{r.label}</Text>
                    <Text style={styles.attrValue}>{r.value}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {!!description && (
            <View style={styles.section}>
              <Text style={styles.h3}>{tr('Описание')}</Text>
              <Text style={styles.text}>{description}</Text>
            </View>
          )}

          {!mine && (
            <Pressable onPress={() => (token ? setReportOpen(true) : router.push('/login'))} style={styles.report} hitSlop={6}>
              <Text style={styles.reportText}>{tr('Пожаловаться')}</Text>
            </Pressable>
          )}
          <Text style={styles.footnote}>
            {[data.views_count != null ? tr('просмотров: {n}', { n: data.views_count }) : '', data.number ? tr('Объявление №{n}', { n: String(data.number) }) : '', relTime(data.published_at)].filter(Boolean).join('  ·  ')}
          </Text>
        </View>
        <CardsRow title={tr('Ещё у продавца')} items={more} exclude={data.id} />
        <CardsRow title={tr('Похожие')} items={similar} exclude={data.id} />
      </ScrollView>

      {back}
      <Pressable style={[styles.shareTop, { top: insets.top + 8 }]} hitSlop={6} accessibilityLabel={tr('Поделиться')}
        onPress={() => Share.share({ message: `${title} — ${formatPrice(data.price, data.currency, data.is_free)}\n${SITE}${data.path ?? ''}` }).catch(() => {})}>
        <Icon name="share" size={19} color="#fff" />
      </Pressable>
      <HeartButton id={data.id} size={40} dark style={[styles.heartTop, { top: insets.top + 8 }]} />
      <ReportSheet visible={reportOpen} listingId={data.id} token={token} onClose={() => setReportOpen(false)} />
      <View style={[styles.bar, { paddingBottom: 10 + insets.bottom }]}>
        {mine ? (
          <View style={[styles.cta, styles.ctaMine]}><Text style={styles.ctaMineText}>{tr('Это ваше объявление')}</Text></View>
        ) : (
          <View style={styles.ctaRow}>
          {owner?.has_phone && (
            <Pressable style={styles.callBtn} disabled={opening} accessibilityLabel={tr('Позвонить через чат')} onPress={() => openChat()}>
              <Icon name="phone" size={20} color={colors.ink} />
            </Pressable>
          )}
          <Pressable style={[styles.cta, { flex: 1 }, opening && { opacity: 0.7 }]} disabled={opening} accessibilityRole="button" onPress={async () => {
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
            <Text style={styles.ctaText}>{tr('Написать продавцу')}</Text>
          </Pressable>
          </View>
        )}
      </View>
    </View>
  )
}

const SHEET_OVERLAP = 22

type IconName = keyof typeof Ionicons.glyphMap
/** Главные характеристики плашками — как AttrChips на сайте: для недвижимости и авто, в том же порядке. */
const FACT_ORDER: Record<string, string[]> = {
  'real-estate': ['rooms', 'area_m2', 'floor', 'renovation', 'furnished', 'balcony'],
  auto: ['year', 'mileage_km', 'transmission', 'fuel_type', 'engine_volume', 'body_type'],
}
const FACT_ICON: Record<string, IconName> = {
  rooms: 'grid-outline', area_m2: 'resize-outline', floor: 'business-outline', renovation: 'construct-outline', furnished: 'bed-outline',
  balcony: 'sunny-outline', year: 'calendar-outline', mileage_km: 'speedometer-outline', transmission: 'git-branch-outline',
  fuel_type: 'water-outline', engine_volume: 'cog-outline', body_type: 'car-outline',
}
const FACT_UNIT: Record<string, string> = { rooms: 'комн.', area_m2: 'м²', year: 'г.', mileage_km: 'км', engine_volume: 'л' }

function rootSlug(l: { category_path?: unknown; category_slug?: string | null }): string {
  const path = l.category_path as { slug?: string }[] | undefined
  return (Array.isArray(path) && path[0]?.slug) || l.category_slug || ''
}

function factChips(root: string, attrs: Record<string, unknown> | undefined, schema: AttrField[]): { key: string; icon: IconName; text: string }[] {
  const keys = FACT_ORDER[root]
  if (!keys || !attrs) return []
  const out: { key: string; icon: IconName; text: string }[] = []
  for (const key of keys) {
    const raw = attrs[key]
    const field = schema.find((f) => f.key === key)
    if (raw === undefined || raw === null || raw === '' || !field) continue
    if (field.type === 'boolean') { if (raw) out.push({ key, icon: FACT_ICON[key], text: ru(field.label) }); continue }
    const opt = field.options?.find((o) => String(o.value) === String(raw))
    const value = opt ? ru(opt.label) : String(raw)
    if (key === 'floor') {
      const total = attrs.total_floors
      out.push({ key, icon: FACT_ICON[key], text: `${value}${total ? `/${total}` : ''} ${tr('этаж')}` })
    } else {
      out.push({ key, icon: FACT_ICON[key], text: `${value} ${FACT_UNIT[key] && !opt ? tr(FACT_UNIT[key]) : ''}`.trim() })
    }
  }
  return out
}

/** Оценка цены — та же, что на сайте («Дешевле похожих на PLONK»). */
const VERDICTS: Record<string, { title: string; icon: IconName; color: string; bg: string }> = {
  cheap: { title: 'Дешевле похожих на PLONK', icon: 'trending-down', color: '#0B5C42', bg: '#DDF3E8' },
  fair: { title: 'Цена как у похожих', icon: 'remove', color: '#4B554E', bg: '#ECECE6' },
  expensive: { title: 'Дороже похожих на PLONK', icon: 'trending-up', color: '#B4501E', bg: '#FCE6DA' },
}

const toneStyle = StyleSheet.create({
  accent: { backgroundColor: colors.accent, color: '#fff' },
  primary: { backgroundColor: colors.primarySoft, color: colors.primaryDeep },
  gold: { backgroundColor: colors.goldDark, color: '#fff' },
  plain: { backgroundColor: colors.sunken, color: colors.inkSoft },
})

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.surface },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 8 },
  back: {
    position: 'absolute', left: 12, width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(20,26,22,0.38)',
    alignItems: 'center', justifyContent: 'center', shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 6, shadowOffset: { width: 0, height: 1 }, elevation: 3,
  },
  heartTop: { position: 'absolute', right: 12 },
  shareTop: {
    position: 'absolute', right: 60, width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(20,26,22,0.38)', alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 6, shadowOffset: { width: 0, height: 1 }, elevation: 3,
  },
  blur: { opacity: 0.6, transform: [{ scale: 1.18 }] },
  counter: { position: 'absolute', alignSelf: 'center', backgroundColor: 'rgba(28,38,32,0.62)', borderRadius: radius.chip, paddingHorizontal: 12, paddingVertical: 5 },
  counterText: { color: '#fff', fontSize: 13, fontFamily: font[700] },
  sheet: {
    marginTop: -SHEET_OVERLAP, backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingHorizontal: 20, paddingTop: 22,
    shadowColor: '#14201A', shadowOpacity: 0.05, shadowRadius: 12, shadowOffset: { width: 0, height: -6 },
  },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10 },
  price: { fontFamily: mono, fontSize: 25, color: colors.primaryDeep },
  oldPrice: { fontFamily: mono, fontSize: 15, color: colors.muted, textDecorationLine: 'line-through' },
  // Как .detail-title сайта: 17,5 / 800 / межстрочный 1,3
  title: { fontFamily: font[800], fontSize: 17.5, lineHeight: 23, letterSpacing: -0.18, color: colors.ink, marginTop: 12 },
  fromTg: { alignSelf: 'flex-start', marginTop: 8, paddingHorizontal: 9, paddingVertical: 4, borderRadius: 8, overflow: 'hidden', backgroundColor: '#EAF3FF', color: '#2D7DD2', fontFamily: font[700], fontSize: 12.5 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  facts: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  fact: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 11, height: 36, borderRadius: 12, backgroundColor: colors.sunken },
  factText: { fontSize: 14, fontFamily: font[700], color: colors.ink },
  priceCheck: { marginTop: 16, flexDirection: 'row', alignItems: 'center', gap: 12, padding: 13, borderRadius: 17, backgroundColor: colors.sunken },
  pcIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  pcTitle: { fontSize: 14.5, fontFamily: font[800], letterSpacing: -0.15, color: colors.ink },
  pcSub: { fontSize: 12.5, fontFamily: font[600], color: colors.muted, marginTop: 1 },
  chip: { overflow: 'hidden', borderRadius: radius.chip, paddingHorizontal: 10, paddingVertical: 5, fontSize: 12, fontFamily: font[800] },
  seller: { marginTop: 20, flexDirection: 'row', alignItems: 'center', gap: 11, paddingVertical: 12, paddingHorizontal: 13, borderRadius: 17, backgroundColor: colors.sunken },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  avatarImg: { width: 52, height: 52 },
  avatarLetter: { color: '#fff', fontSize: 20, fontFamily: font[800] },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  verified: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  seal: { width: 16, height: 16, borderRadius: 8, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  verifiedText: { fontSize: 12.5, fontFamily: font[700], color: colors.primaryDeep },
  // Как .seller-name / .seller-meta сайта: имя 14,5 / 800, строки под ним 12 / 600
  name: { fontSize: 14.5, fontFamily: font[800], color: colors.ink, flexShrink: 1 },
  starsRow: { flexDirection: 'row', alignItems: 'center', gap: 1 },
  sellerSub: { fontSize: 12, fontFamily: font[600], color: colors.muted, marginTop: 2 },
  section: { marginTop: 26, gap: 8 },
  h3: { fontSize: 18, fontFamily: font[800], color: colors.ink },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  loc: { fontSize: 15, fontFamily: font[600], color: colors.inkSoft },
  attrs: { backgroundColor: colors.sunken, borderRadius: 16, paddingHorizontal: 16 },
  attr: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#ECECE6' },
  attrLabel: { fontSize: 14.5, fontFamily: font[500], color: colors.muted, flex: 1 },
  attrValue: { fontSize: 14.5, fontFamily: font[700], color: colors.ink, flex: 1, textAlign: 'right' },
  text: { fontSize: 16, lineHeight: 23, fontFamily: font[400], color: colors.ink },
  h2: { fontSize: 19, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  soft: { fontSize: 14, fontFamily: font[400], color: colors.inkSoft, textAlign: 'center' },
  report: { alignSelf: 'center', marginTop: 28, paddingVertical: 8, paddingHorizontal: 12 },
  reportText: { fontSize: 15, fontFamily: font[700], color: colors.muted },
  footnote: { marginTop: 10, marginBottom: 6, fontSize: 13, fontFamily: font[500], color: colors.muted },
  bar: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 16, paddingTop: 10, backgroundColor: colors.surface, borderTopWidth: 1, borderTopColor: colors.border },
  cta: { height: 52, borderRadius: 16, backgroundColor: colors.primary, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  ctaRow: { flexDirection: 'row', gap: 10 },
  callBtn: { width: 52, height: 52, borderRadius: 16, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  ctaMine: { backgroundColor: colors.sunken },
  ctaMineText: { color: colors.inkSoft, fontSize: 15.5, fontFamily: font[700] },
  retry: { marginTop: 8, height: 44, paddingHorizontal: 20, borderRadius: 12, backgroundColor: colors.primary, justifyContent: 'center' },
  retryText: { color: '#fff', fontFamily: font[800], fontSize: 15 },
})
