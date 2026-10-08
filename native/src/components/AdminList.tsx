/**
 * Общий каркас простых экранов «Панели команды» (тревоги, подозрительные чаты, фоновые задачи, волонтёры, шопсы,
 * письма команды): шапка, уезжающая при прокрутке, скелеты при загрузке, пустое состояние карточкой.
 */
import type { ReactNode } from 'react'
import { FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native'
import { Header } from './Kit'
import Skeleton from './Skeleton'
import { colors, font } from '../theme'

export default function AdminList<T>({ title, kicker, items, render, keyOf, empty, emptyHint, top, onRefresh }: {
  title: string; kicker?: string; items: T[] | null; render: (x: T) => ReactNode; keyOf: (x: T) => string
  empty: string; emptyHint?: string; top?: ReactNode; onRefresh?: () => void
}) {
  return (
    <View style={st.page}>
      <FlatList
        data={items ?? []}
        keyExtractor={keyOf}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60, gap: 8 }}
        refreshControl={onRefresh ? <RefreshControl refreshing={false} onRefresh={onRefresh} /> : undefined}
        ListHeaderComponent={<><Header bleed={16} bleedTop={0} title={title} kicker={kicker} fallback="/admin" />{top}</>}
        ListEmptyComponent={items === null
          ? <View style={{ gap: 8 }}>{[0, 1, 2].map((i) => <Skeleton key={i} style={{ height: 84, borderRadius: 20 }} />)}</View>
          : <View style={st.empty}><Text style={st.emptyT}>{empty}</Text>{!!emptyHint && <Text style={st.emptyH}>{emptyHint}</Text>}</View>}
        renderItem={({ item }) => <>{render(item)}</>}
      />
    </View>
  )
}

export const adm = StyleSheet.create({
  card: { padding: 14, borderRadius: 20, backgroundColor: colors.surface, gap: 6 },
  title: { fontFamily: font[800], fontSize: 15.5, color: colors.ink },
  text: { fontFamily: font[400], fontSize: 14, color: colors.inkSoft, lineHeight: 19 },
  meta: { fontFamily: font[600], fontSize: 12.5, color: colors.muted },
  row: { flexDirection: 'row', gap: 8, marginTop: 4 },
  ok: { flex: 1, height: 44, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  okT: { fontFamily: font[800], fontSize: 14.5, color: colors.onInverse },
  no: { flex: 1, height: 44, borderRadius: 14, backgroundColor: colors.dangerBg, alignItems: 'center', justifyContent: 'center' },
  noT: { fontFamily: font[800], fontSize: 14.5, color: colors.danger },
  bad: { borderLeftWidth: 3, borderLeftColor: colors.danger },
})

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  empty: { alignItems: 'center', padding: 24, borderRadius: 22, backgroundColor: colors.surface, gap: 4 },
  emptyT: { fontFamily: font[800], fontSize: 16, color: colors.ink },
  emptyH: { fontFamily: font[400], fontSize: 13.5, color: colors.muted, textAlign: 'center' },
})
