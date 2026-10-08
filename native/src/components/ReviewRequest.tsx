/**
 * «Как прошла сделка с …?» в переписке — как ReviewRequest на сайте: первый шаг одним нажатием (👍 / 👎),
 * потом звёзды и необязательный комментарий; «Не сейчас» прячет приглашение.
 */
import { useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { authed, createReview } from '../api'
import { tr } from '../i18n'
import { colors, font } from '../theme'

export default function ReviewRequest({ token, chatId, targetId, listingId, name }: { token: string; chatId: string; targetId?: string | null; listingId?: string | null; name?: string | null }) {
  const [rating, setRating] = useState(0)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [state, setState] = useState<'ask' | 'done' | 'hidden'>('ask')
  if (state === 'hidden' || !targetId) return null
  if (state === 'done') return <View style={st.card}><Text style={st.title}>{tr('Спасибо за отзыв')}</Text></View>
  const send = () => {
    setBusy(true)
    createReview(token, { target_id: targetId, listing_id: listingId || null, rating, comment: text.trim() || undefined })
      .then(() => setState('done')).catch(() => {}).finally(() => setBusy(false))
  }
  return (
    <View style={st.card}>
      <Text style={st.title}>{tr('Как прошла сделка с {name}?', { name: name || '' })}</Text>
      {rating === 0 ? (
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <Pressable style={st.quick} onPress={() => setRating(5)}><Text style={st.quickT}>👍 {tr('Хорошо')}</Text></Pressable>
          <Pressable style={st.quick} onPress={() => setRating(2)}><Text style={st.quickT}>👎 {tr('Были проблемы')}</Text></Pressable>
        </View>
      ) : (
        <>
          <View style={{ flexDirection: 'row', gap: 6 }}>
            {[1, 2, 3, 4, 5].map((n) => <Pressable key={n} onPress={() => setRating(n)} hitSlop={4}><Text style={[st.star, n <= rating && { color: '#F5B301' }]}>★</Text></Pressable>)}
          </View>
          <TextInput style={st.input} value={text} onChangeText={setText} placeholder={tr('Расскажите, как прошла сделка (необязательно)')} placeholderTextColor={colors.muted} multiline maxLength={1000} />
          <Pressable style={st.send} disabled={busy} onPress={send}>{busy ? <ActivityIndicator color={colors.onInverse} /> : <Text style={st.sendT}>{tr('Отправить')}</Text>}</Pressable>
        </>
      )}
      <Pressable onPress={() => { setState('hidden'); authed(`/reviews/invite/${chatId}/dismiss`, token, 'POST').catch(() => {}) }} hitSlop={6}><Text style={st.later}>{tr('Не сейчас')}</Text></Pressable>
    </View>
  )
}

const st = StyleSheet.create({
  card: { alignSelf: 'stretch', marginVertical: 8, padding: 14, borderRadius: 20, backgroundColor: colors.surface, gap: 10 },
  title: { fontFamily: font[800], fontSize: 15.5, color: colors.ink },
  quick: { flex: 1, height: 44, borderRadius: 14, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  quickT: { fontFamily: font[800], fontSize: 14, color: colors.ink },
  star: { fontSize: 30, color: colors.sunken },
  input: { minHeight: 70, borderRadius: 14, backgroundColor: colors.sunken, padding: 12, fontFamily: font[400], fontSize: 15, color: colors.ink, textAlignVertical: 'top' },
  send: { height: 46, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  sendT: { fontFamily: font[800], fontSize: 15, color: colors.onInverse },
  later: { textAlign: 'center', fontFamily: font[700], fontSize: 13.5, color: colors.muted },
})
