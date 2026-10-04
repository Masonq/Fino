import { useEvent } from 'expo'
import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useVideoPlayer, VideoView } from 'expo-video'
import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, Modal, Pressable, StatusBar, StyleSheet, Text, useWindowDimensions, View, type ViewToken } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { startChat } from '../../src/api'
import { useAuth } from '../../src/auth'
import { mediaUrl } from '../../src/config'
import { tr } from '../../src/i18n'
import Icon from '../../src/components/Icon'
import { Btn, k } from '../../src/components/Kit'
import { money, type Shop, type ShopItem, shopEvent, shopsFeed } from '../../src/social'
import { colors, font } from '../../src/theme'

const PAGE = 8

/**
 * Лента шопсов: свайп вверх — следующий ролик. Играет только видимый; источник получают текущий, предыдущий
 * и два следующих (буфер готов к свайпу), у остальных плеер пустой — только обложка. Карточки — со своей секунды.
 */
export default function ShopsFeed() {
  const { start } = useLocalSearchParams<{ start?: string }>()
  const { token } = useAuth()
  const { height, width } = useWindowDimensions()
  const insets = useSafeAreaInsets()
  const [items, setItems] = useState<Shop[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [active, setActive] = useState(0)
  const [muted, setMuted] = useState(true)
  const loading = useRef(false)

  const load = useCallback((offset: number) => {
    if (loading.current) return
    loading.current = true
    shopsFeed({ offset, limit: PAGE, start: offset === 0 ? start : null }, token)
      .then((r) => {
        setTotal(r.total)
        setItems((prev) => { const have = new Set(prev.map((x) => x.id)); return [...prev, ...r.items.filter((x) => !have.has(x.id))] })
      })
      .catch(() => setTotal((v) => v ?? 0))
      .finally(() => { loading.current = false })
  }, [start, token])
  useEffect(() => { load(0) }, [load])

  const onViewable = useRef(({ viewableItems }: { viewableItems: ViewToken[] }) => {
    const first = viewableItems.find((v) => v.isViewable)
    if (first?.index != null) setActive(first.index)
  }).current

  return (
    <View style={{ flex: 1, backgroundColor: '#000' }}>
      <StatusBar barStyle="light-content" />
      {total === null && !items.length ? <ActivityIndicator style={{ marginTop: height / 2 - 20 }} color="#fff" /> : null}
      {total === 0 && (
        <View style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center', padding: 24, gap: 16 }]}>
          <Text style={[k.emptyText, { color: '#fff' }]}>{tr('Пока здесь пусто. Снимите короткое видео про свою вещь — его увидят все на главной')}</Text>
          <Btn label={tr('Снимите первый шопс')} onPress={() => router.replace('/shops/new' as never)} />
        </View>
      )}
      <FlatList
        data={items}
        keyExtractor={(s) => s.id}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        decelerationRate="fast"
        snapToInterval={height}
        getItemLayout={(_, i) => ({ length: height, offset: height * i, index: i })}
        onViewableItemsChanged={onViewable}
        viewabilityConfig={{ itemVisiblePercentThreshold: 60 }}
        onEndReached={() => { if (total != null && items.length < total) load(items.length) }}
        onEndReachedThreshold={2}
        windowSize={5}
        initialNumToRender={2}
        maxToRenderPerBatch={2}
        renderItem={({ item, index }) => (
          <Slide shop={item} active={index === active} near={index >= active - 1 && index <= active + 2} muted={muted} width={width} height={height} bottom={insets.bottom} />
        )}
      />
      <Pressable style={[s.round, { top: insets.top + 8, left: 12 }]} onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={8} accessibilityLabel={tr('Назад')}>
        <Icon name="back" size={22} color="#fff" />
      </Pressable>
      <Pressable style={[s.round, { top: insets.top + 8, right: 12 }]} onPress={() => setMuted((m) => !m)} hitSlop={8} accessibilityLabel={tr(muted ? 'Включить звук' : 'Выключить звук')}>
        <Icon name={muted ? 'soundOff' : 'soundOn'} size={20} color="#fff" />
      </Pressable>
    </View>
  )
}

const Slide = memo(function Slide({ shop, active, near, muted, width, height, bottom }: { shop: Shop; active: boolean; near: boolean; muted: boolean; width: number; height: number; bottom: number }) {
  const { token } = useAuth()
  const [paused, setPaused] = useState(false)
  const [sheet, setSheet] = useState(false)
  const sent = useRef({ view: false, complete: false })
  const src = mediaUrl(shop.video_url)
  const player = useVideoPlayer(null, (p) => { p.loop = true; p.muted = true; p.timeUpdateEventInterval = 0.25 })
  const { currentTime } = useEvent(player, 'timeUpdate', { currentTime: 0, currentLiveTimestamp: null, currentOffsetFromLive: null, bufferedPosition: 0 })

  // источник — только в окне предзагрузки: дальние ролики не тратят трафик и память
  const loaded = useRef(false)
  useEffect(() => {
    if (near && src && !loaded.current) { loaded.current = true; player.replaceAsync(src).catch(() => {}) }
    if (!near && loaded.current) { loaded.current = false; player.replaceAsync(null).catch(() => {}) }
  }, [near, src, player])
  useEffect(() => { player.muted = muted }, [muted, player])
  useEffect(() => {
    if (active && !paused) player.play(); else player.pause()
    if (!active) setPaused(false)
  }, [active, paused, player])
  // просмотр — после 2 секунд на экране, досмотр — 90% ролика
  useEffect(() => {
    if (!active || sent.current.view) return undefined
    const t = setTimeout(() => { sent.current.view = true; shopEvent(token, shop.id, 'view') }, 2000)
    return () => clearTimeout(t)
  }, [active, shop.id, token])
  useEffect(() => {
    const d = shop.duration || player.duration
    if (!sent.current.complete && d && currentTime / d > 0.9) { sent.current.complete = true; shopEvent(token, shop.id, 'complete') }
  }, [currentTime, shop.duration, player, shop.id, token])

  const openItem = (it: ShopItem) => { shopEvent(token, shop.id, 'tap', it.id); setSheet(false); router.push(`/listing/${it.id}` as never) }
  const write = async (it: ShopItem) => {
    if (!token) { router.push('/login'); return }
    shopEvent(token, shop.id, 'chat', it.id)
    try { const chat = await startChat(token, it.id); setSheet(false); router.push(`/chat/${chat.id}` as never) } catch { openItem(it) }
  }
  const shown = shop.items.filter((it) => (it.appear_at || 0) <= currentTime + 0.05)
  const progress = Math.min(1, currentTime / (shop.duration || 1))

  const card = (it: ShopItem, light = false) => (
    <View key={it.item_id} style={[s.item, light && s.itemLight, it.status !== 'active' && { opacity: 0.6 }]}>
      <Pressable style={s.itemMain} onPress={() => openItem(it)} accessibilityRole="link">
        {!!it.photo && <Image source={{ uri: mediaUrl(it.photo) ?? undefined }} style={k.thumb} contentFit="cover" />}
        <View style={{ flex: 1 }}>
          <Text style={s.itemTitle} numberOfLines={1}>{it.title}</Text>
          <Text style={s.itemPrice}>{it.status !== 'active' ? tr('Продано') : money(it.price, it.currency)}</Text>
        </View>
      </Pressable>
      {it.status === 'active' && <Pressable style={s.write} onPress={() => write(it)}><Text style={s.writeText}>{tr('Написать')}</Text></Pressable>}
    </View>
  )

  return (
    <View style={{ width, height, backgroundColor: '#000' }}>
      {!!shop.poster_url && <Image source={{ uri: mediaUrl(shop.poster_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}
      <Pressable style={StyleSheet.absoluteFill} onPress={() => setPaused((p) => !p)} accessibilityLabel={tr(paused ? 'Смотреть' : 'Пауза')}>
        <VideoView player={player} style={StyleSheet.absoluteFill} contentFit="cover" nativeControls={false} allowsPictureInPicture={false} />
      </Pressable>
      {paused && <View pointerEvents="none" style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center' }]}><Icon name="play" size={56} color="#fff" /></View>}
      <View pointerEvents="box-none" style={[s.meta, { paddingBottom: bottom + 18 }]}>
        <View style={k.row}>
          <View style={s.ava}>{shop.author?.avatar ? <Image source={{ uri: mediaUrl(shop.author.avatar) ?? undefined }} style={StyleSheet.absoluteFill} /> : <Text style={s.avaText}>{(shop.author?.name || '?')[0]}</Text>}</View>
          <Text style={s.author}>{shop.author?.name}</Text>
          {shop.is_ad && <View style={s.ad}><Text style={s.adText}>{tr('Реклама')}</Text></View>}
        </View>
        {!!shop.caption && <Text style={s.caption} numberOfLines={3}>{shop.caption}</Text>}
        <View style={{ gap: 8, marginTop: 10 }}>
          {shown.slice(-2).map((it) => card(it))}
          {shop.items.length > 1 && (
            <Pressable style={s.all} onPress={() => setSheet(true)}><Text style={s.allText}>{tr('Все товары · {n}', { n: shop.items.length })}</Text></Pressable>
          )}
        </View>
      </View>
      <View style={[s.progress, { bottom: bottom + 6 }]}><View style={[s.progressFill, { width: `${progress * 100}%` }]} /></View>
      <Modal visible={sheet} transparent animationType="slide" onRequestClose={() => setSheet(false)}>
        <Pressable style={k.sheetOverlay} onPress={() => setSheet(false)}>
          <Pressable style={[k.sheet, { paddingBottom: bottom + 16 }]} onPress={() => {}}>
            <View style={k.grab} />
            <Text style={k.sheetTitle}>{tr('Товары в видео')}</Text>
            {shop.items.map((it) => card(it, true))}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  )
})

const s = StyleSheet.create({
  round: { position: 'absolute', width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
  meta: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 12, paddingTop: 60, backgroundColor: 'rgba(0,0,0,0.28)' },
  ava: { width: 32, height: 32, borderRadius: 16, overflow: 'hidden', backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  avaText: { fontFamily: font[800], fontSize: 14, color: colors.primaryDeep },
  author: { fontFamily: font[700], fontSize: 15, color: '#fff' },
  ad: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.2)' },
  adText: { fontFamily: font[700], fontSize: 11, color: '#fff' },
  caption: { marginTop: 8, fontFamily: font[500], fontSize: 14, lineHeight: 20, color: '#fff' },
  item: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 6, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.95)' },
  itemLight: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, marginBottom: 8 },
  itemMain: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  itemTitle: { fontFamily: font[700], fontSize: 14, color: colors.ink },
  itemPrice: { fontFamily: font[800], fontSize: 14, color: colors.ink, marginTop: 2 },
  write: { height: 36, paddingHorizontal: 12, borderRadius: 10, backgroundColor: colors.primary, justifyContent: 'center' },
  writeText: { fontFamily: font[700], fontSize: 13, color: '#fff' },
  all: { alignSelf: 'flex-start', height: 30, paddingHorizontal: 12, borderRadius: 15, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center' },
  allText: { fontFamily: font[700], fontSize: 13, color: '#fff' },
  progress: { position: 'absolute', left: 12, right: 12, height: 3, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.25)' },
  progressFill: { height: 3, borderRadius: 2, backgroundColor: '#fff' },
})
