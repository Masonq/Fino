import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useMemo, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { API, SITE } from '../../src/config'
import { getLang, tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Skeleton from '../../src/components/Skeleton'
import { colors, font } from '../../src/theme'
import { prefs } from '../../src/prefs'
import { TINTS } from '../../src/tints'

export type GuideCard = { slug: string; date: string; cover: string; topic: string; title: string; lead: string }
const TOPIC_BG: Record<string, string> = { home: TINTS['real-estate'], docs: TINTS.electronics, deals: TINTS.services, auto: TINTS.auto, family: TINTS.kids }
const TOPICS: [string, string][] = [['all', 'Все'], ['home', 'Жильё'], ['docs', 'Документы и деньги'], ['deals', 'Покупка и продажа'], ['auto', 'Авто'], ['family', 'Семья и питомцы']]

/** «Полезное» — статьи для жизни в Сербии, как на сайте: главная статья каждый раз другая, без времени чтения. */
export default function Guides() {
  const [items, setItems] = useState<GuideCard[] | null>(null)
  const [topic, setTopic] = useState('all')
  const [turn, setTurn] = useState(0)
  useEffect(() => {
    fetch(`${API}/guides?lang=${getLang()}`).then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => setItems([]))
    prefs.get('plonk_guide_turn').then((v) => { const n = (Number(v) || 0) + 1; prefs.set('plonk_guide_turn', String(n)); setTurn(n) })
  }, [])
  const shown = useMemo(() => (items || []).filter((g) => topic === 'all' || g.topic === topic), [items, topic])
  const featured = topic === 'all' && shown.length ? shown[turn % shown.length] : null
  const rest = featured ? shown.filter((g) => g !== featured) : shown
  return (
    <View style={styles.page}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }}>
        <Header bleed={0} bleedTop={0} title={tr('Полезное')} kicker={tr('Жильё, документы, покупки в Сербии')} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
          {TOPICS.filter(([k]) => k === 'all' || (items || []).some((g) => g.topic === k)).map(([k, l]) => (
            <Pressable key={k} style={[styles.chip, topic === k && styles.chipOn]} onPress={() => setTopic(k)}><Text style={[styles.chipText, topic === k && styles.chipTextOn]}>{tr(l)}</Text></Pressable>
          ))}
        </ScrollView>
        {!items && <View style={{ padding: 16, gap: 12 }}><Skeleton style={{ height: 300, borderRadius: 24 }} /><Skeleton style={{ height: 130, borderRadius: 22 }} /><Skeleton style={{ height: 130, borderRadius: 22 }} /></View>}
        {featured && <Card g={featured} big />}
        {rest.map((g) => <Card key={g.slug} g={g} />)}
      </ScrollView>
    </View>
  )
}

function Card({ g, big }: { g: GuideCard; big?: boolean }) {
  return (
    <Pressable style={[styles.card, big && styles.cardBig]} onPress={() => router.push(`/vodic/${g.slug}` as never)}>
      <View style={[big ? styles.artBig : styles.art, { backgroundColor: TOPIC_BG[g.topic] || colors.sunken }]}>
        <Image source={{ uri: `${SITE}${g.cover}` }} style={{ width: '100%', height: '100%' }} contentFit="contain" />
      </View>
      <View style={styles.body}>
        <Text style={styles.topic}>{tr(TOPICS.find(([k]) => k === g.topic)?.[1] || '')}</Text>
        <Text style={[styles.title, big && styles.titleBig]} numberOfLines={3}>{g.title}</Text>
        <Text style={styles.lead} numberOfLines={big ? 3 : 2}>{g.lead}</Text>
      </View>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  chips: { gap: 8, paddingHorizontal: 16, paddingBottom: 12 },
  chip: { height: 38, paddingHorizontal: 14, borderRadius: 19, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  chipOn: { backgroundColor: colors.inverse },
  chipText: { fontFamily: font[700], fontSize: 14, color: colors.ink },
  chipTextOn: { color: colors.onInverse },
  card: { flexDirection: 'row', marginHorizontal: 16, marginBottom: 12, borderRadius: 22, backgroundColor: colors.surface, overflow: 'hidden' },
  cardBig: { flexDirection: 'column', borderRadius: 24 },
  art: { width: 110, minHeight: 120 },
  artBig: { width: '100%', height: 200 },
  body: { flex: 1, padding: 14, gap: 4 },
  topic: { fontFamily: font[700], fontSize: 12.5, color: colors.muted },
  title: { fontFamily: font[800], fontSize: 16, letterSpacing: -0.3, color: colors.ink },
  titleBig: { fontSize: 22, letterSpacing: -0.6 },
  lead: { fontFamily: font[400], fontSize: 14, lineHeight: 19, color: colors.inkSoft },
})
