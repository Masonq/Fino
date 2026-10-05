import { useEvent } from 'expo'
import { LinearGradient } from 'expo-linear-gradient'
import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useVideoPlayer, VideoView } from 'expo-video'
import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Share, StatusBar, StyleSheet, Text, TextInput, useWindowDimensions, View, type ViewToken } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { startChat } from '../api'
import { useAuth } from '../auth'
import { mediaUrl } from '../config'
import { tr } from '../i18n'
import Icon from './Icon'
import { Btn, k } from './Kit'
import { useTabInset } from '../tabInset'
import { money, type Shop, type ShopComment, type ShopItem, shopComment, shopCommentDelete, shopCommentReport, shopComments, shopEvent, shopLike, shopsFeed } from '../social'
import { SITE } from '../config'
import { useFavorites } from '../favorites'
import { colors, font } from '../theme'

const PAGE = 8

/**
 * Лента шопсов: свайп вверх — следующий ролик. Играет только видимый; источник получают текущий, предыдущий
 * и два следующих (буфер готов к свайпу), у остальных плеер пустой — только обложка. Карточки — со своей секунды.
 */
/** tab — вкладка меню (без кнопки «назад», меню под лентой); start — ролик, с которого открыли. */
export default function ShopsFeedView({ start, tab = false }: { start?: string; tab?: boolean }) {
  const { token } = useAuth()
  const { width, height: winH } = useWindowDimensions()
  const [height, setHeight] = useState(winH) // высота ленты: во вкладке — экран минус меню
  const insets = useSafeAreaInsets()
  const tabInset = useTabInset()
  const [items, setItems] = useState<Shop[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [active, setActive] = useState(0)
  const [muted, setMuted] = useState(true)
  const loading = useRef(false)

  const load = useCallback((offset: number) => {
    if (loading.current) return
    loading.current = true
    shopsFeed({ offset, limit: PAGE, start: offset === 0 ? start : null, withListings: true }, token)
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
    <View style={{ flex: 1, backgroundColor: '#000' }} onLayout={(e) => setHeight(Math.round(e.nativeEvent.layout.height))}>
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
          <Slide shop={item} active={index === active} near={index >= active - 1 && index <= active + 2} muted={muted} width={width} height={height} bottom={tab ? tabInset : insets.bottom} />
        )}
      />
      {!tab && <Pressable style={[s.round, { top: insets.top + 8, left: 12 }]} onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={8} accessibilityLabel={tr('Назад')}>
        <Icon name="back" size={22} color="#fff" />
      </Pressable>}
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
  const [comments, setComments] = useState(false)
  const [like, setLike] = useState({ on: !!shop.liked, n: shop.likes ?? 0 })
  const [nComments, setNComments] = useState(shop.comments ?? 0)
  const [burst, setBurst] = useState(0)
  const lastTap = useRef(0)
  const isShop = shop.kind !== 'listing'
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
    if (!active || sent.current.view || !isShop) return undefined
    const t = setTimeout(() => { sent.current.view = true; shopEvent(token, shop.id, 'view') }, 2000)
    return () => clearTimeout(t)
  }, [active, shop.id, token])
  useEffect(() => {
    const d = shop.duration || player.duration
    if (isShop && !sent.current.complete && d && currentTime / d > 0.9) { sent.current.complete = true; shopEvent(token, shop.id, 'complete') }
  }, [currentTime, shop.duration, player, shop.id, token])

  const fav = useFavorites()
  const listingId = shop.items[0]?.id
  const faved = !isShop && !!listingId && fav.isFav(listingId)
  const toggleLike = (force?: boolean) => {
    if (!isShop) {
      // у видео из объявления своих лайков нет — сердце кладёт вещь в избранное
      if (!token) { router.push('/login'); return }
      if (listingId && (force !== true || !faved)) fav.toggle(listingId)
      return
    }
    if (!token) { router.push('/login'); return }
    const on = force ?? !like.on
    if (on === like.on) return
    setLike((l) => ({ on, n: l.n + (on ? 1 : -1) }))
    shopLike(token, shop.id, on).then((r) => setLike({ on: r.liked, n: r.likes })).catch(() => setLike((l) => ({ on: !on, n: l.n + (on ? -1 : 1) })))
  }
  // один тап — пауза, два быстрых — лайк с сердечком (как в TikTok)
  const onTap = () => {
    const now = Date.now()
    if (now - lastTap.current < 300) { lastTap.current = 0; setPaused(false); toggleLike(true); setBurst((b) => b + 1); return }
    lastTap.current = now
    setTimeout(() => { if (lastTap.current === now) setPaused((p) => !p) }, 300)
  }
  const share = () => Share.share({ message: `${shop.caption || shop.items[0]?.title || 'PLONK'}\n${SITE}/shops?start=${shop.id}` }).catch(() => {})
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
      <Pressable style={StyleSheet.absoluteFill} onPress={onTap} accessibilityLabel={tr(paused ? 'Смотреть' : 'Пауза')}>
        <VideoView player={player} style={StyleSheet.absoluteFill} contentFit="cover" nativeControls={false} allowsPictureInPicture={false} />
      </Pressable>
      {paused && <View pointerEvents="none" style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center' }]}><Icon name="play" size={56} color="rgba(255,255,255,0.9)" filled /></View>}
      {burst > 0 && <View key={burst} pointerEvents="none" style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center' }]}><Icon name="heart" size={96} color="#FF3B5C" filled /></View>}
      <View style={[s.side, { bottom: bottom + 28 }]}>
        <Pressable style={s.sideAva} onPress={() => shop.author && router.push(`/seller/${shop.author.id}` as never)} accessibilityLabel={shop.author?.name}>
          {shop.author?.avatar ? <Image source={{ uri: mediaUrl(shop.author.avatar) ?? undefined }} style={StyleSheet.absoluteFill} /> : <Text style={s.avaText}>{(shop.author?.name || '?')[0]}</Text>}
        </Pressable>
        <Pressable style={s.sideBtn} onPress={() => toggleLike()} hitSlop={6} accessibilityRole="button" accessibilityLabel={tr('Нравится')} accessibilityState={{ selected: isShop ? like.on : faved }}>
          <Icon name="heart" size={30} color={(isShop ? like.on : faved) ? '#FF3B5C' : '#fff'} filled={isShop ? like.on : faved} />
          <Text style={s.sideText}>{isShop ? (like.n || '') : ''}</Text>
        </Pressable>
        <Pressable style={s.sideBtn} onPress={() => (isShop ? setComments(true) : shop.items[0] && write(shop.items[0]))} hitSlop={6} accessibilityLabel={isShop ? tr('Комментарии') : tr('Спросить продавца')}>
          <Icon name="chat" size={30} color="#fff" />
          <Text style={s.sideText}>{isShop ? (nComments || '') : ''}</Text>
        </Pressable>
        <Pressable style={s.sideBtn} onPress={share} hitSlop={6} accessibilityLabel={tr('Поделиться')}>
          <Icon name="share" size={28} color="#fff" />
        </Pressable>
      </View>
      {comments && <Comments shop={shop} onClose={() => setComments(false)} onCount={setNComments} onAsk={(it) => { setComments(false); write(it) }} bottom={bottom} />}
      {/* затемнение под подписью — на всю ширину и плавное, без резкой границы у колонки кнопок */}
      <LinearGradient pointerEvents="none" colors={['rgba(0,0,0,0)', 'rgba(0,0,0,0.18)', 'rgba(0,0,0,0.62)']} locations={[0, 0.35, 1]} style={s.shade} />
      <View pointerEvents="box-none" style={[s.meta, { paddingBottom: bottom + 18 }]}>
        <View style={k.row}>
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
  side: { position: 'absolute', right: 8, alignItems: 'center', gap: 18, zIndex: 2 },
  sideAva: { width: 46, height: 46, borderRadius: 23, borderWidth: 2, borderColor: '#fff', overflow: 'hidden', backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  sideBtn: { alignItems: 'center', gap: 4, minWidth: 48 },
  sideText: { fontFamily: font[700], fontSize: 12, color: '#fff', textShadowColor: 'rgba(0,0,0,0.5)', textShadowRadius: 2 },
  shade: { position: 'absolute', left: 0, right: 0, bottom: 0, height: '46%' },
  meta: { position: 'absolute', left: 0, right: 76, bottom: 0, paddingHorizontal: 12, paddingTop: 60 },
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
  progressFill: { height: 3, borderRadius: 2, backgroundColor: colors.surface },
})


/** Комментарии шопса: номера и ссылки сервер не пропускает — вопрос о товаре кнопкой «Спросить продавца» в чат. */
function Comments({ shop, onClose, onCount, onAsk, bottom }: { shop: Shop; onClose: () => void; onCount: (f: (n: number) => number) => void; onAsk: (it: ShopItem) => void; bottom: number }) {
  const { token, user } = useAuth()
  const [items, setItems] = useState<ShopComment[] | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  useEffect(() => { shopComments(token, shop.id).then((r) => { setItems(r.items); onCount(() => r.total) }).catch(() => setItems([])) }, [shop.id, token]) // eslint-disable-line react-hooks/exhaustive-deps
  const send = async () => {
    if (!token) { onClose(); router.push('/login'); return }
    const v = text.trim()
    if (!v) return
    setBusy(true); setErr('')
    try { const c = await shopComment(token, shop.id, v); setItems((cur) => [c, ...(cur ?? [])]); setText(''); onCount((n) => n + 1) } catch (e) {
      const st = (e as { status?: number; message?: string })
      setErr(st.message === 'comment_contacts' ? tr('Без телефонов и ссылок — вопрос продавцу задайте в чате') : st.status === 429 ? tr('Слишком часто — попробуйте через пару минут') : tr('Не получилось отправить'))
    }
    setBusy(false)
  }
  const item = shop.items[0]
  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={k.sheetOverlay} onPress={onClose}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <Pressable style={[k.sheet, { height: 520, paddingBottom: bottom + 10 }]} onPress={() => {}}>
            <View style={k.grab} />
            <View style={[k.row, { justifyContent: 'space-between' }]}>
              <Text style={[k.sheetTitle, { marginBottom: 0 }]}>{tr('Комментарии')}</Text>
              {item?.status === 'active' && <Btn small label={tr('Спросить продавца')} onPress={() => onAsk(item)} />}
            </View>
            <ScrollView style={{ flex: 1, marginTop: 10 }} keyboardShouldPersistTaps="handled">
              {items === null ? <ActivityIndicator color={colors.primary} /> : !items.length ? <Text style={k.hint}>{tr('Пока без комментариев — будьте первым')}</Text> : items.map((c) => (
                <View key={c.id} style={{ flexDirection: 'row', gap: 10, paddingVertical: 8 }}>
                  <View style={[s.sideAva, { width: 34, height: 34, borderWidth: 0 }]}>{c.user?.avatar ? <Image source={{ uri: mediaUrl(c.user.avatar) ?? undefined }} style={StyleSheet.absoluteFill} /> : <Text style={s.avaText}>{(c.user?.name || '?')[0]}</Text>}</View>
                  <View style={{ flex: 1 }}>
                    <Text style={k.muted}>{c.user?.name}{c.is_author ? ` · ${tr('автор')}` : ''}</Text>
                    <Text style={k.body}>{c.text}</Text>
                    <View style={[k.row, { gap: 14, marginTop: 4 }]}>
                      {c.can_delete && <Pressable onPress={() => token && shopCommentDelete(token, shop.id, c.id).then(() => { setItems((cur) => (cur ?? []).filter((x) => x.id !== c.id)); onCount((n) => Math.max(0, n - 1)) })}><Text style={k.muted}>{tr('Удалить')}</Text></Pressable>}
                      {!!token && c.user?.id !== user?.id && <Pressable onPress={() => shopCommentReport(token, shop.id, c.id).then(() => setItems((cur) => (cur ?? []).filter((x) => x.id !== c.id)))}><Text style={k.muted}>{tr('Пожаловаться')}</Text></Pressable>}
                    </View>
                  </View>
                </View>
              ))}
            </ScrollView>
            {!!err && <Text style={k.err}>{err}</Text>}
            <View style={[k.row, { paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.border }]}>
              <TextInput value={text} onChangeText={setText} maxLength={500} placeholder={token ? tr('Добавьте комментарий…') : tr('Войдите, чтобы ставить лайки и комментировать')}
                placeholderTextColor={colors.muted} style={[k.input, { flex: 1, borderRadius: 20, paddingVertical: 10 }]} onSubmitEditing={send} returnKeyType="send" />
              <Btn small label={tr('Отправить')} busy={busy} disabled={!text.trim()} onPress={send} />
            </View>
          </Pressable>
        </KeyboardAvoidingView>
      </Pressable>
    </Modal>
  )
}
