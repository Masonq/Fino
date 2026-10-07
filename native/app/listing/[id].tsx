import Icon, { Star } from '../../src/components/Icon'
import { getLang, plural, tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import * as Linking from 'expo-linking'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState, useRef } from 'react'
import {
  Alert, FlatList, NativeScrollEvent, NativeSyntheticEvent, Pressable, ScrollView, Share, StyleSheet, Text, useWindowDimensions, View, Modal } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { JobRespond, StorefrontLink } from '../../src/components/ListingExtras'
import { attrRows, type AttrField, ru, categorySchema, type FeedItem, loadListing, type Listing, sellerListings, similarListings, startChat, textOf, sendMessage } from '../../src/api'
import { useAuth } from '../../src/auth'
import { deleteListingStaff } from '../../src/admin'
import MoveSheet from '../../src/components/MoveSheet'
import { readCache } from '../../src/cache'
import { rememberViewed } from '../../src/history'
import { onRetry } from '../../src/net'
import { getSeed } from '../../src/seed'
import CardsRow from '../../src/components/CardsRow'
import HeartButton from '../../src/components/HeartButton'
import ReportSheet from '../../src/components/ReportSheet'
import Sheet, { SheetAction } from '../../src/components/Sheet'
import MapWeb from '../../src/components/MapWeb'
import VideoSlide from '../../src/components/VideoSlide'
import * as Clipboard from 'expo-clipboard'
import ImageView from '../../src/components/PhotoViewer'
import Skeleton from '../../src/components/Skeleton'
import { SITE, mediaUrl } from '../../src/config'
import { cityName, formatPrice, isFresh, monthYear, parseTime, relTime, timeAgo } from '../../src/format'
import { colors, font, mono, radius } from '../../src/theme'
import VerifiedMark from '../../src/components/VerifiedMark'

/**
 * Объявление: галерея на всю ширину (листается, «1 / 5»), цена, название, город и время, метки, описание,
 * продавец с рейтингом и проверкой. Внизу всегда видна «Написать продавцу» — пока ведёт в переписку на сайте.
 */
export default function ListingScreen() {
  const { id, report } = useLocalSearchParams<{ id: string; report?: string }>()
  const { width } = useWindowDimensions()
  const insets = useSafeAreaInsets()
  const [data, setData] = useState<Listing | null>(null)
  const [failed, setFailed] = useState(false)
  const [photo, setPhoto] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const { token, user } = useAuth()
  const staff = user?.role === 'admin' || user?.role === 'moderator'
  const [moveOpen, setMoveOpen] = useState(false)
  const [movedTo, setMovedTo] = useState<string | null>(null)
  const [opening, setOpening] = useState(false)
  const [schema, setSchema] = useState<AttrField[]>([])
  const [similar, setSimilar] = useState<FeedItem[] | null>(null)
  const [more, setMore] = useState<FeedItem[] | null>(null)
  const [reportOpen, setReportOpen] = useState(false)
  // «Пожаловаться» из меню карточки в ленте открывает форму жалобы сразу
  useEffect(() => { if (report === '1' && token) setReportOpen(true) }, [report, token])
  const [gaugeOpen, setGaugeOpen] = useState(false)
  // Фото на весь экран: увеличение щипком и двойным касанием, листание, закрытие смахиванием
  const [viewer, setViewer] = useState<number | null>(null)
  // Карта места — на весь экран, как на сайте: «назад» и название, внизу адрес (по точке) и «скопировать»
  const [mapOpen, setMapOpen] = useState(false)
  const [descOpen, setDescOpen] = useState(false)
  const [attrsOpen, setAttrsOpen] = useState(false)
  const [askOpen, setAskOpen] = useState(false)
  const [mapAddr, setMapAddr] = useState('')
  const [addrCopied, setAddrCopied] = useState(false)
  const stripRef = useRef<FlatList<{ uri: string; poster: string; video: boolean }>>(null)
  useEffect(() => {
    if (!mapOpen || data?.location_lat == null || data.location_approximate) return
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${data.location_lat}&lon=${data.location_lng}&zoom=17&addressdetails=1`, { headers: { 'Accept-Language': getLang() } })
      .then((r) => r.json()).then((j) => setMapAddr(String(j?.display_name || '').split(',').map((x: string) => x.trim()).slice(0, 3).join(', '))).catch(() => {})
  }, [mapOpen, data?.location_lat]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let alive = true
    let fresh = false
    setFailed(false)
    // Мгновенно: данные карточки, затем сохранённая полная версия, затем — свежая с сервера
    const seed = getSeed(String(id))
    if (seed && !data) setData(fromCard(seed))
    readCache<Listing>(`listing:${id}`).then((c) => { if (alive && c && !fresh) setData(c) })
    loadListing(String(id)).then((d) => {
      if (!alive) return
      fresh = true
      setData(d)
      rememberViewed(d.id).catch(() => {})
      // Подписи характеристик, похожие и другие объявления продавца — следом, не задерживая сам экран
      if (d.category_slug) categorySchema(String(d.category_slug)).then((r) => alive && setSchema(r.attribute_schema ?? [])).catch(() => {})
      similarListings(d.id).then((r) => alive && setSimilar(r.items)).catch(() => {})
      if (d.owner?.id) sellerListings(d.owner.id).then((r) => alive && setMore(r.items)).catch(() => {})
    }).catch(() => { if (alive && !fresh) readCache<Listing>(`listing:${id}`).then((c) => { if (alive && !c && !getSeed(String(id))) setFailed(true) }) })
    return () => { alive = false }
  }, [id, attempt]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => onRetry(() => setAttempt((a) => a + 1)), [])

  // Видимая часть фото — как на сайте (≈ 0,66 ширины), плюс зона под строкой состояния и под наезжающим листом
  const photoH = Math.round(Math.min(width * 0.92, 520))
  // лента — фото и видео, как на сайте; на весь экран открываются только фото
  const media = (data?.photos ?? []).map((p) => ({ uri: mediaUrl(p.url) as string, poster: mediaUrl(p.thumbnail_url || p.url) as string, video: !!p.is_video })).filter((m) => !!m.uri)
  const photos = media.filter((m) => !m.video).map((m) => m.uri)
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
  if (owner?.is_company) chips.push({ label: 'Компания', tone: 'primary' })
  if (data.delivery_available) chips.push({ label: 'Доставка', tone: 'plain' })
  if (data.price_negotiable) chips.push({ label: 'Торг уместен', tone: 'plain' })
  const attrs = attrRows(data.attributes as Record<string, unknown> | undefined, schema)
  const keyFacts = factChips(rootSlug(data), data.attributes as Record<string, unknown> | undefined, schema)
  const verdict = VERDICTS[(data as unknown as { price_check?: { verdict?: string } }).price_check?.verdict ?? '']
  const mine = !!(user && owner && user.id === owner.id)
  // Звонок — как на сайте: трубка ведёт в переписку, где запрашивается звонок
  const gone = data.status === 'sold' || data.status === 'archived'
  const isResume = (data.attributes as Record<string, unknown> | undefined)?.listing_kind === 'resume'
  const fromTg = data.external_source === 'telegram' && !!data.external_author
  const askOptions = ['Ещё актуально?', 'Где и когда можно посмотреть?', ...(data.price_negotiable ? ['Торг уместен?'] : []), ...(data.delivery_available ? ['Доставка возможна?'] : [])]
  // как на сайте: выбранный вопрос сразу уходит продавцу, затем — переписка
  const startChatWith = async (text?: string) => {
    if (!token) { router.push('/login'); return }
    setOpening(true)
    try {
      const chat = await startChat(token, data.id)
      if (text) await sendMessage(token, chat.id, text).catch(() => {})
      router.push(`/chat/${chat.id}`)
    } catch { Linking.openURL(`${SITE}${data.path ?? ''}`) } finally { setOpening(false) }
  }
  const openChat = async () => {
    if (!token) { router.push('/login'); return }
    setOpening(true)
    try { const chat = await startChat(token, data.id); router.push(`/chat/${chat.id}`) } catch { /* сеть */ } finally { setOpening(false) }
  }
  const stripH = photoH + insets.top + SHEET_OVERLAP
  // название раздела для «Сейчас: …» в окне переноса
  const cp = (data as unknown as { category_path?: { name?: Record<string, string> | string }[] }).category_path
  const lastCat = Array.isArray(cp) && cp.length ? cp[cp.length - 1]?.name : null
  const catTitle = lastCat ? (typeof lastCat === 'string' ? lastCat : lastCat[getLang()] || lastCat.ru) : (data.category_slug ?? null)
  const staffDelete = () => {
    if (!token) return
    Alert.alert(tr('Удалить объявление?'), tr('Объявление пропадёт из ленты и у продавца.'), [
      { text: tr('Отмена'), style: 'cancel' },
      { text: tr('Удалить'), style: 'destructive', onPress: () => { deleteListingStaff(token, data.id, true).then(() => router.back()).catch(() => Alert.alert(tr('Не получилось удалить'))) } },
    ])
  }

  return (
    <View style={styles.page}>
      <ScrollView contentContainerStyle={{ paddingBottom: 96 + insets.bottom }} showsVerticalScrollIndicator={false}>
        {/* Фото — как на сайте: снимок целиком (contain) на размытой подложке из того же снимка */}
        <View style={{ width, height: stripH, backgroundColor: '#1E2621' }}>
          {media.length > 0 && (
            <FlatList
              ref={stripRef}
              data={media}
              keyExtractor={(m, k) => `${k}-${m.uri}`}
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={onScroll}
              renderItem={({ item, index }) => (
                // overflow hidden: увеличенная размытая подложка не вылезает на соседние фото (были жёсткие полосы по краям)
                <Pressable style={{ width, height: stripH, overflow: 'hidden' }} disabled={item.video} onPress={() => setViewer(photos.indexOf(item.uri))} accessibilityRole="imagebutton" accessibilityLabel={tr('Открыть фото')}>
                  <Image source={{ uri: item.poster }} style={[StyleSheet.absoluteFill, styles.blur]} contentFit="cover" blurRadius={30} />
                  <View style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(20,26,22,0.18)' }]} />
                  {item.video
                    ? <VideoSlide uri={item.uri} active={index === photo} width={width} height={photoH} top={insets.top} />
                    : <Image source={{ uri: item.uri }} style={{ position: 'absolute', left: 0, right: 0, top: insets.top, height: photoH }} contentFit="contain" transition={200} />}
                </Pressable>
              )}
            />
          )}
          {media.length > 1 && (
            <View style={[styles.counter, { bottom: SHEET_OVERLAP + 12 }]}><Text style={styles.counterText}>{photo + 1} / {media.length}</Text></View>
          )}
        </View>

        {/* Белый лист со скруглением наезжает на фото — как .detail-sheet на сайте */}
        <View style={styles.sheet}>
          {gone && (
            <View style={styles.gone}>
              <Text style={styles.goneTitle}>{tr(data.status === 'sold' ? 'Продано' : 'Объявление снято')}</Text>
              <Text style={styles.goneNote}>{tr('Продавец больше не продаёт эту вещь')}</Text>
            </View>
          )}
          {!gone && !!data.is_reserved && (
            <View style={styles.reservedBanner}><Text style={styles.reservedText}>{tr(data.reserved_for_me ? 'Продавец забронировал это для вас' : 'Забронировано другим покупателем')}</Text></View>
          )}
          {/* путь по разделам над ценой — как на сайте */}
          {!!catTitle && (
            <Pressable onPress={() => data.category_slug && router.push(`/c/${data.category_slug}` as never)}>
              <Text style={styles.crumbs} numberOfLines={1}>{catTitle}</Text>
            </Pressable>
          )}
          <View style={styles.priceRow}>
            <Text style={styles.price}>{formatPrice(data.price, data.currency, data.is_free)}</Text>
            {!!data.previous_price && !data.is_free && <Text style={styles.oldPrice}>{formatPrice(data.previous_price, data.currency)}</Text>}
          </View>
          <Text style={styles.title}>{title}</Text>
          {/* факты значками под названием: город, когда, просмотры — как на сайте */}
          <View style={styles.factChips}>
            {!!data.city && <View style={styles.factChip}><Icon name="pin" size={13} color={colors.inkSoft} /><Text style={styles.factChipT}>{cityName(data.city)}</Text></View>}
            {!!data.published_at && <View style={styles.factChip}><Icon name="clock" size={13} color={colors.inkSoft} /><Text style={styles.factChipT}>{timeAgo(data.published_at)}</Text></View>}
            {!!(data as { views_count?: number }).views_count && <View style={styles.factChip}><Icon name="eye" size={13} color={colors.inkSoft} /><Text style={styles.factChipT}>{(data as { views_count?: number }).views_count}</Text></View>}
          </View>
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
            <Pressable style={styles.priceCheck} onPress={() => setGaugeOpen(true)} accessibilityRole="button">
              <Image source={{ uri: `${SITE}/price/price-${(data as unknown as { price_check?: { verdict?: string } }).price_check?.verdict}.png` }} style={styles.pcImg} contentFit="contain" />
              <View style={{ flex: 1 }}>
                <Text style={styles.pcTitle}>{tr(verdict.title)}</Text>
                <Text style={styles.pcSub}>{tr('Оценка PLONK')}</Text>
              </View>
              <Icon name="forward" size={16} color={colors.muted} />
            </Pressable>
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
                  {(owner.official || owner.document_verified) && (
                    <View style={styles.verified}>
                      <VerifiedMark official={owner.official} verified={owner.document_verified} />
                      <Text style={styles.verifiedText}>{owner.official ? tr('Команда PLONK') : tr('Личность подтверждена')}</Text>
                    </View>
                  )}
                </View>
                {(owner.rating_count ?? 0) > 0 ? (
                  <View style={styles.starsRow}>
                    {[1, 2, 3, 4, 5].map((k) => <Star key={k} size={13} color={k <= Math.round(owner.rating_avg ?? 0) ? '#E0A526' : colors.sunken} />)}
                    <Text style={[styles.sellerSub, { marginLeft: 4 }]}>{(owner.rating_avg ?? 0).toFixed(1)} · {owner.rating_count ?? 0} {plural(owner.rating_count ?? 0, { ru: ['отзыв', 'отзыва', 'отзывов'], en: ['review', 'reviews'], sr: ['recenzija', 'recenzije', 'recenzija'] })}</Text>
                  </View>
                ) : <Text style={styles.sellerSub}>{tr('Пока нет отзывов')}</Text>}
                <Text style={styles.sellerSub}>
                  {[since ? tr('Здесь с {date}', { date: monthYear(since) }) : '', (owner.listings_count ?? 0) > 1 ? `${owner.listings_count} ${plural(owner.listings_count ?? 0, { ru: ['объявление', 'объявления', 'объявлений'], en: ['listing', 'listings'], sr: ['oglas', 'oglasa', 'oglasa'] })}` : ''].filter(Boolean).join('  ·  ')}
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
                <Text style={[styles.loc, { flex: 1 }]}>{cityName(data.city)}</Text>
                {data.location_lat != null && (
                  <Pressable onPress={() => setMapOpen(true)} hitSlop={8}><Text style={styles.mapLink}>{tr('Узнать подробности')}</Text></Pressable>
                )}
              </View>
            </View>
          )}

          {attrs.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.h3}>{tr('Характеристики')}</Text>
              <View style={styles.attrs}>
                {(attrsOpen ? attrs : attrs.slice(0, 6)).map((r, k, arr) => (
                  <View key={r.label} style={[styles.attr, k === arr.length - 1 && { borderBottomWidth: 0 }]}>
                    <Text style={styles.attrLabel}>{r.label}</Text>
                    <Text style={styles.attrValue}>{r.value}</Text>
                  </View>
                ))}
              </View>
              {!attrsOpen && attrs.length > 6 && <Pressable onPress={() => setAttrsOpen(true)} hitSlop={6}><Text style={styles.readMore}>{tr('Показать все')}</Text></Pressable>}
            </View>
          )}

          {!!description && (
            <View style={styles.section}>
              <Text style={styles.h3}>{tr('Описание')}</Text>
              <Text style={styles.text} numberOfLines={descOpen || description.length <= 320 ? undefined : 7}>{description}</Text>
              {description.length > 320 && !descOpen && <Pressable onPress={() => setDescOpen(true)} hitSlop={6}><Text style={styles.readMore}>{tr('Читать полностью')}</Text></Pressable>}
            </View>
          )}

          {/* вакансия — «Откликнуться» (работодателю — его отклики); остальное — вход в витрину продавца */}
          {(data.attributes as Record<string, unknown> | undefined)?.listing_kind === 'vacancy' && !gone && data.external_source !== 'telegram' && (
            <View style={{ marginTop: 14 }}><JobRespond listingId={data.id} ownerId={owner?.id} /></View>
          )}
          {!!owner?.id && !isResume && (data.attributes as Record<string, unknown> | undefined)?.listing_kind !== 'vacancy' && <StorefrontLink ownerId={owner.id} />}
          {!mine && (
            <Pressable onPress={() => (token ? setReportOpen(true) : router.push('/login'))} style={styles.report} hitSlop={6}>
              <Text style={styles.reportText}>{tr('Пожаловаться')}</Text>
            </Pressable>
          )}
          {/* как .detail-meta сайта: просмотры, в избранном, дата, номер — отдельными строками */}
          <View style={styles.meta}>
            {(data.views_count ?? 0) > 0 && <Text style={styles.metaLine}>{data.views_count} {plural(data.views_count ?? 0, { ru: ['просмотр', 'просмотра', 'просмотров'], en: ['view', 'views'], sr: ['pregled', 'pregleda', 'pregleda'] })}</Text>}
            {((data as unknown as { favorites_count?: number }).favorites_count ?? 0) > 0 && <Text style={styles.metaLine}>{tr('{n} в избранном', { n: (data as unknown as { favorites_count: number }).favorites_count })}</Text>}
            {!!data.published_at && <Text style={styles.metaLine}>{relTime(data.published_at)}</Text>}
            {!!data.number && <Text style={styles.metaLine}>№ {data.number}</Text>}
          </View>
        </View>
        <CardsRow title={tr('Ещё у этого продавца')} items={more} exclude={data.id} />
        <CardsRow title={tr('Похожие')} items={similar} exclude={data.id} />
      </ScrollView>

      {back}
      <Pressable style={[styles.shareTop, { top: insets.top + 8 }]} hitSlop={6} accessibilityLabel={tr('Поделиться')}
        onPress={() => Share.share({ message: `${title} — ${formatPrice(data.price, data.currency, data.is_free)}\n${SITE}${data.path ?? ''}` }).catch(() => {})}>
        <Icon name="share" size={19} color="#fff" />
      </Pressable>
      <HeartButton id={data.id} size={40} dark style={[styles.heartTop, { top: insets.top + 8 }]} />
      {/* сотрудникам — как на сайте: перенести в другой раздел и удалить */}
      {staff && (
        <>
          <Pressable style={[styles.shareTop, { top: insets.top + 8, right: 108 }]} hitSlop={6} accessibilityLabel={tr('Перенести в раздел')} onPress={() => setMoveOpen(true)}>
            <Icon name="list" size={18} color="#fff" />
          </Pressable>
          <Pressable style={[styles.shareTop, { top: insets.top + 8, right: 156 }]} hitSlop={6} accessibilityLabel={tr('Удалить')} onPress={staffDelete}>
            <Icon name="trash" size={18} color="#FFB4AB" />
          </Pressable>
        </>
      )}
      {moveOpen && !!token && (
        <MoveSheet token={token} listingId={data.id} current={movedTo || catTitle} onClose={() => setMoveOpen(false)}
          onMoved={(name: string) => { setMovedTo(name); setMoveOpen(false); Alert.alert(tr('Перенесено'), name) }} />
      )}
      <ImageView
        images={photos.map((uri) => ({ uri }))}
        imageIndex={Math.max(0, viewer ?? 0)}
        visible={viewer !== null}
        onRequestClose={() => { setViewer(null); stripRef.current?.scrollToOffset({ offset: Math.max(0, media.findIndex((m) => m.uri === photos[photo])) * width, animated: false }) }}
        onImageIndexChange={(i) => setPhoto(Math.max(0, media.findIndex((m) => m.uri === photos[i])))}
        presentationStyle="overFullScreen"
        backgroundColor="#0B0F0D"
        FooterComponent={({ imageIndex }) => (
          <View style={[styles.viewerFoot, { paddingBottom: insets.bottom + 18 }]}>
            <Text style={styles.viewerCount}>{imageIndex + 1} / {photos.length}</Text>
          </View>
        )}
      />
      <Modal visible={mapOpen} animationType="slide" onRequestClose={() => setMapOpen(false)}>
        <View style={[styles.mapPage, { paddingTop: insets.top }]}>
          <View style={styles.mapHead}>
            <Pressable onPress={() => setMapOpen(false)} hitSlop={10} style={styles.mapBack} accessibilityLabel={tr('Назад')}><Icon name="back" size={20} color={colors.ink} /></Pressable>
            <Text style={styles.mapTitle} numberOfLines={1}>{data?.title}</Text>
          </View>
          <View style={{ flex: 1 }}>
            {mapOpen && data?.location_lat != null && <MapWeb mode="show" lat={data.location_lat} lng={data.location_lng} approximate={!!data.location_approximate} height="100%" />}
          </View>
          <View style={[styles.mapAddr, { paddingBottom: insets.bottom + 14 }]}>
            <Text style={styles.mapAddrLabel}>{tr('Местоположение')}</Text>
            <View style={styles.mapAddrRow}>
              <Text style={styles.mapAddrText}>{mapAddr || cityName(data?.city)}</Text>
              <Pressable onPress={async () => { await Clipboard.setStringAsync(mapAddr || cityName(data?.city)).catch(() => {}); setAddrCopied(true); setTimeout(() => setAddrCopied(false), 1500) }} hitSlop={8} style={styles.mapCopy} accessibilityLabel={tr('Копировать')}>
                <Icon name={addrCopied ? 'check' : 'copy'} size={17} color={colors.ink} />
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
      <Sheet visible={gaugeOpen} title={tr('Оценка цены')} onClose={() => setGaugeOpen(false)}>
        {(() => {
          const pc = (data as unknown as { price_check?: { low_eur?: number; median_eur?: number; high_eur?: number; mine_eur?: number; based_on?: number } }).price_check
          if (!pc?.low_eur || !pc.high_eur || pc.mine_eur == null) return null
          const lo = pc.low_eur, hi = pc.high_eur, span = Math.max(hi - lo, 1)
          const pos = Math.min(1, Math.max(0, (pc.mine_eur - lo) / span))
          return (
            <View style={{ paddingHorizontal: 20, paddingBottom: 10, gap: 12 }}>
              <Text style={styles.gaugeLead}>{tr(verdict?.title ?? '')}</Text>
              <View style={styles.gauge}>
                <View style={[styles.gaugePart, { backgroundColor: '#BFE7D3' }]} />
                <View style={[styles.gaugePart, { backgroundColor: colors.sunken }]} />
                <View style={[styles.gaugePart, { backgroundColor: '#F6CDB8' }]} />
                <View style={[styles.gaugeMark, { left: `${pos * 100}%` }]} />
              </View>
              <View style={styles.gaugeLabels}>
                <Text style={styles.gaugeLabel}>{formatPrice(lo, 'EUR')}</Text>
                {!!pc.median_eur && <Text style={styles.gaugeLabel}>{tr('рынок')} {formatPrice(pc.median_eur, 'EUR')}</Text>}
                <Text style={styles.gaugeLabel}>{formatPrice(hi, 'EUR')}</Text>
              </View>
              {!!pc.based_on && <Text style={styles.gaugeNote}>{tr('На основе {n} похожих объявлений', { n: pc.based_on })}</Text>}
            </View>
          )
        })()}
      </Sheet>
      <Sheet visible={askOpen} title={tr('Спросить у продавца')} onClose={() => setAskOpen(false)}>
        {askOptions.map((q) => <SheetAction key={q} label={tr(q)} onPress={() => { setAskOpen(false); startChatWith(tr(q)) }} />)}
        <SheetAction label={tr('Написать своё сообщение')} icon={<Icon name="edit" size={20} color={colors.ink} />} onPress={() => { setAskOpen(false); startChatWith() }} />
      </Sheet>
      <ReportSheet visible={reportOpen} listingId={data.id} token={token} onClose={() => setReportOpen(false)} />
      <View style={[styles.bar, { paddingBottom: 10 + insets.bottom }]}>
        {mine ? (
          <Pressable style={[styles.cta, styles.ctaMine]} onPress={() => router.push(`/edit/${data.id}`)} accessibilityRole="button"><Text style={styles.ctaMineText}>{tr('Редактировать')}</Text></Pressable>
        ) : gone ? (
          <Pressable style={styles.cta} onPress={() => router.push(data.category_slug ? `/c/${data.category_slug}` : '/categories')} accessibilityRole="button"><Text style={styles.ctaText}>{tr('Смотреть похожие в разделе')}</Text></Pressable>
        ) : fromTg ? (
          <Pressable style={[styles.cta, styles.ctaTg]} onPress={() => (token ? Linking.openURL(`https://t.me/${data.external_author}`) : router.push('/login'))} accessibilityRole="button">
            <Icon name="telegram" size={18} color="#fff" filled />
            <Text style={styles.ctaText}>{tr('Написать в Telegram')}</Text>
          </Pressable>
        ) : (
          <View style={styles.ctaRow}>
          {owner?.has_phone && (
            <Pressable style={styles.callBtn} disabled={opening} accessibilityLabel={tr('Позвонить через чат')} onPress={() => openChat()}>
              <Icon name="phone" size={20} color={colors.ink} />
            </Pressable>
          )}
          <Pressable style={[styles.cta, { flex: 1 }, opening && { opacity: 0.7 }]} disabled={opening} accessibilityRole="button" onPress={async () => {
            // как на сайте: сначала «Спросить у продавца» с готовыми вопросами; резюме — сразу в переписку
            if (!token) { router.push('/login'); return }
            if (isResume) startChatWith(); else setAskOpen(true)
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

/** Объявление из данных карточки — пока грузится полное: фото, цена, название, город, время. */
function fromCard(item: FeedItem): Listing {
  const urls = (item.photos && item.photos.length ? item.photos : [item.cover_photo]).filter(Boolean) as string[]
  return {
    id: item.id, price: item.price, currency: item.currency, is_free: item.is_free, city: item.city, published_at: item.published_at,
    photos: urls.map((u) => ({ id: u, url: u, thumbnail_url: u, is_video: false })),
    translations: [{ language: getLang(), title: item.title, description: '' }],
  } as unknown as Listing
}

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
      out.push({ key, icon: FACT_ICON[key], text: `${value}${total ? `/${total}` : ''} ${tr('эт.')}` })
    } else {
      out.push({ key, icon: FACT_ICON[key], text: `${value} ${FACT_UNIT[key] && !opt ? tr(FACT_UNIT[key]) : ''}`.trim() })
    }
  }
  return out
}

/** Оценка цены — та же, что на сайте («Дешевле похожих на PLONK»). */
const VERDICTS: Record<string, { title: string; icon: IconName; color: string; bg: string }> = {
  cheap: { title: 'Дешевле похожих на PLONK', icon: 'trending-down', color: '#0B5C42', bg: '#DDF3E8' },
  fair: { title: 'Цена как у похожих', icon: 'remove', color: colors.inkSoft, bg: colors.sunken },
  expensive: { title: 'Дороже похожих на PLONK', icon: 'trending-up', color: '#B4501E', bg: '#FCE6DA' },
}

const toneStyle = StyleSheet.create({
  accent: { backgroundColor: colors.accent, color: '#fff' },
  primary: { backgroundColor: colors.primarySoft, color: colors.primaryDeep },
  gold: { backgroundColor: colors.goldDark, color: '#fff' },
  plain: { backgroundColor: colors.sunken, color: colors.inkSoft },
})

const styles = StyleSheet.create({
  crumbs: { fontFamily: font[600], fontSize: 13.5, color: colors.muted, marginBottom: 4 },
  factChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  factChip: { flexDirection: 'row', alignItems: 'center', gap: 5, height: 30, paddingHorizontal: 10, borderRadius: 15, backgroundColor: colors.surface, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  factChipT: { fontFamily: font[700], fontSize: 12.5, color: colors.inkSoft },
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
  gone: { marginBottom: 12, padding: 12, borderRadius: 14, backgroundColor: colors.sunken, gap: 2 },
  goneTitle: { fontSize: 15, fontFamily: font[800], color: colors.ink },
  goneNote: { fontSize: 13.5, fontFamily: font[500], color: colors.inkSoft },
  reservedBanner: { marginBottom: 12, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 12, backgroundColor: colors.warmBg },
  reservedText: { fontSize: 13.5, fontFamily: font[700], color: '#8A6A1F' },
  ctaTg: { flexDirection: 'row', gap: 8, backgroundColor: '#229ED9' },
  // как .detail-meta сайта: строки плотно, 12,5, серые
  meta: { marginTop: 12, gap: 2 },
  metaLine: { fontSize: 12.5, lineHeight: 17, fontFamily: font[500], color: colors.muted },
  readMore: { fontSize: 14, fontFamily: font[700], color: colors.primaryDeep, marginTop: 6 },
  mapLink: { fontSize: 13.5, fontFamily: font[700], color: colors.primaryDeep },
  mapPage: { flex: 1, backgroundColor: colors.bg },
  mapHead: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 12, paddingVertical: 8 },
  mapBack: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  mapTitle: { flex: 1, fontSize: 16, fontFamily: font[800], color: colors.ink },
  mapAddr: { paddingHorizontal: 16, paddingTop: 14, backgroundColor: colors.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, marginTop: -16, gap: 4 },
  mapAddrLabel: { fontSize: 12.5, fontFamily: font[700], color: colors.muted },
  mapAddrRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  mapAddrText: { flex: 1, fontSize: 15, lineHeight: 20, fontFamily: font[700], color: colors.ink },
  mapCopy: { width: 36, height: 36, borderRadius: 10, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  blur: { opacity: 0.75, transform: [{ scale: 1.25 }] },
  viewerFoot: { alignItems: 'center' },
  viewerCount: { color: '#fff', fontSize: 14, fontFamily: font[700], backgroundColor: 'rgba(255,255,255,0.14)', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 12, overflow: 'hidden' },
  counter: { position: 'absolute', alignSelf: 'center', backgroundColor: 'rgba(28,38,32,0.62)', borderRadius: radius.chip, paddingHorizontal: 12, paddingVertical: 5 },
  counterText: { color: '#fff', fontSize: 13, fontFamily: font[700] },
  sheet: {
    marginTop: -SHEET_OVERLAP, backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingHorizontal: 20, paddingTop: 22,
    shadowColor: '#14201A', shadowOpacity: 0.05, shadowRadius: 12, shadowOffset: { width: 0, height: -6 },
  },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10 },
  price: { fontFamily: mono, fontSize: 32, letterSpacing: -1, color: colors.ink },
  oldPrice: { fontFamily: mono, fontSize: 15, color: colors.muted, textDecorationLine: 'line-through' },
  // Как .detail-title сайта: 17,5 / 800 / межстрочный 1,3
  title: { fontFamily: font[800], fontSize: 17.5, lineHeight: 23, letterSpacing: -0.18, color: colors.ink, marginTop: 12 },
  fromTg: { alignSelf: 'flex-start', marginTop: 8, paddingHorizontal: 9, paddingVertical: 4, borderRadius: 8, overflow: 'hidden', backgroundColor: '#EAF3FF', color: '#2D7DD2', fontFamily: font[700], fontSize: 12.5 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  facts: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  fact: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 11, height: 36, borderRadius: 12, backgroundColor: colors.sunken },
  factText: { fontSize: 14, fontFamily: font[700], color: colors.ink },
  priceCheck: { marginTop: 16, flexDirection: 'row', alignItems: 'center', gap: 12, padding: 13, borderRadius: 17, backgroundColor: colors.sunken },
  pcImg: { width: 44, height: 44 },
  pcIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  gaugeLead: { fontSize: 15.5, fontFamily: font[800], color: colors.ink },
  gauge: { flexDirection: 'row', height: 12, borderRadius: 6, overflow: 'visible', gap: 3 },
  gaugePart: { flex: 1, borderRadius: 6 },
  gaugeMark: { position: 'absolute', top: -5, width: 4, height: 22, marginLeft: -2, borderRadius: 2, backgroundColor: colors.ink },
  gaugeLabels: { flexDirection: 'row', justifyContent: 'space-between' },
  gaugeLabel: { fontSize: 12.5, fontFamily: font[700], color: colors.inkSoft },
  gaugeNote: { fontSize: 12.5, fontFamily: font[500], color: colors.muted },
  pcTitle: { fontSize: 14.5, fontFamily: font[800], letterSpacing: -0.15, color: colors.ink },
  pcSub: { fontSize: 12.5, fontFamily: font[600], color: colors.muted, marginTop: 1 },
  chip: { overflow: 'hidden', borderRadius: radius.chip, paddingHorizontal: 10, paddingVertical: 5, fontSize: 12, fontFamily: font[800] },
  seller: { marginTop: 20, flexDirection: 'row', alignItems: 'center', gap: 11, paddingVertical: 14, paddingHorizontal: 14, borderRadius: 22, backgroundColor: colors.surface,
    shadowColor: '#0F1512', shadowOpacity: 0.06, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  avatarImg: { width: 52, height: 52 },
  avatarLetter: { color: '#fff', fontSize: 20, fontFamily: font[800] },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  verified: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  seal: { width: 16, height: 16, borderRadius: 8, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  verifiedText: { fontSize: 12.5, fontFamily: font[700], color: colors.inkSoft },
  // Как .seller-name / .seller-meta сайта: имя 14,5 / 800, строки под ним 12 / 600
  name: { fontSize: 14.5, fontFamily: font[800], color: colors.ink, flexShrink: 1 },
  starsRow: { flexDirection: 'row', alignItems: 'center', gap: 1 },
  sellerSub: { fontSize: 12, fontFamily: font[600], color: colors.muted, marginTop: 2 },
  section: { marginTop: 26, gap: 8 },
  h3: { fontSize: 18, fontFamily: font[800], color: colors.ink },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  loc: { fontSize: 15, fontFamily: font[600], color: colors.inkSoft },
  attrs: { backgroundColor: colors.sunken, borderRadius: 16, paddingHorizontal: 16 },
  attr: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: colors.sunken },
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
