import { success } from '../../src/haptics'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { supportCreate, supportMine, type Ticket } from '../../src/api'
import { useAuth } from '../../src/auth'
import Icon from '../../src/components/Icon'
import { shortTime } from '../../src/format'
import { tr } from '../../src/i18n'
import { colors, font } from '../../src/theme'

const TOPICS: [string, string][] = [['listing', 'Объявление'], ['account', 'Аккаунт'], ['payment', 'Оплата'], ['abuse', 'Жалоба на пользователя'], ['other', 'Другое']]
const STATUS: Record<string, string> = { open: 'Открыто', answered: 'Есть ответ', closed: 'Закрыто', pending: 'Ждём вас' }

/** Поддержка: мои обращения (статус, когда обновлено) и новое обращение — тема, суть, подробности. */
export default function Support() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [items, setItems] = useState<Ticket[] | null>(null)
  const [writing, setWriting] = useState(false)
  const [topic, setTopic] = useState('other')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!token) return
    try { setItems((await supportMine(token)).items) } catch { setItems((v) => v ?? []) }
  }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const send = async () => {
    if (!token) return
    setError('')
    if (subject.trim().length < 3 || body.trim().length < 10) { setError(tr('Опишите вопрос: тема — от 3 букв, подробности — от 10.')); return }
    setBusy(true)
    try {
      const t = await supportCreate(token, { topic, subject: subject.trim(), body: body.trim() })
      success()
      setWriting(false); setSubject(''); setBody('')
      router.push(`/support/${t.id}`)
    } catch { setError(tr('Не удалось отправить. Проверьте интернет и попробуйте ещё раз.')) } finally { setBusy(false) }
  }

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (writing ? setWriting(false) : router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr(writing ? 'Новое обращение' : 'Поддержка')}</Text>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          {writing ? (
            <>
              <Text style={styles.label}>{tr('Тема')}</Text>
              <View style={styles.chips}>
                {TOPICS.map(([k, label]) => (
                  <Pressable key={k} onPress={() => setTopic(k)} style={[styles.chip, topic === k && styles.chipOn]}><Text style={[styles.chipText, topic === k && styles.chipTextOn]}>{tr(label)}</Text></Pressable>
                ))}
              </View>
              <Text style={styles.label}>{tr('Коротко о вопросе')}</Text>
              <TextInput value={subject} onChangeText={setSubject} style={styles.input} maxLength={200} placeholder={tr('Например, не публикуется объявление')} placeholderTextColor={colors.muted} />
              <Text style={styles.label}>{tr('Подробности')}</Text>
              <TextInput value={body} onChangeText={setBody} style={[styles.input, styles.area]} multiline textAlignVertical="top" maxLength={4000} placeholder={tr('Что случилось и что вы уже пробовали')} placeholderTextColor={colors.muted} />
              {!!error && <Text style={styles.error}>{error}</Text>}
              <Pressable style={[styles.cta, busy && { opacity: 0.6 }]} disabled={busy} onPress={send}>{busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Отправить')}</Text>}</Pressable>
              <Text style={styles.note}>{tr('Ответ придёт сюда и в уведомления — обычно в течение дня.')}</Text>
            </>
          ) : (
            <>
              <Pressable style={styles.cta} onPress={() => setWriting(true)}><Text style={styles.ctaText}>{tr('Новое обращение')}</Text></Pressable>
              {items === null ? <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} /> : items.length === 0 ? (
                <Text style={styles.empty}>{tr('Обращений пока нет. Напишите — команда PLONK ответит.')}</Text>
              ) : (
                <View style={styles.list}>
                  {items.map((t, i) => (
                    <Pressable key={t.id} style={[styles.row, i === items.length - 1 && { borderBottomWidth: 0 }]} onPress={() => router.push(`/support/${t.id}`)}>
                      <View style={{ flex: 1, gap: 3 }}>
                        <Text style={styles.rowTitle} numberOfLines={1}>{t.subject}</Text>
                        <Text style={[styles.rowStatus, t.status === 'answered' && { color: colors.primaryDeep }]}>{tr(STATUS[t.status] ?? t.status)}  ·  {shortTime(t.updated_at)}</Text>
                      </View>
                      <Icon name="forward" size={16} color={colors.muted} />
                    </Pressable>
                  ))}
                </View>
              )}
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  body: { paddingHorizontal: 16, paddingBottom: 40, paddingTop: 6 },
  label: { fontSize: 15, fontFamily: font[800], color: colors.ink, marginTop: 16, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { height: 36, paddingHorizontal: 13, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  chipOn: { backgroundColor: colors.primary },
  chipText: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  chipTextOn: { color: '#fff' },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontSize: 16, fontFamily: font[500], color: colors.ink },
  area: { minHeight: 130, paddingTop: 13, paddingBottom: 13 },
  error: { fontSize: 13.5, fontFamily: font[600], color: '#B42318', marginTop: 12 },
  cta: { marginTop: 18, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  note: { fontSize: 13, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 10 },
  empty: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 24 },
  list: { marginTop: 18, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 13, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  rowTitle: { fontSize: 15.5, fontFamily: font[700], color: colors.ink },
  rowStatus: { fontSize: 12.5, fontFamily: font[600], color: colors.muted },
})
