import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { ApiError, supportCreate, supportMine, supportReply, type Ticket } from '../../src/api'
import { useAuth } from '../../src/auth'
import Icon from '../../src/components/Icon'
import { success } from '../../src/haptics'
import { tr } from '../../src/i18n'
import { colors, font } from '../../src/theme'

const TOPICS: [string, string][] = [['listing', 'Объявление'], ['account', 'Вход и профиль'], ['payment', 'Оплата'], ['abuse', 'Обман'], ['other', 'Другое']]
const STATUS: Record<string, string> = { open: 'Ждёт ответа', answered: 'Отвечено', closed: 'Закрыто' }

/**
 * «Написать в поддержку» — как /support сайта, одной страницей: сверху форма (тема чипами, «Коротко о сути»
 * и «Что случилось» в одной карточке, «Отправить»), ниже «Мои обращения» — тема, статус, переписка
 * и «Ваш ответ» прямо в карточке.
 */
export default function Support() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [items, setItems] = useState<Ticket[] | null>(null)
  const [topic, setTopic] = useState('other')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [replies, setReplies] = useState<Record<string, string>>({})

  const load = useCallback(async () => { if (token) { try { setItems((await supportMine(token)).items) } catch { setItems((v) => v ?? []) } } }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const send = async () => {
    if (!token) return
    setNote('')
    if (subject.trim().length < 3 || body.trim().length < 10) { setNote(tr('Опишите вопрос: тема — от 3 букв, подробности — от 10.')); return }
    setBusy(true)
    try {
      await supportCreate(token, { topic, subject: subject.trim(), body: body.trim() })
      success(); setSubject(''); setBody(''); setNote(tr('Отправлено. Ответим здесь и в уведомлениях.')); await load()
    } catch (e) {
      setNote(tr(e instanceof ApiError && e.status === 429 ? 'Слишком много обращений подряд. Подождите немного.' : 'Не получилось отправить. Попробуйте ещё раз.'))
    } finally { setBusy(false) }
  }
  const reply = async (id: string) => {
    const text = (replies[id] ?? '').trim()
    if (!token || !text) return
    try { await supportReply(token, id, text); setReplies((r) => ({ ...r, [id]: '' })); await load() } catch { /* сеть */ }
  }

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Написать в поддержку')}</Text>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 24 }]} keyboardShouldPersistTaps="handled">
          {/* как на сайте: «Мы на связи» карточкой со значком и быстрые ответы плитками — многое решается без обращения */}
          <View style={styles.supHero}>
            <View style={styles.supIcon}><Icon name="chat" size={24} color={colors.onInverse} /></View>
            <View style={{ flex: 1 }}><Text style={styles.supT}>{tr('Мы на связи')}</Text><Text style={styles.supS}>{tr('Отвечают живые люди из команды — обычно в течение дня.')}</Text></View>
          </View>
          <View style={{ flexDirection: 'row', gap: 10, marginBottom: 10 }}>
            <Pressable style={[styles.supQ, { backgroundColor: '#E3ECFA' }]} onPress={() => router.push('/legal/rules' as never)}><Text style={styles.supQT}>{tr('Правила')}</Text><Text style={styles.supQS}>{tr('Что можно продавать')}</Text></Pressable>
            <Pressable style={[styles.supQ, { backgroundColor: '#E2F1E6' }]} onPress={() => router.push('/vodic' as never)}><Text style={styles.supQT}>{tr('Полезное')}</Text><Text style={styles.supQS}>{tr('Как продать быстрее')}</Text></Pressable>
          </View>
          <View style={styles.card}>
            <View style={styles.section}>
              <Text style={styles.label}>{tr('О чём вопрос')}</Text>
              <View style={styles.chips}>
                {TOPICS.map(([k, l]) => (
                  <Pressable key={k} onPress={() => setTopic(k)} style={[styles.chip, topic === k && styles.chipOn]}><Text style={[styles.chipText, topic === k && styles.chipTextOn]}>{tr(l)}</Text></Pressable>
                ))}
              </View>
            </View>
            <View style={[styles.section, styles.sep]}>
              <Text style={styles.label}>{tr('Коротко о сути')}</Text>
              <TextInput value={subject} onChangeText={setSubject} placeholder={tr('Коротко о чём')} placeholderTextColor={colors.muted} style={styles.input} maxLength={200} />
            </View>
            <View style={[styles.section, styles.sep]}>
              <Text style={styles.label}>{tr('Что случилось')}</Text>
              <TextInput value={body} onChangeText={setBody} placeholder={tr('Что случилось? Опишите подробно.')} placeholderTextColor={colors.muted} style={[styles.input, styles.area]} multiline textAlignVertical="top" maxLength={4000} />
            </View>
          </View>
          {!!note && <Text style={styles.note}>{note}</Text>}
          <Pressable style={[styles.cta, busy && { opacity: 0.6 }]} disabled={busy} onPress={send}>{busy ? <ActivityIndicator color={colors.onInverse} /> : <Text style={styles.ctaText}>{tr('Отправить')}</Text>}</Pressable>

          {items === null ? <ActivityIndicator style={{ marginTop: 20 }} color={colors.primary} /> : items.length > 0 && (
            <>
              <Text style={styles.h2}>{tr('Мои обращения')}</Text>
              {items.map((t) => (
                <View key={t.id} style={styles.ticket}>
                  <View style={styles.ticketHead}>
                    <Text style={styles.ticketTitle} numberOfLines={2}>{t.subject}</Text>
                    <Text style={[styles.badge, t.status === 'answered' && styles.badgeOn]}>{tr(STATUS[t.status] ?? t.status)}</Text>
                  </View>
                  {(t.messages ?? []).map((m) => (
                    <View key={m.id} style={[styles.msg, m.from_staff && styles.msgStaff]}>
                      {m.from_staff && <Text style={styles.staff}>{tr('Команда PLONK')}</Text>}
                      <Text style={styles.msgText}>{m.body}</Text>
                    </View>
                  ))}
                  {t.status !== 'closed' && (
                    <View style={styles.replyRow}>
                      <TextInput value={replies[t.id] ?? ''} onChangeText={(v) => setReplies((r) => ({ ...r, [t.id]: v }))} placeholder={tr('Ваш ответ')} placeholderTextColor={colors.muted} style={styles.replyInput} />
                      <Pressable style={styles.replyBtn} onPress={() => reply(t.id)}><Text style={styles.replyBtnText}>{tr('Отправить')}</Text></Pressable>
                    </View>
                  )}
                </View>
              ))}
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  supHero: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 16, borderRadius: 24, backgroundColor: '#E9F5EC', marginBottom: 10 },
  supIcon: { width: 52, height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  supT: { fontFamily: font[800], fontSize: 18, color: colors.ink, letterSpacing: -0.4 },
  supS: { fontFamily: font[400], fontSize: 13.5, color: colors.inkSoft, marginTop: 2, lineHeight: 18 },
  supQ: { flex: 1, padding: 14, borderRadius: 20, gap: 2 },
  supQT: { fontFamily: font[800], fontSize: 15, color: '#0F1512' },
  supQS: { fontFamily: font[400], fontSize: 12.5, color: '#434B46' },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, minHeight: 56 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { fontSize: 27, fontFamily: font[800], letterSpacing: -0.8, color: colors.ink, marginLeft: 8 },
  body: { paddingHorizontal: 12 },
  card: { gap: 10 },   // поля отдельными карточками (как сайт): без общей рамки и линий-разделителей
  section: { padding: 14, gap: 8, borderRadius: 20, backgroundColor: colors.surface },
  sep: {},
  label: { fontSize: 12.5, fontFamily: font[700], color: colors.inkSoft },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { height: 34, paddingHorizontal: 13, borderRadius: 17, borderWidth: 0, backgroundColor: colors.surface, justifyContent: 'center' },
  chipOn: { backgroundColor: colors.inverse, borderColor: colors.inverse },
  chipText: { fontSize: 13, fontFamily: font[700], color: colors.ink },
  chipTextOn: { color: colors.onInverse },
  input: { fontSize: 15, fontFamily: font[500], color: colors.ink, paddingVertical: 2 },
  area: { minHeight: 110 },
  note: { fontSize: 13.5, fontFamily: font[600], color: colors.inkSoft, marginTop: 10 },
  cta: { marginTop: 12, height: 50, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 15.5, fontFamily: font[800] },
  h2: { fontSize: 16, fontFamily: font[800], color: colors.ink, marginTop: 22, marginBottom: 10 },
  ticket: { padding: 12, marginBottom: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 0, gap: 8 },
  ticketHead: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  ticketTitle: { flex: 1, fontSize: 14.5, fontFamily: font[800], color: colors.ink },
  badge: { fontSize: 11.5, fontFamily: font[700], color: colors.muted, backgroundColor: colors.sunken, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 7, overflow: 'hidden' },
  badgeOn: { color: colors.primaryDeep, backgroundColor: colors.primarySoft },
  msg: { alignSelf: 'flex-start', maxWidth: '88%', paddingHorizontal: 11, paddingVertical: 8, borderRadius: 12, backgroundColor: colors.sunken },
  msgStaff: { backgroundColor: colors.primarySoft },
  staff: { fontSize: 11.5, fontFamily: font[800], color: colors.primaryDeep, marginBottom: 2 },
  msgText: { fontSize: 14, lineHeight: 19, fontFamily: font[400], color: colors.ink },
  replyRow: { flexDirection: 'row', gap: 8, marginTop: 2 },
  replyInput: { flex: 1, height: 42, borderRadius: 11, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, fontSize: 14.5, fontFamily: font[500], color: colors.ink },
  replyBtn: { height: 42, paddingHorizontal: 14, borderRadius: 11, borderWidth: 0, justifyContent: 'center' },
  replyBtnText: { fontSize: 14, fontFamily: font[700], color: colors.ink },
})
