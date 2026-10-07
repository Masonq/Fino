import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { API, SITE } from '../../src/config'
import { getLang, tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Skeleton from '../../src/components/Skeleton'
import { colors, font } from '../../src/theme'
import type { GuideCard } from './index'

type Guide = GuideCard & { blocks: { t: string; v: unknown }[]; others?: GuideCard[] }

/** Статья «Полезного»: заголовки, абзацы, списки и кнопки в нужный раздел — как на сайте. */
export default function GuideScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const [g, setG] = useState<Guide | null>(null)
  useEffect(() => { fetch(`${API}/guides/${slug}?lang=${getLang()}`).then((r) => r.json()).then(setG).catch(() => {}) }, [slug])
  return (
    <View style={styles.page}>
      <Header title={tr('Полезное')} fallback="/vodic" />
      {!g ? (
        <View style={{ padding: 16, gap: 12 }}><Skeleton style={{ height: 220, borderRadius: 24 }} /><Skeleton style={{ height: 30, width: '80%' }} /><Skeleton style={{ height: 120 }} /></View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }}>
          <View style={styles.art}><Image source={{ uri: `${SITE}${g.cover}` }} style={{ width: '100%', height: '100%' }} contentFit="contain" /></View>
          <Text style={styles.h1}>{g.title}</Text>
          <Text style={styles.lead}>{g.lead}</Text>
          {g.blocks.map((b, i) => {
            if (b.t === 'h2') return <Text key={i} style={styles.h2}>{String(b.v)}</Text>
            if (b.t === 'p') return <Text key={i} style={styles.p}>{String(b.v)}</Text>
            if (b.t === 'ul') return <View key={i} style={{ gap: 6, marginTop: 6 }}>{(b.v as string[]).map((li, j) => <View key={j} style={styles.li}><View style={styles.dot} /><Text style={[styles.p, { flex: 1, marginTop: 0 }]}>{li}</Text></View>)}</View>
            if (b.t === 'cta') {
              const [label, href] = b.v as [string, string]
              return <Pressable key={i} style={styles.cta} onPress={() => router.push(href as never)}><Text style={styles.ctaText}>{label}</Text></Pressable>
            }
            return null
          })}
          {!!g.others?.length && <Text style={styles.h2}>{tr('Ещё полезное')}</Text>}
          {g.others?.map((o) => (
            <Pressable key={o.slug} style={styles.other} onPress={() => router.push(`/vodic/${o.slug}` as never)}>
              <Text style={styles.otherTitle} numberOfLines={2}>{o.title}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  art: { height: 200, borderRadius: 24, backgroundColor: colors.primarySoft, overflow: 'hidden', marginBottom: 16 },
  h1: { fontFamily: font[800], fontSize: 26, letterSpacing: -0.8, color: colors.ink },
  lead: { fontFamily: font[400], fontSize: 16, lineHeight: 23, color: colors.inkSoft, marginTop: 8 },
  h2: { fontFamily: font[800], fontSize: 20, letterSpacing: -0.4, color: colors.ink, marginTop: 22 },
  p: { fontFamily: font[400], fontSize: 16, lineHeight: 24, color: colors.ink, marginTop: 8 },
  li: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.primary, marginTop: 9 },
  cta: { marginTop: 14, height: 50, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 },
  ctaText: { fontFamily: font[800], fontSize: 15.5, color: colors.onInverse },
  other: { marginTop: 10, padding: 14, borderRadius: 18, backgroundColor: colors.surface },
  otherTitle: { fontFamily: font[700], fontSize: 15, color: colors.ink },
})
