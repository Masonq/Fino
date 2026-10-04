import { Image } from 'expo-image'
import * as ImagePicker from 'expo-image-picker'
import { router, useLocalSearchParams } from 'expo-router'
import { useVideoPlayer, VideoView } from 'expo-video'
import { useEffect, useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { fetchFeed, type FeedItem, myListings } from '../../src/api'
import { useAuth } from '../../src/auth'
import { mediaUrl } from '../../src/config'
import { tr } from '../../src/i18n'
import Icon from '../../src/components/Icon'
import { Btn, Field, Header, k } from '../../src/components/Kit'
import { money, type Shop, shopGet, shopOrders, shopsMine, shopSubmit, shopUpdate, shopUpload } from '../../src/social'
import { colors, font } from '../../src/theme'

const MAX_ITEMS = 5
type Pick = { id: string; title: string; photo?: string | null; price?: number | null; currency?: string | null; appear_at: number }
const photoOf = (l: FeedItem) => l.cover_photo || l.photos?.[0] || null

/** Снять шопс: видео до минуты → до 5 объявлений со своей секундой → подпись → на проверку. */
export default function ShopEditor() {
  const { id, order } = useLocalSearchParams<{ id?: string; order?: string }>()
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const [shop, setShop] = useState<Shop | null>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [caption, setCaption] = useState('')
  const [items, setItems] = useState<Pick[]>([])
  const [mine, setMine] = useState<FeedItem[]>([])
  const [creator, setCreator] = useState(false)
  const [q, setQ] = useState('')
  const [found, setFound] = useState<FeedItem[]>([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const ready = !!shop && shop.status !== 'processing' && shop.status !== 'failed'
  const player = useVideoPlayer(ready && shop?.video_url ? mediaUrl(shop.video_url) : null, (p) => { p.loop = true; p.muted = true })

  useEffect(() => { if (!token) router.replace('/login') }, [token])
  useEffect(() => {
    if (!token) return
    myListings(token).then((r) => setMine(r.items.filter((l) => l.status === 'active'))).catch(() => {})
    shopsMine(token).then((r) => setCreator(r.creator?.status === 'approved')).catch(() => {})
    if (order) shopOrders(token, 'taken').then((r) => {
      const o = r.items.find((x) => x.id === order)
      if (o?.listing) setItems((cur) => (cur.some((x) => x.id === o.listing!.id) ? cur : [{ ...o.listing!, appear_at: 0 }, ...cur]))
    }).catch(() => {})
  }, [token, order])
  useEffect(() => {
    if (!id || !token) return
    shopGet(token, id).then((s) => { setShop(s); setCaption(s.caption || ''); setItems(s.items.map((it) => ({ ...it, appear_at: it.appear_at || 0 }))) }).catch(() => setErr(tr('Не удалось открыть шопс')))
  }, [id, token])
  // видео обрабатывается на сервере — спрашиваем раз в 2 секунды
  useEffect(() => {
    if (shop?.status !== 'processing' || !token) return undefined
    const t = setInterval(() => shopGet(token, shop.id).then((s) => { if (s.status !== 'processing') setShop(s) }).catch(() => {}), 2000)
    return () => clearInterval(t)
  }, [shop?.status, shop?.id, token])
  useEffect(() => {
    if (!creator || q.trim().length < 2) { setFound([]); return undefined }
    const t = setTimeout(() => fetchFeed({ tab: 'all', offset: 0, q: q.trim() }).then((r) => setFound(r.items)).catch(() => setFound([])), 300)
    return () => clearTimeout(t)
  }, [q, creator])

  const pickVideo = async () => {
    if (!token) return
    setErr('')
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], videoMaxDuration: 60, quality: 1 })
    if (res.canceled || !res.assets[0]) return
    const a = res.assets[0]
    if (a.duration && a.duration > 61000) { setErr(tr('Видео длиннее минуты — обрежьте до 60 секунд')); return }
    setProgress(0)
    try { setShop(await shopUpload(token, a.uri, a.mimeType || 'video/mp4', setProgress)) } catch (e) {
      const code = (e as { message?: string }).message
      setErr(code === 'file_too_large' ? tr('Видео больше 150 МБ') : code === 'unsupported_format' ? tr('Такой формат видео не подходит') : tr('Не удалось загрузить видео'))
    }
    setProgress(null)
  }
  const add = (l: FeedItem) => {
    if (items.length >= MAX_ITEMS || items.some((x) => x.id === l.id)) return
    setItems([...items, { id: l.id, title: l.title, photo: photoOf(l), price: l.price, currency: l.currency, appear_at: Math.round((player.currentTime || 0) * 10) / 10 }])
    setQ('')
  }
  const setAt = (lid: string) => setItems(items.map((x) => (x.id === lid ? { ...x, appear_at: Math.round((player.currentTime || 0) * 10) / 10 } : x)))
  const save = async (submit: boolean) => {
    if (!shop || !token) return
    if (submit && !items.length) { setErr(tr('Прикрепите хотя бы одно объявление')); return }
    setBusy(true); setErr('')
    try {
      await shopUpdate(token, shop.id, { caption, items: items.map((x) => ({ listing_id: x.id, appear_at: x.appear_at })), order_id: order || null })
      if (submit) await shopSubmit(token, shop.id)
      router.replace('/shops/mine' as never)
    } catch (e) {
      const code = (e as { message?: string }).message
      setErr(code === 'only_own_listings' ? tr('Без статуса автора можно прикреплять только свои объявления') : tr('Не получилось сохранить'))
    }
    setBusy(false)
  }

  const candidates = (creator && q.trim().length >= 2 ? found : mine).filter((l) => !items.some((x) => x.id === l.id))
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Header title={id ? tr('Шопс') : tr('Новый шопс')} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: insets.bottom + 32 }} keyboardShouldPersistTaps="handled">
          {!shop ? (
            <Pressable style={s.drop} onPress={pickVideo} disabled={progress != null} accessibilityRole="button">
              {progress != null ? (
                <><View style={s.bar}><View style={[s.barFill, { width: `${Math.round(progress * 100)}%` }]} /></View><Text style={k.muted}>{tr('Загружаем… {p}%', { p: Math.round(progress * 100) })}</Text></>
              ) : (
                <><Icon name="video" size={40} color={colors.inkSoft} /><Text style={s.dropTitle}>{tr('Выберите видео')}</Text><Text style={[k.muted, { textAlign: 'center' }]}>{tr('Вертикальное, до 60 секунд. Покажите вещь в деле — так смотрят дольше')}</Text></>
              )}
            </Pressable>
          ) : (
            <View style={{ alignItems: 'center', gap: 8 }}>
              {shop.status === 'processing' && <View style={[k.row, { paddingVertical: 40 }]}><ActivityIndicator color={colors.primary} /><Text style={k.body}>{tr('Готовим видео — можно пока выбрать товары')}</Text></View>}
              {shop.status === 'failed' && <Text style={k.err}>{tr('Не удалось обработать видео. Попробуйте другое')}</Text>}
              {ready && <VideoView player={player} style={s.preview} nativeControls contentFit="contain" />}
            </View>
          )}
          {!!shop && (
            <>
              <Text style={k.section}>{tr('Товары в видео · {n} из {max}', { n: items.length, max: MAX_ITEMS })}</Text>
              {items.map((x) => (
                <View key={x.id} style={[k.pick, { borderColor: colors.primary }]}>
                  {!!x.photo && <Image source={{ uri: mediaUrl(x.photo) ?? undefined }} style={k.thumb} />}
                  <View style={{ flex: 1 }}><Text style={k.name} numberOfLines={1}>{x.title}</Text><Text style={k.muted}>{money(x.price, x.currency)} · {tr('с {s} с', { s: x.appear_at })}</Text></View>
                  {ready && <Btn small kind="ghost" label={tr('С этой секунды')} onPress={() => setAt(x.id)} />}
                  <Pressable style={s.x} onPress={() => setItems(items.filter((y) => y.id !== x.id))} accessibilityLabel={tr('Удалить')}><Icon name="close" size={16} color={colors.ink} /></Pressable>
                </View>
              ))}
              {ready && items.length > 0 && <Text style={k.hint}>{tr('Поставьте видео на момент, где появляется вещь, и нажмите «С этой секунды» — карточка всплывёт ровно тогда')}</Text>}
              {items.length < MAX_ITEMS && (
                <>
                  {creator && <Field label={tr('Найти объявление на PLONK')} value={q} onChangeText={setQ} />}
                  {candidates.slice(0, 20).map((l) => (
                    <Pressable key={l.id} style={k.pick} onPress={() => add(l)}>
                      {!!photoOf(l) && <Image source={{ uri: mediaUrl(photoOf(l)) ?? undefined }} style={k.thumb} />}
                      <View style={{ flex: 1 }}><Text style={k.name} numberOfLines={1}>{l.title}</Text><Text style={k.muted}>{money(l.price, l.currency)}</Text></View>
                      <View style={s.add}><Icon name="plus" size={16} color={colors.primaryDeep} /></View>
                    </Pressable>
                  ))}
                  {!candidates.length && <Text style={k.hint}>{creator ? tr('Ваши объявления — сверху; чужие найдите поиском') : tr('У вас нет активных объявлений. Разместите вещь, чтобы прикрепить её к шопсу')}</Text>}
                </>
              )}
              <Field label={tr('Подпись')} value={caption} maxLength={500} multiline placeholder={tr('Пара слов о ролике')} onChangeText={setCaption} />
              {!!err && <Text style={k.err}>{err}</Text>}
              <View style={k.actions}>
                <View style={{ flex: 1 }}><Btn kind="ghost" label={tr('Сохранить')} onPress={() => save(false)} busy={busy} /></View>
                <View style={{ flex: 1 }}><Btn label={ready ? tr('Опубликовать') : tr('Ждём видео…')} disabled={!ready} busy={busy} onPress={() => save(true)} /></View>
              </View>
              <Text style={k.hint}>{tr('Шопс проверяют модераторы и показывают 30 дней. Вещь должна быть видна в кадре не меньше 3 секунд')}</Text>
            </>
          )}
          {!shop && !!err && <Text style={k.err}>{err}</Text>}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const s = StyleSheet.create({
  drop: { minHeight: 260, borderRadius: 18, borderWidth: 2, borderStyle: 'dashed', borderColor: colors.border, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', gap: 10, padding: 24 },
  dropTitle: { fontFamily: font[800], fontSize: 17, color: colors.ink },
  bar: { width: '80%', height: 6, borderRadius: 3, backgroundColor: colors.sunken, overflow: 'hidden' },
  barFill: { height: 6, backgroundColor: colors.primary },
  preview: { width: 220, height: 390, borderRadius: 16, backgroundColor: '#000' },
  x: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  add: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
})
