import { Image } from 'expo-image'
import { useEffect, useState } from 'react'
import { Text, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { creatorDecide, shopDecide, shopQueue, type ShopQ } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { SITE } from '../../src/config'
import { tr } from '../../src/i18n'
import AdminList, { adm } from '../../src/components/AdminList'

type Row = ShopQ & { _kind: 'shop' | 'creator' }

/** Шопсы на проверке и заявки авторов: обложка, подпись, «Одобрить» / «Отклонить». */
export default function ShopsReview() {
  const { token } = useAuth()
  const [items, setItems] = useState<Row[] | null>(null)
  const load = () => {
    if (!token) return
    shopQueue(token).then((q) => setItems([...q.shops.map((s) => ({ ...s, _kind: 'shop' as const })), ...q.creators.map((c) => ({ ...c, _kind: 'creator' as const }))])).catch(() => setItems([]))
  }
  useEffect(load, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  const decide = (r: Row, ok: boolean) => {
    if (!token) return
    setItems((x) => (x ?? []).filter((y) => y.id !== r.id))
    ;(r._kind === 'shop' ? shopDecide(token, r.id, ok) : creatorDecide(token, r.id, ok)).catch(load)
  }
  return (
    <AdminList title={tr('Шопсы на проверке')} kicker={items ? (items.length ? tr('{n} ждут проверки', { n: items.length }) : tr('Очередь пуста')) : ' '} items={items} keyOf={(r) => r._kind + r.id} onRefresh={load}
      empty={tr('Нечего проверять')}
      render={(r) => (
        <View style={adm.card}>
          {r._kind === 'shop' && !!r.poster_url && <Image source={{ uri: r.poster_url.startsWith('http') ? r.poster_url : `${SITE}${r.poster_url}` }} style={{ width: '100%', aspectRatio: 9 / 12, borderRadius: 16 }} contentFit="cover" />}
          <Text style={adm.meta}>{r._kind === 'shop' ? tr('Шопс') : tr('Заявка автора')}</Text>
          <Text style={adm.title}>{r._kind === 'shop' ? (r.caption || '—') : (r.display_name || r.name || '—')}</Text>
          {r._kind === 'shop' && !!r.author?.name && <Text style={adm.meta}>{r.author.name}</Text>}
          <View style={adm.row}>
            <Pressable style={adm.ok} onPress={() => decide(r, true)}><Text style={adm.okT}>{tr('Одобрить')}</Text></Pressable>
            <Pressable style={adm.no} onPress={() => decide(r, false)}><Text style={adm.noT}>{tr('Отклонить')}</Text></Pressable>
          </View>
        </View>
      )} />
  )
}
