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
  const set = LEGAL[(doc as 'rules' | 'terms' | 'privacy')] ?? LEGAL.rules
  const d = set[getLang()] ?? set.ru
  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title} numberOfLines={1}>{d.title}</Text>
      </View>
      <ScrollView contentContainerStyle={styles.body}>
        {!!d.updated && <Text style={styles.updated}>{d.updated}</Text>}
        {d.sections.map((sec, i) => (
          <View key={i} style={{ gap: 8, marginTop: 16 }}>
            {!!sec.h && <Text style={styles.h}>{sec.h}</Text>}
            {(sec.p ?? []).map((p, k) => <Text key={k} style={styles.p} selectable>{p}</Text>)}
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { flex: 1, fontSize: 19, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  body: { paddingHorizontal: 18, paddingBottom: 40 },
  updated: { fontSize: 13, fontFamily: font[600], color: colors.muted },
  h: { fontSize: 16.5, fontFamily: font[800], color: colors.ink },
  p: { fontSize: 15, lineHeight: 22, fontFamily: font[400], color: colors.ink },
})
