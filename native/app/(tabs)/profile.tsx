import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { balance as fetchBalance, type MyListing, myListings } from '../../src/api'
import { useAuth } from '../../src/auth'
import Segmented from '../../src/components/Segmented'
import { mediaUrl } from '../../src/config'
import { formatPrice } from '../../src/format'
import { colors } from '../../src/theme'

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
export default function Profile() {
  const { user, ready, token, signOut } = useAuth()
  const [items, setItems] = useState<MyListing[] | null>(null)
  const [bal, setBal] = useState<{ balance?: number; money?: number; bonus?: number } | null>(null)
  const [tab, setTab] = useState<Tab>('active')
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    const [l, b] = await Promise.allSettled([myListings(token), fetchBalance(token)])
    if (l.status === 'fulfilled') setItems(l.value.items)
    if (b.status === 'fulfilled') setBal(b.value as { balance?: number; money?: number; bonus?: number })
  }, [token])

  useFocusEffect(useCallback(() => { load() }, [load]))

  if (!ready) return <SafeAreaView style={[styles.page, styles.center]}><ActivityIndicator color={colors.primary} /></SafeAreaView>
  if (!user) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <View style={styles.circle}><Ionicons name="person-outline" size={30} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>Войдите в PLONK</Text>
        <Text style={styles.text}>Чтобы сохранять объявления, писать продавцам и размещать свои.</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>Войти</Text></Pressable>
      </SafeAreaView>
    )
  }

  const name = user.display_name || user.email?.split('@')[0] || 'Профиль'
  const count = (t: Tab) => (items ?? []).filter((i) => tabOf(i.status) === t).length
  const shown = (items ?? []).filter((i) => tabOf(i.status) === tab)
  const tabs: { key: Tab; label: string }[] = [
    { key: 'active', label: `Активные ${count('active')}` },
    { key: 'pending', label: `На проверке ${count('pending')}` },
    { key: 'other', label: `Другие ${count('other')}` },
  ]

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}
        contentContainerStyle={{ paddingBottom: 32 }}>
        <View style={styles.head}>
          <View style={styles.avatar}><Text style={styles.avatarLetter}>{name.slice(0, 1).toUpperCase()}</Text></View>
          <View style={{ flex: 1 }}>
            <Text style={styles.name} numberOfLines={1}>{name}</Text>
            {!!user.email && <Text style={styles.email} numberOfLines={1}>{user.email}</Text>}
          </View>
        </View>

        <View style={styles.balance}>
          <Text style={styles.balanceLabel}>Баланс</Text>
          <Text style={styles.balanceValue}>{bal ? rsd(bal.balance ?? 0) : '—'}</Text>
          {!!bal && (bal.bonus ?? 0) > 0 && <Text style={styles.balanceSub}>из них бонусы — {rsd(bal.bonus ?? 0)}</Text>}
        </View>

        <View style={styles.sectionHead}>
          <Text style={styles.h2}>Мои объявления</Text>
          <Pressable onPress={() => router.navigate('/post')} hitSlop={8}><Text style={styles.link}>+ Разместить</Text></Pressable>
        </View>
        <View style={{ paddingHorizontal: 16 }}><Segmented options={tabs} value={tab} onChange={setTab} /></View>

        {items === null ? <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} /> : shown.length === 0 ? (
          <Text style={styles.empty}>{tab === 'active' ? 'Активных объявлений пока нет.' : tab === 'pending' ? 'На проверке ничего нет.' : 'Здесь будут проданные, архивные и отклонённые.'}</Text>
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
                      <Text style={[styles.status, { color: st.tone, backgroundColor: st.bg }]}>{st.label}</Text>
                      {i.views_count != null && <Text style={styles.views}><Ionicons name="eye-outline" size={13} /> {i.views_count}</Text>}
                    </View>
                  </View>
                </Pressable>
              )
            })}
          </View>
        )}

        <Pressable style={styles.logout} onPress={signOut}>
          <Ionicons name="log-out-outline" size={20} color="#B42318" />
          <Text style={styles.logoutText}>Выйти</Text>
        </Pressable>
        <Text style={{ textAlign: 'center', color: '#8D958E', fontSize: 13, marginTop: 18 }}>Тест обновления A</Text>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  text: { fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 40, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  head: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 16, paddingTop: 16, paddingBottom: 16 },
  avatar: { width: 60, height: 60, borderRadius: 30, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center' },
  avatarLetter: { color: '#fff', fontSize: 24, fontWeight: '800' },
  name: { fontSize: 21, fontWeight: '800', color: colors.ink },
  email: { fontSize: 14.5, color: colors.inkSoft, marginTop: 2 },
  balance: { marginHorizontal: 16, padding: 16, borderRadius: 18, backgroundColor: colors.primaryDeep, gap: 2 },
  balanceLabel: { color: 'rgba(255,255,255,0.75)', fontSize: 13.5, fontWeight: '700' },
  balanceValue: { color: '#fff', fontSize: 28, fontWeight: '800' },
  balanceSub: { color: 'rgba(255,255,255,0.75)', fontSize: 13 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, marginTop: 24, marginBottom: 10 },
  h2: { fontSize: 20, fontWeight: '800', color: colors.ink },
  link: { fontSize: 15, fontWeight: '800', color: colors.primaryDeep },
  empty: { fontSize: 14.5, color: colors.muted, textAlign: 'center', marginTop: 24, paddingHorizontal: 32 },
  list: { marginHorizontal: 16, marginTop: 12, gap: 10 },
  row: { flexDirection: 'row', gap: 12, padding: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  thumb: { width: 76, height: 76, borderRadius: 12, backgroundColor: colors.photo, overflow: 'hidden' },
  thumbImg: { width: 76, height: 76 },
  rowTitle: { fontSize: 15, color: colors.ink, fontWeight: '600' },
  rowPrice: { fontSize: 16, fontWeight: '800', color: colors.ink },
  rowMeta: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  status: { fontSize: 12, fontWeight: '800', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999, overflow: 'hidden' },
  views: { fontSize: 12.5, color: colors.muted },
  logout: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 28, height: 50, marginHorizontal: 16, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  logoutText: { fontSize: 16, fontWeight: '700', color: '#B42318' },
})
