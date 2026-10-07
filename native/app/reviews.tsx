import { success } from '../src/haptics'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { createReview, waitingReviews, type Waiting } from '../src/api'
import { useAuth } from '../src/auth'
import Icon, { Star } from '../src/components/Icon'
import Sheet from '../src/components/Sheet'
import { mediaUrl } from '../src/config'
import { tr } from '../src/i18n'
import { colors, font } from '../src/theme'

/** «Ждут отзыва» — сделки, где можно оценить собеседника: звёзды 1–5 и комментарий по желанию. */
export default function Reviews() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [items, setItems] = useState<Waiting[] | null>(null)
  const [target, setTarget] = useState<Waiting | null>(null)
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => { if (token) setItems((await waitingReviews(token).catch(() => ({ items: [] }))).items) }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const send = async () => {
    if (!token || !target || !rating) return
    setBusy(true)
    try { await createReview(token, { target_id: target.target_id, listing_id: target.listing_id, rating, comment: comment.trim() }); success(); setTarget(null); await load() } finally { setBusy(false) }
  }

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Ждут вашего отзыва')}</Text>
      </View>
      {items === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
          {items.length === 0 && <View style={styles.emptyBox}><View style={styles.emptyIcon}><Icon name="star" size={28} color={colors.primary} /></View><Text style={styles.emptyMsg}>{tr('Никто не ждёт отзыва. Отзывы появляются после переписки, похожей на сделку.')}</Text></View>}
          {items.map((w) => (
            <Pressable key={w.chat_id} style={styles.card} onPress={() => { setTarget(w); setRating(0); setComment('') }}>
              <View style={styles.thumb}>{w.listing_photo ? <Image source={{ uri: mediaUrl(w.listing_photo) ?? undefined }} style={{ width: 52, height: 52 }} contentFit="cover" /> : null}</View>
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{w.target_name || tr('Собеседник')}</Text>
                {!!w.listing_title && <Text style={styles.sub} numberOfLines={1}>{w.listing_title}</Text>}
              </View>
              <Text style={styles.rate}>{tr('Оценить')}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}
      <Sheet visible={!!target} title={tr('Как прошла сделка?')} onClose={() => setTarget(null)}>
        <View style={{ paddingHorizontal: 20, gap: 12 }}>
          <Text style={styles.sub}>{target?.target_name}</Text>
          <View style={styles.stars}>
            {[1, 2, 3, 4, 5].map((k) => (
              <Pressable key={k} onPress={() => setRating(k)} hitSlop={4} accessibilityLabel={`${k}`}><Star size={36} color={k <= rating ? '#E0A526' : colors.sunken} /></Pressable>
            ))}
          </View>
          <TextInput value={comment} onChangeText={setComment} placeholder={tr('Пара слов о сделке (необязательно)')} placeholderTextColor={colors.muted} multiline textAlignVertical="top" style={styles.input} maxLength={1000} />
          <Pressable style={[styles.cta, (!rating || busy) && { opacity: 0.45 }]} disabled={!rating || busy} onPress={send}>
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Отправить отзыв')}</Text>}
          </Pressable>
        </View>
      </Sheet>
    </View>
  )
}

const styles = StyleSheet.create({
  emptyBox: { alignItems: 'center', gap: 14, paddingTop: 44, paddingHorizontal: 32 },
  emptyIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  emptyMsg: { fontSize: 13.5, lineHeight: 19, fontFamily: font[500], color: colors.muted, textAlign: 'center' },
  emptyBtn: { height: 42, paddingHorizontal: 20, borderRadius: 13, backgroundColor: colors.inverse, justifyContent: 'center' },
  emptyBtnText: { color: colors.onInverse, fontSize: 14.5, fontFamily: font[800] },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  empty: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 24 },
  card: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  thumb: { width: 52, height: 52, borderRadius: 12, backgroundColor: colors.photo, overflow: 'hidden' },
  name: { fontSize: 15.5, fontFamily: font[800], color: colors.ink },
  sub: { fontSize: 13, fontFamily: font[600], color: colors.muted },
  rate: { fontSize: 14, fontFamily: font[800], color: colors.primaryDeep },
  stars: { flexDirection: 'row', gap: 10, justifyContent: 'center', paddingVertical: 6 },
  input: { minHeight: 90, borderRadius: 13, backgroundColor: colors.sunken, padding: 12, fontSize: 15.5, fontFamily: font[400], color: colors.ink },
  cta: { height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
})
