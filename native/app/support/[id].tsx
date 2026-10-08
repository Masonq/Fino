import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { supportReply, supportTicket, type Ticket } from '../../src/api'
import { useAuth } from '../../src/auth'
import Icon from '../../src/components/Icon'
import { shortTime } from '../../src/format'
import { tr } from '../../src/i18n'
import { colors, font } from '../../src/theme'

/** Переписка по обращению: мои сообщения справа, ответы команды PLONK слева с подписью; ответить. */
export default function TicketScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [t, setT] = useState<Ticket | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => { if (token) setT(await supportTicket(token, String(id)).catch(() => null)) }, [token, id])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const send = async () => {
    if (!token || !text.trim()) return
    setBusy(true)
    try { await supportReply(token, String(id), text.trim()); setText(''); await load() } finally { setBusy(false) }
  }

  const msgs = [...(t?.messages ?? [])].reverse()
  return (
    <KeyboardAvoidingView style={[styles.page, { paddingTop: insets.top }]} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/support'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title} numberOfLines={1}>{t?.subject ?? tr('Обращение')}</Text>
      </View>
      {!t ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <FlatList data={msgs} inverted keyExtractor={(m) => m.id} contentContainerStyle={{ padding: 12, gap: 8 }}
          renderItem={({ item }) => (
            <View style={[styles.bubbleRow, !item.from_staff && styles.bubbleRowMe]}>
              <View style={[styles.bubble, item.from_staff ? styles.staff : styles.me]}>
                {item.from_staff && <Text style={styles.staffName}>{tr('Команда PLONK')}</Text>}
                <Text style={[styles.text, !item.from_staff && { color: '#fff' }]}>{item.body}</Text>
                <Text style={[styles.time, !item.from_staff && { color: 'rgba(255,255,255,0.8)' }]}>{shortTime(item.created_at)}</Text>
              </View>
            </View>
          )} />
      )}
      {t && t.status !== 'closed' && (
        <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 10) }]}>
          <TextInput value={text} onChangeText={setText} placeholder={tr('Сообщение')} placeholderTextColor={colors.muted} multiline style={styles.input} maxLength={4000} />
          <Pressable style={[styles.sendBtn, (!text.trim() || busy) && { opacity: 0.4 }]} disabled={!text.trim() || busy} onPress={send} accessibilityLabel={tr('Отправить')}>
            <Icon name="forward" size={20} color={colors.onInverse} strokeWidth={2.6} />
          </Pressable>
        </View>
      )}
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface }   // «назад» кружком — как на сайте и на остальных экранах,
  title: { flex: 1, fontSize: 18, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  bubbleRow: { flexDirection: 'row' },
  bubbleRowMe: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '82%', paddingHorizontal: 12, paddingTop: 8, paddingBottom: 6, borderRadius: 18 },
  staff: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderBottomLeftRadius: 6 },
  me: { backgroundColor: colors.primary, borderBottomRightRadius: 6 },
  staffName: { fontSize: 12, fontFamily: font[800], color: colors.primaryDeep, marginBottom: 2 },
  text: { fontSize: 15.5, lineHeight: 21, fontFamily: font[400], color: colors.ink },
  time: { fontSize: 11, fontFamily: font[500], color: colors.muted, alignSelf: 'flex-end', marginTop: 3 },
  bar: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, paddingHorizontal: 10, paddingTop: 8, backgroundColor: colors.surface, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  input: { flex: 1, minHeight: 42, maxHeight: 120, borderRadius: 21, backgroundColor: colors.sunken, paddingHorizontal: 16, paddingTop: 11, paddingBottom: 11, fontSize: 16, fontFamily: font[400], color: colors.ink },
  sendBtn: { width: 42, height: 42, borderRadius: 21, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
})
