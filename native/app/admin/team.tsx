import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, Text, View } from 'react-native'
import { type TeamChat, teamChats } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { timeAgo } from '../../src/format'
import { tr } from '../../src/i18n'
import AdminList, { adm } from '../../src/components/AdminList'

/** Письма команды — переписки людей с командой PLONK; непрочитанные отмечены. */
export default function Team() {
  const { token } = useAuth()
  const [items, setItems] = useState<TeamChat[] | null>(null)
  const [unread, setUnread] = useState(0)
  const load = () => { if (token) teamChats(token).then((r) => { setItems(r.items); setUnread(r.unread) }).catch(() => setItems([])) }
  useEffect(load, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <AdminList title={tr('Письма команды')} kicker={unread ? tr('{n} непрочитанных', { n: unread }) : tr('Всё прочитано')} items={items} keyOf={(c) => c.id} onRefresh={load}
      empty={tr('Писем пока нет')} emptyHint={tr('Здесь появятся ответы людей на письма команды.')}
      render={(c) => (
        <Pressable style={adm.card} onPress={() => router.push(`/admin/team/${c.id}` as never)}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
            <Text style={adm.title} numberOfLines={1}>{c.person?.name || '—'}</Text>
            <Text style={adm.meta}>{c.last_at ? timeAgo(c.last_at) : ''}</Text>
          </View>
          <Text style={[adm.text, (c.unread ?? 0) > 0 && { fontWeight: '800', color: '#0F1512' }]} numberOfLines={2}>{c.last_from_team ? `${tr('Вы')}: ` : ''}{c.last_text || ''}</Text>
        </Pressable>
      )} />
  )
}
