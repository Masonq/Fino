import { useCallback, useEffect, useState } from 'react'
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { supportAnswer, supportClose, supportQueue, supportTicket, type Ticket } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Icon from '../../src/components/Icon'
import Segmented from '../../src/components/Segmented'
import Skeleton from '../../src/components/Skeleton'
import { colors, font } from '../../src/theme'

const QUICK: [string, string][] = [
  ['Посмотрим', 'Здравствуйте! Спасибо, что написали — посмотрим и ответим сегодня.'],
  ['Исправили', 'Проверили и исправили — попробуйте, пожалуйста, ещё раз.'],
  ['Нужен скриншот', 'Пришлите, пожалуйста, снимок экрана — так быстрее разберёмся.'],
  ['Спасибо', 'Спасибо! Если что-то ещё — пишите сюда.'],
]

/** Обращения — как на сайте: карточка-переписка, быстрые ответы, «Отправить» и «Закрыть». */
export default function Support() {
  const { token } = useAuth()
  const [tab, setTab] = useState<'open' | 'answered' | 'closed'>('open')
  const [items, setItems] = useState<Ticket[] | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)
  const [card, setCard] = useState<Ticket | null>(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(() => { if (token) { setItems(null); supportQueue(token, tab).then(setItems).catch(() => setItems([])) } }, [token, tab])
  useEffect(() => { load() }, [load])
  const open = (id: string) => {
    if (openId === id) { setOpenId(null); return }
    setOpenId(id); setCard(null); setDraft('')
    if (token) supportTicket(token, id).then(setCard).catch(() => {})
  }
  const send = async () => {
    if (!token || !openId || !draft.trim()) return
    setBusy(true)
    await supportAnswer(token, openId, draft.trim()).catch(() => {})
    setBusy(false); setDraft(''); setOpenId(null); load()
  }
  const close = async () => { if (!token || !openId) return; setBusy(true); await supportClose(token, openId).catch(() => {}); setBusy(false); setOpenId(null); load() }
  return (
    <KeyboardAvoidingView style={styles.page} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={{ paddingHorizontal: 16, paddingBottom: 10 }}>
        <Segmented stretch options={[{ key: 'open', label: tr('Ждёт ответа') }, { key: 'answered', label: tr('Отвечено') }, { key: 'closed', label: tr('Закрыто') }]} value={tab} onChange={setTab} />
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, paddingTop: 4, gap: 10, paddingBottom: 60 }} keyboardShouldPersistTaps="handled">
        <Header bleed={16} bleedTop={4} title={tr('Обращения')} fallback="/admin" />
        {!items && <Skeleton style={{ height: 76, borderRadius: 22 }} />}
        {items?.length === 0 && <View style={styles.calm}><Text style={styles.calmT}>{tr('Очередь пуста — новые появятся здесь')}</Text></View>}
        {items?.map((tk) => (
          <View key={tk.id} style={styles.card}>
            <Pressable style={styles.head} onPress={() => open(tk.id)}>
              <View style={styles.ava}><Text style={styles.avaT}>{(tk.contact || '?').replace(/^[@+]/, '').slice(0, 1).toUpperCase()}</Text></View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={styles.subject} numberOfLines={1}>{tk.subject}</Text>
                <Text style={styles.contact} numberOfLines={1}>{tk.contact}</Text>
              </View>
              <Icon name="down" size={14} color={colors.muted} />
            </Pressable>
            {openId === tk.id && (
              <View style={styles.body}>
                {!card ? <Skeleton style={{ height: 50, borderRadius: 16 }} /> : card.messages?.map((m) => (
                  <View key={m.id} style={[styles.msg, m.from_staff && styles.msgMe]}>
                    <Text style={[styles.msgT, m.from_staff && { color: '#FFFFFF' }]}>{m.body}</Text>
                    {!!m.author && <Text style={[styles.msgA, m.from_staff && { color: 'rgba(255,255,255,0.75)' }]}>{m.author}</Text>}
                  </View>
                ))}
                {tab !== 'closed' && (
                  <>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
                      {QUICK.map(([s, full]) => <Pressable key={s} style={styles.quick} onPress={() => setDraft((d) => (d ? `${d} ` : '') + tr(full))}><Text style={styles.quickT}>{tr(s)}</Text></Pressable>)}
                    </ScrollView>
                    <TextInput style={styles.input} value={draft} onChangeText={setDraft} placeholder={tr('Ответ человеку')} placeholderTextColor={colors.muted} multiline />
                    <View style={{ flexDirection: 'row', gap: 8 }}>
                      <Pressable style={[styles.btn, styles.send, (!draft.trim() || busy) && { opacity: 0.5 }]} disabled={!draft.trim() || busy} onPress={send}><Text style={styles.sendT}>{tr('Отправить')}</Text></Pressable>
                      <Pressable style={[styles.btn, styles.close]} disabled={busy} onPress={close}><Text style={styles.closeT}>{tr('Закрыть')}</Text></Pressable>
                    </View>
                  </>
                )}
              </View>
            )}
          </View>
        ))}
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  card: { borderRadius: 22, backgroundColor: colors.surface, overflow: 'hidden' },
  head: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14 },
  ava: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center' },
  avaT: { fontFamily: font[800], fontSize: 18, color: '#FFFFFF' },
  subject: { fontFamily: font[800], fontSize: 16, color: colors.ink },
  contact: { fontFamily: font[600], fontSize: 13, color: colors.muted, marginTop: 2 },
  body: { padding: 14, paddingTop: 4, gap: 8, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  msg: { alignSelf: 'flex-start', maxWidth: '86%', padding: 11, borderRadius: 18, borderBottomLeftRadius: 6, backgroundColor: colors.sunken },
  msgMe: { alignSelf: 'flex-end', backgroundColor: colors.primary, borderBottomLeftRadius: 18, borderBottomRightRadius: 6 },
  msgT: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.ink },
  msgA: { fontFamily: font[600], fontSize: 11.5, color: colors.muted, marginTop: 4 },
  quick: { height: 34, paddingHorizontal: 12, borderRadius: 17, borderWidth: 1, borderColor: colors.border, justifyContent: 'center', backgroundColor: colors.bg },
  quickT: { fontFamily: font[700], fontSize: 13, color: colors.ink },
  input: { minHeight: 70, borderRadius: 16, backgroundColor: colors.sunken, padding: 12, fontFamily: font[400], fontSize: 16, color: colors.ink, textAlignVertical: 'top' },
  btn: { flex: 1, height: 48, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  send: { backgroundColor: colors.inverse },
  sendT: { fontFamily: font[800], fontSize: 15, color: colors.onInverse },
  close: { backgroundColor: colors.sunken },
  closeT: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  calm: { padding: 20, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center' },
  calmT: { fontFamily: font[700], fontSize: 15, color: colors.inkSoft },
})
