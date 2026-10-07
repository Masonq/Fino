import EmptyArt from '../../src/components/EmptyArt'
import * as Haptics from 'expo-haptics'
import SwipeRow from '../../src/components/SwipeRow'
import { tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useRef, useState } from 'react'
import { ActionSheetIOS, Alert, Animated, FlatList, Platform, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { type Chat, chatPref, isOffer } from '../../src/api'
import { useAuth } from '../../src/auth'
import { useChats } from '../../src/chats'
import Icon from '../../src/components/Icon'
import Skeleton from '../../src/components/Skeleton'
import { mediaUrl } from '../../src/config'
import { plainText, shortTime, timeAgo } from '../../src/format'
import { colors, font } from '../../src/theme'
import { useTabInset } from '../../src/tabInset'

/** Сообщения: список переписок — фото объявления, собеседник, последнее сообщение, время, непрочитанные. */
export default function Chats() {
  const tabInset = useTabInset()
  const { token, ready } = useAuth()
  const { chats, refresh, failed } = useChats()
  const [refreshing, setRefreshing] = useState(false)
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<'all' | 'unread' | 'buy' | 'sell'>('all')
  const scrollY = useRef(new Animated.Value(0)).current
  const [headH, setHeadH] = useState(150)

  useFocusEffect(useCallback(() => { refresh() }, [refresh]))

  // как свайп на сайте: долгое нажатие на переписку — закрепить, без звука, непрочитано, удалить у себя
  const chatMenu = (c: Chat) => {
    if (!token) return
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {})
    const acts: [string, string][] = [
      [c.pinned ? 'unpin' : 'pin', c.pinned ? tr('Открепить') : tr('Закрепить')],
      [c.muted ? 'unmute' : 'mute', c.muted ? tr('Включить звук') : tr('Без звука')],
      [(c.unread ?? 0) > 0 ? 'read' : 'unread', (c.unread ?? 0) > 0 ? tr('Прочитано') : tr('Непрочитано')],
      ['hide', tr('Удалить у себя')],
    ]
    const run = (i: number) => { const a = acts[i]; if (a) chatPref(token, c.id, a[0]).then(() => refresh()).catch(() => {}) }
    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions({ options: [...acts.map((a) => a[1]), tr('Отмена')], destructiveButtonIndex: 3, cancelButtonIndex: 4 }, run)
    } else {
      Alert.alert(c.other_name || tr('Переписка'), undefined, [...acts.map((a, i) => ({ text: a[1], style: (i === 3 ? 'destructive' : 'default') as 'destructive' | 'default', onPress: () => run(i) })), { text: tr('Отмена'), style: 'cancel' as const }])
    }
  }

  if (!ready) return <SafeAreaView style={styles.page} />
  if (!token) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <EmptyArt name="chats" />
        <Text style={styles.title}>{tr('Переписка с продавцами')}</Text>
        <Text style={styles.text}>{tr('Войдите, чтобы писать продавцам и отвечать покупателям.')}</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>{tr('Войти')}</Text></Pressable>
      </SafeAreaView>
    )
  }

  const row = ({ item }: { item: Chat }) => {
    const photo = mediaUrl(item.listing_photo)
    const name = item.is_team ? tr('Команда PLONK') : (item.other_name || tr('Собеседник'))
    const preview = isOffer(item.last_kind) ? tr('Предложение цены') : plainText(item.last_text).replace(/\n+/g, ' ')
    const unread = item.unread || 0
    const act = (action: string) => { if (token) chatPref(token, item.id, action).then(() => refresh()).catch(() => {}) }
    return (
      // свайп, как на сайте: вправо — «Закрепить» / «Непрочитано», влево — «Без звука» / «Удалить» (длинный — сразу)
      <SwipeRow
        left={[
          { label: item.pinned ? tr('Открепить') : tr('Закрепить'), color: '#2F6BFF', onPress: () => act(item.pinned ? 'unpin' : 'pin') },
          { label: unread > 0 ? tr('Прочитано') : tr('Непрочитано'), color: '#0FA36A', onPress: () => act(unread > 0 ? 'read' : 'unread') },
        ]}
        right={[
          { label: item.muted ? tr('Включить звук') : tr('Без звука'), color: '#8A8F8C', onPress: () => act(item.muted ? 'unmute' : 'mute') },
          { label: tr('Удалить у себя'), color: '#E5533D', onPress: () => act('hide') },
        ]}>
      <Pressable style={[styles.row, unread > 0 && styles.rowUnread]} onPress={() => router.push(`/chat/${item.id}`)} onLongPress={() => chatMenu(item)} delayLongPress={420} accessibilityRole="button">
        <View style={styles.thumb}>
          {item.is_team
            ? <Image source={require('../../assets/icon.png')} style={styles.thumbImg} contentFit="cover" />
            : photo ? <Image source={{ uri: photo }} style={styles.thumbImg} contentFit="cover" transition={150} />
              : <Ionicons name="image-outline" size={22} color={colors.muted} />}
        </View>
        <View style={styles.rowBody}>
          <View style={styles.rowTop}>
            <Text style={styles.name} numberOfLines={1}>{name}</Text>
            {item.pinned && <Ionicons name="pin" size={13} color={colors.muted} />}
            {item.muted && <Ionicons name="notifications-off-outline" size={13} color={colors.muted} />}
            <Text style={styles.time}>{timeAgo(item.last_at)}</Text>
          </View>
          {!!item.listing_title && <Text style={styles.listing} numberOfLines={1}>{item.listing_title}</Text>}
          <View style={styles.rowTop}>
            <Text style={[styles.preview, unread > 0 && styles.previewOn]} numberOfLines={1}>
              {item.last_from_me && !!preview ? <Text style={styles.you}>{tr('Вы')}: </Text> : null}{preview || tr('Сообщений пока нет')}
            </Text>
            {unread > 0 && <View style={styles.badge}><Text style={styles.badgeText}>{unread > 99 ? '99+' : unread}</Text></View>}
          </View>
        </View>
      </Pressable>
      </SwipeRow>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      {/* шапка (заголовок, поиск, фильтры) уезжает вверх при прокрутке, как на сайте, и возвращается при
          прокрутке назад к началу; поверх списка, список начинается под ней */}
      <Animated.View onLayout={(e) => setHeadH(e.nativeEvent.layout.height)}
        style={[styles.headWrap, { transform: [{ translateY: scrollY.interpolate({ inputRange: [0, Math.max(1, headH)], outputRange: [0, -headH], extrapolate: 'clamp' }) }] }]}>
      {/* как на сайте: подводка (непрочитанные) и крупный заголовок */}
      <View style={{ paddingHorizontal: 16, paddingTop: 10, paddingBottom: 10 }}>
        <Text style={styles.kicker}>{(() => { const n = (chats ?? []).filter((c) => (c.unread ?? 0) > 0).length; return n ? tr('{n} непрочитанных', { n }) : tr('Покупки и продажи') })()}</Text>
        <Text style={[styles.h1, { paddingHorizontal: 0, paddingTop: 0, paddingBottom: 0 }]}>{tr('Сообщения')}</Text>
      </View>
      {/* Поиск и фильтры — как на сайте */}
      <View style={styles.search}>
        <Icon name="search" size={17} color={colors.muted} />
        <TextInput value={q} onChangeText={setQ} placeholder={tr('Поиск по переписке')} placeholderTextColor={colors.muted} style={styles.searchInput} returnKeyType="search" />
        {!!q && <Pressable onPress={() => setQ('')} hitSlop={8}><Icon name="close" size={15} color={colors.muted} /></Pressable>}
      </View>
      <View style={styles.filters}>
        {([['all', 'Все'], ['unread', 'Непрочитанные'], ['buy', 'Покупаю'], ['sell', 'Продаю']] as const).map(([k, label]) => (
          <Pressable key={k} onPress={() => setFilter(k)} style={[styles.pill, filter === k && styles.pillOn]} accessibilityRole="tab" accessibilityState={{ selected: filter === k }}>
            <Text style={[styles.pillText, filter === k && styles.pillTextOn]}>{tr(label)}</Text>
          </Pressable>
        ))}
      </View>
      </Animated.View>
      {chats === null ? (
        failed ? (
          <View style={styles.center}>
            <Text style={styles.title}>{tr('Не удалось загрузить')}</Text>
            <Pressable style={styles.cta} onPress={refresh}><Text style={styles.ctaText}>{tr('Повторить')}</Text></Pressable>
          </View>
        ) : (
          <View style={{ paddingHorizontal: 16, gap: 18, paddingTop: 6 + headH }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <View key={i} style={{ flexDirection: 'row', gap: 12 }}>
                <Skeleton style={{ width: 56, height: 56, borderRadius: 14 }} />
                <View style={{ flex: 1, gap: 7, paddingTop: 4 }}>
                  <Skeleton style={{ width: '55%', height: 14 }} />
                  <Skeleton style={{ width: '80%', height: 12 }} />
                </View>
              </View>
            ))}
          </View>
        )
      ) : (
        <Animated.FlatList
          onScroll={Animated.event([{ nativeEvent: { contentOffset: { y: scrollY } } }], { useNativeDriver: true })}
          scrollEventThrottle={16}
          data={[...chats].sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned)).filter((c) => {
            if (filter === 'unread' && !(c.unread ?? 0)) return false
            if (filter === 'buy' && c.is_seller) return false
            if (filter === 'sell' && !c.is_seller) return false
            const needle = q.trim().toLowerCase()
            return !needle || [c.other_name, c.listing_title, c.last_text].some((v) => (v ?? '').toLowerCase().includes(needle))
          })}
          keyExtractor={(c) => c.id}
          renderItem={row}
          progressViewOffset={headH}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          contentContainerStyle={chats.length === 0 ? { flexGrow: 1, paddingTop: headH, paddingBottom: tabInset } : { paddingTop: headH, paddingBottom: 16 + tabInset }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await refresh(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
          ListEmptyComponent={
            <View style={styles.center}>
              <EmptyArt name="chats" />
              <Text style={styles.title}>{tr('Пока нет переписок')}</Text>
              <Text style={styles.text}>{tr('Откройте объявление и нажмите «Написать продавцу».')}</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  headWrap: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 5, backgroundColor: colors.bg },
  you: { fontFamily: font[700], color: colors.ink },
  page: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  kicker: { fontSize: 15, fontFamily: font[600], color: colors.inkSoft },
  h1: { fontSize: 30, fontFamily: font[800], letterSpacing: -1, color: colors.ink, paddingHorizontal: 16, paddingTop: 10, paddingBottom: 10 },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, marginHorizontal: 12, height: 46, borderRadius: 18, backgroundColor: colors.surface, paddingHorizontal: 14,
    shadowColor: '#0F1512', shadowOpacity: 0.05, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 1 },
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontSize: 15, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  filters: { flexDirection: 'row', alignSelf: 'flex-start', gap: 2, marginHorizontal: 12, marginTop: 10, marginBottom: 8, padding: 3, borderRadius: 14, backgroundColor: colors.sunken },
  pill: { height: 34, paddingHorizontal: 12, borderRadius: 11, justifyContent: 'center' },
  pillOn: { backgroundColor: colors.inverse },
  pillText: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  pillTextOn: { color: colors.onInverse },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 36, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  row: { flexDirection: 'row', gap: 12, padding: 12, alignItems: 'center', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.bg },
  rowUnread: { backgroundColor: colors.surface },
  // как .chat-thumb сайта: 52, скругление 11 — фото объявления, не кружок
  thumb: { width: 52, height: 52, borderRadius: 11, backgroundColor: colors.photo, overflow: 'hidden', alignItems: 'center', justifyContent: 'center' },
  thumbImg: { width: 52, height: 52 },
  rowBody: { flex: 1, gap: 2 },
  rowTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  name: { flex: 1, fontSize: 14, fontFamily: font[700], color: colors.ink },
  time: { fontSize: 12, fontFamily: font[500], color: colors.muted },
  listing: { fontSize: 12.5, fontFamily: font[600], color: colors.inkSoft },
  preview: { flex: 1, fontSize: 13, fontFamily: font[400], color: colors.muted },
  previewOn: { color: colors.inkSoft, fontFamily: font[600] },
  badge: { minWidth: 20, height: 20, borderRadius: 10, paddingHorizontal: 6, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  badgeText: { color: '#fff', fontSize: 12, fontFamily: font[800] },
  sep: { height: 0 },
})
