import EmptyArt from '../src/components/EmptyArt'
import { tr } from '../src/i18n'
import * as Linking from 'expo-linking'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View, Alert } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { markAllNoticesRead, markNoticeRead, type Notice, notifications, clearAllNotifications } from '../src/api'
import SwipeRow from '../src/components/SwipeRow'
import { authed } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { SITE } from '../src/config'
import { plainText, relTime, timeAgo } from '../src/format'
import { colors, font } from '../src/theme'

/** Куда ведёт уведомление: переписка и объявление — внутри приложения, остальное — на сайте. */
export function openNoticeLink(link?: string | null) {
  if (!link) return
  const chat = link.match(/^\/chat\/([\w-]+)/)
  const go = link.match(/^\/go\/([\w-]+)/)
  if (chat) router.push(`/chat/${chat[1]}`)
  else if (go) router.push(`/listing/${go[1]}`)
  else Linking.openURL(link.startsWith('http') ? link : `${SITE}${link}`)
}

/** Уведомления: новые — с точкой и жирным, нажатие отмечает прочитанным и ведёт по ссылке; «Прочитать все». */
export default function Notifications() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [items, setItems] = useState<Notice[] | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    try { setItems((await notifications(token)).items) } catch { setItems((v) => v ?? []) }
  }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const remove = (id: string) => {
    setItems((x) => (x ?? []).filter((n) => n.id !== id))
    if (token) authed(`/notifications/${id}`, token, 'DELETE').catch(() => {})
  }
  const open = (n: Notice) => {
    if (!n.is_read && token) {
      setItems((all) => (all ?? []).map((x) => (x.id === n.id ? { ...x, is_read: true } : x)))
      markNoticeRead(token, n.id).catch(() => {})
    }
    openNoticeLink(n.link)
  }
  const unread = (items ?? []).filter((n) => !n.is_read).length

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.head}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}>
          <Icon name="back" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.h1}>{tr('Уведомления')}</Text>
        {/* как на сайте: «Прочитать всё» — если есть непрочитанные, «Очистить» — если уведомления есть */}
        <View style={styles.headActions}>
          {unread > 0 && !!token && (
            <Pressable hitSlop={8} onPress={async () => { await markAllNoticesRead(token).catch(() => {}); load() }}>
              <Text style={styles.all}>{tr('Прочитать всё')}</Text>
            </Pressable>
          )}
          {!!items?.length && !!token && (
            <Pressable hitSlop={8} onPress={() => Alert.alert(tr('Удалить все уведомления?'), undefined, [
              { text: tr('Отмена'), style: 'cancel' },
              { text: tr('Очистить'), style: 'destructive', onPress: async () => { await clearAllNotifications(token).catch(() => {}); load() } },
            ])}>
              <Text style={[styles.all, { color: colors.muted }]}>{tr('Очистить')}</Text>
            </Pressable>
          )}
        </View>
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <FlatList
          data={items}
          keyExtractor={(n) => n.id}
          contentContainerStyle={items.length === 0 ? { flexGrow: 1 } : { paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          renderItem={({ item }) => (
            // как .notif-row сайта: непрочитанное — зелёная подложка и точка слева; текст 13,5, время 11 («28 мин»)
            // свайп влево — «Удалить», как на сайте
            <SwipeRow right={[{ label: tr('Удалить'), color: '#E5533D', onPress: () => remove(item.id) }]}>
            <Pressable style={[styles.nRow, !item.is_read && styles.nRowUnread]} onPress={() => open(item)}>
              {!item.is_read && <View style={styles.nDot} />}
              <Text style={styles.nText}>{plainText(item.text)}</Text>
              <Text style={styles.nTime}>{timeAgo(item.created_at)}</Text>
            </Pressable>
            </SwipeRow>
          )}
          ListEmptyComponent={
            // Как на сайте: значок и текст вверху экрана, без отдельного заголовка
            <View style={styles.empty}>
              <EmptyArt name="notifications" />
              <Text style={styles.emptyText}>{tr('Уведомлений пока нет — здесь появятся решения по объявлениям, ответы в чатах и новое по вашим подпискам.')}</Text>
            </View>
          }
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  nRow: { paddingVertical: 14, paddingHorizontal: 16, marginHorizontal: 12, marginTop: 8, borderRadius: 20, backgroundColor: colors.surface,
    shadowColor: '#0F1512', shadowOpacity: 0.05, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 1 },
  nRowUnread: { borderLeftWidth: 3, borderLeftColor: colors.primary },
  nDot: { position: 'absolute', left: 6, top: 19, width: 7, height: 7, borderRadius: 4, backgroundColor: colors.primary },
  nText: { fontSize: 13.5, lineHeight: 19, fontFamily: font[500], color: colors.ink, paddingLeft: 14 },
  nTime: { fontSize: 11, fontFamily: font[500], color: colors.muted, marginTop: 5, paddingLeft: 14 },
  // кнопки «Прочитать всё» и «Очистить» — строкой под заголовком, как на сайте (рядом с ним они сжимали заголовок)
  headActions: { flexDirection: 'row', alignItems: 'center', gap: 16, width: '100%', paddingLeft: 52, marginTop: 4 },
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingTop: 6, paddingBottom: 8 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  h1: { fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  all: { fontSize: 13.5, fontFamily: font[700], color: colors.primaryDeep },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14 },
  dot: { width: 9, height: 9, borderRadius: 5, backgroundColor: colors.accent },
  text: { fontFamily: font[400], fontSize: 15.5, lineHeight: 21, color: colors.inkSoft },
  textOn: { color: colors.ink, fontFamily: font[700] },
  time: { fontFamily: font[400], fontSize: 12.5, color: colors.muted },
  sep: { height: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginLeft: 37 },
  empty: { alignItems: 'center', gap: 14, paddingTop: 44, paddingHorizontal: 32 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink },
  emptyText: { fontSize: 14, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center' },
})
