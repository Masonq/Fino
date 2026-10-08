import { select, success } from '../../src/haptics'
import { getLang, tr } from '../../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import * as ImagePicker from 'expo-image-picker'
import { router, useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { ApiError, type Category, createListing, fetchCategories, type Uploaded, uploadPhoto, type AttrField, categorySchema, uploadVideo } from '../../src/api'
import { useAuth } from '../../src/auth'
import Icon from '../../src/components/Icon'
import SheetFrame from '../../src/components/SheetFrame'
import LocationPicker from '../../src/components/LocationPicker'
import CityPicker from '../../src/components/CityPicker'
import Segmented from '../../src/components/Segmented'
import { mediaUrl, SITE } from '../../src/config'
import { catPath } from '../../src/artFit'
import { cityName, CITY_COORDS } from '../../src/format'
import { colors, font } from '../../src/theme'
import { useTabInset } from '../../src/tabInset'
import { TINTS } from '../../src/tints'

const MAX = 10
type Shot = { key: string; uri: string; mime: string; state: 'loading' | 'done' | 'failed'; uploaded?: Uploaded }

/**
 * Размещение объявления. Фото — с камеры или из галереи, до 10, каждое загружается сразу (первое — обложка).
 * Раздел — по дереву, название, описание, цена (€ / RSD), «Торг уместен», город. Проверка — подсказками
 * у полей. После отправки — «Отправлено на проверку» и переход в мои объявления.
 */
const labelOf = (l: unknown): string => (typeof l === 'string' ? l : (l as Record<string, string> | undefined)?.[getLang()] || (l as Record<string, string> | undefined)?.ru || '')

/** Характеристики для сервера: пустые не отправляем, числа — числами. */
function cleanAttrs(a: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(a)) {
    if (v === undefined || v === null || v === '' || v === false) continue
    out[k] = typeof v === 'string' && /^\d+(\.\d+)?$/.test(v) ? Number(v) : v
  }
  return out
}

/** Название квартиры собирается само — как на сайте: «2-комнатная квартира, 54 м²», «Квартира-студия, 30 м²». */
function apartmentTitle(attrs: Record<string, unknown>): string {
  const area = attrs.area_m2
  if (!area) return ''
  const rooms = attrs.rooms === undefined || attrs.rooms === '' ? '' : String(attrs.rooms)
  const head = !rooms ? tr('Квартира') : rooms === 'studio' ? tr('Квартира-студия') : rooms === '1.5' ? tr('1,5-комнатная квартира') : rooms === '1' ? tr('1-комнатная квартира') : tr('{n}-комнатная квартира', { n: rooms })
  return tr('{head}, {area} м²', { head, area: String(area) })
}

export default function Post() {
  const tabInset = useTabInset()
  const { token, ready } = useAuth()
  const [shots, setShots] = useState<Shot[]>([])
  const [cat, setCat] = useState<{ c: Category; path: string } | null>(null)
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState<'EUR' | 'RSD'>('EUR')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState<string | null>('beograd')
  const [cityOpen, setCityOpen] = useState(false)
  const [tried, setTried] = useState(false)
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState<{ id: string } | null>(null)
  const [error, setError] = useState('')
  // Мастер, как на сайте: 1 — раздел (сетка с картинками), 2 — подраздел, 3 — фото и описание
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1)
  const [schema, setSchema] = useState<AttrField[] | null>(null)
  // все состояния — до любых ранних выходов: иначе при смене шага меняется число хуков (ошибка React #310)
  const [videoError, setVideoError] = useState('')
  const [point, setPoint] = useState<{ lat: number | null; lng: number | null }>({ lat: null, lng: null })
  const [hideAddr, setHideAddr] = useState(false)
  const isApartment = !!schema?.some((f) => f.key === 'rooms') && !!schema?.some((f) => f.key === 'area_m2')
  const [attrs, setAttrs] = useState<Record<string, unknown>>({})
  const [selectField, setSelectField] = useState<AttrField | null>(null)
  const [roots, setRoots] = useState<Category[] | null>(null)
  const [trail, setTrail] = useState<Category[]>([])
  useEffect(() => { fetchCategories().then(setRoots).catch(() => setRoots([])) }, [])
  // /post?cat=<раздел> — сразу к параметрам этого раздела (кнопки «Разместить вакансию», «Создайте резюме»)
  const { cat: catParam } = useLocalSearchParams<{ cat?: string }>()
  useEffect(() => {
    if (!roots || !catParam) return
    const find = (list: Category[], path: Category[]): Category[] | null => {
      for (const c of list) {
        if (c.slug === catParam) return [...path, c]
        const r = find(c.children ?? [], [...path, c])
        if (r) return r
      }
      return null
    }
    const path = find(roots, [])
    if (!path) return
    const c = path[path.length - 1]
    setCat({ c, path: path.map(nameOf).join(' › ') }); setTrail([]); setAttrs({}); setSchema(null); setStep(3)
    categorySchema(c.slug).then((r) => setSchema(r.attribute_schema ?? [])).catch(() => setSchema([]))
    router.setParams({ cat: undefined })
  }, [roots, catParam])

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
    setStep(1); setTrail([]); setShots([]); setPoint({ lat: null, lng: null }); setHideAddr(false); setAttrs({}); setSchema(null); setCat(null); setTitle(''); setDesc(''); setPrice(''); setNegotiable(false); setTried(false); setDone(null); setError('')
  }

  const upload = async (shot: Shot) => {
    setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'loading' } : x)))
    try {
      const up = shot.mime.startsWith('video') ? await uploadVideo(token, shot.uri, shot.mime) : await uploadPhoto(token, shot.uri, shot.mime)
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'done', uploaded: up } : x)))
    } catch (e) {
      if (shot.mime.startsWith('video')) {
        // видео с ошибкой формата, размера или длины убираем и объясняем — как на сайте
        const code = e instanceof ApiError ? e.message : ''
        const msg: Record<string, string> = {
          unsupported_format: 'Формат не поддерживается — снимите видео обычной камерой телефона',
          file_too_large: 'Файл слишком большой',
          video_too_long: 'Видео слишком длинное — до полутора минут',
          processing_failed: 'Не удалось обработать видео — попробуйте другое',
        }
        setShots((s) => s.filter((x) => x.key !== shot.key))
        setVideoError(tr(msg[code] ?? 'Не получилось загрузить видео'))
        return
      }
      setShots((s) => s.map((x) => (x.key === shot.key ? { ...x, state: 'failed' } : x)))
    }
  }

  // Видео — одно, до полутора минут, как на сайте
  const hasVideo = shots.some((x) => x.mime.startsWith('video'))
  const addVideo = async () => {
    setVideoError('')
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) { Alert.alert(tr('Нет доступа'), tr('Разрешите доступ к фото в настройках телефона.')); return }
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['videos'], videoMaxDuration: 90, quality: 1 })
    if (res.canceled || !res.assets[0]) return
    const a = res.assets[0]
    const shot: Shot = { key: `video-${Date.now()}`, uri: a.uri, mime: a.mimeType || 'video/mp4', state: 'loading' }
    setShots((s) => [...s, shot])
    upload(shot)
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
    photos: shots.filter((s) => s.state === 'done' && !s.mime.startsWith('video')).length === 0 ? tr('Добавьте хотя бы одно фото') : shots.some((s) => s.state === 'loading') ? tr('Дождитесь загрузки фото') : '',
    cat: cat ? '' : tr('Выберите раздел'),
    title: ((isApartment && apartmentTitle(attrs)) || title).trim().length < 3 ? tr('Название — хотя бы 3 буквы') : '',
    desc: desc.trim().length < 10 ? tr('Опишите вещь хотя бы парой предложений') : '',
  }
  const ok = !Object.values(problems).some(Boolean)

  const submit = async () => {
    setTried(true); setError('')
    if (!ok || !cat) return
    setSending(true)
    try {
      const res = await createListing(token, {
        category_id: cat.c.id, title: (isApartment && apartmentTitle(attrs)) || title.trim(), description: desc.trim(),
        price: price ? Number(price) : null, currency, price_negotiable: negotiable, city,
        photos: shots.filter((s) => s.state === 'done' && s.uploaded).map((s) => s.uploaded as Uploaded),
        attributes: cleanAttrs(attrs),
        location_lat: point.lat, location_lng: point.lng, hide_exact_address: hideAddr,
      })
      success()
      setDone({ id: res.id })
    } catch (e) {
      setError(e instanceof ApiError && e.message ? e.message : tr('Не удалось отправить. Проверьте интернет и попробуйте ещё раз.'))
    } finally {
      setSending(false)
    }
  }

  const hint = (text: string) => (tried && text ? <Text style={styles.hint}>{text}</Text> : null)
  const nameOf = (c: Category) => (typeof c.name === 'string' ? c.name : c.name?.[getLang()] || c.name?.ru || c.slug)
  const choose = (c: Category) => {
    const path = [...trail, c]
    if (c.children && c.children.length) { setTrail(path); setStep(2); return }
    setCat({ c, path: path.map(nameOf).join(' › ') }); setTrail([]); setAttrs({}); setSchema(null); setStep(3)
    categorySchema(c.slug).then((r) => setSchema(r.attribute_schema ?? [])).catch(() => setSchema([]))
  }
  const dots = (
    <View style={styles.steps}>
      {[1, 2, 3, 4].map((n) => <View key={n} style={[styles.stepDot, n <= (step <= 2 ? 1 : step - 1) && styles.stepDotOn]} />)}
    </View>
  )

  if (step === 1) {
    return (
      <SafeAreaView style={styles.page} edges={['top']}>
        <ScrollView contentContainerStyle={[styles.form, { paddingBottom: 24 + tabInset }]}>
          {dots}
          <Text style={styles.stepTitle}>{tr('Что продаёте?')}</Text>
          <Text style={styles.stepHint}>{tr('Выберите раздел — подраздел уточним на следующем шаге')}</Text>
          {roots === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
            <View style={styles.grid}>
              {roots.map((c) => (
                <Pressable key={c.id} style={[styles.catItem, TINTS[c.slug] ? { backgroundColor: TINTS[c.slug], borderWidth: 0 } : null]} onPress={() => choose(c)} accessibilityRole="button">
                  <Image source={{ uri: `${SITE}${catPath(c.slug)}` }} style={styles.catImg} contentFit="contain" />
                  <Text style={styles.catLabel} numberOfLines={2}>{nameOf(c)}</Text>
                </Pressable>
              ))}
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    )
  }

  if (step === 2) {
    const level = trail[trail.length - 1]?.children ?? []
    return (
      <SafeAreaView style={styles.page} edges={['top']}>
        <ScrollView contentContainerStyle={[styles.form, { paddingBottom: 24 + tabInset }]}>
          {dots}
          <View style={styles.stepHead}>
            <Pressable onPress={() => { const t = trail.slice(0, -1); setTrail(t); if (!t.length) setStep(1) }} hitSlop={10} style={styles.stepBack} accessibilityLabel={tr('Назад')}>
              <Icon name="back" size={22} color={colors.ink} />
            </Pressable>
            <Text style={styles.stepTitle} numberOfLines={1}>{nameOf(trail[trail.length - 1])}</Text>
          </View>
          <Text style={styles.stepHint}>{tr('Уточните подраздел')}</Text>
          <View style={styles.subList}>
            {trail.length >= 2 && (() => {
              // как на сайте: «Телефоны» вели только в «Запчасти и ремонт» — сам раздел тоже можно выбрать
              const cur = trail[trail.length - 1]
              return (
                <Pressable style={styles.subRow} onPress={() => {
                  setCat({ c: cur, path: trail.map(nameOf).join(' › ') }); setTrail([]); setAttrs({}); setSchema(null); setStep(3)
                  categorySchema(cur.slug).then((r) => setSchema(r.attribute_schema ?? [])).catch(() => setSchema([]))
                }} accessibilityRole="button">
                  <View style={{ flex: 1 }}>
                    <Text style={styles.subText}>{nameOf(cur)}</Text>
                    <Text style={styles.subNote}>{tr('Общий раздел — если ниже нет подходящего')}</Text>
                  </View>
                  <Icon name="forward" size={16} color={colors.muted} />
                </Pressable>
              )
            })()}
            {level.map((c, i) => (
              <Pressable key={c.id} style={[styles.subRow, i === level.length - 1 && { borderBottomWidth: 0 }]} onPress={() => choose(c)} accessibilityRole="button">
                <Text style={styles.subText}>{nameOf(c)}</Text>
                <Icon name="forward" size={16} color={colors.muted} />
              </Pressable>
            ))}
          </View>
        </ScrollView>
      </SafeAreaView>
    )
  }

  // Шаг 2 «Параметры» — как на сайте: поля из схемы раздела; обязательные — «*», без них дальше нельзя
  if (step === 3) {
    const fields = schema ?? []
    const filled = fields.filter((f) => f.required).every((f) => { const v = attrs[f.key]; return v !== undefined && v !== null && v !== '' })
    return (
      <SafeAreaView style={styles.page} edges={['top']}>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={[styles.form, { paddingBottom: 24 + tabInset }]} keyboardShouldPersistTaps="handled">
            {dots}
            <View style={styles.stepHead}>
              <Pressable onPress={() => setStep(1)} hitSlop={10} style={styles.stepBack} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
              <Text style={styles.stepTitle}>{tr('Параметры')}</Text>
            </View>
            <Text style={styles.stepHint}>{cat?.path}</Text>
            {schema === null ? <ActivityIndicator style={{ marginTop: 20 }} color={colors.primary} />
              : fields.length === 0 ? <Text style={styles.stepHint}>{tr('У этой категории пока нет доп. параметров — переходите дальше.')}</Text>
              : fields.map((f) => {
                const label = `${labelOf(f.label) || f.key}${f.required ? ' *' : ''}`
                const v = attrs[f.key]
                if (f.type === 'boolean') {
                  return (
                    <Pressable key={f.key} style={styles.paramCheck} onPress={() => setAttrs((a) => ({ ...a, [f.key]: !a[f.key] }))} accessibilityRole="checkbox" accessibilityState={{ checked: !!v }}>
                      <View style={[styles.box, !!v && styles.boxOn]}>{!!v && <Icon name="check" size={12} color="#fff" />}</View>
                      <Text style={styles.paramCheckText}>{labelOf(f.label)}</Text>
                    </Pressable>
                  )
                }
                return (
                  <View key={f.key}>
                    <Text style={styles.label}>{label}</Text>
                    {f.type === 'select' ? (
                      <Pressable style={styles.select} onPress={() => setSelectField(f)}>
                        <Text style={[styles.selectText, v === undefined || v === '' ? { color: colors.muted } : null]}>
                          {v === undefined || v === '' ? '—' : labelOf(f.options?.find((o) => String(o.value) === String(v))?.label) || String(v)}
                        </Text>
                        <Icon name="down" size={14} color={colors.muted} />
                      </Pressable>
                    ) : (
                      <TextInput value={v === undefined ? '' : String(v)} onChangeText={(t) => setAttrs((a) => ({ ...a, [f.key]: f.type === 'number' ? t.replace(/[^\d.,]/g, '').replace(',', '.') : t }))}
                        keyboardType={f.type === 'number' ? 'decimal-pad' : 'default'} style={styles.input} placeholderTextColor={colors.muted} maxLength={120} />
                    )}
                  </View>
                )
              })}
            <Pressable style={[styles.cta, styles.submit, !filled && { opacity: 0.45 }]} disabled={!filled || schema === null} onPress={() => setStep(4)} accessibilityRole="button">
              <Text style={styles.ctaText}>{tr('Далее')}</Text>
            </Pressable>
          </ScrollView>
        </KeyboardAvoidingView>
        <SheetFrame visible={!!selectField} onClose={() => setSelectField(null)}>
          <View style={styles.optSheet}>
            <View style={styles.optHandle} />
            <Text style={styles.optTitle}>{labelOf(selectField?.label)}</Text>
            <ScrollView style={{ maxHeight: 460 }}>
              {(selectField?.options ?? []).map((o) => {
                const on = String(attrs[selectField!.key]) === String(o.value)
                return (
                  <Pressable key={String(o.value)} style={styles.optRow} onPress={() => { setAttrs((a) => ({ ...a, [selectField!.key]: o.value })); setSelectField(null) }}>
                    <Text style={[styles.optText, on && { color: colors.primaryDeep, fontFamily: font[800] }]}>{labelOf(o.label)}</Text>
                    {on && <Icon name="check" size={16} color={colors.primary} />}
                  </Pressable>
                )
              })}
            </ScrollView>
          </View>
        </SheetFrame>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={[styles.form, { paddingBottom: 24 + tabInset }]} keyboardShouldPersistTaps="handled">
          {dots}
          <Text style={styles.stepTitle}>{tr(step === 5 ? 'Цена и город' : 'Описание и фото')}</Text>
          {step === 4 && (<>

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
            {!hasVideo && (
              <Pressable style={styles.addShot} onPress={addVideo} accessibilityLabel={tr('Добавить видео')}>
                <Icon name="video" size={24} color={colors.primaryDeep} />
                <Text style={[styles.addText, { textAlign: 'center' }]}>{tr('Добавить видео')}</Text>
              </Pressable>
            )}
            {shots.map((s, i) => (
              <Pressable key={s.key} style={styles.shot} onPress={() => { if (s.state === 'failed') upload(s) }}
                // удерживать — «Сделать обложкой», как на сайте: фото встаёт первым
                onLongPress={() => { if (i > 0) { setShots((all) => [s, ...all.filter((x) => x.key !== s.key)]); select() } }} delayLongPress={350}>
                {s.mime.startsWith('video')
                  ? (s.uploaded?.thumbnail_url ? <Image source={{ uri: mediaUrl(s.uploaded.thumbnail_url) ?? undefined }} style={styles.shotImg} contentFit="cover" /> : <View style={[styles.shotImg, { backgroundColor: colors.ink }]} />)
                  : <Image source={{ uri: s.uri }} style={styles.shotImg} contentFit="cover" />}
                {s.mime.startsWith('video') && s.state === 'done' && <View style={styles.playBadge}><Icon name="play" size={12} color="#fff" filled /></View>}
                {s.state === 'loading' && <View style={styles.shotOverlay}><ActivityIndicator color="#fff" /></View>}
                {s.state === 'failed' && <View style={[styles.shotOverlay, { backgroundColor: 'rgba(180,35,24,0.72)' }]}><Ionicons name="refresh" size={22} color="#fff" /></View>}
                {i === 0 && <Text style={styles.cover}>{tr('Обложка')}</Text>}
                <Pressable style={styles.remove} onPress={() => setShots((all) => all.filter((x) => x.key !== s.key))} hitSlop={6} accessibilityLabel={tr('Убрать фото')}>
                  <Ionicons name="close" size={14} color="#fff" />
                </Pressable>
              </Pressable>
            ))}
          </ScrollView>
          {shots.length > 1 && <Text style={styles.coverHint}>{tr('Удерживайте фото, чтобы сделать его обложкой')}</Text>}
          {hint(problems.photos)}
          {!!videoError && <Text style={styles.hint}>{videoError}</Text>}
          {shots.some((x) => x.mime.startsWith('video') && x.state === 'loading') && <Text style={styles.small}>{tr('Обрабатывается — обычно недолго')}</Text>}

          <Text style={styles.label}>{tr('Раздел')}</Text>
          <Pressable style={styles.select} onPress={() => { setTrail([]); setStep(1) }}>
            <Text style={[styles.selectText, !cat && { color: colors.muted }]} numberOfLines={2}>{cat ? cat.path : tr('Выберите раздел')}</Text>
            <Ionicons name="chevron-forward" size={18} color={colors.muted} />
          </Pressable>
          {hint(problems.cat)}

          <Text style={styles.label}>{tr('Название')}</Text>
          <TextInput value={isApartment && apartmentTitle(attrs) ? apartmentTitle(attrs) : title} editable={!(isApartment && apartmentTitle(attrs))} onChangeText={setTitle} placeholder={tr('Например, велосипед Trek FX 2')} placeholderTextColor={colors.muted} style={styles.input} maxLength={120} />
          {hint(problems.title)}

          <Text style={styles.label}>{tr('Описание')}</Text>
          <TextInput value={desc} onChangeText={setDesc} placeholder={tr('Состояние, размеры, причина продажи')} placeholderTextColor={colors.muted} style={[styles.input, styles.area]} multiline maxLength={5000} textAlignVertical="top" />
          {hint(problems.desc)}
          </>)}

          {step === 4 && (
            <Pressable style={[styles.cta, styles.submit]} onPress={() => {
              if (problems.photos || problems.cat || problems.title || problems.desc) { setTried(true); return }
              setStep(5)
            }} accessibilityRole="button"><Text style={styles.ctaText}>{tr('Далее')}</Text></Pressable>
          )}

          {step === 5 && (<>
          <Pressable onPress={() => setStep(4)} hitSlop={8} style={styles.backLink}><Icon name="back" size={16} color={colors.primaryDeep} /><Text style={styles.backLinkText}>{tr('Описание и фото')}</Text></Pressable>
          <View style={styles.labelRow}>
            <Text style={styles.label}>{tr('Цена')}</Text>
            <Segmented options={[{ key: 'EUR', label: '€' }, { key: 'RSD', label: 'RSD' }]} value={currency} onChange={(c) => setCurrency(c as 'EUR' | 'RSD')} />
          </View>
          <TextInput value={price} onChangeText={(v) => setPrice(v.replace(/\D/g, '').slice(0, 9))} placeholder={tr('Пусто — «цена не указана»')} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.input} />
          <View style={styles.switchRow}>
            <Text style={styles.switchText}>{tr('Торг уместен')}</Text>
            <Switch value={negotiable} onValueChange={setNegotiable} trackColor={{ true: colors.primary, false: colors.sunken }} />
          </View>

          <Text style={styles.label}>{tr('Город')}</Text>
          <Pressable style={styles.select} onPress={() => setCityOpen(true)}>
            <Text style={styles.selectText}>{city ? cityName(city) : tr('Не указан')}</Text>
            <Icon name="forward" size={16} color={colors.muted} />
          </Pressable>
          <LocationPicker lat={point.lat} lng={point.lng} hide={hideAddr} center={city ? CITY_COORDS[city] : undefined} onChange={(a, b) => setPoint({ lat: a, lng: b })} onHide={setHideAddr} />

          {!!error && <Text style={[styles.hint, { marginTop: 14 }]}>{error}</Text>}
          <Pressable style={[styles.cta, styles.submit, (sending || (tried && !ok)) && { opacity: 0.55 }]} disabled={sending} onPress={submit} accessibilityRole="button" accessibilityLabel={tr('Отправить объявление')}>
            {sending ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Разместить')}</Text>}
          </Pressable>
          <Text style={styles.small}>{tr('Объявление проверят модераторы — обычно это несколько минут.')}</Text>
          </>)}
        </ScrollView>
      </KeyboardAvoidingView>
      <CityPicker visible={cityOpen} value={city} onPick={setCity} onClose={() => setCityOpen(false)} />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  coverHint: { fontFamily: font[600], fontSize: 12.5, color: colors.muted, marginTop: 6 },
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 52, paddingHorizontal: 36, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  link: { fontSize: 15.5, fontFamily: font[700], color: colors.primaryDeep },
  form: { paddingHorizontal: 16, paddingBottom: 40, paddingTop: 10 },
  // Как на сайте: .post-steps (полоски 4 px), .post-cat-grid (3 колонки, 8 px), .post-cat-item (118, скругление 16)
  backLink: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6, alignSelf: 'flex-start' },
  backLinkText: { fontSize: 14, fontFamily: font[700], color: colors.primaryDeep },
  paramCheck: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 16 },
  paramCheckText: { flex: 1, fontSize: 15, fontFamily: font[600], color: colors.ink },
  box: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  boxOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  optSheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8, paddingBottom: 26 },
  optHandle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: 8 },
  optTitle: { fontSize: 18, fontFamily: font[800], color: colors.ink, paddingHorizontal: 20, paddingBottom: 8 },
  optRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 50, paddingHorizontal: 20, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  optText: { fontSize: 16, fontFamily: font[600], color: colors.ink },
  playBadge: { position: 'absolute', left: 6, top: 6, width: 22, height: 22, borderRadius: 11, backgroundColor: 'rgba(28,38,32,0.7)', alignItems: 'center', justifyContent: 'center' },
  subNote: { fontSize: 12.5, fontFamily: font[500], color: colors.muted, marginTop: 2 },
  steps: { flexDirection: 'row', gap: 6, marginBottom: 14 },
  stepDot: { flex: 1, height: 4, borderRadius: 3, backgroundColor: colors.border },
  stepDotOn: { backgroundColor: colors.primary },
  stepHead: { flexDirection: 'row', alignItems: 'center', gap: 4, marginLeft: -8 },
  stepBack: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  stepTitle: { flexShrink: 1, fontSize: 28, fontFamily: font[800], letterSpacing: -0.9, color: colors.ink },
  stepHint: { fontSize: 13, lineHeight: 18, fontFamily: font[500], color: colors.muted, marginTop: 4, marginBottom: 14 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  catItem: { width: '31.9%', height: 118, borderRadius: 16, paddingTop: 10, paddingHorizontal: 6, paddingBottom: 9, alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  catImg: { width: 68, height: 68 },
  catLabel: { height: 28, fontSize: 11.5, lineHeight: 14, fontFamily: font[700], color: colors.ink, textAlign: 'center', textAlignVertical: 'center' },
  subList: { borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden' },
  subRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 52, paddingHorizontal: 16, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  subText: { flex: 1, fontSize: 15.5, fontFamily: font[600], color: colors.ink, paddingRight: 8 },
  h1: { fontSize: 26, fontFamily: font[800], color: colors.ink, paddingTop: 8, paddingBottom: 6 },
  // как подписи полей формы сайта: 12,5 / 700, серо-зелёные
  label: { fontSize: 12.5, fontFamily: font[700], color: colors.inkSoft, marginTop: 16, marginBottom: 6 },
  labelRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, marginBottom: 8 },
  count: { color: colors.muted, fontFamily: font[600], fontSize: 14 },
  shots: { gap: 8, paddingRight: 8 },
  addShot: { width: 92, height: 92, borderRadius: 14, backgroundColor: colors.primarySoft, borderWidth: 1.5, borderColor: 'rgba(14,159,110,0.3)', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center', gap: 4 },
  addText: { fontSize: 12.5, fontFamily: font[700], color: colors.primaryDeep },
  shot: { width: 92, height: 92, borderRadius: 14, overflow: 'hidden', backgroundColor: colors.photo },
  shotImg: { width: 92, height: 92 },
  shotOverlay: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center' },
  cover: { position: 'absolute', left: 6, bottom: 6, backgroundColor: 'rgba(28,38,32,0.7)', color: '#fff', fontSize: 10.5, fontFamily: font[800], paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
  remove: { position: 'absolute', top: 5, right: 5, width: 22, height: 22, borderRadius: 11, backgroundColor: 'rgba(28,38,32,0.72)', alignItems: 'center', justifyContent: 'center' },
  select: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, flexDirection: 'row', alignItems: 'center', gap: 8 },
  selectText: { flex: 1, fontFamily: font[400], fontSize: 16, color: colors.ink, paddingVertical: 12 },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontFamily: font[400], fontSize: 16, color: colors.ink },
  area: { minHeight: 120, paddingTop: 13, paddingBottom: 13 },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
  switchText: { fontFamily: font[400], fontSize: 16, color: colors.ink },
  hint: { fontFamily: font[400], fontSize: 13.5, color: colors.danger, marginTop: 6 },
  submit: { marginTop: 26, paddingHorizontal: 0 },
  small: { fontFamily: font[400], fontSize: 13, color: colors.muted, textAlign: 'center', marginTop: 10 },
})
