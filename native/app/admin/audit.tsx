import { useEffect, useState } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { adminAudit, type AuditItem } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { timeAgo } from '../../src/format'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Segmented from '../../src/components/Segmented'
import Skeleton from '../../src/components/Skeleton'
import { colors, font } from '../../src/theme'

const ACTION: Record<string, string> = {
  'listing.approve': 'Одобрил объявление', 'listing.reject': 'Отклонил объявление', 'listing.move': 'Перенёс в раздел', 'listing.delete': 'Удалил объявление',
  'user.block': 'Заблокировал', 'user.unblock': 'Разблокировал', 'user.role': 'Сменил роль', 'user.verify': 'Галочка «Проверен»', 'ticket.answer': 'Ответил на обращение',
}

/** Журнал действий команды — кто, что и когда сделал; как на сайте. */
export default function Audit() {
  const { token } = useAuth()
  const [kind, setKind] = useState('')
  const [items, setItems] = useState<AuditItem[] | null>(null)
  useEffect(() => { if (!token) return; setItems(null); adminAudit(token, kind).then((r) => setItems(r.items)).catch(() => setItems([])) }, [token, kind])
  return (
    <View style={st.page}>
      <FlatList
        data={items ?? []}
        keyExtractor={(x) => x.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60, gap: 8 }}
        ListHeaderComponent={<>
          <Header bleed={16} bleedTop={0} title={tr('Журнал действий')} fallback="/admin" />
          <View style={{ marginBottom: 6 }}><Segmented options={[{ key: '', label: tr('Всё') }, { key: 'user', label: tr('Люди') }, { key: 'listing', label: tr('Объявления') }]} value={kind} onChange={setKind} /></View>
        </>}
        ListEmptyComponent={items === null ? <View style={{ gap: 8 }}>{[0, 1, 2, 3].map((i) => <Skeleton key={i} style={{ height: 70, borderRadius: 18 }} />)}</View> : <Text style={st.empty}>{tr('Пока пусто')}</Text>}
        renderItem={({ item }) => (
          <View style={st.row}>
            <Text style={st.what}>{tr(ACTION[item.action] || item.action)}</Text>
            {!!(item.details as { subject?: string; title?: string } | null)?.subject && <Text style={st.det} numberOfLines={1}>{String((item.details as { subject?: string }).subject)}</Text>}
            {!!item.reason && <Text style={st.det} numberOfLines={2}>{tr('Причина')}: {item.reason}</Text>}
            <Text style={st.meta}>{item.actor} · {timeAgo(item.created_at)}</Text>
          </View>
        )}
      />
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  row: { padding: 14, borderRadius: 18, backgroundColor: colors.surface, gap: 3 },
  what: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  det: { fontFamily: font[400], fontSize: 13.5, color: colors.inkSoft },
  meta: { fontFamily: font[600], fontSize: 12, color: colors.muted, marginTop: 2 },
  empty: { textAlign: 'center', padding: 30, fontFamily: font[600], color: colors.muted },
})
