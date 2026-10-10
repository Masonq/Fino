import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Text, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { clearChatFlag, type FlaggedChat, flaggedChats } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { tr } from '../../src/i18n'
import AdminList, { adm } from '../../src/components/AdminList'

/** Подозрительные чаты — переписки, где сработали признаки обмана: что насторожило, последние сообщения, решение. */
export default function Flagged() {
  const { token } = useAuth()
  const [items, setItems] = useState<FlaggedChat[] | null>(null)
  const load = () => { if (token) flaggedChats(token).then((r) => setItems(r.items)).catch(() => setItems([])) }
  useEffect(load, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  const clear = (id: string) => { if (!token) return; setItems((x) => (x ?? []).filter((c) => c.id !== id)); clearChatFlag(token, id).catch(load) }
  return (
    <AdminList title={tr('Подозрительные чаты')} items={items} keyOf={(c) => c.id} onRefresh={load}
      empty={tr('Подозрительных чатов нет')} emptyHint={tr('Сюда попадают переписки, где похоже на обман.')}
      render={(c) => (
        <View style={[adm.card, adm.bad]}>
          {!!c.listing?.title && <Text style={adm.title} numberOfLines={1}>{c.listing.title}</Text>}
          {!!c.reason && <Text style={[adm.meta, { color: '#C0392B' }]}>{c.reason}</Text>}
          {(c.messages || []).slice(-3).map((m, i) => <Text key={i} style={adm.text} numberOfLines={2}><Text style={{ fontWeight: '800' }}>{m.from}: </Text>{m.text}</Text>)}
          <View style={adm.row}>
            {!!c.seller_id && <Pressable style={adm.no} onPress={() => router.push(`/admin/users/${c.seller_id}` as never)}><Text style={adm.noT}>{tr('Продавец')}</Text></Pressable>}
            <Pressable style={adm.ok} onPress={() => clear(c.id)}><Text style={adm.okT}>{tr('Всё в порядке')}</Text></Pressable>
          </View>
        </View>
      )} />
  )
}
