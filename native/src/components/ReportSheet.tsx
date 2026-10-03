import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'

import { ApiError, type ReportReason, sendReport } from '../api'
import { colors } from '../theme'
import Sheet from './Sheet'

const REASONS: { key: ReportReason; label: string }[] = [
  { key: 'fraud', label: 'Похоже на мошенничество' },
  { key: 'prohibited_item', label: 'Запрещённый товар' },
  { key: 'spam', label: 'Спам или реклама' },
  { key: 'duplicate', label: 'Повтор объявления' },
  { key: 'wrong_category', label: 'Не тот раздел' },
  { key: 'other', label: 'Другое' },
]

/** Жалоба на объявление: причина, по желанию — комментарий; после отправки — «Спасибо, проверим». */
export default function ReportSheet({ visible, listingId, token, onClose }: { visible: boolean; listingId: string; token: string | null; onClose: () => void }) {
  const [reason, setReason] = useState<ReportReason | null>(null)
  const [comment, setComment] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'done' | 'error'>('idle')
  const [already, setAlready] = useState(false)
  const [errorText, setErrorText] = useState('')
  useEffect(() => { if (visible) { setReason(null); setComment(''); setState('idle'); setAlready(false); setErrorText('') } }, [visible])

  const send = async () => {
    if (!reason || !token) return
    setState('sending')
    try {
      await sendReport(token, listingId, reason, comment.trim())
      setState('done')
    } catch (e) {
      const code = e instanceof ApiError ? e.message : ''
      // Сервер отвечает кодами: уже жаловались — это не ошибка; на своё нельзя; слишком часто
      if (code === 'already_reported') { setAlready(true); setState('done'); return }
      setErrorText(code === 'self_report' ? 'Это ваше объявление — на него нельзя пожаловаться.'
        : code === 'too_many_reports' || (e instanceof ApiError && e.status === 429) ? 'Слишком много жалоб подряд. Попробуйте позже.'
          : 'Не удалось отправить. Попробуйте ещё раз.')
      setState('error')
    }
  }

  return (
    <Sheet visible={visible} title={state === 'done' ? undefined : 'Пожаловаться'} onClose={onClose}>
      {state === 'done' ? (
        <View style={styles.done}>
          <Text style={styles.doneTitle}>{already ? 'Вы уже пожаловались' : 'Спасибо, проверим'}</Text>
          <Text style={styles.doneText}>{already ? 'Мы уже проверяем это объявление — второй раз отправлять не нужно.' : 'Модераторы посмотрят объявление. Если оно нарушает правила, его снимут.'}</Text>
          <Pressable style={styles.btn} onPress={onClose}><Text style={styles.btnText}>Понятно</Text></Pressable>
        </View>
      ) : (
        <View style={{ paddingHorizontal: 20, gap: 4 }}>
          {REASONS.map((r) => {
            const on = reason === r.key
            return (
              <Pressable key={r.key} style={styles.row} onPress={() => setReason(r.key)} accessibilityRole="radio" accessibilityState={{ selected: on }}>
                <View style={[styles.radio, on && styles.radioOn]}>{on && <View style={styles.dot} />}</View>
                <Text style={styles.rowText}>{r.label}</Text>
              </Pressable>
            )
          })}
          <TextInput value={comment} onChangeText={setComment} placeholder="Комментарий (необязательно)" placeholderTextColor={colors.muted}
            style={styles.input} multiline maxLength={1000} textAlignVertical="top" />
          {state === 'error' && <Text style={styles.error}>{errorText}</Text>}
          <Pressable style={[styles.btn, !reason && { opacity: 0.45 }]} disabled={!reason || state === 'sending'} onPress={send}>
            {state === 'sending' ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Отправить</Text>}
          </Pressable>
        </View>
      )}
    </Sheet>
  )
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 46 },
  radio: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: '#C9CEC9', alignItems: 'center', justifyContent: 'center' },
  radioOn: { borderColor: colors.primary },
  dot: { width: 11, height: 11, borderRadius: 6, backgroundColor: colors.primary },
  rowText: { fontSize: 16, color: colors.ink, flex: 1 },
  input: { minHeight: 80, borderRadius: 13, backgroundColor: colors.sunken, padding: 12, fontSize: 15.5, color: colors.ink, marginTop: 8 },
  error: { color: '#B42318', fontSize: 14, marginTop: 6 },
  btn: { height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', marginTop: 12 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  done: { paddingHorizontal: 24, paddingVertical: 10, gap: 8, alignItems: 'center' },
  doneTitle: { fontSize: 20, fontWeight: '800', color: colors.ink },
  doneText: { fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
})
