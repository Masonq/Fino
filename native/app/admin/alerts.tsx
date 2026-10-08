import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, Text } from 'react-native'
import { type Alert, adminAlerts } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { tr } from '../../src/i18n'
import AdminList, { adm } from '../../src/components/AdminList'

const TEXT: Record<string, (a: Alert) => [string, string]> = {
  queue_stale: (a) => [tr('Очередь модерации стоит {n} ч', { n: a.count }), tr('Открыть модерацию')],
  same_ip: (a) => [tr('{n} регистраций с одного адреса', { n: a.count }), tr('За сутки, похоже на пачку аккаунтов')],
  many_rejected: (a) => [tr('{v}: {n} отклонено за сутки', { v: a.value || '', n: a.count }), tr('Открыть карточку человека')],
  photo_reuse: (a) => [tr('Одни фото у {n} разных людей', { n: a.count }), tr('Перепродажа чужих объявлений или смена аккаунтов')],
}
const LINK: Record<string, (a: Alert) => string | null> = {
  queue_stale: () => '/admin/moderation', many_rejected: (a) => (a.user_id ? `/admin/users/${a.user_id}` : null), photo_reuse: (a) => (a.listing_id ? `/listing/${a.listing_id}` : null),
}

/** Тревоги — то, что требует внимания команды прямо сейчас; нажатие ведёт туда, где это разбирать. */
export default function Alerts() {
  const { token } = useAuth()
  const [items, setItems] = useState<Alert[] | null>(null)
  const load = () => { if (token) adminAlerts(token).then((r) => setItems(r.items)).catch(() => setItems([])) }
  useEffect(load, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <AdminList title={tr('Тревоги')} items={items} keyOf={(a) => a.kind + (a.user_id || a.listing_id || '')} onRefresh={load}
      empty={tr('Всё спокойно')} emptyHint={tr('Новое появится здесь сразу.')}
      render={(a) => {
        const [title, hint] = (TEXT[a.kind] || (() => [a.kind, '']))(a)
        const to = LINK[a.kind]?.(a)
        return (
          <Pressable style={[adm.card, a.level === 'danger' && adm.bad]} disabled={!to} onPress={() => to && router.push(to as never)}>
            <Text style={adm.title}>{title}</Text>
            {!!hint && <Text style={adm.meta}>{hint}</Text>}
          </Pressable>
        )
      }} />
  )
}
