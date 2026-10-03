import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { listingDashboard, type ListingDashboard } from '../../src/api'
import { useAuth } from '../../src/auth'
import Icon from '../../src/components/Icon'
import Segmented from '../../src/components/Segmented'
import { parseTime } from '../../src/format'
import { tr } from '../../src/i18n'
import { hasLdash, ldash } from '../../src/ldash'
import { colors, font } from '../../src/theme'

/**
 * Показатели объявления — как /my/:id/stats сайта: период (7 / 30 / 90 дней), просмотры, в среднем за день,
 * в избранном, связались, конверсия, просмотры по дням столбиками, сколько осталось до снятия, советы.
 */
export default function Stats() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [days, setDays] = useState<'7' | '30' | '90'>('30')
  const [d, setD] = useState<ListingDashboard | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!token) return
    setD(null); setFailed(false)
    listingDashboard(token, String(id), Number(days)).then(setD).catch(() => setFailed(true))
  }, [token, id, days])

  const views = d?.daily.reduce((n, x) => n + x.views, 0) ?? 0
  const maxDay = Math.max(1, ...(d?.daily.map((x) => x.views) ?? [1]))
  const avg = d ? (views / Math.max(1, d.daily.length)).toFixed(1).replace('.', ',') : '—'
  const conv = d && views > 0 ? `${Math.round(((d.chats_count ?? 0) / views) * 1000) / 10}%`.replace('.', ',') : '—'
  const exp = parseTime(d?.expires_at)
  const daysLeft = exp ? Math.max(0, Math.ceil((exp.getTime() - Date.now()) / 86400000)) : null

  const card = (label: string, value: string | number) => (
    <View style={styles.card}><Text style={styles.cardValue}>{value}</Text><Text style={styles.cardLabel}>{label}</Text></View>
  )

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/my'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{ldash('title')}</Text>
      </View>
      <ScrollView contentContainerStyle={styles.body}>
        <Segmented options={(['7', '30', '90'] as const).map((n) => ({ key: n, label: `${n} ${tr('дней')}` }))} value={days} onChange={setDays} />
        {failed ? <Text style={styles.note}>{ldash('not_owner')}</Text> : !d ? <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} /> : (
          <>
            <View style={styles.cards}>
              {card(ldash('views_total'), views)}
              {card(ldash('avg_per_day'), avg)}
              {card(ldash('favorites'), d.favorites_count ?? 0)}
              {card(ldash('chats'), d.chats_count ?? 0)}
              {card(ldash('conversion'), conv)}
              {daysLeft != null && card(ldash('days_left'), daysLeft === 0 ? ldash('expires_today') : daysLeft)}
            </View>

            <Text style={styles.h}>{ldash('stats_by_day')}</Text>
            <View style={styles.chart}>
              {d.daily.map((x) => <View key={x.day} style={[styles.bar, { height: `${Math.max(2, (x.views / maxDay) * 100)}%`, opacity: x.views ? 1 : 0.25 }]} />)}
            </View>
            <View style={styles.chartAxis}>
              <Text style={styles.axis}>{d.daily[0]?.day.slice(5).split('-').reverse().join('.')}</Text>
              <Text style={styles.axis}>{d.daily[d.daily.length - 1]?.day.slice(5).split('-').reverse().join('.')}</Text>
            </View>

            {!d.is_complete && <Text style={[styles.tip, styles.tipWarn]}>{ldash('incomplete_hint')}</Text>}
            {(d.tips ?? []).filter((t) => hasLdash(`tip_${t.code}`)).map((t) => (
              <Text key={t.code} style={[styles.tip, t.level === 'warn' && styles.tipWarn]}>{ldash(`tip_${t.code}`)}</Text>
            ))}
          </>
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  body: { paddingHorizontal: 16, paddingBottom: 40 },
  daysUnit: { fontSize: 12.5, fontFamily: font[600], color: colors.muted, marginTop: 4 },
  note: { fontSize: 14.5, fontFamily: font[500], color: colors.muted, marginTop: 20 },
  cards: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 14 },
  card: { width: '48.8%', padding: 13, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  cardValue: { fontSize: 22, fontFamily: font[800], color: colors.ink },
  cardLabel: { fontSize: 12.5, fontFamily: font[600], color: colors.muted, marginTop: 2 },
  h: { fontSize: 17, fontFamily: font[800], color: colors.ink, marginTop: 22, marginBottom: 10 },
  chart: { flexDirection: 'row', alignItems: 'flex-end', gap: 2, height: 120, padding: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  bar: { flex: 1, borderRadius: 3, backgroundColor: colors.primary },
  chartAxis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4, paddingHorizontal: 4 },
  axis: { fontSize: 11.5, fontFamily: font[600], color: colors.muted },
  tip: { marginTop: 12, padding: 12, borderRadius: 14, backgroundColor: colors.primarySoft, fontSize: 14, lineHeight: 19, fontFamily: font[600], color: colors.primaryDeep },
  tipWarn: { backgroundColor: '#FBF3E3', color: '#8A6A1F' },
})
