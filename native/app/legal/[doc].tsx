import { useRef } from 'react'
import { router, useLocalSearchParams } from 'expo-router'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import Icon from '../../src/components/Icon'
import { getLang, tr } from '../../src/i18n'
import { LEGAL } from '../../src/legal'
import { colors, font } from '../../src/theme'

/** Правила, условия, политика конфиденциальности — тексты сайта на языке приложения. */
export default function LegalScreen() {
  const { doc } = useLocalSearchParams<{ doc: string }>()
  const insets = useSafeAreaInsets()
  const scrollRef = useRef<ScrollView>(null)
  const offsets = useRef<number[]>([])
  const set = LEGAL[(doc as 'rules' | 'terms' | 'privacy')] ?? LEGAL.rules
  const d = set[getLang()] ?? set.ru
  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title} numberOfLines={2}>{d.title}</Text>
      </View>
      <ScrollView ref={scrollRef} contentContainerStyle={styles.body}>
        {!!d.updated && <Text style={styles.updated}>{d.updated}</Text>}
        {/* содержание чипами — как на сайте: нажал — и сразу к разделу */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginHorizontal: -16, marginBottom: 6 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16 }}>
          {d.sections.filter((x) => !!x.h).map((x, i) => (
            <Pressable key={i} style={styles.toc} onPress={() => scrollRef.current?.scrollTo({ y: Math.max(0, (offsets.current[i] ?? 0) - 8), animated: true })}>
              <Text style={styles.tocT}>{String(x.h).replace(/^\d+\.\s*/, '')}</Text>
            </Pressable>
          ))}
        </ScrollView>
        {d.sections.map((sec, i) => (
          <View key={i} style={styles.card} onLayout={(e) => { offsets.current[i] = e.nativeEvent.layout.y }}>
            {!!sec.h && <Text style={styles.h}>{sec.h}</Text>}
            {(sec.p ?? []).map((p, k) => <Text key={k} style={styles.p} selectable>{p}</Text>)}
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  toc: { height: 36, paddingHorizontal: 14, borderRadius: 18, backgroundColor: colors.surface, justifyContent: 'center' },
  tocT: { fontFamily: font[700], fontSize: 13, color: colors.ink },
  card: { gap: 8, marginTop: 10, padding: 16, borderRadius: 22, backgroundColor: colors.surface },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, minHeight: 56 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  title: { flex: 1, fontFamily: font[800], fontSize: 22, lineHeight: 26, letterSpacing: -0.6, color: colors.ink },
  body: { paddingHorizontal: 18, paddingBottom: 40 },
  updated: { fontSize: 13, fontFamily: font[600], color: colors.muted },
  h: { fontSize: 16.5, fontFamily: font[800], color: colors.ink },
  p: { fontSize: 15, lineHeight: 22, fontFamily: font[400], color: colors.ink },
})
