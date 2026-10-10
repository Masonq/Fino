import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAuth } from '../../src/auth'
import { tr } from '../../src/i18n'
import { Btn, Empty, Header, k } from '../../src/components/Kit'
import { JOB_DOT, JOB_ST, when } from '../../src/components/ListingExtras'
import { jobMyResponses, type JobResp } from '../../src/social'
import { colors, font } from '../../src/theme'
import { RowSkeletons } from '../../src/components/Skeleton'

/** Соискатель: «Мои отклики» со статусами. */
export default function MyResponses() {
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const [items, setItems] = useState<JobResp[] | null>(null)
  useEffect(() => { if (token) jobMyResponses(token).then((r) => setItems(r.items)).catch(() => setItems([])); else router.replace('/login') }, [token])
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: insets.bottom + 24 }}>
        <Header bleed={12} bleedTop={0} title={tr('Мои отклики')} />
        {items === null ? <RowSkeletons thumb="square" /> : !items.length ? (
          <Empty art="responses" text={tr('Вы ещё не откликались на вакансии')}><Btn label={tr('Смотреть вакансии')} onPress={() => router.push('/c/jobs' as never)} /></Empty>
        ) : items.map((r) => (
          <View key={r.id} style={k.card}>
            {!!r.vacancy && <Pressable onPress={() => router.push(`/listing/${r.vacancy!.id}` as never)}><Text style={k.name}>{r.vacancy.title}</Text></Pressable>}
            <View style={[k.row, { marginTop: 6 }]}><View style={[s.dot, { backgroundColor: JOB_DOT[r.status] }]} /><Text style={s.st}>{tr(JOB_ST[r.status])}</Text></View>
            {r.status === 'invited' && !!r.interview_at && <Text style={s.inv}>✅ {tr('Собеседование {when}', { when: when(r.interview_at) })}{r.interview_note ? ` · ${r.interview_note}` : ''}</Text>}
            <View style={k.actions}>
              {!!r.chat_id && <Btn small kind="ghost" label={tr('Открыть чат')} onPress={() => router.push(`/chat/${r.chat_id}` as never)} />}
              <Text style={k.muted}>{when(r.created_at)}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  dot: { width: 8, height: 8, borderRadius: 4 },
  st: { fontFamily: font[600], fontSize: 14, color: colors.ink },
  inv: { marginTop: 10, padding: 10, borderRadius: 12, overflow: 'hidden', backgroundColor: colors.primarySoft, fontFamily: font[600], fontSize: 14, color: colors.primaryDeep },
})
