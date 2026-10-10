import { router } from 'expo-router'
import Segmented from '../../src/components/Segmented'
import { Image } from 'expo-image'
import * as Haptics from 'expo-haptics'
import { useCallback, useEffect, useState } from 'react'
import { Alert, FlatList, ScrollView, StyleSheet, Text, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { modBulk, type ModDay, type ModItem, modApprove, modMyDay, modQueue, modReject, type Report, reportsQueue, resolveReport } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { mediaUrl } from '../../src/config'
import { formatPrice } from '../../src/format'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Skeleton from '../../src/components/Skeleton'
import { colors, font, tint } from '../../src/theme'

const REPORT_REASON: Record<string, string> = { fraud: 'Мошенничество', prohibited_item: 'Запрещённый товар', spam: 'Спам', duplicate: 'Дубликат', wrong_category: 'Не та категория', other: 'Другое', offensive_user: 'Оскорбительное поведение' }
const REASONS = ['Непонятный заголовок', 'Плохие или чужие фото', 'Запрещённый товар', 'Дубль объявления', 'Не тот раздел']

/** Модерация — как на сайте: крупная лента фото, название, цена, продавец, «Одобрить» / «Отклонить» с причиной. */
export default function Moderation() {
  const { token } = useAuth()
  const [items, setItems] = useState<ModItem[] | null>(null)
  const load = useCallback(() => { if (token) modQueue(token).then((r) => setItems(r.items)).catch(() => setItems([])) }, [token])
  useEffect(() => { load() }, [load])
  const drop = (id: string) => setItems((p) => (p ?? []).filter((x) => x.id !== id))
  // как на сайте: вкладки «Объявления / Жалобы» и цифры дня плитками
  const [tab, setTab] = useState<'listings' | 'reports'>('listings')
  // выбор нескольких — массовое решение, как на сайте
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const toggle = (id: string) => setPicked((p) => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const bulk = (approve: boolean, reason?: string) => {
    if (!token || !picked.size) return
    const ids = [...picked]
    setItems((p) => (p ?? []).filter((x) => !picked.has(x.id))); setPicked(new Set())
    modBulk(token, ids, approve, reason).catch(() => load())
  }
  const [reports, setReports] = useState<Report[] | null>(null)
  const [day, setDay] = useState<ModDay | null>(null)
  useEffect(() => {
    if (!token) return
    reportsQueue(token).then((r) => setReports(r.items)).catch(() => setReports([]))
    modMyDay(token).then(setDay).catch(() => {})
  }, [token])
  const resolve = (r: Report, action: 'dismiss' | 'block_listing' | 'block_user') => {
    if (!token) return
    setReports((x) => (x ?? []).filter((y) => y.id !== r.id))
    resolveReport(token, r.id, action).catch(() => reportsQueue(token).then((q) => setReports(q.items)).catch(() => {}))
  }
  const head = (
    <View style={{ gap: 10 }}>
      <Header bleed={16} bleedTop={16} title={tr('Модерация')} kicker={items ? (items.length ? tr('{n} ждут проверки', { n: items.length }) : tr('Очередь пуста')) : ' '} fallback="/admin" />
      <Segmented options={[{ key: 'listings', label: `${tr('Объявления')}${items?.length ? ` ${items.length}` : ''}` }, { key: 'reports', label: `${tr('Жалобы')}${reports?.length ? ` ${reports.length}` : ''}` }]} value={tab} onChange={(v) => setTab(v as 'listings' | 'reports')} />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {([[day ? day.mine.approved + day.mine.rejected : '—', tr('мои за сутки'), tint('#E2F1E6')], [day ? day.team.approved + day.team.rejected : '—', tr('всего за сутки'), tint('#E3ECFA')],
          [day?.oldest_waiting_hours != null ? (day.oldest_waiting_hours < 1 ? '<1' : Math.round(day.oldest_waiting_hours)) : '—', tr('ч ждёт старейшее'), tint('#FAE5EE')]] as [string | number, string, string][]).map(([n, l, bg], i) => (
          <View key={l} style={[styles.dayTile, { backgroundColor: bg }]}><Text style={[styles.dayN, i === 2 && Number(n) >= 24 && { color: '#C0392B' }]}>{n}</Text><Text style={styles.dayL}>{l}</Text></View>
        ))}
      </View>
    </View>
  )
  const approve = (it: ModItem) => { if (!token) return; Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {}); drop(it.id); modApprove(token, it.id).catch(load) }
  const reject = (it: ModItem) => {
    if (!token) return
    Alert.alert(tr('Причина отказа'), undefined, [...REASONS.map((r) => ({ text: tr(r), onPress: () => { drop(it.id); modReject(token, it.id, tr(r)).catch(load) } })), { text: tr('Отмена'), style: 'cancel' as const }])
  }
  return (
    <View style={styles.page}>
      {!items ? <View style={{ padding: 16, gap: 12 }}><Skeleton style={{ height: 380, borderRadius: 24 }} /></View> : (
        <FlatList
          ListHeaderComponent={head}
          data={(tab === 'listings' ? items : []) as ModItem[]}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 60 }}
          ListFooterComponent={tab === 'reports' ? (
            <View style={{ gap: 10 }}>
              {reports === null ? <Skeleton style={{ height: 120, borderRadius: 22 }} /> : reports.length === 0 ? (
                <View style={styles.calm}><Text style={styles.calmT}>{tr('Жалоб нет')}</Text></View>
              ) : reports.map((r) => (
                <View key={r.id} style={styles.repCard}>
                  <Text style={styles.repReason}>{tr(REPORT_REASON[r.reason] || r.reason)}{(r.same_target_count ?? 1) > 1 ? ` · ${tr('жалоб: {n}', { n: r.same_target_count ?? 1 })}` : ''}</Text>
                  <Pressable disabled={!r.listing_id && !r.target_user_id} onPress={() => router.push((r.listing_id ? `/listing/${r.listing_id}` : `/admin/users/${r.target_user_id}`) as never)}>
                    <Text style={styles.title}>{r.listing_title || (r.target_user_name ? `${tr('На пользователя')}: ${r.target_user_name}` : '—')}</Text>
                  </Pressable>
                  {!!r.comment && <Text style={styles.desc}>{r.comment}</Text>}
                  <View style={styles.actions}>
                    <Pressable style={[styles.btn, styles.ok]} onPress={() => resolve(r, 'dismiss')}><Text style={styles.okT}>{tr('Отклонить жалобу')}</Text></Pressable>
                    {!!r.listing_id && <Pressable style={[styles.btn, styles.no]} onPress={() => resolve(r, 'block_listing')}><Text style={styles.noT}>{tr('Снять объявление')}</Text></Pressable>}
                    {!!r.target_user_id && <Pressable style={[styles.btn, styles.no]} onPress={() => resolve(r, 'block_user')}><Text style={styles.noT}>{tr('Заблокировать')}</Text></Pressable>}
                  </View>
                </View>
              ))}
            </View>
          ) : null}
          ListEmptyComponent={tab === 'reports' ? null : <View style={styles.calm}><Text style={styles.calmT}>{tr('Очередь пуста — всё проверено')}</Text></View>}
          renderItem={({ item }) => (
            <View style={[styles.card, picked.has(item.id) && styles.cardPicked]}>
              <Pressable style={[styles.pick, picked.has(item.id) && styles.pickOn]} onPress={() => toggle(item.id)} hitSlop={8} accessibilityLabel={tr('Выбрать')}>
                {picked.has(item.id) && <Text style={{ color: '#fff', fontWeight: '900', fontSize: 15 }}>✓</Text>}
              </Pressable>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6, padding: 10, paddingBottom: 0 }}>
                {item.photos.map((p) => <Image key={p} source={{ uri: mediaUrl(p) || p }} style={styles.photo} contentFit="cover" />)}
              </ScrollView>
              <View style={{ padding: 14, gap: 4 }}>
                {!!item.category_name && <Text style={styles.cat}>{item.category_name}</Text>}
                <Text style={styles.title}>{item.title || tr('Без названия')}</Text>
                <Text style={styles.price}>{formatPrice(item.price ?? null, item.currency)}</Text>
                {!!item.description && <Text style={styles.desc} numberOfLines={4}>{item.description}</Text>}
                <Text style={styles.meta}>{[item.city, item.owner_name, item.owner_verified ? tr('проверен') : null, tr('{n} в ленте', { n: item.owner_active ?? 0 }), item.owner_rejected ? tr('{n} отклонено', { n: item.owner_rejected }) : null].filter(Boolean).join(' · ')}</Text>
                {item.looks_duplicate && <Text style={styles.dup}>{tr('Похоже на дубль')}</Text>}
              </View>
              <View style={styles.actions}>
                <Pressable style={[styles.btn, styles.ok]} onPress={() => approve(item)}><Text style={styles.okT}>{tr('Одобрить')}</Text></Pressable>
                <Pressable style={[styles.btn, styles.no]} onPress={() => reject(item)}><Text style={styles.noT}>{tr('Отклонить')}</Text></Pressable>
              </View>
            </View>
          )}
        />
      )}
      {picked.size > 0 && tab === 'listings' && (
        <View style={styles.bulkBar}>
          <Text style={styles.bulkT}>{tr('Выбрано: {n}', { n: picked.size })}</Text>
          <Pressable style={[styles.btn, styles.ok, { flex: 0, paddingHorizontal: 16 }]} onPress={() => bulk(true)}><Text style={styles.okT}>{tr('Одобрить')}</Text></Pressable>
          <Pressable style={[styles.btn, styles.no, { flex: 0, paddingHorizontal: 16 }]} onPress={() => Alert.alert(tr('Причина отказа'), undefined, [...REASONS.map((r) => ({ text: tr(r), onPress: () => bulk(false, tr(r)) })), { text: tr('Отмена'), style: 'cancel' as const }])}><Text style={styles.noT}>{tr('Отклонить')}</Text></Pressable>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  cardPicked: { borderWidth: 2, borderColor: colors.primary },
  pick: { position: 'absolute', zIndex: 3, top: 16, right: 16, width: 30, height: 30, borderRadius: 15, borderWidth: 2, borderColor: 'rgba(15,21,18,0.25)', backgroundColor: 'rgba(255,255,255,0.92)', alignItems: 'center', justifyContent: 'center' },
  pickOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  bulkBar: { position: 'absolute', left: 12, right: 12, bottom: 28, flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10, borderRadius: 22, backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.18, shadowRadius: 18, shadowOffset: { width: 0, height: 8 }, elevation: 6 },
  bulkT: { flex: 1, fontFamily: font[800], fontSize: 14.5, color: colors.ink, paddingLeft: 6 },
  dayTile: { flex: 1, minHeight: 72, padding: 10, borderRadius: 16, justifyContent: 'flex-end' },
  dayN: { fontFamily: font[800], fontSize: 22, color: colors.ink },
  dayL: { fontFamily: font[700], fontSize: 11, color: colors.inkSoft },
  repCard: { padding: 14, borderRadius: 22, backgroundColor: colors.surface, gap: 6 },
  repReason: { fontFamily: font[800], fontSize: 12.5, color: colors.danger, textTransform: 'uppercase', letterSpacing: 0.4 },
  page: { flex: 1, backgroundColor: colors.bg },
  card: { borderRadius: 24, backgroundColor: colors.surface, overflow: 'hidden' },
  photo: { width: 160, height: 200, borderRadius: 16, backgroundColor: colors.sunken },
  cat: { fontFamily: font[700], fontSize: 12.5, color: colors.primaryDeep },
  title: { fontFamily: font[800], fontSize: 18, letterSpacing: -0.3, color: colors.ink },
  price: { fontFamily: font[800], fontSize: 17, color: colors.ink },
  desc: { fontFamily: font[400], fontSize: 14.5, lineHeight: 20, color: colors.inkSoft, marginTop: 2 },
  meta: { fontFamily: font[600], fontSize: 12.5, color: colors.muted, marginTop: 4 },
  dup: { alignSelf: 'flex-start', marginTop: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, overflow: 'hidden', backgroundColor: colors.dangerBg, color: colors.danger, fontFamily: font[800], fontSize: 12 },
  actions: { flexDirection: 'row', gap: 8, padding: 14, paddingTop: 4 },
  btn: { flex: 1, height: 50, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  ok: { backgroundColor: colors.primary },
  okT: { fontFamily: font[800], fontSize: 16, color: '#FFFFFF' },
  no: { backgroundColor: colors.dangerBg },
  noT: { fontFamily: font[800], fontSize: 16, color: colors.danger },
  calm: { padding: 20, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center' },
  calmT: { fontFamily: font[700], fontSize: 15, color: colors.inkSoft },
})
