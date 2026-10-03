import { tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import type { Chat } from '../../src/api'
import { useAuth } from '../../src/auth'
import { useChats } from '../../src/chats'
import Skeleton from '../../src/components/Skeleton'
import { mediaUrl } from '../../src/config'
import { plainText, relTime } from '../../src/format'
import { colors, font } from '../../src/theme'

/** Сообщения: список переписок — фото объявления, собеседник, последнее сообщение, время, непрочитанные. */
export default function Chats() {
  const { token, ready } = useAuth()
  const { chats, refresh, failed } = useChats()
  const [refreshing, setRefreshing] = useState(false)

  useFocusEffect(useCallback(() => { refresh() }, [refresh]))

  if (!ready) return <SafeAreaView style={styles.page} />
  if (!token) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <View style={styles.circle}><Ionicons name="chatbubble-outline" size={28} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>{tr('Переписка с продавцами')}</Text>
        <Text style={styles.text}>{tr('Войдите, чтобы писать продавцам и отвечать покупателям.')}</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>{tr('Войти')}</Text></Pressable>
      </SafeAreaView>
    )
  }

  const row = ({ item }: { item: Chat }) => {
    const photo = mediaUrl(item.listing_photo)
    const name = item.is_team ? tr('Команда PLONK') : (item.other_name || tr('Собеседник'))
    const preview = item.last_kind === 'offer' ? tr('Предложение цены') : plainText(item.last_text).replace(/\n+/g, ' ')
    const unread = item.unread || 0
    return (
      <Pressable style={styles.row} onPress={() => router.push(`/chat/${item.id}`)} accessibilityRole="button">
        <View style={styles.thumb}>
          {item.is_team
            ? <Image source={require('../../assets/icon.png')} style={styles.thumbImg} contentFit="cover" />
            : photo ? <Image source={{ uri: photo }} style={styles.thumbImg} contentFit="cover" transition={150} />
              : <Ionicons name="image-outline" size={22} color={colors.muted} />}
        </View>
        <View style={styles.rowBody}>
          <View style={styles.rowTop}>
            <Text style={styles.name} numberOfLines={1}>{name}</Text>
            <Text style={[styles.time, unread > 0 && styles.timeOn]}>{relTime(item.last_at)}</Text>
          </View>
          {!!item.listing_title && <Text style={styles.listing} numberOfLines={1}>{item.listing_title}</Text>}
          <View style={styles.rowTop}>
            <Text style={[styles.preview, unread > 0 && styles.previewOn]} numberOfLines={1}>
              {item.last_from_me ? tr('Вы: ') : ''}{preview}
            </Text>
            {unread > 0 && <View style={styles.badge}><Text style={styles.badgeText}>{unread > 99 ? '99+' : unread}</Text></View>}
          </View>
        </View>
      </Pressable>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <Text style={styles.h1}>{tr('Сообщения')}</Text>
      {chats === null ? (
        failed ? (
          <View style={styles.center}>
            <Text style={styles.title}>{tr('Не удалось загрузить')}</Text>
            <Pressable style={styles.cta} onPress={refresh}><Text style={styles.ctaText}>{tr('Повторить')}</Text></Pressable>
          </View>
        ) : (
          <View style={{ paddingHorizontal: 16, gap: 18, paddingTop: 6 }}>
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
        <FlatList
          data={chats}
          keyExtractor={(c) => c.id}
          renderItem={row}
          ItemSeparatorComponent={() => <View style={styles.sep} />}
          contentContainerStyle={chats.length === 0 ? { flexGrow: 1 } : { paddingBottom: 16 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await refresh(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
          ListEmptyComponent={
            <View style={styles.center}>
              <View style={styles.circle}><Ionicons name="chatbubble-outline" size={28} color={colors.primaryDeep} /></View>
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
  page: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  h1: { fontSize: 26, fontFamily: font[800], color: colors.ink, paddingHorizontal: 16, paddingTop: 8, paddingBottom: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 36, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  row: { flexDirection: 'row', gap: 12, paddingHorizontal: 16, paddingVertical: 12, alignItems: 'center' },
  thumb: { width: 56, height: 56, borderRadius: 14, backgroundColor: colors.photo, overflow: 'hidden', alignItems: 'center', justifyContent: 'center' },
  thumbImg: { width: 56, height: 56 },
  rowBody: { flex: 1, gap: 2 },
  rowTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  name: { flex: 1, fontSize: 16, fontFamily: font[800], color: colors.ink },
  time: { fontFamily: font[400], fontSize: 12.5, color: colors.muted },
  timeOn: { color: colors.accent, fontFamily: font[700] },
  listing: { fontFamily: font[400], fontSize: 13.5, color: colors.inkSoft },
  preview: { flex: 1, fontFamily: font[400], fontSize: 14.5, color: colors.muted },
  previewOn: { color: colors.ink, fontFamily: font[600] },
  badge: { minWidth: 22, height: 22, borderRadius: 11, paddingHorizontal: 6, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  badgeText: { color: '#fff', fontSize: 12, fontFamily: font[800] },
  sep: { height: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginLeft: 84 },
})
