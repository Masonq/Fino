import { useEffect, useState } from 'react'
import { Pressable, Text, View } from 'react-native'
import { volunteerDecide, volunteerQueue, type VolApp } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { timeAgo } from '../../src/format'
import { tr } from '../../src/i18n'
import AdminList, { adm } from '../../src/components/AdminList'
import Segmented from '../../src/components/Segmented'

/** Заявки в команду (волонтёры): кто, на какую роль, языки, часы; «Принять» / «Отклонить». */
export default function Volunteers() {
  const { token } = useAuth()
  const [tab, setTab] = useState('new')
  const [items, setItems] = useState<VolApp[] | null>(null)
  const load = () => { if (!token) return; setItems(null); volunteerQueue(token, tab).then((r) => setItems(r.items)).catch(() => setItems([])) }
  useEffect(load, [token, tab]) // eslint-disable-line react-hooks/exhaustive-deps
  const decide = (id: string, ok: boolean) => { if (!token) return; setItems((x) => (x ?? []).filter((a) => a.id !== id)); volunteerDecide(token, id, ok).catch(load) }
  return (
    <AdminList title={tr('Заявки в команду')} items={items} keyOf={(a) => a.id} onRefresh={load}
      top={<View style={{ marginBottom: 6 }}><Segmented options={[{ key: 'new', label: tr('Новые') }, { key: 'accepted', label: tr('Приняты') }, { key: 'rejected', label: tr('Отклонены') }]} value={tab} onChange={setTab} /></View>}
      empty={tr('Заявок нет')}
      render={(a) => (
        <View style={adm.card}>
          <Text style={adm.title}>{a.user?.display_name || a.user?.email || '—'}</Text>
          <Text style={adm.meta}>{[a.role, Array.isArray(a.languages) ? a.languages.join(', ') : a.languages, a.hours_per_week ? tr('{n} ч в неделю', { n: a.hours_per_week }) : ''].filter(Boolean).join(' · ')}</Text>
          {!!a.about && <Text style={adm.text}>{a.about}</Text>}
          <Text style={adm.meta}>{a.created_at ? timeAgo(a.created_at) : ''}</Text>
          {tab === 'new' && (
            <View style={adm.row}>
              <Pressable style={adm.ok} onPress={() => decide(a.id, true)}><Text style={adm.okT}>{tr('Принять')}</Text></Pressable>
              <Pressable style={adm.no} onPress={() => decide(a.id, false)}><Text style={adm.noT}>{tr('Отклонить')}</Text></Pressable>
            </View>
          )}
        </View>
      )} />
  )
}
