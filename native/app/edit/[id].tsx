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
  addListingPhoto, ApiError, deleteListingPhoto, fetchListing, type ListingPatch, textOf, updateListing, type Uploaded, uploadPhoto,
} from '../../src/api'
import { useAuth } from '../../src/auth'
import CityPicker from '../../src/components/CityPicker'
import Segmented from '../../src/components/Segmented'
import { mediaUrl } from '../../src/config'
import { cityName } from '../../src/format'
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
  const [orig, setOrig] = useState<Required<Pick<ListingPatch, 'title' | 'description' | 'currency' | 'price_negotiable'>> & { price: number | null; city: string | null } | null>(null)
  const [shots, setShots] = useState<Shot[]>([])
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
      setOrig({ title: t.title, description: t.description, price: l.price ?? null, currency: cur, price_negotiable: !!l.price_negotiable, city: l.city ?? null })
      setTitle(t.title); setDesc(t.description); setPrice(l.price != null ? String(Math.round(l.price)) : '')
      setCurrency(cur); setNegotiable(!!l.price_negotiable); setCity(l.city ?? null)
      setShots(l.photos.filter((p) => !p.is_video).map((p) => ({ key: p.id, existingId: p.id, uri: mediaUrl(p.thumbnail_url || p.url) as string, state: 'done' })))
      setLoaded(true)
    }).catch(() => setError(tr('Не удалось открыть объявление')))
  }, [id])

  const upload = async (shot: Shot) => {
    setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'loading' } : x)))
    try {
      const up = await uploadPhoto(token as string, shot.uri, shot.mime)
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'done', uploaded: up } : x)))
    } catch {
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'failed' } : x)))
    }
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
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
              {shots.length < MAX && (
                <>
                  <Pressable style={styles.addShot} onPress={() => add('camera')} accessibilityLabel={tr('Сфотографировать')}><Ionicons name="camera-outline" size={26} color={colors.primaryDeep} /><Text style={styles.addText}>{tr('Камера')}</Text></Pressable>
                  <Pressable style={styles.addShot} onPress={() => add('library')} accessibilityLabel={tr('Выбрать из галереи')}><Ionicons name="images-outline" size={26} color={colors.primaryDeep} /><Text style={styles.addText}>{tr('Галерея')}</Text></Pressable>
                </>
              )}
              {shots.map((s, i) => (
                <Pressable key={s.key} style={styles.shot} disabled={s.state !== 'failed'} onPress={() => upload(s)}>
                  <Image source={{ uri: s.uri }} style={styles.shotImg} contentFit="cover" />
                  {s.state === 'loading' && <View style={styles.overlay}><ActivityIndicator color="#fff" /></View>}
                  {s.state === 'failed' && <View style={[styles.overlay, { backgroundColor: 'rgba(180,35,24,0.72)' }]}><Ionicons name="refresh" size={22} color="#fff" /></View>}
                  {i === 0 && <Text style={styles.cover}>{tr('Обложка')}</Text>}
                  <Pressable style={styles.remove} onPress={() => remove(s)} hitSlop={6} accessibilityLabel={tr('Убрать фото')}><Ionicons name="close" size={14} color="#fff" /></Pressable>
                </Pressable>
              ))}
            </ScrollView>

            <Text style={styles.label}>{tr('Название')}</Text>
            <TextInput value={title} onChangeText={setTitle} style={styles.input} maxLength={120} />
            <Text style={styles.label}>{tr('Описание')}</Text>
            <TextInput value={desc} onChangeText={setDesc} style={[styles.input, styles.area]} multiline maxLength={5000} textAlignVertical="top" />
            <View style={styles.labelRow}>
              <Text style={styles.label}>{tr('Цена')}</Text>
              <Segmented options={[{ key: 'EUR', label: '€' }, { key: 'RSD', label: 'RSD' }]} value={currency} onChange={(c) => setCurrency(c as 'EUR' | 'RSD')} />
            </View>
            <TextInput value={price} onChangeText={(v) => setPrice(v.replace(/\D/g, '').slice(0, 9))} placeholder={tr('Пусто — «цена не указана»')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.input} />
            <View style={styles.switchRow}>
              <Text style={styles.switchText}>{tr('Торг уместен')}</Text>
              <Switch value={negotiable} onValueChange={setNegotiable} trackColor={{ true: colors.primary, false: '#D8DCD8' }} />
            </View>
            <Text style={styles.label}>{tr('Город')}</Text>
            <Pressable style={styles.select} onPress={() => setCityOpen(true)}>
              <Text style={styles.selectText}>{city ? cityName(city) : tr('Не указан')}</Text>
              <Ionicons name="chevron-forward" size={18} color={colors.muted} />
            </Pressable>
            {!!error && <Text style={[styles.hint, { marginTop: 14 }]}>{error}</Text>}
            <Pressable style={[styles.cta, saving && { opacity: 0.6 }]} disabled={saving} onPress={save} accessibilityRole="button" accessibilityLabel={tr('Сохранить изменения')}>
              {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Сохранить')}</Text>}
            </Pressable>
            <Text style={styles.small}>{tr('После правок объявление может уйти на повторную проверку.')}</Text>
          </ScrollView>
        </KeyboardAvoidingView>
      )}
      <CityPicker visible={cityOpen} value={city} onPick={setCity} onClose={() => setCityOpen(false)} />
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  h1: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  form: { paddingHorizontal: 16, paddingBottom: 40 },
  label: { fontSize: 16, fontFamily: font[800], color: colors.ink, marginTop: 18, marginBottom: 8 },
  labelRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, marginBottom: 8 },
  count: { color: colors.muted, fontFamily: font[600], fontSize: 14 },
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
  hint: { fontFamily: font[400], fontSize: 13.5, color: '#B42318', marginTop: 6, paddingHorizontal: 16 },
  cta: { marginTop: 26, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  small: { fontFamily: font[400], fontSize: 13, color: colors.muted, textAlign: 'center', marginTop: 10 },
})
