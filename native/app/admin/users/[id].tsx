import { mediaUrl } from '../../../src/config'
import { Image } from 'expo-image'
import { router } from 'expo-router'
import { formatPrice } from '../../../src/format'
import Segmented from '../../../src/components/Segmented'
import { useLocalSearchParams } from 'expo-router'
import * as Linking from 'expo-linking'
import { useEffect, useState } from 'react'
import { Alert, ScrollView, StyleSheet, Switch, Text, View } from 'react-native'
import Pressable from '../../../src/components/Pressable'
import { type AuditItem, adminDeleteUser, adminUserAudit, adminUserListings, type UserListing, adminBlock, adminResetName, adminSetRole, adminUnblock, type AdminUser, adminUser, adminUserLogins, adminUserSummary, adminVerify, type Login, type UserSummary } from '../../../src/admin'
import { useAuth } from '../../../src/auth'
import { timeAgo } from '../../../src/format'
import { tr } from '../../../src/i18n'
import { Header } from '../../../src/components/Kit'
import Icon from '../../../src/components/Icon'
import Skeleton from '../../../src/components/Skeleton'
import { TINTS } from '../../../src/tints'
import { colors, font } from '../../../src/theme'

const STATUS_LABEL: Record<string, string> = { active: 'В ленте', pending_moderation: 'На проверке', rejected: 'Отклонено', sold: 'Продано', archived: 'В архиве', draft: 'Черновик' }
const AUDIT_LABEL: Record<string, string> = { 'user.block': 'Заблокировал', 'user.unblock': 'Разблокировал', 'user.role': 'Сменил роль', 'user.verify': 'Галочка «Проверен»', 'user.reset_name': 'Сбросил имя', 'listing.approve': 'Одобрил объявление', 'listing.reject': 'Отклонил объявление', 'listing.delete': 'Удалил объявление', 'listing.move': 'Перенёс в раздел' }
const ROLES = ['buyer', 'seller', 'seller_business', 'moderator', 'admin']
const ROLE: Record<string, string> = { admin: 'Владелец', moderator: 'Модератор', seller_business: 'Компания', buyer: 'Покупатель', seller: 'Продавец' }

/** Пользователь — как на сайте: карточка человека, контакты с действием, цифры, управление и опасная зона внизу. */
export default function UserScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { token, user: me } = useAuth()
  const [u, setU] = useState<AdminUser | null>(null)
  const [busy, setBusy] = useState(false)
  const [sum, setSum] = useState<UserSummary | null>(null)
  const [logins, setLogins] = useState<Login[] | null>(null)
  const [listings, setListings] = useState<UserListing[] | null>(null)
  const [history, setHistory] = useState<AuditItem[] | null>(null)
  const [lsTab, setLsTab] = useState<'active' | 'other'>('active')
  const load = () => {
    if (!token) return
    adminUser(token, id).then(setU).catch(() => {})
    adminUserSummary(token, id).then(setSum).catch(() => {})
    adminUserLogins(token, id).then((r) => setLogins(r.items)).catch(() => setLogins([]))
    adminUserListings(token, id).then((r) => setListings(r.items)).catch(() => setListings([]))
    adminUserAudit(token, id).then((r) => setHistory(r.items)).catch(() => setHistory([]))
  }
  useEffect(load, [token, id]) // eslint-disable-line react-hooks/exhaustive-deps
  const canEdit = me?.role === 'admin'
  const act = async (fn: () => Promise<unknown>) => { setBusy(true); try { await fn(); load() } catch { Alert.alert(tr('Не получилось')) } finally { setBusy(false) } }
  if (!u) return <View style={st.page}><Header title={tr('Пользователь')} fallback="/admin/users" /><View style={{ padding: 16, gap: 12 }}><Skeleton style={{ height: 200, borderRadius: 28 }} /><Skeleton style={{ height: 110, borderRadius: 22 }} /></View></View>
  const name = u.company_name || u.display_name || '—'
  return (
    <View style={st.page}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 60, gap: 12 }}>
        <Header bleed={16} bleedTop={16} title={tr('Пользователь')} fallback="/admin/users" />
        <View style={st.card}>
          <View style={[st.ava, { overflow: 'hidden' }]}>{u.avatar_url ? <Image source={{ uri: mediaUrl(u.avatar_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" /> : <Text style={st.avaT}>{name.slice(0, 1).toUpperCase()}</Text>}</View>
          <Text style={st.name}>{name}</Text>
          <View style={st.badges}>
            <Text style={st.badge}>{tr(ROLE[u.role] || u.role)}</Text>
            {u.document_verified && <Text style={[st.badge, st.ok]}>✓ {tr('Проверен')}</Text>}
            {u.is_blocked && <Text style={[st.badge, st.bad]}>{tr('Заблокирован')}</Text>}
          </View>
          <Text style={st.when}>{tr('зарег.')} {timeAgo(u.created_at)} · {u.last_seen_at ? `${tr('был')} ${timeAgo(u.last_seen_at)}` : tr('не заходил')}</Text>
        </View>

        <View style={st.group}>
          <Row icon="mail" label={tr('Почта')} value={u.email || '—'} go={u.email ? () => Linking.openURL(`mailto:${u.email}`) : undefined} goLabel={tr('Написать')} />
          <Row icon="phone" label={tr('Телефон')} value={u.phone || '—'} go={u.phone ? () => Linking.openURL(`tel:${u.phone}`) : undefined} goLabel={tr('Позвонить')} last />
        </View>

        <View style={{ flexDirection: 'row', gap: 8 }}>
          {([[u.listings_active ?? 0, tr('в ленте'), TINTS['real-estate']], [u.listings ?? 0, tr('всего'), TINTS.auto], [u.rating_count ?? 0, tr('отзывов'), TINTS.fashion]] as [number, string, string][]).map(([n, l, bg]) => (
            <View key={l} style={[st.stat, { backgroundColor: bg }]}><Text style={st.statN}>{n}</Text><Text style={st.statL}>{l}</Text></View>
          ))}
        </View>

        {!!u.block_reason && <Text style={st.alert}>{tr('Причина блокировки')}: {u.block_reason}</Text>}
        {/* подозрительное — как на сайте */}
        {!!sum?.listings_suspicious && <Text style={st.warn}>{tr('За сутки объявлений: {n}, учётной записи {d} дн. — стоит посмотреть внимательнее.', { n: sum.listings_last_day, d: sum.account_age_days })}</Text>}
        {!!sum?.device_changed && (sum.country_changed || sum.isp_changed) && <Text style={st.warn}>{tr('Резко сменились и устройство, и страна разом (последний вход — {where}) — похоже, аккаунтом пользуется кто-то другой.', { where: sum.last_city ? `${sum.last_city}, ${sum.last_country}` : (sum.last_country || '—') })}</Text>}
        {/* объявления человека — как на сайте: в ленте / остальные (на проверке, отклонённые, проданные, в архиве) */}
        <Text style={st.sec}>{tr('Объявления')}{listings ? ` · ${listings.length}` : ''}</Text>
        {!listings ? <Skeleton style={{ height: 120, borderRadius: 22 }} /> : listings.length === 0 ? <Text style={st.rowS}>{tr('Объявлений нет')}</Text> : (
          <>
            <Segmented options={[{ key: 'active', label: `${tr('В ленте')} ${listings.filter((l) => l.status === 'active').length}` }, { key: 'other', label: `${tr('Остальные')} ${listings.filter((l) => l.status !== 'active').length}` }]} value={lsTab} onChange={(v) => setLsTab(v as 'active' | 'other')} />
            <View style={st.group}>
              {listings.filter((l) => (lsTab === 'active') === (l.status === 'active')).slice(0, 50).map((l, i, arr) => (
                <Pressable key={l.id} style={[st.row, i === arr.length - 1 && { borderBottomWidth: 0 }]} onPress={() => router.push(`/listing/${l.id}` as never)}>
                  <View style={{ flex: 1, minWidth: 0 }}>
                    <Text style={st.rowT} numberOfLines={1}>{l.title || tr('Без названия')}</Text>
                    <Text style={st.rowS}>{tr(STATUS_LABEL[l.status] || l.status)}{l.created_at ? ` · ${timeAgo(l.created_at)}` : ''}</Text>
                  </View>
                  <Text style={st.rowV}>{l.price != null ? formatPrice(l.price, l.currency || 'RSD') : ''}</Text>
                </Pressable>
              ))}
            </View>
          </>
        )}
        {/* что команда уже делала с этим человеком */}
        {!!history && history.length > 0 && (
          <>
            <Text style={st.sec}>{tr('Действия команды')}</Text>
            <View style={st.group}>
              {history.slice(0, 15).map((a, i, arr) => (
                <View key={a.id} style={[st.row, i === arr.length - 1 && { borderBottomWidth: 0 }]}>
                  <View style={{ flex: 1 }}>
                    <Text style={st.rowT}>{tr(AUDIT_LABEL[a.action] || a.action)}</Text>
                    <Text style={st.rowS}>{a.actor} · {timeAgo(a.created_at)}{a.reason ? ` · ${a.reason}` : ''}</Text>
                  </View>
                </View>
              ))}
            </View>
          </>
        )}
        {/* последние входы: когда, откуда, адрес, устройство */}
        {!!logins && logins.length > 0 && (
          <>
            <Text style={st.sec}>{tr('Входы')}</Text>
            <View style={st.group}>
              {logins.slice(0, 10).map((l, i) => (
                <View key={l.id} style={[st.row, i === Math.min(logins.length, 10) - 1 && { borderBottomWidth: 0 }]}>
                  <View style={{ flex: 1 }}>
                    <Text style={st.rowT}>{l.city ? `${l.city}, ${l.country}` : (l.country || '—')}</Text>
                    <Text style={st.rowS}>{l.created_at ? timeAgo(l.created_at) : '—'} · {l.ip_address || '—'} · {l.device_guid ? l.device_guid.slice(0, 8) : '—'}</Text>
                  </View>
                </View>
              ))}
            </View>
          </>
        )}

        {canEdit && (
          <>
            <Text style={st.sec}>{tr('Управление')}</Text>
            <View style={st.group}>
              <Pressable style={st.row} disabled={busy} onPress={() => Alert.alert(tr('Роль'), undefined, [...ROLES.map((r) => ({ text: tr(ROLE[r]), onPress: () => act(() => adminSetRole(token!, u.id, r)) })), { text: tr('Отмена'), style: 'cancel' as const }])}>
                <View style={st.ico}><Icon name="user" size={18} color={colors.ink} /></View>
                <Text style={st.rowT}>{tr('Роль')}</Text>
                <Text style={st.rowV}>{tr(ROLE[u.role] || u.role)}</Text>
              </Pressable>
              <View style={[st.row, { borderBottomWidth: 0 }]}>
                <View style={st.ico}><Icon name="shield" size={18} color={colors.ink} /></View>
                <View style={{ flex: 1 }}><Text style={st.rowT}>{tr('Галочка «Проверен»')}</Text><Text style={st.rowS}>{tr('Ставьте, когда проверили личность сами')}</Text></View>
                <Switch value={!!u.document_verified} disabled={busy} onValueChange={(v) => act(() => adminVerify(token!, u.id, v))} trackColor={{ true: colors.primary, false: colors.sunken }} />
              </View>
            </View>
            <Pressable style={[st.group, st.row, { borderBottomWidth: 0, marginTop: 8 }]} disabled={busy} onPress={() => Alert.alert(tr('Сбросить имя?'), tr('Имя заменится нейтральным, человек должен будет придумать новое.'), [
              { text: tr('Отмена'), style: 'cancel' },
              { text: tr('Сбросить'), style: 'destructive', onPress: () => act(() => adminResetName(token!, u.id)) },
            ])}>
              <View style={st.ico}><Icon name="edit" size={18} color={colors.ink} /></View>
              <View style={{ flex: 1 }}><Text style={st.rowT}>{tr('Сбросить имя')}</Text><Text style={st.rowS}>{tr('Если имя оскорбительное или чужое')}</Text></View>
            </Pressable>
            <Text style={[st.sec, { color: colors.danger }]}>{tr('Опасная зона')}</Text>
            <View style={st.group}>
              {u.is_blocked ? (
                <Pressable style={[st.row, { borderBottomWidth: 0 }]} disabled={busy} onPress={() => act(() => adminUnblock(token!, u.id))}><Text style={st.rowT}>{tr('Разблокировать')}</Text></Pressable>
              ) : (
                <Pressable style={[st.row, { borderBottomWidth: 0 }]} disabled={busy} onPress={() => Alert.alert(tr('Заблокировать?'), tr('Не сможет входить и писать; объявления скроются.'), [
                  { text: tr('Отмена'), style: 'cancel' },
                  { text: tr('Мошенничество'), style: 'destructive', onPress: () => act(() => adminBlock(token!, u.id, tr('Мошенничество'))) },
                  { text: tr('Спам'), style: 'destructive', onPress: () => act(() => adminBlock(token!, u.id, tr('Спам'))) },
                ])}>
                  <View style={{ flex: 1 }}><Text style={[st.rowT, { color: colors.danger }]}>{tr('Заблокировать')}</Text><Text style={st.rowS}>{tr('Не сможет входить и писать; объявления скроются')}</Text></View>
                </Pressable>
              )}
              <Pressable style={[st.row, { borderBottomWidth: 0, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border }]} disabled={busy} onPress={() => Alert.alert(tr('Удалить пользователя?'), tr('Аккаунт и его объявления удалятся. Это нельзя отменить.'), [
                { text: tr('Отмена'), style: 'cancel' },
                { text: tr('Удалить'), style: 'destructive', onPress: () => { setBusy(true); adminDeleteUser(token!, u.id).then(() => router.back()).catch(() => Alert.alert(tr('Не получилось'))).finally(() => setBusy(false)) } },
              ])}>
                <View style={{ flex: 1 }}><Text style={[st.rowT, { color: colors.danger }]}>{tr('Удалить пользователя')}</Text><Text style={st.rowS}>{tr('Аккаунт и его объявления удалятся навсегда')}</Text></View>
              </Pressable>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  )
}

function Row({ icon, label, value, go, goLabel, last }: { icon: string; label: string; value: string; go?: () => void; goLabel: string; last?: boolean }) {
  return (
    <View style={[st.row, last && { borderBottomWidth: 0 }]}>
      <View style={st.ico}><Icon name={icon} size={18} color={colors.ink} /></View>
      <View style={{ flex: 1, minWidth: 0 }}><Text style={st.rowS}>{label}</Text><Text style={st.rowT} numberOfLines={1}>{value}</Text></View>
      {!!go && <Pressable style={st.go} onPress={go}><Text style={st.goT}>{goLabel}</Text></Pressable>}
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  card: { alignItems: 'center', gap: 8, padding: 22, borderRadius: 28, backgroundColor: colors.surface },
  ava: { width: 84, height: 84, borderRadius: 42, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', borderWidth: 4, borderColor: colors.bg },
  avaT: { fontFamily: font[800], fontSize: 34, color: '#FFFFFF' },
  name: { fontFamily: font[800], fontSize: 24, letterSpacing: -0.6, color: colors.ink, textAlign: 'center' },
  badges: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 6 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10, overflow: 'hidden', backgroundColor: colors.sunken, fontFamily: font[800], fontSize: 12.5, color: colors.inkSoft },
  ok: { backgroundColor: colors.primarySoft, color: colors.primaryDeep },
  bad: { backgroundColor: colors.dangerBg, color: colors.danger },
  when: { fontFamily: font[600], fontSize: 13, color: colors.muted },
  group: { borderRadius: 22, backgroundColor: colors.surface, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 58, paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  ico: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  rowT: { flex: 1, fontFamily: font[700], fontSize: 15.5, color: colors.ink },
  rowS: { fontFamily: font[600], fontSize: 12.5, color: colors.muted },
  rowV: { fontFamily: font[700], fontSize: 14, color: colors.inkSoft },
  go: { height: 34, paddingHorizontal: 14, borderRadius: 17, backgroundColor: colors.inverse, justifyContent: 'center' },
  goT: { fontFamily: font[800], fontSize: 13, color: colors.onInverse },
  stat: { flex: 1, minHeight: 80, padding: 12, borderRadius: 20, justifyContent: 'flex-end' },
  statN: { fontFamily: font[800], fontSize: 24, color: colors.ink },
  statL: { fontFamily: font[700], fontSize: 12, color: colors.inkSoft },
  warn: { padding: 12, borderRadius: 16, backgroundColor: colors.warmBg, color: colors.ink, fontFamily: font[600], fontSize: 13.5, lineHeight: 19 },
  alert: { padding: 12, borderRadius: 16, backgroundColor: colors.dangerBg, color: colors.danger, fontFamily: font[600], fontSize: 14 },
  sec: { fontFamily: font[800], fontSize: 13, letterSpacing: 0.6, textTransform: 'uppercase', color: colors.muted, marginTop: 8, marginLeft: 4 },
})
