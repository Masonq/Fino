import { tr } from '../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import * as Linking from 'expo-linking'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { markAllNoticesRead, markNoticeRead, type Notice, notifications } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { SITE } from '../src/config'
import { plainText, relTime } from '../src/format'
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
          <Ionicons name="chevron-back" size={26} color={colors.ink} />
        </Pressable>
        <Text style={styles.h1}>{tr('Уведомления')}</Text>
        {unread > 0 && token ? (
          <Pressable hitSlop={8} onPress={async () => { await markAllNoticesRead(token).catch(() => {}); load() }}>
            <Text style={styles.all}>{tr('Прочитать все')}</Text>
          </Pressable>
        ) : <View style={{ width: 40 }} />}
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <FlatList
          data={items}
          keyExtractor={(n) => n.id}
          contentContainerStyle={items.length === 0 ? { flexGrow: 1 } : { paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          renderItem={({ item }) => (
            <Pressable style={styles.row} onPress={() => open(item)}>
              <View style={[styles.dot, item.is_read && { backgroundColor: 'transparent' }]} />
              <View style={{ flex: 1, gap: 3 }}>
                <Text style={[styles.text, !item.is_read && styles.textOn]}>{plainText(item.text)}</Text>
                <Text style={styles.time}>{relTime(item.created_at)}</Text>
              </View>
              {!!item.link && <Ionicons name="chevron-forward" size={18} color={colors.muted} />}
            </Pressable>
          )}
          ListEmptyComponent={
            // Как на сайте: значок и текст вверху экрана, без отдельного заголовка
            <View style={styles.empty}>
              <View style={styles.circle}><Icon name="bell" size={28} color={colors.primary} /></View>
              <Text style={styles.emptyText}>{tr('Уведомлений пока нет — здесь появятся решения по объявлениям, ответы в чатах и новое по вашим подпискам.')}</Text>
            </View>
          }
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 8, paddingRight: 16, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  h1: { flex: 1, fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  all: { fontSize: 14.5, fontFamily: font[700], color: colors.primaryDeep },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14 },
  dot: { width: 9, height: 9, borderRadius: 5, backgroundColor: colors.accent },
  text: { fontFamily: font[400], fontSize: 15.5, lineHeight: 21, color: colors.inkSoft },
  textOn: { color: colors.ink, fontFamily: font[700] },
  time: { fontFamily: font[400], fontSize: 12.5, color: colors.muted },
  sep: { height: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginLeft: 37 },
  empty: { alignItems: 'center', gap: 14, paddingTop: 44, paddingHorizontal: 32 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink },
  emptyText: { fontSize: 14, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center' },
})
