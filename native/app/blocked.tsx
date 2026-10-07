import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type BlockedUser, blockedUsers, unblockUser } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { tr } from '../src/i18n'
import { colors, font } from '../src/theme'

/** Заблокированные: кто не может вам писать; «Разблокировать». */
export default function Blocked() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [items, setItems] = useState<BlockedUser[] | null>(null)
  const load = useCallback(async () => { if (token) setItems((await blockedUsers(token).catch(() => ({ items: [] }))).items) }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Заблокированные')}</Text>
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
          {items.length === 0 && <View style={styles.emptyBox}><View style={styles.emptyIcon}><Icon name="ban" size={28} color={colors.primary} /></View><Text style={styles.emptyMsg}>{tr('Никого не заблокировали')}</Text></View>}
          {items.map((u) => (
            <View key={u.id} style={styles.row}>
              <View style={styles.avatar}><Text style={styles.letter}>{(u.display_name || '?').slice(0, 1).toUpperCase()}</Text></View>
              <Text style={styles.name} numberOfLines={1}>{u.display_name || tr('Собеседник')}</Text>
              <Pressable style={styles.btn} onPress={async () => { if (token) { await unblockUser(token, u.id).catch(() => {}); load() } }}>
                <Text style={styles.btnText}>{tr('Разблокировать')}</Text>
              </Pressable>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  emptyBox: { alignItems: 'center', gap: 14, paddingTop: 44, paddingHorizontal: 32 },
  emptyIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  emptyMsg: { fontSize: 13.5, lineHeight: 19, fontFamily: font[500], color: colors.muted, textAlign: 'center' },
  emptyBtn: { height: 42, paddingHorizontal: 20, borderRadius: 13, backgroundColor: colors.inverse, justifyContent: 'center' },
  emptyBtnText: { color: colors.onInverse, fontSize: 14.5, fontFamily: font[800] },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  empty: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 24 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  avatar: { width: 42, height: 42, borderRadius: 21, backgroundColor: '#B8BDB8', alignItems: 'center', justifyContent: 'center' },
  letter: { color: '#fff', fontSize: 17, fontFamily: font[800] },
  name: { flex: 1, fontSize: 15.5, fontFamily: font[700], color: colors.ink },
  btn: { height: 34, paddingHorizontal: 12, borderRadius: 10, backgroundColor: colors.sunken, justifyContent: 'center' },
  btnText: { fontSize: 13.5, fontFamily: font[800], color: colors.ink },
})
