import EmptyArt from '../src/components/EmptyArt'
import { getLang, tr } from '../src/i18n'
import { success } from '../src/haptics'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Alert, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native'
import Pressable from '../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { balance as fetchBalance, deleteListing, type MyListing, myListings, setListingStatus, renewListing } from '../src/api'
import PromoteSheet from '../src/components/PromoteSheet'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import Segmented from '../src/components/Segmented'
import Sheet, { SheetAction } from '../src/components/Sheet'
import { mediaUrl } from '../src/config'
import { formatPrice, parseTime } from '../src/format'
import { colors, font } from '../src/theme'

// Вкладки — как на сайте: активные, на проверке, отклонено, продано, в архиве (истёкшие и снятые — в архиве)
type Tab = 'active' | 'pending' | 'rejected' | 'sold' | 'archived'
const STATUS: Record<string, { label: string; tone: string; bg: string }> = {
  active: { label: 'Активно', tone: colors.primaryDeep, bg: colors.primarySoft },
  pending_moderation: { label: 'На проверке', tone: '#8A6A1F', bg: colors.warmBg },
  draft: { label: 'Черновик', tone: colors.inkSoft, bg: colors.sunken },
  sold: { label: 'Продано', tone: colors.inkSoft, bg: colors.sunken },
  archived: { label: 'В архиве', tone: colors.inkSoft, bg: colors.sunken },
  rejected: { label: 'Отклонено', tone: colors.danger, bg: colors.dangerBg },
}
const tabOf = (s: string): Tab => (s === 'active' ? 'active' : s === 'pending_moderation' ? 'pending' : s === 'rejected' ? 'rejected' : s === 'sold' ? 'sold' : 'archived')
const rsd = (n: number) => `${String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')}\u00A0RSD`

/** Профиль: кто ты, баланс, мои объявления по вкладкам (активные / на проверке / другие), «Выйти». */
export default function MyListings() {
  const { user, ready, token } = useAuth()
  const [items, setItems] = useState<MyListing[] | null>(null)
  const [bal, setBal] = useState<{ balance?: number; money?: number; bonus?: number } | null>(null)
  const params = useLocalSearchParams<{ tab?: string }>()
  const insets = useSafeAreaInsets()
  const [tab, setTab] = useState<Tab>((['pending', 'rejected', 'sold', 'archived'] as string[]).includes(String(params.tab)) ? (params.tab as Tab) : 'active')
  const [refreshing, setRefreshing] = useState(false)
  // все хуки — до раннего выхода ниже (иначе React #310)
  const [renewing, setRenewing] = useState<string | null>(null)
  const [menu, setMenu] = useState<MyListing | null>(null)
  const [promoFor, setPromoFor] = useState<string | null>(null)   // «Поднять просмотры» — шторка продвижения

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
  const renew = async (id: string) => {
    if (!token) return
    setRenewing(id)
    try { await renewListing(token, id); success(); await load() } catch { /* обновится при следующем открытии */ } finally { setRenewing(null) }
  }
  const tabs: { key: Tab; label: string }[] = [
    { key: 'active', label: 'Активные' }, { key: 'pending', label: 'На проверке' }, { key: 'rejected', label: 'Отклонено' },
    { key: 'sold', label: 'Продано' }, { key: 'archived', label: 'В архиве' },
  ]

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.backBtn} accessibilityLabel={tr('Назад')}>
          <Icon name="back" size={22} color={colors.ink} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.kicker}>{tr('Ваши продажи')}</Text>
          <Text style={styles.topTitle}>{tr('Мои объявления')}</Text>
        </View>
      </View>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
        contentContainerStyle={{ paddingBottom: 32 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabsWrap}><View style={styles.tabs}>
          {tabs.map((t) => {
            const on = t.key === tab
            const n = count(t.key)
            return (
              <Pressable key={t.key} onPress={() => setTab(t.key)} style={[styles.tab, on && styles.tabOn]} accessibilityRole="tab" accessibilityState={{ selected: on }}>
                <Text style={[styles.tabText, on && styles.tabTextOn]}>{tr(t.label)}</Text>
                {n > 0 && <Text style={[styles.tabCount, on && styles.tabTextOn]}>{n}</Text>}
              </Pressable>
            )
          })}
        </View></ScrollView>

        {items === null ? <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} /> : shown.length === 0 ? (
          <View style={styles.emptyBox}>
            <EmptyArt name="my" />
            <Text style={styles.emptyText}>{tr('Здесь пока пусто')}</Text>
            <Pressable style={styles.emptyBtn} onPress={() => router.navigate('/post')}><Text style={styles.emptyBtnText}>{tr('Разместить')}</Text></Pressable>
          </View>
        ) : (
          <View style={styles.list}>
            {shown.map((i) => {
              const st = STATUS[i.status] ?? STATUS.draft
              const photo = mediaUrl(i.cover_photo)
              return (
                <View key={i.id} style={styles.card}>
                <Pressable style={styles.row} onPress={() => router.push(`/listing/${i.id}`)}>
                  <View style={styles.thumb}>{photo ? <Image source={{ uri: photo }} style={styles.thumbImg} contentFit="cover" /> : null}</View>
                  <View style={{ flex: 1, gap: 3 }}>
                    <Text style={styles.rowTitle} numberOfLines={2}>{i.title}</Text>
                    <Text style={styles.rowPrice}>{formatPrice(i.price, i.currency, i.is_free)}</Text>
                    <View style={styles.rowMeta}>
                      <Text style={[styles.status, { color: st.tone, backgroundColor: st.bg }]}>{tr(st.label)}</Text>
                      {i.views_count != null && <Text style={styles.views}><Ionicons name="eye-outline" size={13} /> {i.views_count}</Text>}
                    </View>
                    {(() => {
                      const left = daysLeft(i.expires_at)
                      if (i.status !== 'active' || left === null || left > 7) return null
                      return (
                        <View style={styles.expiry}>
                          <Text style={styles.expiryText}>{expiresIn(left)}</Text>
                          <Pressable style={[styles.renew, renewing === i.id && { opacity: 0.6 }]} disabled={renewing === i.id} onPress={() => renew(i.id)}><Text style={styles.renewText}>{tr('Продлить')}</Text></Pressable>
                        </View>
                      )
                    })()}
                  </View>
                  <Pressable onPress={() => setMenu(i)} hitSlop={10} style={styles.more} accessibilityLabel={tr('Действия с объявлением')}>
                    <Ionicons name="ellipsis-horizontal" size={20} color={colors.inkSoft} />
                  </Pressable>
                </Pressable>
                {/* как на сайте: главные действия кнопками под карточкой, остальное — в «…» */}
                {i.status === 'active' && (
                  <View style={styles.quick}>
                    <View style={{ flexDirection: 'row', gap: 8 }}>
                      <Pressable style={styles.qBtn} onPress={() => act(() => setListingStatus(token as string, i.id, 'sold'))}><Text style={styles.qBtnT}>{tr('Продано')}</Text></Pressable>
                      <Pressable style={styles.qBtn} onPress={() => act(() => setListingStatus(token as string, i.id, 'archived'))}><Text style={styles.qBtnT}>{tr('Снять с публикации')}</Text></Pressable>
                    </View>
                    <Pressable style={[styles.qBtn, styles.qPromo]} onPress={() => setPromoFor(i.id)}><Text style={[styles.qBtnT, { color: colors.onInverse }]}>{tr('Поднять просмотры')}</Text></Pressable>
                  </View>
                )}
                </View>
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
      {!!promoFor && !!token && <PromoteSheet token={token} listingId={promoFor} onClose={() => setPromoFor(null)} />}
    </View>
  )
}

/** «Снимем через N дней» — три формы, как в словаре сайта (my.expires_in_*), на трёх языках. */
function expiresIn(n: number): string {
  if (getLang() === 'en') return `Expires in ${n} ${n === 1 ? 'day' : 'days'}`
  const i = n % 10 === 1 && n % 100 !== 11 ? 0 : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? 1 : 2
  return tr(['Снимем через {n} день', 'Снимем через {n} дня', 'Снимем через {n} дней'][i], { n })
}

const daysLeft = (iso?: string | null) => { const d = parseTime(iso); return d ? Math.max(0, Math.ceil((d.getTime() - Date.now()) / 86400000)) : null }

const styles = StyleSheet.create({
  kicker: { fontFamily: font[600], fontSize: 14, color: colors.inkSoft },
  expiry: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: 6, paddingLeft: 10, paddingRight: 4, paddingVertical: 4, borderRadius: 10, backgroundColor: colors.warmBg },
  expiryText: { flex: 1, fontSize: 12.5, fontFamily: font[700], color: '#8A6A1F' },
  renew: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, backgroundColor: colors.surface },
  renewText: { fontSize: 12.5, fontFamily: font[800], color: colors.ink },
  // как .my-tabs .pill-track сайта: серая дорожка 3 / 13, выбранная — зелёная плашка 11
  tabsWrap: { paddingHorizontal: 12, paddingBottom: 14, paddingTop: 2 },
  tabs: { flexDirection: 'row', gap: 2, padding: 3, borderRadius: 13, backgroundColor: colors.sunken },
  tab: { flexDirection: 'row', alignItems: 'center', gap: 5, height: 34, paddingHorizontal: 13, borderRadius: 11 },
  tabOn: { backgroundColor: colors.inverse },
  tabText: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  tabTextOn: { color: colors.onInverse },
  tabCount: { fontSize: 12, fontFamily: font[800], color: colors.muted },
  emptyBox: { alignItems: 'center', gap: 14, paddingTop: 44, paddingHorizontal: 32 },
  emptyIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  emptyText: { fontSize: 14.5, fontFamily: font[600], color: colors.muted },
  emptyBtn: { marginTop: 4, height: 42, paddingHorizontal: 20, borderRadius: 13, backgroundColor: colors.inverse, justifyContent: 'center' },
  emptyBtnText: { color: colors.onInverse, fontSize: 14.5, fontFamily: font[800] },
  topBar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  backBtn: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  topTitle: { fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 40, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  head: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, paddingTop: 16, paddingBottom: 16 },
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
  row: { flexDirection: 'row', gap: 12, padding: 10, borderRadius: 16, borderWidth: 0 },
  card: { backgroundColor: colors.surface, borderRadius: 20, overflow: 'hidden' },
  quick: { gap: 8, paddingHorizontal: 12, paddingBottom: 12 },
  qBtn: { flex: 1, height: 40, borderRadius: 12, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  qBtnT: { fontFamily: font[800], fontSize: 13.5, color: colors.ink },
  qPromo: { flex: 0, flexGrow: 0, flexShrink: 0, flexBasis: 'auto', height: 42, alignSelf: 'stretch', backgroundColor: colors.inverse },
  thumb: { width: 76, height: 76, borderRadius: 12, backgroundColor: colors.photo, overflow: 'hidden' },
  thumbImg: { width: 76, height: 76 },
  rowTitle: { fontSize: 15, color: colors.ink, fontFamily: font[600] },
  rowPrice: { fontSize: 16, fontFamily: font[800], color: colors.ink },
  rowMeta: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  status: { fontSize: 12, fontFamily: font[800], paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999, overflow: 'hidden' },
  views: { fontFamily: font[400], fontSize: 12.5, color: colors.muted },
  more: { width: 32, alignItems: 'center', paddingTop: 2 },
  links: { marginHorizontal: 16, marginTop: 26, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 0, overflow: 'hidden' },
  linkRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, height: 54, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  linkText: { flex: 1, fontSize: 16, color: colors.ink, fontFamily: font[600] },
  langRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginHorizontal: 16, marginTop: 14, paddingHorizontal: 16, paddingVertical: 8, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 0 },
  langText: { flex: 1, fontSize: 16, color: colors.ink, fontFamily: font[600] },
  logout: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 14, height: 50, marginHorizontal: 16, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 0 },
  logoutText: { fontSize: 16, fontFamily: font[700], color: colors.danger },
})
