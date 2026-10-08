import { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { adminCatStats, adminDaily, adminFunnel, adminQuality, adminSources, adminStats, type AdminStats, type DayRow, type Funnel } from '../../src/admin'
import { getLang } from '../../src/i18n'
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
  const [fun, setFun] = useState<Funnel | null>(null)
  const [src, setSrc] = useState<{ source: string; title?: string | null; count: number }[] | null>(null)
  const [cats, setCats] = useState<{ slug: string; count: number; name: Record<string, string> }[] | null>(null)
  const [qual, setQual] = useState<Record<string, number> | null>(null)
  useEffect(() => {
    if (!token) return
    setS(null)
    adminStats(token, +days).then(setS).catch(() => {})
    adminDaily(token, 14).then((r) => setDaily(r.items)).catch(() => setDaily([]))
    adminFunnel(token, +days).then(setFun).catch(() => {})
    adminSources(token, +days).then((r) => setSrc(r.items)).catch(() => setSrc([]))
    adminCatStats(token, +days).then((r) => setCats(r.items)).catch(() => setCats([]))
    adminQuality(token, +days).then(setQual).catch(() => {})
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
        {/* воронка: показы → просмотры → контакты, как на сайте */}
        {!!fun && (
          <View style={st.card}>
            <Text style={st.cardT}>{tr('Воронка')}</Text>
            {([[tr('Показы в ленте'), fun.funnel.impressions], [tr('Открыли объявление'), fun.funnel.views], [tr('Связались'), fun.funnel.contacts], [tr('Написали'), fun.funnel.messages], [tr('Открыли телефон'), fun.funnel.phone_reveals]] as [string, number][]).map(([l, n], i, arr) => (
              <View key={l} style={st.fRow}>
                <Text style={st.fL}>{l}</Text>
                <View style={st.fBarBox}><View style={[st.fBar, { width: `${Math.max(2, (n / Math.max(1, arr[0][1])) * 100)}%` }]} /></View>
                <Text style={st.fN}>{n.toLocaleString('ru-RU')}</Text>
              </View>
            ))}
            <Text style={st.note}>{tr('Объявлений за период: {n}, с контактом: {c}, продано: {s}', { n: fun.liquidity.listings, c: fun.liquidity.with_contact, s: fun.liquidity.sold })}{fun.liquidity.median_hours_to_contact != null ? ` · ${tr('до первого контакта ~{h} ч', { h: Math.round(fun.liquidity.median_hours_to_contact) })}` : ''}</Text>
          </View>
        )}
        {!!cats && cats.length > 0 && (
          <View style={st.card}>
            <Text style={st.cardT}>{tr('Новые объявления по разделам')}</Text>
            {cats.slice(0, 8).map((c) => (
              <View key={c.slug} style={st.fRow}>
                <Text style={st.fL} numberOfLines={1}>{c.name?.[getLang()] || c.name?.ru || c.slug}</Text>
                <View style={st.fBarBox}><View style={[st.fBar, { width: `${Math.max(2, (c.count / Math.max(1, cats[0].count)) * 100)}%` }]} /></View>
                <Text style={st.fN}>{c.count}</Text>
              </View>
            ))}
          </View>
        )}
        {!!src && src.length > 0 && (
          <View style={st.card}>
            <Text style={st.cardT}>{tr('Откуда объявления')}</Text>
            {src.map((x) => <View key={x.source + (x.title || '')} style={st.fRow}><Text style={st.fL} numberOfLines={1}>{x.source === 'own' ? tr('Размещены на PLONK') : (x.title || x.source)}</Text><Text style={st.fN}>{x.count}</Text></View>)}
          </View>
        )}
        {!!qual && (
          <View style={st.card}>
            <Text style={st.cardT}>{tr('Качество ленты')}</Text>
            {([[tr('Без цены'), qual.no_price], [tr('Без фото'), qual.no_photo], [tr('Без города'), qual.no_city], [tr('Без перевода'), qual.not_translated]] as [string, number][]).map(([l, n]) => (
              <View key={l} style={st.fRow}><Text style={st.fL}>{l}</Text><Text style={[st.fN, n > 0 && { color: colors.danger }]}>{n} / {qual.active}</Text></View>
            ))}
          </View>
        )}
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
  fRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 },
  fL: { width: 130, fontFamily: font[600], fontSize: 13, color: colors.inkSoft },
  fBarBox: { flex: 1, height: 10, borderRadius: 5, backgroundColor: colors.sunken, overflow: 'hidden' },
  fBar: { height: 10, borderRadius: 5, backgroundColor: colors.primary },
  fN: { minWidth: 44, textAlign: 'right', fontFamily: font[800], fontSize: 13.5, color: colors.ink, marginLeft: 'auto' },
  note: { fontFamily: font[400], fontSize: 12.5, color: colors.muted, lineHeight: 18 },
  axisT: { fontFamily: font[600], fontSize: 11, color: colors.muted },
})
