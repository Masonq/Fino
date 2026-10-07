import { tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import * as ImagePicker from 'expo-image-picker'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import {
  addListingPhoto, ApiError, deleteListingPhoto, fetchListing, type ListingPatch, textOf, updateListing, type Uploaded, uploadPhoto, reorderListingPhotos, uploadVideo } from '../../src/api'
import { useAuth } from '../../src/auth'
import CityPicker from '../../src/components/CityPicker'
import Segmented from '../../src/components/Segmented'
import Icon from '../../src/components/Icon'
import Sheet, { SheetAction } from '../../src/components/Sheet'
import LocationPicker from '../../src/components/LocationPicker'
import { mediaUrl } from '../../src/config'
import { cityName, CITY_COORDS } from '../../src/format'
import { colors, font } from '../../src/theme'

const MAX = 10
type Shot = { key: string; uri: string; existingId?: string; mime?: string; state: 'done' | 'loading' | 'failed'; uploaded?: Uploaded }

/**
 * Редактирование своего объявления: фото (убрать старые, добавить новые), название, описание, цена, валюта,
 * «Торг уместен», город. Раздел не меняется — так устроен сервер. Сохраняется только изменённое.
 */
export default function EditListing() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [loaded, setLoaded] = useState(false)
  const [orig, setOrig] = useState<Required<Pick<ListingPatch, 'title' | 'description' | 'currency' | 'price_negotiable'>> & { price: number | null; city: string | null ; location_lat: number | null; location_lng: number | null; hide_exact_address: boolean } | null>(null)
  const [shots, setShots] = useState<Shot[]>([])
  const [addOpen, setAddOpen] = useState(false)
  const [point, setPoint] = useState<{ lat: number | null; lng: number | null }>({ lat: null, lng: null })
  const [hideAddr, setHideAddr] = useState(false)
  const [coverBusy, setCoverBusy] = useState(false)
  const [coverErr, setCoverErr] = useState('')
  // «Сделать обложкой» — как на сайте: сразу показываем, сохраняем порядок фото на сервере, при ошибке откатываем
  const makeCover = async (shot: Shot) => {
    if (!token || !shot.existingId) return
    const before = shots
    const next = [shot, ...shots.filter((x) => x.key !== shot.key)]
    setShots(next); setCoverBusy(true); setCoverErr('')
    try { await reorderListingPhotos(token, String(id), next.filter((x) => x.existingId).map((x) => x.existingId as string)) }
    catch { setShots(before); setCoverErr(tr('Не удалось изменить фото, попробуйте ещё раз')) }
    finally { setCoverBusy(false) }
  }
  const [removed, setRemoved] = useState<string[]>([])
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState<'EUR' | 'RSD'>('EUR')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState<string | null>(null)
  const [cityOpen, setCityOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchListing(String(id)).then((l) => {
      const t = textOf(l)
      const cur = (l.currency === 'RSD' ? 'RSD' : 'EUR') as 'EUR' | 'RSD'
      setOrig({ title: t.title, description: t.description, price: l.price ?? null, currency: cur, price_negotiable: !!l.price_negotiable, city: l.city ?? null, location_lat: l.location_lat ?? null, location_lng: l.location_lng ?? null, hide_exact_address: !!l.hide_exact_address })
      setTitle(t.title); setDesc(t.description); setPrice(l.price != null ? String(Math.round(l.price)) : '')
      setCurrency(cur); setNegotiable(!!l.price_negotiable); setCity(l.city ?? null)
      // видео тоже показываем (раньше отфильтровывалось — его нельзя было ни увидеть, ни удалить)
      setPoint({ lat: l.location_lat ?? null, lng: l.location_lng ?? null }); setHideAddr(!!l.hide_exact_address)
      setShots(l.photos.map((p) => ({ key: p.id, existingId: p.id, uri: mediaUrl(p.thumbnail_url || p.url) as string, state: 'done' as const, mime: p.is_video ? 'video/mp4' : 'image/jpeg' })))
      setLoaded(true)
    }).catch(() => setError(tr('Не удалось открыть объявление')))
  }, [id])

  const upload = async (shot: Shot) => {
    setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'loading' } : x)))
    try {
      const up = shot.mime?.startsWith('video') ? await uploadVideo(token as string, shot.uri, shot.mime) : await uploadPhoto(token as string, shot.uri, shot.mime)
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'done', uploaded: up, uri: up.is_video && up.thumbnail_url ? (mediaUrl(up.thumbnail_url) as string) : x.uri } : x)))
    } catch (e) {
      if (shot.mime?.startsWith('video')) {
        const code = e instanceof ApiError ? e.message : ''
        const msg: Record<string, string> = {
          unsupported_format: 'Формат не поддерживается — снимите видео обычной камерой телефона', file_too_large: 'Файл слишком большой',
          video_too_long: 'Видео слишком длинное — до полутора минут', processing_failed: 'Не удалось обработать видео — попробуйте другое',
        }
        setShots((s) => s.filter((x) => x.key !== shot.key))
        setCoverErr(tr(msg[code] ?? 'Не получилось загрузить видео'))
        return
      }
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'failed' } : x)))
    }
  }

  // «Добавить видео» — одно, до полутора минут, как на сайте
  const hasVideo = shots.some((x) => x.mime?.startsWith('video'))
  const addVideo = async () => {
    setCoverErr('')
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) { Alert.alert(tr('Нет доступа'), tr('Разрешите доступ к фото в настройках телефона.')); return }
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], videoMaxDuration: 90, quality: 1 })
    if (res.canceled || !res.assets[0]) return
    const shot: Shot = { key: `video-${Date.now()}`, uri: '', mime: res.assets[0].mimeType || 'video/mp4', state: 'loading' }
    setShots((s) => [...s, { ...shot, uri: res.assets[0].uri }])
    upload({ ...shot, uri: res.assets[0].uri })
  }

  const add = async (from: 'camera' | 'library') => {
    const left = MAX - shots.length
    if (left <= 0) return
    const perm = from === 'camera' ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) { Alert.alert(tr('Нет доступа'), tr('Разрешите доступ в настройках телефона.')); return }
    const opts: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.85, allowsMultipleSelection: from === 'library', selectionLimit: left }
    const res = from === 'camera' ? await ImagePicker.launchCameraAsync(opts) : await ImagePicker.launchImageLibraryAsync(opts)
    if (res.canceled) return
    const fresh: Shot[] = res.assets.slice(0, left).map((a, i) => ({ key: `new-${Date.now()}-${i}`, uri: a.uri, mime: a.mimeType || 'image/jpeg', state: 'loading' }))
    setShots((s) => [...s, ...fresh])
    fresh.forEach(upload)
  }

  const remove = (s: Shot) => {
    setShots((all) => all.filter((x) => x.key !== s.key))
    if (s.existingId) setRemoved((r) => [...r, s.existingId as string])
  }

  const save = async () => {
    if (!orig || !token) return
    setError('')
    if (shots.filter((s) => s.state === 'done').length === 0) { setError(tr('Оставьте хотя бы одно фото')); return }
    if (shots.some((s) => s.state === 'loading')) { setError(tr('Дождитесь загрузки фото')); return }
    if (title.trim().length < 3) { setError(tr('Название — хотя бы 3 буквы')); return }
    setSaving(true)
    try {
      const patch: ListingPatch = {}
      const p = price ? Number(price) : null
      if (title.trim() !== orig.title) patch.title = title.trim()
      if (desc.trim() !== orig.description) patch.description = desc.trim()
      if (p !== orig.price) patch.price = p
      if (currency !== orig.currency) patch.currency = currency
      if (negotiable !== orig.price_negotiable) patch.price_negotiable = negotiable
      if (city !== orig.city) patch.city = city
      // точка на карте — только если изменилась
      if (point.lat !== (orig.location_lat ?? null) || point.lng !== (orig.location_lng ?? null)) { patch.location_lat = point.lat; patch.location_lng = point.lng }
      if (hideAddr !== !!orig.hide_exact_address) patch.hide_exact_address = hideAddr
      if (Object.keys(patch).length) await updateListing(token, String(id), patch)
      for (const photoId of removed) await deleteListingPhoto(token, String(id), photoId)
      for (const s of shots) if (!s.existingId && s.uploaded) await addListingPhoto(token, String(id), s.uploaded)
      router.back()
    } catch (e) {
      setError(e instanceof ApiError && e.message ? e.message : tr('Не удалось сохранить. Проверьте интернет и попробуйте ещё раз.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.head}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}>
          <Ionicons name="chevron-back" size={26} color={colors.ink} />
        </Pressable>
        <Text style={styles.h1}>{tr('Редактирование')}</Text>
      </View>
      {!loaded ? (error ? <Text style={styles.hint}>{error}</Text> : <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} />) : (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
            <Text style={styles.label}>{tr('Фото')} <Text style={styles.count}>{shots.length}/{MAX}</Text></Text>
            <View style={styles.grid}>
              {shots.map((s, i) => (
                <Pressable key={s.key} style={styles.shot} disabled={s.state !== 'failed'} onPress={() => upload(s)}>
                  {s.mime?.startsWith('video') && !s.uploaded && !s.existingId ? <View style={[styles.shotImg, { backgroundColor: colors.ink }]} /> : <Image source={{ uri: s.uri }} style={styles.shotImg} contentFit="cover" />}
                  {s.mime?.startsWith('video') && s.state === 'done' && <View style={styles.playBadge}><Icon name="play" size={12} color="#fff" filled /></View>}
                  {s.state === 'loading' && <View style={styles.overlay}><ActivityIndicator color="#fff" /></View>}
                  {s.state === 'failed' && <View style={[styles.overlay, { backgroundColor: 'rgba(180,35,24,0.72)' }]}><Ionicons name="refresh" size={22} color="#fff" /></View>}
                  {i === 0
                    ? <Text style={styles.cover}>{tr('Обложка')}</Text>
                    : !!s.existingId && !s.mime?.startsWith('video') && <Pressable style={styles.makeCover} onPress={() => makeCover(s)} disabled={coverBusy}><Text style={styles.makeCoverText}>{tr('Сделать обложкой')}</Text></Pressable>}
                  <Pressable style={styles.remove} onPress={() => remove(s)} hitSlop={6} accessibilityLabel={tr('Убрать фото')}><Ionicons name="close" size={14} color="#fff" /></Pressable>
                </Pressable>
              ))}
              {shots.length < MAX && (
                <Pressable style={styles.addTile} onPress={() => setAddOpen(true)} accessibilityLabel={tr('Добавить фото')}>
                  <Icon name="plus" size={20} color={colors.ink} strokeWidth={2} />
                  <Text style={styles.addTileText}>{tr('Фото')}</Text>
                </Pressable>
              )}
              {!hasVideo && (
                <Pressable style={styles.addTile} onPress={addVideo} accessibilityLabel={tr('Добавить видео')}>
                  <Icon name="video" size={20} color={colors.ink} />
                  <Text style={[styles.addTileText, { textAlign: 'center' }]}>{tr('Добавить видео')}</Text>
                </Pressable>
              )}
            </View>
            {!!coverErr && <Text style={styles.coverErr}>{coverErr}</Text>}

            <Text style={styles.label}>{tr('Заголовок')}</Text>
            <TextInput value={title} onChangeText={setTitle} style={styles.input} maxLength={120} />
            <Text style={styles.label}>{tr('Описание')}</Text>
            <TextInput value={desc} onChangeText={setDesc} style={[styles.input, styles.area]} multiline maxLength={5000} textAlignVertical="top" />
            <Text style={styles.label}>{tr('Цена')}</Text>
            <View style={styles.priceBox}>
              <TextInput value={price} onChangeText={(v) => setPrice(v.replace(/\D/g, '').slice(0, 9))} placeholder={tr('Пусто — «цена не указана»')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.priceInput} />
              <View style={{ alignSelf: 'center' }}><Segmented options={[{ key: 'RSD', label: 'RSD' }, { key: 'EUR', label: 'EUR' }]} value={currency} onChange={(c) => setCurrency(c as 'EUR' | 'RSD')} /></View>
            </View>
            <Pressable style={styles.check} onPress={() => setNegotiable(!negotiable)} accessibilityRole="checkbox" accessibilityState={{ checked: negotiable }}>
              <View style={[styles.box, negotiable && styles.boxOn]}>{negotiable && <Icon name="check" size={12} color="#fff" />}</View>
              <Text style={styles.checkText}>{tr('Торг уместен')}</Text>
            </Pressable>
            <Text style={styles.label}>{tr('Город')}</Text>
            <Pressable style={styles.select} onPress={() => setCityOpen(true)}>
              <Text style={styles.selectText}>{city ? cityName(city) : tr('Не указан')}</Text>
              <Ionicons name="chevron-forward" size={18} color={colors.muted} />
            </Pressable>
            <LocationPicker lat={point.lat} lng={point.lng} hide={hideAddr} center={city ? CITY_COORDS[city] : undefined} onChange={(a, b) => setPoint({ lat: a, lng: b })} onHide={setHideAddr} />
            {!!error && <Text style={[styles.hint, { marginTop: 14 }]}>{error}</Text>}
            <Pressable style={[styles.cta, saving && { opacity: 0.6 }]} disabled={saving} onPress={save} accessibilityRole="button" accessibilityLabel={tr('Сохранить изменения')}>
              {saving ? <ActivityIndicator color={colors.onInverse} /> : <Text style={styles.ctaText}>{tr('Сохранить')}</Text>}
            </Pressable>
            <Text style={styles.small}>{tr('После изменения фото, названия, описания или цены объявление снова пройдёт проверку')}</Text>
          </ScrollView>
        </KeyboardAvoidingView>
      )}
      <CityPicker visible={cityOpen} value={city} onPick={setCity} onClose={() => setCityOpen(false)} />
      <Sheet visible={addOpen} onClose={() => setAddOpen(false)}>
        <SheetAction label={tr('Сфотографировать')} icon={<Icon name="camera" size={20} color={colors.ink} />} onPress={() => { setAddOpen(false); add('camera') }} />
        <SheetAction label={tr('Выбрать из галереи')} icon={<Icon name="image" size={20} color={colors.ink} />} onPress={() => { setAddOpen(false); add('library') }} />
      </Sheet>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  h1: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  form: { paddingHorizontal: 16, paddingBottom: 40 },
  // как подписи полей формы сайта: 12,5 / 700, серо-зелёные
  label: { fontSize: 12.5, fontFamily: font[700], color: colors.inkSoft, marginTop: 16, marginBottom: 6 },
  labelRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, marginBottom: 8 },
  count: { color: colors.muted, fontFamily: font[600], fontSize: 14 },
  playBadge: { position: 'absolute', left: 6, top: 6, width: 22, height: 22, borderRadius: 11, backgroundColor: 'rgba(28,38,32,0.7)', alignItems: 'center', justifyContent: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  addTile: { width: 92, height: 92, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', gap: 4 },
  addTileText: { fontSize: 12.5, fontFamily: font[700], color: colors.ink },
  makeCover: { position: 'absolute', left: 4, right: 4, bottom: 4, borderRadius: 7, backgroundColor: 'rgba(14,69,49,0.86)', paddingVertical: 3, alignItems: 'center' },
  makeCoverText: { color: '#fff', fontSize: 9.5, fontFamily: font[800], textAlign: 'center' },
  coverErr: { fontSize: 13, fontFamily: font[600], color: colors.danger, marginTop: 6 },
  priceBox: { flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingLeft: 14, paddingRight: 4 },
  priceInput: { flex: 1, fontSize: 16, fontFamily: font[500], color: colors.ink, paddingVertical: 10 },
  check: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 12 },
  box: { width: 20, height: 20, borderRadius: 5, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  boxOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkText: { fontSize: 14.5, fontFamily: font[700], color: colors.ink },
  addShot: { width: 92, height: 92, borderRadius: 14, backgroundColor: colors.primarySoft, borderWidth: 1.5, borderColor: 'rgba(14,159,110,0.3)', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center', gap: 4 },
  addText: { fontSize: 12.5, fontFamily: font[700], color: colors.primaryDeep },
  shot: { width: 92, height: 92, borderRadius: 14, overflow: 'hidden', backgroundColor: colors.photo },
  shotImg: { width: 92, height: 92 },
  overlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
  cover: { position: 'absolute', left: 6, bottom: 6, backgroundColor: 'rgba(28,38,32,0.7)', color: '#fff', fontSize: 10.5, fontFamily: font[800], paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
  remove: { position: 'absolute', top: 5, right: 5, width: 22, height: 22, borderRadius: 11, backgroundColor: 'rgba(28,38,32,0.72)', alignItems: 'center', justifyContent: 'center' },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontFamily: font[400], fontSize: 16, color: colors.ink },
  area: { minHeight: 120, paddingTop: 13, paddingBottom: 13 },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
  switchText: { fontFamily: font[400], fontSize: 16, color: colors.ink },
  select: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center', gap: 8 },
  selectText: { flex: 1, fontFamily: font[400], fontSize: 16, color: colors.ink, paddingVertical: 12 },
  hint: { fontFamily: font[400], fontSize: 13.5, color: colors.danger, marginTop: 6, paddingHorizontal: 16 },
  cta: { marginTop: 26, height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  small: { fontFamily: font[400], fontSize: 13, color: colors.muted, textAlign: 'center', marginTop: 10 },
})
