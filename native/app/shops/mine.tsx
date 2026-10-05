import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type MyListing, myListings } from '../../src/api'
import { useAuth } from '../../src/auth'
import { mediaUrl } from '../../src/config'
import { tr } from '../../src/i18n'
import { Btn, Empty, Field, Header, k, Tabs } from '../../src/components/Kit'
import { creatorApply, money, type Order, type Shop, shopOrderCancel, shopOrderCreate, shopOrders, shopOrderTake, shopRemove, shopsMine } from '../../src/social'
import { colors, font } from '../../src/theme'

const ST: Record<string, [string, string, string]> = {
  processing: ['Обрабатывается', colors.warmBg, colors.goldDark], draft: ['Черновик', colors.sunken, colors.inkSoft], moderation: ['На проверке', colors.warmBg, colors.goldDark],
  active: ['Опубликован', colors.primarySoft, colors.primaryDeep], rejected: ['Отклонён', colors.dangerBg, '#A33232'], failed: ['Ошибка видео', colors.dangerBg, '#A33232'],
}
const OST: Record<string, string> = { open: 'ищет автора', taken: 'в работе', done: 'готов', cancelled: 'отменён' }

/** Мои шопсы со статистикой, биржа заказов и заявка на «Автора» — как на сайте. */
export default function ShopsCabinet() {
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const params = useLocalSearchParams<{ tab?: string }>()
  const [tab, setTab] = useState<'shops' | 'orders' | 'creator'>(params.tab === 'creator' || params.tab === 'orders' ? params.tab : 'shops')
  const [data, setData] = useState<{ items: Shop[]; creator: { status: string | null } } | null>(null)
  const reload = useCallback(() => { if (token) shopsMine(token).then(setData).catch(() => setData({ items: [], creator: { status: null } })) }, [token])
  useEffect(() => { if (!token) router.replace('/login'); else reload() }, [token, reload])
  const creator = data?.creator?.status ?? null
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Header title={tr('Шопсы')} right={<Btn small label={tr('Снять шопс')} onPress={() => router.push('/shops/new' as never)} />} />
      <ScrollView contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: insets.bottom + 32 }} keyboardShouldPersistTaps="handled">
        <Tabs value={tab} onChange={setTab} items={[{ key: 'shops', label: tr('Мои шопсы') }, { key: 'orders', label: tr('Заказы') }, { key: 'creator', label: tr('Автор') }]} />
        {tab === 'shops' && <MyShops data={data} reload={reload} />}
        {tab === 'orders' && <Orders creator={creator === 'approved'} />}
        {tab === 'creator' && <Creator status={creator} onDone={reload} />}
      </ScrollView>
    </View>
  )
}

function MyShops({ data, reload }: { data: { items: Shop[] } | null; reload: () => void }) {
  const { token } = useAuth()
  if (!data) return <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} />
  if (!data.items.length) return <Empty text={tr('У вас пока нет шопсов')}><Btn label={tr('Снимите первый шопс')} onPress={() => router.push('/shops/new' as never)} /></Empty>
  return data.items.map((sh) => {
    const [label, bg, fg] = ST[sh.status] ?? ST.draft
    return (
      <View key={sh.id} style={[k.card, { flexDirection: 'row', gap: 12, padding: 10 }]}>
        <View style={s.poster}>{!!sh.poster_url && <Image source={{ uri: mediaUrl(sh.poster_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}</View>
        <View style={{ flex: 1 }}>
          <View style={[k.status, { backgroundColor: bg }]}><Text style={[k.statusText, { color: fg }]}>{tr(label)}</Text></View>
          <Text style={[k.name, { marginTop: 6 }]} numberOfLines={2}>{sh.caption || tr('Без подписи')}</Text>
          {sh.status === 'rejected' && !!sh.reject_reason && <Text style={k.err}>{sh.reject_reason}</Text>}
          {!!sh.stats && <Text style={[k.muted, { marginTop: 6 }]}>👁 {sh.stats.views}   ✓ {sh.stats.completes}   👆 {sh.stats.taps}   💬 {sh.stats.chats}</Text>}
          <View style={k.actions}>
            {sh.status === 'active' && <Btn small kind="ghost" label={tr('Смотреть')} onPress={() => router.push(`/shops?start=${sh.id}` as never)} />}
            {sh.status !== 'processing' && <Btn small kind="ghost" label={tr('Изменить')} onPress={() => router.push(`/shops/new?id=${sh.id}` as never)} />}
            <Btn small kind="danger" label={tr('Удалить')} onPress={() => Alert.alert(tr('Удалить шопс?'), '', [{ text: tr('Отмена'), style: 'cancel' }, { text: tr('Удалить'), style: 'destructive', onPress: () => { if (token) shopRemove(token, sh.id).then(reload) } }])} />
          </View>
        </View>
      </View>
    )
  })
}

function Orders({ creator }: { creator: boolean }) {
  const { token } = useAuth()
  const [open, setOpen] = useState<Order[] | null>(null)
  const [taken, setTaken] = useState<Order[]>([])
  const [mine, setMine] = useState<Order[]>([])
  const [listings, setListings] = useState<MyListing[]>([])
  const [form, setForm] = useState({ listing_id: '', fee: '', currency: 'EUR', note: '' })
  const [err, setErr] = useState('')
  const reload = useCallback(() => {
    if (!token) return
    shopOrders(token, 'mine').then((r) => setMine(r.items)).catch(() => {})
    if (creator) {
      shopOrders(token, 'open').then((r) => setOpen(r.items)).catch(() => setOpen([]))
      shopOrders(token, 'taken').then((r) => setTaken(r.items)).catch(() => {})
    }
  }, [token, creator])
  useEffect(() => { reload(); if (token) myListings(token).then((r) => setListings(r.items.filter((l) => l.status === 'active'))).catch(() => {}) }, [reload, token])

  const create = async () => {
    if (!token) return
    if (!form.listing_id) { setErr(tr('Выберите объявление')); return }
    setErr('')
    try { await shopOrderCreate(token, { ...form, fee: form.fee ? Number(form.fee) : null }); setForm({ listing_id: '', fee: '', currency: 'EUR', note: '' }); reload() } catch (e) {
      setErr((e as { message?: string }).message === 'order_exists' ? tr('На это объявление заказ уже есть') : tr('Не получилось сохранить'))
    }
  }
  const card = (o: Order, actions: React.ReactNode) => (
    <View key={o.id} style={[k.card, { flexDirection: 'row', gap: 10, padding: 10 }]}>
      {!!o.listing?.photo && <Image source={{ uri: mediaUrl(o.listing.photo) ?? undefined }} style={k.thumb} />}
      <View style={{ flex: 1 }}>
        <Text style={k.name} numberOfLines={1}>{o.listing?.title}</Text>
        <Text style={k.muted}>{o.fee ? tr('Оплата: {v}', { v: money(o.fee, o.currency) }) : tr('Оплата по договорённости')} · {tr(OST[o.status] ?? o.status)}</Text>
        {!!o.note && <Text style={[k.body, { fontSize: 14, marginTop: 6 }]}>{o.note}</Text>}
        <View style={k.actions}>{actions}</View>
      </View>
    </View>
  )
  return (
    <>
      <Text style={k.section}>{tr('Заказать шопс у автора')}</Text>
      <Text style={k.hint}>{tr('Авторы снимут ролик про ваше объявление. Об оплате договариваетесь в чате и рассчитываетесь напрямую — PLONK покажет вам статистику ролика')}</Text>
      <Text style={k.fieldLabel}>{tr('Объявление')}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingVertical: 8 }}>
        {listings.map((l) => (
          <Pressable key={l.id} style={[s.lst, form.listing_id === l.id && { borderColor: colors.primary }]} onPress={() => setForm({ ...form, listing_id: l.id })}>
            {!!l.cover_photo && <Image source={{ uri: mediaUrl(l.cover_photo) ?? undefined }} style={s.lstImg} />}
            <Text style={s.lstText} numberOfLines={2}>{l.title}</Text>
          </Pressable>
        ))}
      </ScrollView>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}><Field label={tr('Готовы заплатить')} value={form.fee} keyboardType="number-pad" placeholder="0" onChangeText={(v) => setForm({ ...form, fee: v.replace(/\D/g, '').slice(0, 7) })} /></View>
        <View style={{ justifyContent: 'flex-end', paddingBottom: 12 }}><Tabs value={form.currency} onChange={(c) => setForm({ ...form, currency: c })} items={[{ key: 'EUR', label: '€' }, { key: 'RSD', label: 'RSD' }]} /></View>
      </View>
      <Field label={tr('Что показать')} value={form.note} multiline maxLength={1000} placeholder={tr('Например: диван в интерьере, как раскладывается')} onChangeText={(v) => setForm({ ...form, note: v })} />
      {!!err && <Text style={k.err}>{err}</Text>}
      <Btn wide label={tr('Разместить заказ')} onPress={create} />
      {mine.length > 0 && <Text style={k.section}>{tr('Мои заказы')}</Text>}
      {mine.map((o) => card(o, <>
        {!!o.creator && <Text style={k.muted}>{tr('Взял: {name}', { name: o.creator.name })}</Text>}
        {(o.status === 'open' || o.status === 'taken') && <Btn small kind="danger" label={tr('Отменить')} onPress={() => token && shopOrderCancel(token, o.id).then(reload)} />}
      </>))}
      {creator && (
        <>
          {taken.length > 0 && <Text style={k.section}>{tr('Я снимаю')}</Text>}
          {taken.map((o) => card(o, o.status === 'taken' ? <>
            <Btn small label={tr('Снять шопс')} onPress={() => router.push(`/shops/new?order=${o.id}` as never)} />
            <Btn small kind="ghost" label={tr('Отказаться')} onPress={() => token && shopOrderCancel(token, o.id).then(reload)} />
          </> : null))}
          <Text style={k.section}>{tr('Заказы продавцов')}</Text>
          {open === null ? <ActivityIndicator color={colors.primary} /> : !open.length ? <Text style={k.hint}>{tr('Свободных заказов пока нет')}</Text>
            : open.map((o) => card(o, <Btn small label={tr('Взять заказ')} onPress={() => token && shopOrderTake(token, o.id).then((r) => router.push(`/chat/${r.chat_id}` as never)).catch(reload)} />))}
        </>
      )}
    </>
  )
}

function Creator({ status, onDone }: { status: string | null; onDone: () => void }) {
  const { token } = useAuth()
  const [form, setForm] = useState({ links: '', audience: '', about: '' })
  const [err, setErr] = useState('')
  if (status === 'approved') return <View style={[k.card, { backgroundColor: colors.primarySoft, borderColor: 'transparent' }]}><Text style={[k.body, { color: colors.primaryDeep }]}>🎬 {tr('Вы — автор. Можно прикреплять любые объявления и брать заказы продавцов')}</Text></View>
  if (status === 'pending') return <View style={k.card}><Text style={k.body}>⏳ {tr('Заявка на проверке — ответим уведомлением')}</Text></View>
  const send = async () => {
    if (!token) return
    if (form.links.trim().length < 5) { setErr(tr('Укажите хотя бы одну ссылку')); return }
    try { await creatorApply(token, { links: form.links, about: form.about, audience: form.audience ? Number(form.audience) : null }); onDone() } catch { setErr(tr('Не получилось сохранить')) }
  }
  return (
    <>
      <View style={k.card}><Text style={k.body}>{status === 'rejected' ? tr('Прошлую заявку не одобрили — можно подать снова') : tr('Автор прикрепляет к шопсам любые объявления PLONK и берёт заказы продавцов. Расскажите о себе')}</Text></View>
      <Field label={tr('Ваши страницы')} value={form.links} autoCapitalize="none" placeholder="instagram.com/…, t.me/…" onChangeText={(v) => setForm({ ...form, links: v })} />
      <Field label={tr('Подписчиков')} value={form.audience} keyboardType="number-pad" onChangeText={(v) => setForm({ ...form, audience: v.replace(/\D/g, '').slice(0, 9) })} />
      <Field label={tr('О чём снимаете')} value={form.about} multiline onChangeText={(v) => setForm({ ...form, about: v })} />
      {!!err && <Text style={k.err}>{err}</Text>}
      <Btn wide label={tr('Отправить заявку')} onPress={send} />
    </>
  )
}

const s = StyleSheet.create({
  poster: { width: 76, height: 116, borderRadius: 12, overflow: 'hidden', backgroundColor: '#1c2620' },
  lst: { width: 110, padding: 6, borderRadius: 12, borderWidth: 2, borderColor: 'transparent', backgroundColor: colors.surface },
  lstImg: { width: '100%', height: 80, borderRadius: 8, backgroundColor: colors.photo },
  lstText: { marginTop: 4, fontFamily: font[600], fontSize: 12, color: colors.ink },
})
