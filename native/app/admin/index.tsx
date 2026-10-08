import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { counters, type Counters, daily, stats } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { SITE } from '../../src/config'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Icon from '../../src/components/Icon'
import Skeleton from '../../src/components/Skeleton'
import { TINTS } from '../../src/tints'
import { colors, font } from '../../src/theme'

/** Панель команды — как на сайте: 4 главных числа за неделю, «Требует внимания» (только непустые очереди), разделы. */
export default function AdminHome() {
  const { token, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [c, setC] = useState<Counters | null>(null)
  const [kpi, setKpi] = useState<{ label: string; value: number; delta: number | null }[] | null>(null)
  useFocusEffect(useCallback(() => {
    if (!token) return
    counters(token).then(setC).catch(() => setC({}))
    if (isAdmin) {
      Promise.all([daily(token, 14), stats(token, 7)]).then(([d, s]) => {
        const cur = d.items.slice(-7), prev = d.items.slice(-14, -7)
        const sum = (a: typeof cur, k: 'visitors' | 'own' | 'signups') => a.reduce((n, r) => n + (Number(r[k]) || 0), 0)
        const card = (label: string, k: 'visitors' | 'own' | 'signups') => {
          const now = sum(cur, k), before = prev.length === 7 ? sum(prev, k) : 0
          return { label, value: now, delta: before ? Math.round(((now - before) / before) * 100) : null }
        }
        setKpi([card(tr('Посетители'), 'visitors'), card(tr('Новые объявления'), 'own'), card(tr('Новые люди'), 'signups'), { label: tr('В ленте сейчас'), value: s.listings.active, delta: null }])
      }).catch(() => setKpi([]))
    }
  }, [token, isAdmin]))
  const queues = [
    { n: c?.moderation, label: tr('объявлений ждут проверки'), go: () => router.push('/admin/moderation' as never) },
    { n: c?.support, label: tr('обращений без ответа'), go: () => router.push('/admin/support' as never) },
    { n: c?.team_chats, label: tr('ответов на письма команды'), go: () => Linking.openURL(`${SITE}/ru/admin/team-chats`) },
    { n: c?.flagged_chats, label: tr('подозрительных переписок'), go: () => Linking.openURL(`${SITE}/ru/admin/flagged`) },
  ].filter((q) => (q.n ?? 0) > 0)
  const SECTIONS: [string, string, string, () => void][] = [
    ['shield', tr('Модерация'), TINTS['real-estate'], () => router.push('/admin/moderation' as never)],
    ['chat', tr('Обращения'), TINTS.auto, () => router.push('/admin/support' as never)],
    ['user', tr('Пользователи'), TINTS.fashion, () => router.push('/admin/users' as never)],
    ['list', tr('Показатели'), TINTS.electronics, () => router.push('/admin/stats' as never)],
    ['flag', tr('Подозрительные чаты'), TINTS.services, () => Linking.openURL(`${SITE}/ru/admin/flagged`)],
    ['doc', tr('Журнал действий'), TINTS.business, () => router.push('/admin/audit' as never)],
  ]
  return (
    <View style={styles.page}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Header bleed={16} bleedTop={16} title={tr('Панель команды')} kicker={isAdmin ? tr('Всё о PLONK за неделю') : tr('Очереди и разделы')} />
        {isAdmin && (kpi === null
          ? <View style={styles.kpis}>{[0, 1, 2, 3].map((i) => <Skeleton key={i} style={styles.kpi} />)}</View>
          : <View style={styles.kpis}>{kpi.map((k) => (
            <View key={k.label} style={styles.kpi}>
              <Text style={styles.kpiL}>{k.label}</Text>
              <Text style={styles.kpiV}>{k.value.toLocaleString('ru-RU')}</Text>
              {k.delta !== null && <Text style={[styles.delta, k.delta > 0 ? styles.up : k.delta < 0 ? styles.down : null]}>{k.delta > 0 ? '↑' : k.delta < 0 ? '↓' : '→'} {Math.abs(k.delta)}%</Text>}
            </View>
          ))}</View>)}
        <Text style={styles.sec}>{tr('Требует внимания')}</Text>
        {c === null ? <Skeleton style={{ height: 72, borderRadius: 22 }} /> : queues.length === 0 ? (
          <View style={styles.calm}><Text style={styles.calmIco}>✓</Text><View style={{ flex: 1 }}><Text style={styles.calmT}>{tr('Всё разобрано')}</Text><Text style={styles.calmS}>{tr('Очереди пусты — новое появится здесь сразу.')}</Text></View></View>
        ) : queues.map((q) => (
          <Pressable key={q.label} style={styles.queue} onPress={q.go}>
            <View style={styles.qn}><Text style={styles.qnT}>{q.n}</Text></View>
            <Text style={styles.ql}>{q.label}</Text>
            <Icon name="forward" size={16} color={colors.muted} />
          </Pressable>
        ))}
        <Text style={styles.sec}>{tr('Разделы')}</Text>
        <View style={styles.grid}>
          {SECTIONS.map(([ic, label, bg, go]) => (
            <Pressable key={label} style={[styles.tile, { backgroundColor: bg }]} onPress={go}>
              <Icon name={ic} size={22} color={colors.ink} />
              <Text style={styles.tileT}>{label}</Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  kpis: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  kpi: { width: '48%', flexGrow: 1, minHeight: 100, padding: 14, borderRadius: 22, backgroundColor: colors.surface },
  kpiL: { fontFamily: font[700], fontSize: 12.5, color: colors.inkSoft },
  kpiV: { fontFamily: font[800], fontSize: 28, letterSpacing: -1, color: colors.ink, marginTop: 2 },
  delta: { alignSelf: 'flex-start', marginTop: 6, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 9, overflow: 'hidden', fontFamily: font[800], fontSize: 12, backgroundColor: colors.sunken, color: colors.inkSoft },
  up: { backgroundColor: colors.primarySoft, color: colors.primaryDeep },
  down: { backgroundColor: colors.dangerBg, color: colors.danger },
  sec: { fontFamily: font[800], fontSize: 20, letterSpacing: -0.5, color: colors.ink, marginTop: 22, marginBottom: 10 },
  calm: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 16, borderRadius: 22, backgroundColor: colors.surface },
  calmIco: { width: 44, height: 44, borderRadius: 22, textAlign: 'center', lineHeight: 44, overflow: 'hidden', backgroundColor: colors.primarySoft, color: colors.primaryDeep, fontFamily: font[800], fontSize: 20 },
  calmT: { fontFamily: font[800], fontSize: 16, color: colors.ink },
  calmS: { fontFamily: font[400], fontSize: 13.5, color: colors.inkSoft, marginTop: 2 },
  queue: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 14, borderRadius: 22, backgroundColor: colors.surface, marginBottom: 8 },
  qn: { minWidth: 48, height: 48, borderRadius: 16, paddingHorizontal: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.inverse },
  qnT: { fontFamily: font[800], fontSize: 20, color: colors.onInverse },
  ql: { flex: 1, fontFamily: font[700], fontSize: 15.5, color: colors.ink },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: { width: '48%', flexGrow: 1, minHeight: 100, padding: 14, borderRadius: 22, justifyContent: 'space-between' },
  tileT: { fontFamily: font[800], fontSize: 15, color: colors.ink },
})
