import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAuth } from '../../src/auth'
import { plural, tr } from '../../src/i18n'
import Icon from '../../src/components/Icon'
import { Empty, Header, k } from '../../src/components/Kit'
import { type Brief, jobIncoming } from '../../src/social'
import { colors, font } from '../../src/theme'
import { RowSkeletons } from '../../src/components/Skeleton'

/** Работодатель: вакансии с откликами, новые — сверху. */
export default function Incoming() {
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const [items, setItems] = useState<{ vacancy: Brief; counts: Record<string, number> }[] | null>(null)
  useEffect(() => { if (token) jobIncoming(token).then((r) => setItems(r.items)).catch(() => setItems([])); else router.replace('/login') }, [token])
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: insets.bottom + 24 }}>
        <Header bleed={12} bleedTop={0} title={tr('Отклики на вакансии')} />
        {items === null ? <RowSkeletons thumb="square" /> : !items.length ? <Empty text={tr('Откликов пока нет. Они появятся здесь и в чатах')} /> : items.map(({ vacancy, counts }) => (
          <Pressable key={vacancy.id} style={[k.card, k.row]} onPress={() => router.push(`/jobs/${vacancy.id}` as never)}>
            <Text style={[k.name, { flex: 1 }]} numberOfLines={2}>{vacancy.title}</Text>
            {counts.new > 0 && <View style={s.badge}><Text style={s.badgeText}>{tr('{n} новых', { n: counts.new })}</Text></View>}
            <Text style={k.muted}>{counts.total} {plural(counts.total, { ru: ['отклик', 'отклика', 'откликов'], en: ['application', 'applications'], sr: ['prijava', 'prijave', 'prijava'] })}</Text>
            <Icon name="forward" size={18} color={colors.muted} />
          </Pressable>
        ))}
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  badge: { height: 22, paddingHorizontal: 8, borderRadius: 11, backgroundColor: colors.accent, justifyContent: 'center' },
  badgeText: { fontFamily: font[700], fontSize: 12, color: '#fff' },
})
