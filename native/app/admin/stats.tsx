import { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { adminDaily, adminStats, type AdminStats, type DayRow } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Segmented from '../../src/components/Segmented'
import Skeleton from '../../src/components/Skeleton'
import { TINTS } from '../../src/tints'
import { colors, font } from '../../src/theme'

/** Показатели — как на сайте: цифры за период плитками и столбики по дням (объявления, посетители, регистрации). */
export default function Stats() {
  const { token } = useAuth()
  const [days, setDays] = useState<'7' | '30'>('7')
  const [s, setS] = useState<AdminStats | null>(null)
  const [daily, setDaily] = useState<DayRow[] | null>(null)
  useEffect(() => {
    if (!token) return
    setS(null)
    adminStats(token, +days).then(setS).catch(() => {})
    adminDaily(token, 14).then((r) => setDaily(r.items)).catch(() => setDaily([]))
  }, [token, days])
  const tiles: [string, number | undefined, string][] = s ? [
    [tr('Объявлений в ленте'), s.listings.active, TINTS['real-estate']], [tr('Новых за период'), s.listings.fresh, TINTS.auto],
    [tr('Ждут проверки'), s.listings.pending, TINTS.fashion], [tr('Людей всего'), s.people.total, TINTS.electronics],
    [tr('Новых людей'), s.people.fresh, TINTS.kids], [tr('Продавцов'), s.people.sellers, TINTS.services],
  ] : []
  return (
    <View style={st.page}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60 }}>
        <Header bleed={16} bleedTop={0} title={tr('Показатели')} fallback="/admin" />
        <Segmented options={[{ key: '7', label: tr('7 дней') }, { key: '30', label: tr('30 дней') }]} value={days} onChange={(v) => setDays(v as '7' | '30')} />
        <View style={st.grid}>
          {!s ? [0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} style={st.tileSk} />) : tiles.map(([l, n, bg]) => (
            <View key={l} style={[st.tile, { backgroundColor: bg }]}><Text style={st.n}>{n ?? 0}</Text><Text style={st.l}>{l}</Text></View>
          ))}
        </View>
        {([['visitors', tr('Посетители по дням')], ['listings', tr('Новые объявления по дням')], ['signups', tr('Регистрации по дням')]] as [keyof DayRow, string][]).map(([k, title]) => (
          <View key={k} style={st.card}>
            <Text style={st.cardT}>{title}</Text>
            {!daily ? <Skeleton style={{ height: 110, borderRadius: 12 }} /> : <Bars rows={daily} k={k} />}
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

function Bars({ rows, k }: { rows: DayRow[]; k: keyof DayRow }) {
  const vals = rows.map((r) => Number(r[k]) || 0)
  const max = Math.max(1, ...vals)
  return (
    <View>
      <View style={st.bars}>
        {vals.map((v, i) => (
          <View key={i} style={st.barCol}>
            {v > 0 && <Text style={st.barN}>{v}</Text>}
            <View style={[st.bar, { height: Math.max(3, (v / max) * 90) }]} />
          </View>
        ))}
      </View>
      <View style={st.axis}><Text style={st.axisT}>{rows[0]?.day.slice(5).split('-').reverse().join('.')}</Text><Text style={st.axisT}>{rows[rows.length - 1]?.day.slice(5).split('-').reverse().join('.')}</Text></View>
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  tile: { width: '31.6%', minHeight: 84, borderRadius: 20, padding: 12, justifyContent: 'flex-end' },
  tileSk: { width: '31.6%', height: 84, borderRadius: 20 },
  n: { fontFamily: font[800], fontSize: 24, color: colors.ink, letterSpacing: -0.5 },
  l: { fontFamily: font[700], fontSize: 11.5, color: colors.inkSoft },
  card: { marginTop: 12, padding: 16, borderRadius: 22, backgroundColor: colors.surface, gap: 10 },
  cardT: { fontFamily: font[800], fontSize: 16, color: colors.ink },
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 4, height: 110 },
  barCol: { flex: 1, alignItems: 'center', justifyContent: 'flex-end' },
  bar: { width: '100%', borderRadius: 4, backgroundColor: colors.primary },
  barN: { fontFamily: font[700], fontSize: 9, color: colors.muted, marginBottom: 2 },
  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  axisT: { fontFamily: font[600], fontSize: 11, color: colors.muted },
})
