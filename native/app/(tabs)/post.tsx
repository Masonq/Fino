import { tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import * as ImagePicker from 'expo-image-picker'
import { router } from 'expo-router'
import { useState } from 'react'
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { ApiError, type Category, createListing, type Uploaded, uploadPhoto } from '../../src/api'
import { useAuth } from '../../src/auth'
import CategoryPicker from '../../src/components/CategoryPicker'
import CityPicker from '../../src/components/CityPicker'
import Segmented from '../../src/components/Segmented'
import { cityName } from '../../src/format'
import { colors } from '../../src/theme'

const MAX = 10
type Shot = { key: string; uri: string; mime: string; state: 'loading' | 'done' | 'failed'; uploaded?: Uploaded }

/**
 * Размещение объявления. Фото — с камеры или из галереи, до 10, каждое загружается сразу (первое — обложка).
 * Раздел — по дереву, название, описание, цена (€ / RSD), «Торг уместен», город. Проверка — подсказками
 * у полей. После отправки — «Отправлено на проверку» и переход в мои объявления.
 */
export default function Post() {
  const { token, ready } = useAuth()
  const [shots, setShots] = useState<Shot[]>([])
  const [cat, setCat] = useState<{ c: Category; path: string } | null>(null)
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState<'EUR' | 'RSD'>('EUR')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState<string | null>('beograd')
  const [catOpen, setCatOpen] = useState(false)
  const [cityOpen, setCityOpen] = useState(false)
  const [tried, setTried] = useState(false)
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState<{ id: string } | null>(null)
  const [error, setError] = useState('')

  if (!ready) return <SafeAreaView style={styles.page} />
  if (!token) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <View style={styles.circle}><Ionicons name="add" size={32} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>{tr('Разместите объявление')}</Text>
        <Text style={styles.text}>{tr('Это бесплатно. Войдите, чтобы покупатели могли вам написать.')}</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>{tr('Войти')}</Text></Pressable>
      </SafeAreaView>
    )
  }

  if (done) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <View style={[styles.circle, { backgroundColor: colors.primary }]}><Ionicons name="checkmark" size={34} color="#fff" /></View>
        <Text style={styles.title}>{tr('Отправлено на проверку')}</Text>
        <Text style={styles.text}>{tr('Обычно это занимает несколько минут. Когда объявление опубликуют, оно появится в ленте.')}</Text>
        <Pressable style={styles.cta} onPress={() => { reset(); router.navigate('/profile') }}><Text style={styles.ctaText}>{tr('Мои объявления')}</Text></Pressable>
        <Pressable onPress={reset} style={{ marginTop: 6, padding: 10 }}><Text style={styles.link}>{tr('Разместить ещё')}</Text></Pressable>
      </SafeAreaView>
    )
  }

  function reset() {
    setShots([]); setCat(null); setTitle(''); setDesc(''); setPrice(''); setNegotiable(false); setTried(false); setDone(null); setError('')
  }

  const upload = async (shot: Shot) => {
    setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'loading' } : x)))
    try {
      const up = await uploadPhoto(token, shot.uri, shot.mime)
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'done', uploaded: up } : x)))
    } catch {
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'failed' } : x)))
    }
  }

  const add = async (from: 'camera' | 'library') => {
    const left = MAX - shots.length
    if (left <= 0) return
    const perm = from === 'camera' ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) {
      Alert.alert(tr('Нет доступа'), from === 'camera' ? tr('Разрешите доступ к камере в настройках телефона.') : tr('Разрешите доступ к фото в настройках телефона.'))
      return
    }
    const opts: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.85, allowsMultipleSelection: from === 'library', selectionLimit: left }
    const res = from === 'camera' ? await ImagePicker.launchCameraAsync(opts) : await ImagePicker.launchImageLibraryAsync(opts)
    if (res.canceled) return
    const fresh: Shot[] = res.assets.slice(0, left).map((a, i) => ({ key: `${Date.now()}-${i}`, uri: a.uri, mime: a.mimeType || 'image/jpeg', state: 'loading' }))
    setShots((s) => [...s, ...fresh])
    fresh.forEach(upload)
  }

  const problems = {
    photos: shots.filter((s) => s.state === 'done').length === 0 ? tr('Добавьте хотя бы одно фото') : shots.some((s) => s.state === 'loading') ? tr('Дождитесь загрузки фото') : '',
    cat: cat ? '' : tr('Выберите раздел'),
    title: title.trim().length < 3 ? tr('Название — хотя бы 3 буквы') : '',
    desc: desc.trim().length < 10 ? tr('Опишите вещь хотя бы парой предложений') : '',
  }
  const ok = !Object.values(problems).some(Boolean)

  const submit = async () => {
    setTried(true); setError('')
    if (!ok || !cat) return
    setSending(true)
    try {
      const res = await createListing(token, {
        category_id: cat.c.id, title: title.trim(), description: desc.trim(),
        price: price ? Number(price) : null, currency, price_negotiable: negotiable, city,
        photos: shots.filter((s) => s.state === 'done' && s.uploaded).map((s) => s.uploaded as Uploaded),
      })
      setDone({ id: res.id })
    } catch (e) {
      setError(e instanceof ApiError && e.message ? e.message : tr('Не удалось отправить. Проверьте интернет и попробуйте ещё раз.'))
    } finally {
      setSending(false)
    }
  }

  const hint = (text: string) => (tried && text ? <Text style={styles.hint}>{text}</Text> : null)

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Text style={styles.h1}>{tr('Новое объявление')}</Text>

          <Text style={styles.label}>{tr('Фото')} <Text style={styles.count}>{shots.length}/{MAX}</Text></Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.shots}>
            {shots.length < MAX && (
              <>
                <Pressable style={styles.addShot} onPress={() => add('camera')} accessibilityLabel={tr('Сфотографировать')}>
                  <Ionicons name="camera-outline" size={26} color={colors.primaryDeep} />
                  <Text style={styles.addText}>{tr('Камера')}</Text>
                </Pressable>
                <Pressable style={styles.addShot} onPress={() => add('library')} accessibilityLabel={tr('Выбрать из галереи')}>
                  <Ionicons name="images-outline" size={26} color={colors.primaryDeep} />
                  <Text style={styles.addText}>{tr('Галерея')}</Text>
                </Pressable>
              </>
            )}
            {shots.map((s, i) => (
              <Pressable key={s.key} style={styles.shot} disabled={s.state !== 'failed'} onPress={() => upload(s)}>
                <Image source={{ uri: s.uri }} style={styles.shotImg} contentFit="cover" />
                {s.state === 'loading' && <View style={styles.shotOverlay}><ActivityIndicator color="#fff" /></View>}
                {s.state === 'failed' && <View style={[styles.shotOverlay, { backgroundColor: 'rgba(180,35,24,0.72)' }]}><Ionicons name="refresh" size={22} color="#fff" /></View>}
                {i === 0 && <Text style={styles.cover}>{tr('Обложка')}</Text>}
                <Pressable style={styles.remove} onPress={() => setShots((all) => all.filter((x) => x.key !== s.key))} hitSlop={6} accessibilityLabel={tr('Убрать фото')}>
                  <Ionicons name="close" size={14} color="#fff" />
                </Pressable>
              </Pressable>
            ))}
          </ScrollView>
          {hint(problems.photos)}

          <Text style={styles.label}>{tr('Раздел')}</Text>
          <Pressable style={styles.select} onPress={() => setCatOpen(true)}>
            <Text style={[styles.selectText, !cat && { color: colors.muted }]} numberOfLines={2}>{cat ? cat.path : tr('Выберите раздел')}</Text>
            <Ionicons name="chevron-forward" size={18} color={colors.muted} />
          </Pressable>
          {hint(problems.cat)}

          <Text style={styles.label}>{tr('Название')}</Text>
          <TextInput value={title} onChangeText={setTitle} placeholder={tr('Например, велосипед Trek FX 2')} placeholderTextColor={colors.muted} style={styles.input} maxLength={120} />
          {hint(problems.title)}

          <Text style={styles.label}>{tr('Описание')}</Text>
          <TextInput value={desc} onChangeText={setDesc} placeholder={tr('Состояние, размеры, причина продажи')} placeholderTextColor={colors.muted} style={[styles.input, styles.area]} multiline maxLength={5000} textAlignVertical="top" />
          {hint(problems.desc)}

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
          <Pressable style={[styles.cta, styles.submit, (sending || (tried && !ok)) && { opacity: 0.55 }]} disabled={sending} onPress={submit} accessibilityRole="button" accessibilityLabel={tr('Отправить объявление')}>
            {sending ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Разместить')}</Text>}
          </Pressable>
          <Text style={styles.small}>{tr('Объявление проверят модераторы — обычно это несколько минут.')}</Text>
        </ScrollView>
      </KeyboardAvoidingView>
      <CategoryPicker visible={catOpen} onPick={(c, path) => setCat({ c, path })} onClose={() => setCatOpen(false)} />
      <CityPicker visible={cityOpen} value={city} onPick={setCity} onClose={() => setCityOpen(false)} />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  text: { fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 52, paddingHorizontal: 36, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  link: { fontSize: 15.5, fontWeight: '700', color: colors.primaryDeep },
  form: { paddingHorizontal: 16, paddingBottom: 40 },
  h1: { fontSize: 26, fontWeight: '800', color: colors.ink, paddingTop: 8, paddingBottom: 6 },
  label: { fontSize: 16, fontWeight: '800', color: colors.ink, marginTop: 18, marginBottom: 8 },
  labelRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, marginBottom: 8 },
  count: { color: colors.muted, fontWeight: '600', fontSize: 14 },
  shots: { gap: 8, paddingRight: 8 },
  addShot: { width: 92, height: 92, borderRadius: 14, backgroundColor: colors.primarySoft, borderWidth: 1.5, borderColor: 'rgba(14,159,110,0.3)', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center', gap: 4 },
  addText: { fontSize: 12.5, fontWeight: '700', color: colors.primaryDeep },
  shot: { width: 92, height: 92, borderRadius: 14, overflow: 'hidden', backgroundColor: colors.photo },
  shotImg: { width: 92, height: 92 },
  shotOverlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
  cover: { position: 'absolute', left: 6, bottom: 6, backgroundColor: 'rgba(28,38,32,0.7)', color: '#fff', fontSize: 10.5, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
  remove: { position: 'absolute', top: 5, right: 5, width: 22, height: 22, borderRadius: 11, backgroundColor: 'rgba(28,38,32,0.72)', alignItems: 'center', justifyContent: 'center' },
  select: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center', gap: 8 },
  selectText: { flex: 1, fontSize: 16, color: colors.ink, paddingVertical: 12 },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontSize: 16, color: colors.ink },
  area: { minHeight: 120, paddingTop: 13, paddingBottom: 13 },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
  switchText: { fontSize: 16, color: colors.ink },
  hint: { fontSize: 13.5, color: '#B42318', marginTop: 6 },
  submit: { marginTop: 26, paddingHorizontal: 0 },
  small: { fontSize: 13, color: colors.muted, textAlign: 'center', marginTop: 10 },
})
