import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router } from 'expo-router'
import { memo, useState } from 'react'
import { FlatList, NativeScrollEvent, NativeSyntheticEvent, Pressable, StyleSheet, Text, View } from 'react-native'

import type { FeedItem } from '../api'
import { mediaUrl } from '../config'
import { cityName, formatPrice, isFresh, relTime } from '../format'
import { colors, radius } from '../theme'

/**
 * Карточка ленты — как на сайте: фото листаются пальцем (до пяти, с полосками внизу), метки поверх фото
 * («Продвигается», «Забронировано» сверху, «Новое» и «Компания» снизу), огонёк у цены, если она ниже похожих,
 * золотая рамка у платного выделения. Нажатие открывает объявление.
 */
function ListingCard({ item, width }: { item: FeedItem; width: number }) {
  const [index, setIndex] = useState(0)
  const photoH = Math.round(width * 0.95)
  const list = (item.photos && item.photos.length ? item.photos : item.cover_photo ? [item.cover_photo] : [])
    .map((u) => mediaUrl(u))
    .filter(Boolean) as string[]
  const open = () => router.push(`/listing/${item.id}`)
  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const next = Math.round(e.nativeEvent.contentOffset.x / width)
    if (next !== index) setIndex(next)
  }

  return (
    <Pressable onPress={open} style={[styles.card, { width }, item.is_highlighted && styles.highlighted]}
      accessibilityRole="button" accessibilityLabel={`${item.title}, ${formatPrice(item.price, item.currency, item.is_free)}`}>
      <View style={[styles.photoBox, { height: photoH }]}>
        {list.length > 1 ? (
          <FlatList
            data={list}
            keyExtractor={(u, i) => `${i}-${u}`}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onScroll={onScroll}
            scrollEventThrottle={32}
            renderItem={({ item: uri }) => (
              <Pressable onPress={open}>
                <Image source={{ uri }} style={{ width, height: photoH }} contentFit="cover" transition={220} recyclingKey={uri} />
              </Pressable>
            )}
          />
        ) : list.length === 1 ? (
          <Image source={{ uri: list[0] }} style={{ width, height: photoH }} contentFit="cover" transition={220} />
        ) : null}

        <View style={StyleSheet.absoluteFill} pointerEvents="none">
          {(item.is_xl || item.is_reserved) && (
            <View style={styles.topBadges}>
              {item.is_xl && <Text style={[styles.badge, styles.badgeDark]}>Продвигается</Text>}
              {item.is_reserved && <Text style={[styles.badge, styles.badgeGold]}>Забронировано</Text>}
            </View>
          )}
          {isFresh(item.published_at) && (
            <View style={[styles.badgeRow, styles.fresh]}>
              <View style={styles.freshDot} />
              <Text style={styles.freshText}>Новое</Text>
            </View>
          )}
          {item.is_company && <Text style={[styles.badge, styles.company]}>Компания</Text>}
          {list.length > 1 && (
            <View style={styles.bars}>
              {list.map((u, i) => <View key={`${i}-${u}`} style={[styles.bar, i === index && styles.barOn]} />)}
            </View>
          )}
        </View>
      </View>

      <View style={styles.body}>
        <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
        <View style={styles.priceRow}>
          <Text style={styles.price} numberOfLines={1}>{formatPrice(item.price, item.currency, item.is_free)}</Text>
          {!!item.price_mark && <Ionicons name="flame" size={16} color={colors.accent} accessibilityLabel="Дешевле похожих" />}
        </View>
        <View style={styles.meta}>
          <Text style={styles.metaText} numberOfLines={1}>{cityName(item.city)}</Text>
          <Text style={styles.metaText}>{relTime(item.published_at)}</Text>
        </View>
      </View>
    </Pressable>
  )
}

export default memo(ListingCard)

const styles = StyleSheet.create({
  card: { backgroundColor: colors.surface, borderRadius: radius.card, overflow: 'hidden', borderWidth: 1, borderColor: colors.border },
  highlighted: { backgroundColor: colors.warmBg, borderColor: colors.gold, borderWidth: 1.5 },
  photoBox: { backgroundColor: colors.photo, overflow: 'hidden' },
  topBadges: { position: 'absolute', top: 10, left: 10, gap: 6, alignItems: 'flex-start' },
  badge: { overflow: 'hidden', borderRadius: radius.chip, paddingHorizontal: 9, paddingVertical: 4, fontSize: 10.5, fontWeight: '800' },
  badgeDark: { backgroundColor: colors.ink, color: '#fff' },
  badgeGold: { backgroundColor: colors.goldDark, color: '#fff' },
  badgeRow: { flexDirection: 'row', alignItems: 'center' },
  fresh: { position: 'absolute', left: 10, bottom: 10, backgroundColor: colors.accent, borderRadius: radius.chip, paddingLeft: 7, paddingRight: 9, paddingVertical: 4, gap: 5 },
  freshDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#fff' },
  freshText: { color: '#fff', fontSize: 11, fontWeight: '800' },
  company: { position: 'absolute', right: 10, bottom: 10, backgroundColor: colors.primarySoft, color: colors.primaryDeep },
  bars: { position: 'absolute', left: 10, right: 10, bottom: 4, flexDirection: 'row', gap: 3 },
  bar: { flex: 1, height: 2.5, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.45)' },
  barOn: { backgroundColor: '#fff' },
  body: { paddingHorizontal: 10, paddingTop: 8, paddingBottom: 10 },
  title: { fontSize: 14.5, lineHeight: 19, color: colors.ink, minHeight: 38 },
  priceRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  price: { fontSize: 18, fontWeight: '800', color: colors.ink, flexShrink: 1 },
  meta: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4, gap: 6 },
  metaText: { fontSize: 12, color: colors.muted, flexShrink: 1 },
})
