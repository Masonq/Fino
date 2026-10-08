import { useEffect, useState } from 'react'
import { Text, View } from 'react-native'
import { adminJobs, type JobRun } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { timeAgo } from '../../src/format'
import { tr } from '../../src/i18n'
import AdminList, { adm } from '../../src/components/AdminList'

/** Фоновые задачи за неделю (уборка ленты, переводы, рассылки): когда шли, сколько сделали, где ошибка. */
export default function Jobs() {
  const { token } = useAuth()
  const [items, setItems] = useState<JobRun[] | null>(null)
  const load = () => { if (token) adminJobs(token).then((r) => setItems(r.jobs)).catch(() => setItems([])) }
  useEffect(load, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  const bad = (items ?? []).filter((j) => j.error).length
  return (
    <AdminList title={tr('Фоновые задачи')} kicker={items ? (bad ? tr('С ошибкой: {n}', { n: bad }) : tr('Всё идёт по плану')) : ' '} items={items} keyOf={(j) => j.name} onRefresh={load}
      empty={tr('За неделю задач не было')}
      render={(j) => (
        <View style={[adm.card, j.error && adm.bad]}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
            <Text style={adm.title} numberOfLines={1}>{j.name}</Text>
            <Text style={adm.meta}>{j.at ? timeAgo(j.at) : ''}</Text>
          </View>
          <Text style={adm.text}>{j.done > 0 ? tr('Сделано: {n}', { n: j.done }) : tr('Ничего не понадобилось')}</Text>
          {!!j.reason && <Text style={[adm.meta, j.error && { color: '#C0392B' }]}>{j.reason}</Text>}
        </View>
      )} />
  )
}
