import { tr } from '../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { balance as fetchBalance, deleteListing, type MyListing, myListings, setListingStatus } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import Segmented from '../src/components/Segmented'
import Sheet, { SheetAction } from '../src/components/Sheet'
import { mediaUrl } from '../src/config'
import { formatPrice } from '../src/format'
import { colors, font } from '../src/theme'

type Tab = 'active' | 'pending' | 'other'
const STATUS: Record<string, { label: string; tone: string; bg: string }> = {
  active: { label: 'Активно', tone: colors.primaryDeep, bg: colors.primarySoft },
  pending_moderation: { label: 'На проверке', tone: '#8A6A1F', bg: '#FBF3E3' },
  draft: { label: 'Черновик', tone: colors.inkSoft, bg: colors.sunken },
  sold: { label: 'Продано', tone: colors.inkSoft, bg: colors.sunken },
  archived: { label: 'В архиве', tone: colors.inkSoft, bg: colors.sunken },
  rejected: { label: 'Отклонено', tone: '#B42318', bg: '#FDECEA' },
}
const tabOf = (s: string): Tab => (s === 'active' ? 'active' : s === 'pending_moderation' ? 'pending' : 'other')
const rsd = (n: number) => `${String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')}\u00A0RSD`

/** Профиль: кто ты, баланс, мои объявления по вкладкам (активные / на проверке / другие), «Выйти». */
export default function MyListings() {
  const { user, ready, token } = useAuth()
  const [items, setItems] = useState<MyListing[] | null>(null)
  const [bal, setBal] = useState<{ balance?: number; money?: number; bonus?: number } | null>(null)
  const params = useLocalSearchParams<{ tab?: string }>()
  const insets = useSafeAreaInsets()
  const [tab, setTab] = useState<Tab>(params.tab === 'pending' ? 'pending' : params.tab === 'other' ? 'other' : 'active')
  const [refreshing, setRefreshing] = useState(false)
  const [menu, setMenu] = useState<MyListing | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    const [l, b] = await Promise.allSettled([myListings(token), fetchBalance(token)])
    if (l.status === 'fulfilled') setItems(l.value.items)
    if (b.status === 'fulfilled') setBal(b.value as { balance?: number; money?: number; bonus?: number })
  }, [token])

  useFocusEffect(useCallback(() => { load() }, [load]))

  if (!ready || !user) return <View style={styles.page} />

  const name = user.display_name || user.email?.split('@')[0] || tr('Профиль')

  const act = async (fn: () => Promise<unknown>) => {
    setMenu(null)
    try { await fn() } catch { Alert.alert(tr('Не получилось'), tr('Проверьте интернет и попробуйте ещё раз.')) }
    load()
  }
  const askDelete = (l: MyListing) => {
    setMenu(null)
    Alert.alert(tr('Удалить объявление?'), tr('«{title}» исчезнет насовсем.', { title: l.title }), [
      { text: tr('Отмена'), style: 'cancel' },
      { text: tr('Удалить'), style: 'destructive', onPress: () => act(() => deleteListing(token as string, l.id)) },
    ])
  }
  const count = (t: Tab) => (items ?? []).filter((i) => tabOf(i.status) === t).length
  const shown = (items ?? []).filter((i) => tabOf(i.status) === tab)
  const tabs: { key: Tab; label: string }[] = [
    { key: 'active', label: tr('Активные {n}', { n: count('active') }) },
    { key: 'pending', label: tr('На проверке {n}', { n: count('pending') }) },
    { key: 'other', label: tr('Другие {n}', { n: count('other') }) },
  ]

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.backBtn} accessibilityLabel={tr('Назад')}>
          <Icon name="back" size={22} color={colors.ink} />
        </Pressable>
        <Text style={styles.topTitle}>{tr('Мои объявления')}</Text>
        <Pressable onPress={() => router.navigate('/post')} hitSlop={8} style={{ marginLeft: 'auto', paddingRight: 8 }}><Text style={styles.link}>{tr('+ Разместить')}</Text></Pressable>
      </View>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
        contentContainerStyle={{ paddingBottom: 32 }}>
        <View style={{ paddingHorizontal: 16, paddingTop: 4 }}><Segmented options={tabs} value={tab} onChange={setTab} /></View>

        {items === null ? <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} /> : shown.length === 0 ? (
          <Text style={styles.empty}>{tab === 'active' ? tr('Активных объявлений пока нет.') : tab === 'pending' ? tr('На проверке ничего нет.') : tr('Здесь будут проданные, архивные и отклонённые.')}</Text>
        ) : (
          <View style={styles.list}>
            {shown.map((i) => {
              const st = STATUS[i.status] ?? STATUS.draft
              const photo = mediaUrl(i.cover_photo)
              return (
                <Pressable key={i.id} style={styles.row} onPress={() => router.push(`/listing/${i.id}`)}>
                  <View style={styles.thumb}>{photo ? <Image source={{ uri: photo }} style={styles.thumbImg} contentFit="cover" /> : null}</View>
                  <View style={{ flex: 1, gap: 3 }}>
                    <Text style={styles.rowTitle} numberOfLines={2}>{i.title}</Text>
                    <Text style={styles.rowPrice}>{formatPrice(i.price, i.currency, i.is_free)}</Text>
                    <View style={styles.rowMeta}>
                      <Text style={[styles.status, { color: st.tone, backgroundColor: st.bg }]}>{tr(st.label)}</Text>
                      {i.views_count != null && <Text style={styles.views}><Ionicons name="eye-outline" size={13} /> {i.views_count}</Text>}
                    </View>
                  </View>
                  <Pressable onPress={() => setMenu(i)} hitSlop={10} style={styles.more} accessibilityLabel={tr('Действия с объявлением')}>
                    <Ionicons name="ellipsis-horizontal" size={20} color={colors.inkSoft} />
                  </Pressable>
                </Pressable>
              )
            })}
          </View>
        )}

        <Sheet visible={!!menu} title={menu?.title} onClose={() => setMenu(null)}>
          {menu && <SheetAction label={tr('Показатели')} icon={<Icon name="history" size={20} color={colors.ink} />} onPress={() => { const m = menu; setMenu(null); router.push(`/stats/${m.id}`) }} />}
          {menu && menu.status !== 'sold' && (
            <SheetAction label={tr('Редактировать')} icon={<Ionicons name="create-outline" size={20} color={colors.ink} />} onPress={() => { const m = menu; setMenu(null); router.push(`/edit/${m.id}`) }} />
          )}
          {menu?.status === 'active' && (
            <>
              <SheetAction label={tr('Отметить «Продано»')} icon={<Ionicons name="checkmark-done-outline" size={20} color={colors.ink} />} onPress={() => act(() => setListingStatus(token as string, menu.id, 'sold'))} />
              <SheetAction label={tr('Снять с публикации')} icon={<Ionicons name="archive-outline" size={20} color={colors.ink} />} onPress={() => act(() => setListingStatus(token as string, menu.id, 'archived'))} />
            </>
          )}
          {(menu?.status === 'sold' || menu?.status === 'archived') && (
            <SheetAction label={tr('Вернуть в продажу')} icon={<Ionicons name="refresh-outline" size={20} color={colors.ink} />} onPress={() => act(() => setListingStatus(token as string, menu.id, 'active'))} />
          )}
          {menu && <SheetAction label={tr('Удалить')} danger icon={<Ionicons name="trash-outline" size={20} color="#B42318" />} onPress={() => askDelete(menu)} />}
        </Sheet>



      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  topBar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  backBtn: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  topTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 40, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  head: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 16, paddingTop: 16, paddingBottom: 16 },
  avatar: { width: 60, height: 60, borderRadius: 30, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center' },
  avatarLetter: { color: '#fff', fontSize: 24, fontFamily: font[800] },
  name: { fontSize: 21, fontFamily: font[800], color: colors.ink },
  email: { fontFamily: font[400], fontSize: 14.5, color: colors.inkSoft, marginTop: 2 },
  balance: { marginHorizontal: 16, padding: 16, borderRadius: 18, backgroundColor: colors.primaryDeep, gap: 2 },
  balanceLabel: { color: 'rgba(255,255,255,0.75)', fontSize: 13.5, fontFamily: font[700] },
  balanceValue: { color: '#fff', fontSize: 28, fontFamily: font[800] },
  balanceSub: { color: 'rgba(255,255,255,0.75)', fontFamily: font[400], fontSize: 13 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, marginTop: 24, marginBottom: 10 },
  h2: { fontSize: 20, fontFamily: font[800], color: colors.ink },
  link: { fontSize: 15, fontFamily: font[800], color: colors.primaryDeep },
  empty: { fontFamily: font[400], fontSize: 14.5, color: colors.muted, textAlign: 'center', marginTop: 24, paddingHorizontal: 32 },
  list: { marginHorizontal: 16, marginTop: 12, gap: 10 },
  row: { flexDirection: 'row', gap: 12, padding: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  thumb: { width: 76, height: 76, borderRadius: 12, backgroundColor: colors.photo, overflow: 'hidden' },
  thumbImg: { width: 76, height: 76 },
  rowTitle: { fontSize: 15, color: colors.ink, fontFamily: font[600] },
  rowPrice: { fontSize: 16, fontFamily: font[800], color: colors.ink },
  rowMeta: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  status: { fontSize: 12, fontFamily: font[800], paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999, overflow: 'hidden' },
  views: { fontFamily: font[400], fontSize: 12.5, color: colors.muted },
  more: { width: 32, alignItems: 'center', paddingTop: 2 },
  links: { marginHorizontal: 16, marginTop: 26, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden' },
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, height: 54, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  linkText: { flex: 1, fontSize: 16, color: colors.ink, fontFamily: font[600] },
  langRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginHorizontal: 16, marginTop: 14, paddingHorizontal: 16, paddingVertical: 8, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  langText: { flex: 1, fontSize: 16, color: colors.ink, fontFamily: font[600] },
  logout: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 14, height: 50, marginHorizontal: 16, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  logoutText: { fontSize: 16, fontFamily: font[700], color: '#B42318' },
})
