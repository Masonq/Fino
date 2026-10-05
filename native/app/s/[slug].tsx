import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useMemo, useState } from 'react'
import { ActivityIndicator, FlatList, Modal, Pressable, ScrollView, Share, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAuth } from '../../src/auth'
import { mediaUrl, SITE } from '../../src/config'
import { plural, tr } from '../../src/i18n'
import Icon from '../../src/components/Icon'
import { Btn, Empty, k, Tabs } from '../../src/components/Kit'
import ListingCard from '../../src/components/ListingCard'
import { sfFollow, sfPublic, sfReport, type StorefrontPublic } from '../../src/social'
import { colors, font, space } from '../../src/theme'

const REASONS: [string, string][] = [['spam', 'Спам'], ['fraud', 'Мошенничество'], ['prohibited_item', 'Запрещённые товары'], ['offensive_user', 'Выдаёт себя за другого или оскорбления'], ['other', 'Другое']]
const items = (n: number) => plural(n, { ru: ['товар', 'товара', 'товаров'], en: ['item', 'items'], sr: ['stvar', 'stvari', 'stvari'] })

/** Витрина продавца — как /s/:slug на сайте: обложка, подписка, «Поделиться», подборки, товары, видео. */
export default function Storefront() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [sf, setSf] = useState<StorefrontPublic | null>(null)
  const [error, setError] = useState(false)
  const [coll, setColl] = useState<string>('all')
  const [tab, setTab] = useState<'items' | 'video'>('items')
  const [report, setReport] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (slug) sfPublic(slug, token).then(setSf).catch(() => setError(true)) }, [slug, token])
  const list = useMemo(() => {
    if (!sf) return []
    const c = sf.collections.find((x) => x.id === coll)
    if (!c) return sf.items
    const byId = new Map(sf.items.map((l) => [l.id, l]))
    return c.listing_ids.map((id) => byId.get(id)).filter(Boolean) as typeof sf.items
  }, [sf, coll])

  if (error) return <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: insets.top + 40 }}><Empty text={tr('Витрина не найдена или закрыта')}><Btn label={tr('Назад')} onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} /></Empty></View>
  if (!sf) return <View style={{ flex: 1, backgroundColor: colors.bg }}><ActivityIndicator style={{ marginTop: insets.top + 80 }} color={colors.primary} /></View>

  const follow = async () => {
    if (!token) { router.push('/login'); return }
    setBusy(true)
    try { const r = await sfFollow(token, sf.slug, !sf.following); setSf({ ...sf, following: r.following }) } catch { /* оставляем как было */ }
    setBusy(false)
  }
  const share = () => {
    const c = sf.collections.find((x) => x.id === coll)
    Share.share({ message: `${c ? `${c.title} — ` : ''}${sf.name}\n${SITE}/s/${sf.slug}${c ? `/c/${c.id}` : ''}` }).catch(() => {})
  }
  const pausedUntil = sf.status === 'paused' && sf.pause_until ? new Date(sf.pause_until).toLocaleDateString(undefined, { day: 'numeric', month: 'long' }) : null

  const head = (
    <View>
      <View style={s.cover}>
        {!!sf.cover_url && <Image source={{ uri: mediaUrl(sf.cover_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}
        <Pressable style={[s.round, { top: insets.top + 8 }]} onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color="#fff" /></Pressable>
      </View>
      <View style={s.head}>
        <View style={s.ava}>{sf.owner.avatar ? <Image source={{ uri: mediaUrl(sf.owner.avatar) ?? undefined }} style={StyleSheet.absoluteFill} /> : <Text style={s.avaText}>{(sf.name || '?')[0]}</Text>}</View>
        <Text style={s.name}>{sf.name}</Text>
        <Text style={s.sub}>
          {sf.owner.name !== sf.name ? `${sf.owner.name} · ` : ''}{sf.items.length} {items(sf.items.length)}
          {sf.followers != null ? ` · ${sf.followers} ${plural(sf.followers, { ru: ['подписчик', 'подписчика', 'подписчиков'], en: ['follower', 'followers'], sr: ['pratilac', 'pratioca', 'pratilaca'] })}` : ''}
        </Text>
        {!!sf.description && <Text style={s.desc}>{sf.description}</Text>}
        {sf.status === 'paused' && <View style={s.paused}><Text style={s.pausedText}>🌴 {pausedUntil ? tr('В отпуске до {date}', { date: pausedUntil }) : tr('Продавец в отпуске')}{sf.pause_note ? ` · ${sf.pause_note}` : ''}</Text></View>}
        <View style={s.actions}>
          {sf.mine ? <Btn label={tr('Управлять витриной')} onPress={() => router.push('/vitrina' as never)} />
            : <Btn kind={sf.following ? 'ghost' : 'primary'} busy={busy} label={sf.following ? tr('Вы подписаны') : tr('Подписаться')} onPress={follow} />}
          <Btn kind="ghost" label={tr('Поделиться')} onPress={share} />
          {!sf.mine && <Pressable style={s.more} onPress={() => (token ? setReport(true) : router.push('/login'))} accessibilityLabel={tr('Пожаловаться')}><Icon name="dots" size={18} color={colors.ink} /></Pressable>}
        </View>
      </View>
      <View style={{ paddingHorizontal: space.page }}>
        {sf.shops.length > 0 && <Tabs value={tab} onChange={setTab} items={[{ key: 'items', label: tr('Товары') }, { key: 'video', label: tr('Видео'), n: sf.shops.length }]} />}
        {tab === 'items' && sf.collections.length > 0 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <Tabs value={coll} onChange={setColl} items={[{ key: 'all', label: tr('Все') }, ...sf.collections.map((c) => ({ key: c.id, label: c.title, n: c.listing_ids.length }))]} />
          </ScrollView>
        )}
        {tab === 'video' && (
          <View style={s.videos}>
            {sf.shops.map((v) => (
              <Pressable key={v.id} style={[s.video, { width: (width - space.page * 2 - 16) / 3 }]} onPress={() => router.push(`/shops?start=${v.id}` as never)}>
                {!!v.poster_url && <Image source={{ uri: mediaUrl(v.poster_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}
              </Pressable>
            ))}
          </View>
        )}
      </View>
    </View>
  )

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <FlatList
        data={tab === 'items' ? list : []}
        keyExtractor={(i) => i.id}
        numColumns={2}
        ListHeaderComponent={head}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        columnWrapperStyle={{ gap: space.gap, paddingHorizontal: space.page }}
        contentContainerStyle={{ gap: space.gap, paddingBottom: insets.bottom + 24 }}
        ListEmptyComponent={tab === 'items' ? <Empty text={tr('Здесь пока ничего нет')} /> : null}
      />
      <Modal visible={report} transparent animationType="slide" onRequestClose={() => setReport(false)}>
        <Pressable style={k.sheetOverlay} onPress={() => setReport(false)}>
          <Pressable style={[k.sheet, { paddingBottom: insets.bottom + 16 }]} onPress={() => {}}>
            <View style={k.grab} />
            <Text style={k.sheetTitle}>{tr('Пожаловаться')}</Text>
            {REASONS.map(([key, label]) => (
              <Pressable key={key} style={s.reason} onPress={() => { if (token) sfReport(token, sf.slug, key).catch(() => {}); setReport(false) }}>
                <Text style={k.body}>{tr(label)}</Text>
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  )
}

const s = StyleSheet.create({
  cover: { height: 180, backgroundColor: colors.primarySoft, overflow: 'hidden' },
  round: { position: 'absolute', left: 12, width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
  head: { alignItems: 'center', marginTop: -36, paddingHorizontal: 16 },
  ava: { width: 72, height: 72, borderRadius: 36, borderWidth: 4, borderColor: colors.bg, overflow: 'hidden', backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  avaText: { fontFamily: font[800], fontSize: 28, color: colors.primaryDeep },
  name: { marginTop: 8, fontFamily: font[800], fontSize: 22, color: colors.ink, textAlign: 'center' },
  sub: { marginTop: 2, fontFamily: font[500], fontSize: 14, color: colors.muted, textAlign: 'center' },
  desc: { marginTop: 10, fontFamily: font[500], fontSize: 15, lineHeight: 21, color: colors.ink, textAlign: 'center' },
  paused: { marginTop: 10, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12, backgroundColor: colors.warmBg },
  pausedText: { fontFamily: font[600], fontSize: 14, color: colors.goldDark },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 14, marginBottom: 8 },
  more: { width: 44, height: 44, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  videos: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  video: { aspectRatio: 9 / 16, borderRadius: 12, overflow: 'hidden', backgroundColor: '#1c2620' },
  reason: { paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: colors.border },
})
