import { useEffect, useState } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { adminAudit, type AuditItem, auditActors } from '../../src/admin'
import { Pressable, ScrollView } from 'react-native'
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
  // фильтр по сотруднику — как на сайте: кто сколько сделал за 30 дней
  const [actors, setActors] = useState<{ id: string; name: string; total: number }[]>([])
  const [actor, setActor] = useState('')
  useEffect(() => { if (token) auditActors(token).then((r) => setActors(r.items)).catch(() => {}) }, [token])
  useEffect(() => { if (!token) return; setItems(null); adminAudit(token, kind, actor).then((r) => setItems(r.items)).catch(() => setItems([])) }, [token, kind, actor])
  return (
    <View style={st.page}>
      <FlatList
        data={items ?? []}
        keyExtractor={(x) => x.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60, gap: 8 }}
        ListHeaderComponent={<>
          <Header bleed={16} bleedTop={0} title={tr('Журнал действий')} fallback="/admin" />
          {actors.length > 1 && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6, paddingBottom: 8 }}>
              {[{ id: '', name: tr('Все сотрудники'), total: 0 }, ...actors].map((a) => (
                <Pressable key={a.id || 'all'} style={[st.chip, actor === a.name && st.chipOn, !a.id && !actor && st.chipOn]} onPress={() => setActor(a.id ? a.name : '')}>
                  <Text style={[st.chipT, (actor === a.name || (!a.id && !actor)) && { color: colors.onInverse }]}>{a.name}{a.total ? ` · ${a.total}` : ''}</Text>
                </Pressable>
              ))}
            </ScrollView>
          )}
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
  chip: { height: 34, paddingHorizontal: 14, borderRadius: 17, backgroundColor: colors.surface, justifyContent: 'center' },
  chipOn: { backgroundColor: colors.inverse },
  chipT: { fontFamily: font[700], fontSize: 13, color: colors.ink },
  empty: { textAlign: 'center', padding: 30, fontFamily: font[600], color: colors.muted },
})
