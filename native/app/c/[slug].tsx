import { Image } from 'expo-image'
import { LinearGradient } from 'expo-linear-gradient'
import Segmented from '../../src/components/Segmented'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, ImageBackground, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native'
import Pressable from '../../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type Category, fetchCategories, fetchFeed, type FeedItem, type Filters, get } from '../../src/api'
import Icon from '../../src/components/Icon'
import SheetFrame from '../../src/components/SheetFrame'
import { CAR_BRANDS, CAR_MODELS, CAR_OTHER, LANDINGS, type LandingField, landingParams, LUI, t3 } from '../../src/landings'
import JobsLanding from '../../src/components/JobsLanding'
import { TILE, artLayout, catPath, circleArt, longestWordWidth, oneLineWidth, tileFor, type TileFit } from '../../src/artFit'
import { TileLabelArt } from '../../src/components/TileArt'
import ListingCard from '../../src/components/ListingCard'
import { SITE } from '../../src/config'
import { select } from '../../src/haptics'
import { getLang, plural, tr } from '../../src/i18n'
import { cityList, cityName } from '../../src/format'
import { colors, font, space } from '../../src/theme'
import { TINTS } from '../../src/tints'

/** Картинка подраздела; своей нет — картинка родительского раздела, как CategoryArt на сайте. */
function SubArt({ slug, fallback }: { slug: string; fallback?: string }) {
  const [src, setSrc] = useState(slug)
  return <Image source={{ uri: `${SITE}${catPath(src)}` }} style={styles.subArt} contentFit="contain" onError={() => { if (fallback && src !== fallback) setSrc(fallback) }} />
}

/** Одно особое поле раздела: чипы, выбор марки/модели или диапазон «от — до». */
function FieldView({ f, values, setVal, onPick }: { f: LandingField; values: Record<string, string>; setVal: (k: string, v: string) => void; onPick: (k: 'brand' | 'model') => void }) {
  if (f.type === 'chips') {
    return (
      <View style={{ gap: 6 }}>
        <Text style={styles.fieldLabel}>{t3(f.label)}</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
          {(f.options ?? []).map((o) => {
            const on = values[f.key] === o.value
            return (
              <Pressable key={o.value} onPress={() => { select(); setVal(f.key, on ? '' : o.value) }} style={[styles.roundChip, on && styles.roundChipOn]}>
                <Text style={[styles.roundChipText, on && styles.roundChipTextOn]}>{t3(o.label)}</Text>
              </Pressable>
            )
          })}
        </ScrollView>
      </View>
    )
  }
  if (f.type === 'select' || f.type === 'car-model') {
    const isModel = f.type === 'car-model'
    // Модель — только когда выбрана марка с известными моделями, как на сайте
    if (isModel && (!values.brand || values.brand === CAR_OTHER || !CAR_MODELS[values.brand])) return null
    const value = values[isModel ? 'model' : 'brand']
    return (
      <View style={{ gap: 6 }}>
        <Text style={styles.fieldLabel}>{t3(f.label)}</Text>
        <Pressable onPress={() => onPick(isModel ? 'model' : 'brand')} style={styles.selectField}>
          <Text style={[styles.selectValue, !value && { color: colors.ink }]} numberOfLines={1}>{value ? (value === CAR_OTHER ? t3(LUI.other) : value) : (isModel ? t3(LUI.modelPh) : t3(LUI.brandPh))}</Text>
          <Icon name="down" size={14} color={colors.inkSoft} />
        </Pressable>
      </View>
    )
  }
  if (f.type === 'range') {
    return (
      <View style={{ gap: 6 }}>
        <Text style={styles.fieldLabel}>{t3(f.label)}</Text>
        <View style={styles.priceRow}>
          <TextInput value={values[`${f.key}_min`] ?? ''} onChangeText={(v) => setVal(`${f.key}_min`, v.replace(/\D/g, '').slice(0, 9))} placeholder={t3(LUI.from)} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.priceInput} />
          <TextInput value={values[`${f.key}_max`] ?? ''} onChangeText={(v) => setVal(`${f.key}_max`, v.replace(/\D/g, '').slice(0, 9))} placeholder={t3(LUI.to)} placeholderTextColor={colors.muted} keyboardType="number-pad" style={styles.priceInput} />
        </View>
      </View>
    )
  }
  return null
}

const SORTS: [Filters['sort'], string][] = [['', 'По умолчанию'], ['new', 'Сначала новые'], ['cheap', 'Дешевле'], ['expensive', 'Дороже']]
const nameOf = (c?: Category | null) => (!c ? '' : typeof c.name === 'string' ? c.name : c.name?.[getLang()] || c.name?.ru || c.slug)
function rootOf(list: Category[], slug: string): Category | null {
  return list.find((r) => findNode([r], slug)) ?? null
}
function findNode(list: Category[], slug: string): Category | null {
  for (const c of list) {
    if (c.slug === slug) return c
    const hit = c.children ? findNode(c.children, slug) : null
    if (hit) return hit
  }
  return null
}

/**
 * Страница раздела — как CategoryLanding сайта: название и число предложений, подразделы с картинками
 * (вглубь — своя страница), поиск внутри раздела, цена от/до, сортировка, объявления сеткой с подгрузкой.
 */
// Заголовок цветной карточки поиска — как «Найти автомобиль» у Авито
const CARD_TITLES: Record<string, string> = {"auto": "Найти автомобиль", "electronics": "Найти технику", "home-garden": "Найти для дома", "fashion": "Найти одежду", "kids": "Найти для детей", "hobby-sport": "Найти для хобби", "pets": "Найти для питомца", "beauty": "Найти для красоты", "services": "Найти исполнителя", "business": "Найти для бизнеса", "real-estate": "Все фильтры"}

/** Плитки по образцу Авито: ряд из 3 или из 2 широких (длинное название); не больше 3 рядов, дальше — «Все категории →». */
function gridRows<T>(list: T[], name: (x: T) => string, narrowText: number, maxRows = 3): (T | null)[][] {
  // широкая плитка — если название не помещается в узкую одной строкой (запас по самому широкому шрифту)
  const wide = (n: string) => oneLineWidth(n) > narrowText
  const narrowQ = list.filter((x) => !wide(name(x))), wideQ = list.filter((x) => wide(name(x)))
  const rows: (T | null)[][] = []
  // ряды по очереди появления: короткие — по три, длинные — парами; остатки — парой или одной широкой
  while ((narrowQ.length || wideQ.length) && rows.length < maxRows) {
    const nextNarrow = narrowQ.length && (!wideQ.length || list.indexOf(narrowQ[0]) < list.indexOf(wideQ[0]))
    if (nextNarrow && narrowQ.length >= 3) rows.push(narrowQ.splice(0, 3))
    else if (!nextNarrow && wideQ.length >= 2) rows.push(wideQ.splice(0, 2))
    else rows.push([...(nextNarrow ? narrowQ : wideQ).splice(0, 1), ...(nextNarrow ? wideQ : narrowQ).splice(0, 1)])
  }
  if ((narrowQ.length || wideQ.length) && rows.length) { const last = rows[rows.length - 1]; last[last.length - 1] = null }
  return rows
}

// Вопрос-заголовок раздела — как «Какую работу вы ищете?»
const LANDING_TITLES: Record<string, string> = {"real-estate": "Какую недвижимость ищете?", "auto": "Какой транспорт ищете?", "electronics": "Какую технику ищете?", "home-garden": "Что ищете для дома?", "fashion": "Какую одежду ищете?", "kids": "Что ищете для детей?", "hobby-sport": "Что ищете для хобби и спорта?", "pets": "Что ищете для питомца?", "beauty": "Что ищете для красоты?", "services": "Какие услуги ищете?", "business": "Что ищете для бизнеса?"}

/** «Работа» — свой экран по образцу Авито (две вкладки), остальные разделы — как раньше. */
export default function CategoryRoute() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  return slug === 'jobs' ? <JobsLanding /> : <CategoryScreen />
}

function CategoryScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [node, setNode] = useState<Category | null>(null)
  const [root, setRoot] = useState<Category | null>(null)
  const [intro, setIntro] = useState<string | null>(null)
  useEffect(() => {
    if (!slug) return
    get<Record<string, string>>(`/categories/${encodeURIComponent(String(slug))}/intro`).then((r) => setIntro(r?.[getLang()] || r?.sr || null)).catch(() => {})
  }, [slug])
  const [deal, setDeal] = useState('')
  const [values, setValues] = useState<Record<string, string>>({})
  const [picker, setPicker] = useState<'brand' | 'model' | null>(null)
  const [pickQ, setPickQ] = useState('')
  const [allSubs, setAllSubs] = useState(false)
  const [svcCity, setSvcCity] = useState<string | null>(null) // «Услуги»: город в «Поиске исполнителя»
  const [citySheet, setCitySheet] = useState(false)
  const [sheet, setSheet] = useState<null | 'rooms' | 'price'>(null) // Недвижимость: шторки «Комнаты» и «Цена»
  const [moreFilters, setMoreFilters] = useState(false) // Недвижимость: кнопка «фильтры» раскрывает остальные поля
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<Filters['sort']>('')
  const [applied, setApplied] = useState({ q: '', sort: '' as Filters['sort'], deal: '', values: {} as Record<string, string> })
  const [more, setMore] = useState(false)
  const req = useRef(0)

  useEffect(() => { fetchCategories().then((list) => { setNode(findNode(list, String(slug))); setRoot(rootOf(list, String(slug))) }).catch(() => {}) }, [slug])
  // Особые фильтры — по верхнему разделу, как на сайте (в «Легковых» — те же, что в «Авто»)
  const landing = root ? LANDINGS[root.slug] : undefined
  const isParts = node?.slug === 'car-parts' // «Запчасти»: плашки и «Поиск запчастей для авто», как у Авито
  const isServices = node?.slug === 'services' && root?.slug === 'services' // «Услуги»: «Поиск исполнителя»
  const isBusiness = node?.slug === 'business' && root?.slug === 'business' // «Бизнес»: круглые значки и «Сервисы»
  const isRE = root?.slug === 'real-estate' && node?.slug === root.slug // верх по образцу Авито — только на самой «Недвижимости»
  const setVal = (k: string, v: string) => setValues((prev) => ({ ...prev, [k]: v }))

  const load = useCallback(async () => {
    const id = ++req.current
    // старые результаты не убираем, пока не пришли новые: иначе страница становилась короче экрана
    // и «Показать» было некуда прокрутить
    try {
      const res = await fetchFeed({ tab: 'all', offset: 0, q: applied.q, city: (applied as { city?: string | null }).city ?? null, category: String(slug), filters: { sort: applied.sort }, extra: landingParams(applied.deal, applied.values) })
      if (id === req.current) { setItems(res.items); setTotal(res.total) }
    } catch { if (id === req.current) setItems([]) }
  }, [slug, applied])
  useEffect(() => { load() }, [load])

  const loadMore = async () => {
    if (!items || more || items.length >= total) return
    setMore(true)
    try {
      const res = await fetchFeed({ tab: 'all', offset: items.length, q: applied.q, city: (applied as { city?: string | null }).city ?? null, category: String(slug), filters: { sort: applied.sort }, extra: landingParams(applied.deal, applied.values) })
      setItems((prev) => [...(prev ?? []), ...res.items.filter((n) => !(prev ?? []).some((p) => p.id === n.id))])
    } finally { setMore(false) }
  }

  // Сколько найдётся с выбранными условиями — для кнопки «Показать N объявлений», как на сайте
  const [preview, setPreview] = useState<number | null>(null)
  useEffect(() => {
    const t = setTimeout(() => {
      fetchFeed({ tab: 'all', offset: 0, q, category: String(slug), filters: { sort }, extra: landingParams(deal, values) })
        .then((r) => setPreview(r.total)).catch(() => {})
    }, 350)
    return () => clearTimeout(t)
  }, [q, deal, values, sort, slug])
  const dirty = q !== applied.q || sort !== applied.sort || deal !== applied.deal || JSON.stringify(values) !== JSON.stringify(applied.values)
  const [searched, setSearched] = useState(false)
  const listRef = useRef<FlatList<FeedItem>>(null)
  // Как на сайте: «Показать» — плавно к результатам, заголовок «Найдено: N» вместо «Свежие объявления»
  const pendingScroll = useRef(false)
  const apply = () => { setApplied({ q, sort, deal, values }); setSearched(true); pendingScroll.current = true }
  // прокрутка к результатам — когда они пришли
  useEffect(() => {
    if (!pendingScroll.current || items === null) return
    pendingScroll.current = false
    // к первому объявлению результатов с местом под заголовок «Найдено: N» — без запомненной позиции заголовка
    // (она устаревала, пока догружались подразделы и фильтры); нет результатов — в конец страницы
    setTimeout(() => {
      if (items.length) listRef.current?.scrollToIndex({ index: 0, viewOffset: 46, animated: true })
      else listRef.current?.scrollToEnd({ animated: true })
    }, 60)
  }, [items])
  const subs = node?.children ?? []
  const countWord = (n: number) => plural(n, { ru: ['объявление', 'объявления', 'объявлений'], en: ['listing', 'listings'], sr: ['oglas', 'oglasa', 'oglasa'] })
  const heroSlug = root?.slug ?? String(slug)
  // ── сетка плиток подразделов по образцу Авито: по 3 в ряд или 2 широких, «Все категории →» последней
  const gridW = width - space.page * 2
  const smallW = Math.floor((gridW - 16) / 3), wideW = Math.floor((gridW - 8) / 2)
  const grid = gridRows(subs, nameOf, smallW - 22)
  const tile = (c: (typeof subs)[number] | null, w: number, key: string) => {
    if (!c) {
      return (
        <Pressable key={key} style={[styles.lTile, { width: w }]} onPress={() => setAllSubs(true)} accessibilityRole="button">
          <Text style={[styles.lTileText, { maxWidth: w - 22 }]}>{tr('Все категории')}</Text>
          <View style={{ marginTop: 6 }}><Icon name="forward" size={18} color={colors.ink} /></View>
        </Pressable>
      )
    }
    // узкая плитка — надпись на всю ширину (название в одну строку); широкая — не шире половины, но не уже самого длинного слова: справа колонка под картинку
    const base: TileFit = { kind: '', tile: w, text: w < wideW ? w - 22 : Math.min(w - 22, Math.max(longestWordWidth(nameOf(c)) + 4, Math.round(w * 0.5))), art: 'big' }
    const { fit } = artLayout(nameOf(c), base, c.slug)
    return (
      <Pressable key={key} style={[styles.lTile, { width: w }, TINTS[root?.slug ?? String(slug)] ? { backgroundColor: TINTS[root?.slug ?? String(slug)] } : null]} onPress={() => { select(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
        <TileLabelArt uri={`${SITE}${catPath(c.slug)}`} name={nameOf(c)} fit={fit} style={styles.lTileText} />
      </Pressable>
    )
  }
  const tilesGrid = subs.length > 0 && (
    <View style={styles.grid}>
      {grid.map((row, r) => (
        <View key={r} style={styles.gridRow}>
          {row.map((c, k) => tile(c, row.length === 3 ? smallW : row.length === 2 ? wideW : gridW, `${r}-${k}`))}
        </View>
      ))}
    </View>
  )
  const showLabel = preview != null ? tr('Показать {n} {word}', { n: preview, word: countWord(preview) }) : tr('Показать')
  const fullForm = (
    <View style={styles.form}>
      <Text style={styles.formTitle}>{tr(CARD_TITLES[String(root?.slug)] ?? 'Подобрать точнее')}</Text>
      {!!landing?.deal && !isRE && (
        <Segmented options={landing.deal.options.map((o) => ({ key: o.value, label: t3(o.label) }))} value={deal} onChange={(v) => setDeal(v === deal ? '' : v)} onSunken />
      )}
      {landing?.fields.filter((f) => f.type !== 'text' && !(isRE && (f.key === 'rooms' || f.key === 'price'))).map((f) => <FieldView key={f.key} f={f} values={values} setVal={setVal} onPick={(k) => { setPickQ(''); setPicker(k) }} />)}
      <Pressable style={styles.go} onPress={apply} accessibilityRole="button"><Text style={styles.goText}>{showLabel}</Text></Pressable>
    </View>
  )
  // ── Недвижимость: свой верх, как у Авито — заголовок по центру, сделка, категория, комнаты и цена, показать + фильтры
  const roomsField = landing?.fields.find((f) => f.key === 'rooms')
  const priceText = values.price_min && values.price_max ? `${values.price_min} – ${values.price_max} €` : values.price_min ? `${tr('от')} ${values.price_min} €` : values.price_max ? `${tr('до')} ${values.price_max} €` : ''
  const reHead = (
    <View style={styles.reHead}>
      <Text style={styles.reTitle}>{nameOf(root)}</Text>
      <Text style={styles.reCount}>{items ? `${total} ${countWord(total)}` : ' '}</Text>
      {!!landing?.deal && <Segmented options={landing.deal.options.map((o) => ({ key: o.value, label: t3(o.label) }))} value={deal} onChange={(v) => setDeal(v === deal ? '' : v)} stretch />}
      <Pressable style={styles.reField} onPress={() => setAllSubs(true)} accessibilityRole="button">
        <Text style={styles.reFieldText} numberOfLines={1}>{tr('Квартиры, дома, комнаты…')}</Text>
        <Icon name="down" size={16} color={colors.ink} />
      </Pressable>
      <View style={styles.reRow}>
        {!!roomsField && (
          <Pressable style={[styles.reField, { flex: 1 }]} onPress={() => setSheet('rooms')} accessibilityRole="button">
            <Text style={[styles.reFieldText, !values.rooms && styles.reFieldPh]} numberOfLines={1}>{values.rooms ? `${tr('Комнаты')}: ${values.rooms === 'studio' ? tr('Студия') : values.rooms}` : tr('Комнаты')}</Text>
            <Icon name="down" size={16} color={colors.ink} />
          </Pressable>
        )}
        <Pressable style={[styles.reField, { flex: 1 }]} onPress={() => setSheet('price')} accessibilityRole="button">
          <Text style={[styles.reFieldText, !priceText && styles.reFieldPh]} numberOfLines={1}>{priceText || tr('Цена')}</Text>
        </Pressable>
      </View>
      <View style={styles.reRow}>
        <Pressable style={[styles.go, styles.goWide]} onPress={apply} accessibilityRole="button"><Text style={styles.goText}>{showLabel}</Text></Pressable>
        <Pressable style={[styles.reFilter, moreFilters && styles.reFilterOn]} onPress={() => { select(); setMoreFilters((v) => !v) }} accessibilityRole="button" accessibilityLabel={tr('Все фильтры')}>
          <Icon name="filter" size={20} color={colors.ink} />
        </Pressable>
      </View>
    </View>
  )
  const runSearch = (patch: { q?: string; values?: Record<string, string>; city?: string | null }) => {
    setApplied({ q: patch.q ?? q, sort, deal: patch.values ? '' : deal, values: patch.values ?? values, city: patch.city ?? null } as typeof applied)
    setSearched(true); pendingScroll.current = true
  }
  // «Запчасти»: плашки-ярлыки подразделов и поиск по марке и модели (по названию — в разделе «Запчасти»)
  const partsText = [values.brand, values.model].filter((v) => v && v !== CAR_OTHER).join(' ')
  const partsBlock = (
    <View>
      {subs.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickBar}>
          {subs.map((c) => (
            <Pressable key={c.id} style={styles.quickChip} onPress={() => { select(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
              <Text style={styles.quickChipText}>{nameOf(c)}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}
      <View style={styles.form}>
        <Text style={styles.formTitle}>{tr('Поиск запчастей для авто')}</Text>
        <Pressable style={styles.selectField} onPress={() => { setPickQ(''); setPicker('brand') }} accessibilityRole="button">
          <Text style={[styles.selectValue, !values.brand && { color: colors.muted }]} numberOfLines={1}>{values.brand ? (values.brand === CAR_OTHER ? t3(LUI.other) : values.brand) : tr('Марка')}</Text>
          <Icon name="down" size={14} color={colors.inkSoft} />
        </Pressable>
        {!!values.brand && values.brand !== CAR_OTHER && !!CAR_MODELS[values.brand] && (
          <Pressable style={styles.selectField} onPress={() => { setPickQ(''); setPicker('model') }} accessibilityRole="button">
            <Text style={[styles.selectValue, !values.model && { color: colors.muted }]} numberOfLines={1}>{values.model ? (values.model === CAR_OTHER ? t3(LUI.other) : values.model) : tr('Модель')}</Text>
            <Icon name="down" size={14} color={colors.inkSoft} />
          </Pressable>
        )}
        <Pressable style={styles.go} onPress={() => runSearch({ q: partsText, values: {} })} accessibilityRole="button"><Text style={styles.goText}>{tr('Показать объявления')}</Text></Pressable>
      </View>
    </View>
  )
  // «Услуги»: «Поиск исполнителя» — услуга (шторка подразделов) и город
  const servicesCard = (
    <View style={styles.form}>
      <Text style={styles.formTitle}>{tr('Поиск исполнителя')}</Text>
      <Pressable style={styles.selectField} onPress={() => setAllSubs(true)} accessibilityRole="button">
        <Text style={[styles.selectValue, { color: colors.muted }]} numberOfLines={1}>{tr('Услуга или специалист')}</Text>
        <Icon name="down" size={14} color={colors.inkSoft} />
      </Pressable>
      <Pressable style={styles.selectField} onPress={() => setCitySheet(true)} accessibilityRole="button">
        <Text style={styles.selectValue} numberOfLines={1}>{svcCity ? cityName(svcCity) : tr('Вся Сербия')}</Text>
        <Icon name="down" size={14} color={colors.inkSoft} />
      </Pressable>
      <Pressable style={styles.go} onPress={() => runSearch({ city: svcCity })} accessibilityRole="button"><Text style={styles.goText}>{tr('Показать объявления')}</Text></Pressable>
    </View>
  )
  // «Бизнес»: подразделы круглыми значками по 4 в ряд и «Сервисы»
  // по три в ряд: у Авито по четыре, но наши названия длиннее («Оборудование», «Аренда оборудования») — не помещались
  const circleW = Math.floor((gridW - 16) / 3)
  const businessBlock = (
    <View>
      <View style={styles.circleGrid}>
        {subs.map((c) => (
          <Pressable key={c.id} style={[styles.circleItem, { width: circleW }]} onPress={() => { select(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
            <View style={styles.circle}><Image source={{ uri: `${SITE}${catPath(c.slug)}` }} style={circleArt(c.slug)} contentFit="contain" /></View>
            <Text style={styles.circleText}>{nameOf(c)}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.servicesTitle}>{tr('Сервисы')}</Text>
      <View style={styles.servicesRow}>
        <Pressable style={styles.serviceCard} onPress={() => router.push('/profile-edit')} accessibilityRole="button">
          <View style={styles.serviceIcon}><Icon name="shield" size={22} color={colors.primary} /></View>
          <Text style={styles.serviceTitle}>{tr('Бизнес-аккаунт')}</Text>
          <Text style={styles.serviceLink}>{tr('Оформить')} ›</Text>
        </Pressable>
        <Pressable style={styles.serviceCard} onPress={() => router.push('/post?cat=business')} accessibilityRole="button">
          <View style={styles.serviceIcon}><Icon name="plus" size={22} color={colors.primary} /></View>
          <Text style={styles.serviceTitle}>{tr('Разместить как компания')}</Text>
          <Text style={styles.serviceLink}>{tr('Подать объявление')} ›</Text>
        </Pressable>
      </View>
    </View>
  )
  const head = (
    <View>
      {isRE ? reHead : (
        <View style={styles.lHead}>
          <Text style={styles.lTitle}>{isParts ? tr('Запчасти и аксессуары для авто и мото') : tr(node && root && node.slug !== root.slug ? nameOf(node) : (LANDING_TITLES[String(slug)] ?? nameOf(node)))}</Text>
          <Text style={styles.lCount}>{items ? `${total} ${countWord(total)}` : ' '}</Text>
        </View>
      )}
      {isParts ? partsBlock : isBusiness ? businessBlock : !isRE && tilesGrid}
      {isServices ? servicesCard : !isParts && (!isRE || moreFilters) && fullForm}
      <Text style={styles.fresh}>{searched ? tr('Найдено: {n}', { n: items ? total : '…' }) : tr('Свежие объявления')}</Text>
      {items === null && <ActivityIndicator style={{ marginTop: 20 }} color={colors.primary} />}
    </View>
  )


  const pickList = picker === 'brand' ? CAR_BRANDS : picker === 'model' ? [...(CAR_MODELS[values.brand] ?? []), CAR_OTHER] : []
  const pickShown = pickList.filter((x) => x.toLowerCase().includes(pickQ.trim().toLowerCase()))
  return (
    <View style={styles.page}>
      {/* как .landing-topbar сайта: «назад» и поиск закреплены вверху, лента прокручивается под ними */}
      <View style={[styles.heroBar, { paddingTop: insets.top + 10 }]}>
          <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={8} style={styles.heroBack} accessibilityLabel={tr('Назад')}><Icon name="back" size={20} color={colors.ink} /></Pressable>
          <View style={styles.heroSearch}>
            <Icon name="search" size={17} color={colors.muted} />
            <TextInput value={q} onChangeText={setQ} placeholder={landing?.fields.find((f) => f.type === 'text')?.hint ? t3(landing.fields.find((f) => f.type === 'text')?.hint) : tr('Что ищете?')} placeholderTextColor={colors.muted} style={styles.searchInput} returnKeyType="search" onSubmitEditing={apply} />
          </View>
      </View>
      <SheetFrame visible={sheet === 'rooms'} onClose={() => setSheet(null)}>
        <View style={[styles.pickSheet, styles.sheetPad]}>
          <View style={styles.pickHandle} />
          <View style={styles.sheetHead}>
            <Pressable onPress={() => setSheet(null)} hitSlop={8} accessibilityLabel={tr('Закрыть')}><Icon name="close" size={22} color={colors.ink} /></Pressable>
            <Text style={styles.sheetTitle}>{tr('Комнаты')}</Text>
            <Pressable onPress={() => setVal('rooms', '')} hitSlop={8}><Text style={styles.sheetClear}>{tr('Очистить')}</Text></Pressable>
          </View>
          <View style={styles.sheetChips}>
            {(roomsField?.options ?? []).map((o) => {
              const on = values.rooms === o.value
              return (
                <Pressable key={o.value} style={[styles.sheetChip, on && styles.sheetChipOn]} onPress={() => { select(); setVal('rooms', on ? '' : o.value) }} accessibilityRole="button" accessibilityState={{ selected: on }}>
                  <Text style={[styles.sheetChipText, on && styles.sheetChipTextOn]}>{t3(o.label)}</Text>
                </Pressable>
              )
            })}
          </View>
          <View style={styles.reRow}><Pressable style={[styles.go, styles.goWide]} onPress={() => { setSheet(null); apply() }}><Text style={styles.goText}>{tr('Применить')}</Text></Pressable></View>
        </View>
      </SheetFrame>
      <SheetFrame visible={sheet === 'price'} onClose={() => setSheet(null)}>
        <View style={[styles.pickSheet, styles.sheetPad]}>
          <View style={styles.pickHandle} />
          <View style={styles.sheetHead}>
            <Pressable onPress={() => setSheet(null)} hitSlop={8} accessibilityLabel={tr('Закрыть')}><Icon name="close" size={22} color={colors.ink} /></Pressable>
            <Text style={styles.sheetTitle}>{tr('Цена')}, €</Text>
            <Pressable onPress={() => { setVal('price_min', ''); setVal('price_max', '') }} hitSlop={8}><Text style={styles.sheetClear}>{tr('Очистить')}</Text></Pressable>
          </View>
          <View style={[styles.priceRow, { marginBottom: 18 }]}>
            <TextInput value={values.price_min ?? ''} onChangeText={(v) => setVal('price_min', v.replace(/\D/g, '').slice(0, 9))} placeholder={t3(LUI.from)} placeholderTextColor={colors.muted} keyboardType="number-pad" style={[styles.priceInput, { backgroundColor: colors.sunken, borderWidth: 0 }]} />
            <TextInput value={values.price_max ?? ''} onChangeText={(v) => setVal('price_max', v.replace(/\D/g, '').slice(0, 9))} placeholder={t3(LUI.to)} placeholderTextColor={colors.muted} keyboardType="number-pad" style={[styles.priceInput, { backgroundColor: colors.sunken, borderWidth: 0 }]} />
          </View>
          <View style={styles.reRow}><Pressable style={[styles.go, styles.goWide]} onPress={() => { setSheet(null); apply() }}><Text style={styles.goText}>{tr('Применить')}</Text></Pressable></View>
        </View>
      </SheetFrame>
      <SheetFrame visible={citySheet} onClose={() => setCitySheet(false)}>
        <View style={styles.pickSheet}>
          <View style={styles.pickHandle} />
          <Text style={styles.pickTitle}>{tr('Город')}</Text>
          <ScrollView style={{ maxHeight: 520 }}>
            {[{ slug: '', label: tr('Вся Сербия') }, ...cityList()].map((c) => (
              <Pressable key={c.slug || 'all'} style={[styles.pickRow, { flexDirection: 'row', alignItems: 'center', gap: 12 }]} onPress={() => { setSvcCity(c.slug || null); setCitySheet(false) }}>
                <Text style={[styles.pickText, { flex: 1 }]}>{c.label}</Text>
                {(svcCity ?? '') === c.slug && <Icon name="check" size={18} color={colors.primary} />}
              </Pressable>
            ))}
          </ScrollView>
        </View>
      </SheetFrame>
      <SheetFrame visible={allSubs} onClose={() => setAllSubs(false)}>
        <View style={styles.pickSheet}>
          <View style={styles.pickHandle} />
          <Text style={styles.pickTitle}>{tr('Все категории')}</Text>
          <ScrollView style={{ maxHeight: 520 }}>
            {subs.map((c) => (
              <Pressable key={c.id} style={[styles.pickRow, { flexDirection: 'row', alignItems: 'center', gap: 12 }]} onPress={() => { setAllSubs(false); router.push(`/c/${c.slug}`) }}>
                <Text style={[styles.pickText, { flex: 1 }]}>{nameOf(c)}</Text>
                <Icon name="forward" size={15} color={colors.muted} />
              </Pressable>
            ))}
          </ScrollView>
        </View>
      </SheetFrame>
      <SheetFrame visible={!!picker} onClose={() => setPicker(null)}>
        <View style={styles.pickSheet}>
          <View style={styles.pickHandle} />
          <Text style={styles.pickTitle}>{picker === 'brand' ? t3(landing?.fields.find((f) => f.key === 'brand')?.label) : t3(landing?.fields.find((f) => f.key === 'model')?.label)}</Text>
          <TextInput value={pickQ} onChangeText={setPickQ} placeholder={tr('Найти')} placeholderTextColor={colors.muted} style={styles.pickSearch} autoCorrect={false} />
          <ScrollView style={{ maxHeight: 420 }} keyboardShouldPersistTaps="handled">
            <Pressable style={styles.pickRow} onPress={() => { setVal(picker as string, ''); if (picker === 'brand') setVal('model', ''); setPicker(null) }}>
              <Text style={[styles.pickText, { color: colors.muted }]}>{tr('Любая')}</Text>
            </Pressable>
            {pickShown.map((x) => (
              <Pressable key={x} style={styles.pickRow} onPress={() => { select(); setVal(picker as string, x); if (picker === 'brand') setVal('model', ''); setPicker(null) }}>
                <Text style={[styles.pickText, values[picker as string] === x && { fontFamily: font[800], color: colors.primaryDeep }]}>{x === CAR_OTHER ? t3(LUI.other) : x}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      </SheetFrame>
      <FlatList
        ref={listRef}
        onScrollToIndexFailed={() => listRef.current?.scrollToEnd({ animated: true })}
        data={items ?? []}
        keyExtractor={(i) => i.id}
        numColumns={2}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        columnWrapperStyle={styles.row}
        contentContainerStyle={{ gap: space.gap, paddingBottom: 32 }}
        ListHeaderComponent={head}
        keyboardShouldPersistTaps="handled"
        onEndReachedThreshold={0.6}
        onEndReached={loadMore}
        ListEmptyComponent={items ? <Text style={styles.empty}>{tr('В этом разделе пока ничего нет. Попробуйте изменить условия.')}</Text> : null}
        ListFooterComponent={more ? <ActivityIndicator style={{ marginVertical: 16 }} color={colors.primary} />
          /* вступление о разделе внизу — как на сайте */
          : intro ? <Text style={styles.intro}>{intro}</Text> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  intro: { fontFamily: font[400], fontSize: 13.5, lineHeight: 20, color: colors.muted, marginHorizontal: space.page, marginTop: 18, marginBottom: 30 },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingBottom: 10 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },   // «назад» кружком — как на сайте и на остальных экранах
  title: { fontSize: 21, fontFamily: font[800], letterSpacing: -0.3, color: colors.ink },
  count: { fontSize: 13, fontFamily: font[600], color: colors.muted, marginTop: 1 },
  hero: { height: 132, paddingHorizontal: 12, paddingBottom: 12, justifyContent: 'flex-end', overflow: 'hidden', borderBottomLeftRadius: 18, borderBottomRightRadius: 18, backgroundColor: '#D8DED9' },
  heroBar: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 12, paddingBottom: 10, backgroundColor: colors.bg },
  heroBack: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surface, shadowColor: '#101828', shadowOpacity: 0.12, shadowRadius: 4, shadowOffset: { width: 0, height: 1 }, elevation: 2, alignItems: 'center', justifyContent: 'center' },
  heroSearch: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8, height: 42, borderRadius: 13, backgroundColor: colors.surface, paddingHorizontal: 12, shadowColor: '#101828', shadowOpacity: 0.12, shadowRadius: 10, shadowOffset: { width: 0, height: 2 }, elevation: 3 },
  heroTitle: { fontSize: 24, fontFamily: font[800], color: '#fff', textShadowColor: 'rgba(0,0,0,0.35)', textShadowRadius: 10 },
  heroCount: { fontSize: 13, lineHeight: 17, fontFamily: font[600], color: 'rgba(255,255,255,0.92)', marginTop: 2, textShadowColor: 'rgba(0,0,0,0.35)', textShadowRadius: 8 },
  deal: { marginTop: 2 },
  roundChip: { minWidth: 44, height: 38, paddingHorizontal: 14, borderRadius: 19, borderWidth: 0, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  roundChipOn: { borderColor: colors.primary, borderWidth: 1.5, backgroundColor: colors.primarySoft },
  roundChipText: { fontSize: 14, fontFamily: font[600], color: colors.ink },
  roundChipTextOn: { color: colors.primaryDeep, fontFamily: font[800] },
  // как у Авито: в карточке кнопка по ширине текста; в верху Недвижимости и в шторках — на всю ширину (goWide)
  go: { marginTop: 6, height: 50, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center', alignSelf: 'flex-start', paddingHorizontal: 22 },
  goWide: { flex: 1, alignSelf: 'stretch', marginTop: 0 },
  goText: { color: colors.onInverse, fontSize: 15, fontFamily: font[700] },
  fresh: { fontSize: 16, fontFamily: font[800], color: colors.ink, paddingHorizontal: 12, paddingTop: 14, paddingBottom: 10 },
  subs: { flexDirection: 'row', flexWrap: 'wrap', gap: 9, paddingHorizontal: 12, paddingTop: 20, paddingBottom: 4 },
  // как .landing-sub сайта: 68 высотой, название слева (не шире 60 %), картинка 74 справа, чуть за краем
  sub: { width: '48.6%', height: 68, paddingVertical: 10, paddingHorizontal: 12, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 0, overflow: 'hidden', justifyContent: 'center' },
  subArt: { position: 'absolute', right: -10, top: -3, width: 74, height: 74 },
  // minWidth 0 — длинное слово («электротранспорт») не выталкивает стрелку за край плитки
  subName: { maxWidth: '60%', fontSize: 12.5, lineHeight: 15.5, fontFamily: font[700], color: colors.ink, zIndex: 2 },
  // фильтры — серой карточкой, как карточки «Работы»
  // цветная карточка поиска — как «Найти автомобиль» у Авито (у них голубая, у нас — в фирменном зелёном)
  form: { marginHorizontal: space.page, marginTop: 8, padding: 16, borderRadius: 24, backgroundColor: colors.surface, gap: 10,
    shadowColor: '#0F1512', shadowOpacity: 0.06, shadowRadius: 14, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  formTitle: { fontSize: 19, fontFamily: font[800], color: colors.ink, letterSpacing: -0.3, marginBottom: 2 },
  lHead: { paddingHorizontal: space.page, paddingTop: 14 },
  lTitle: { fontSize: 26, lineHeight: 31, fontFamily: font[800], color: colors.ink, letterSpacing: -0.5 },
  lCount: { fontSize: 14, fontFamily: font[600], color: colors.muted, marginTop: 4 },
  grid: { paddingHorizontal: space.page, paddingTop: 16, paddingBottom: 8, gap: 8 },
  quickBar: { paddingHorizontal: space.page, paddingTop: 14, paddingBottom: 6, gap: 8 },
  quickChip: { height: 40, paddingHorizontal: 16, borderRadius: 14, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  quickChipText: { fontSize: 15, fontFamily: font[600], color: colors.ink },
  circleGrid: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: space.page, paddingTop: 16, rowGap: 14, columnGap: 8 },
  circleItem: { alignItems: 'center', gap: 6 },
  circle: { width: 84, height: 84, borderRadius: 24, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  circleImg: { width: 66, height: 66 },
  circleText: { fontSize: 13, lineHeight: 16, fontFamily: font[600], color: colors.ink, textAlign: 'center' },
  servicesTitle: { fontSize: 22, fontFamily: font[800], color: colors.ink, letterSpacing: -0.4, paddingHorizontal: space.page, marginTop: 22, marginBottom: 10 },
  servicesRow: { flexDirection: 'row', gap: 8, paddingHorizontal: space.page },
  serviceCard: { flex: 1, minHeight: 150, borderRadius: 22, backgroundColor: colors.sunken, padding: 16, gap: 6 },
  serviceIcon: { width: 44, height: 44, borderRadius: 14, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  serviceTitle: { fontSize: 16, lineHeight: 20, fontFamily: font[800], color: colors.ink },
  serviceLink: { fontSize: 14, fontFamily: font[500], color: colors.muted, marginTop: 'auto' },
  gridRow: { flexDirection: 'row', gap: 8 },
  // верх Недвижимости по образцу Авито
  reHead: { paddingHorizontal: space.page, paddingTop: 10, gap: 10 },
  reTitle: { fontSize: 30, lineHeight: 36, fontFamily: font[800], color: colors.ink, textAlign: 'center', letterSpacing: -0.6 },
  reCount: { fontSize: 14, fontFamily: font[600], color: colors.muted, textAlign: 'center', marginTop: -6, marginBottom: 4 },
  reField: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 50, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 16 },
  reFieldText: { flex: 1, fontSize: 16, fontFamily: font[500], color: colors.ink },
  reFieldPh: { color: colors.muted },
  reRow: { flexDirection: 'row', gap: 8 },
  reFilter: { width: 50, height: 50, borderRadius: 14, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  reFilterOn: { backgroundColor: colors.primarySoft },
  sheetPad: { paddingHorizontal: space.page + 4, paddingBottom: 24 },
  sheetHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  sheetTitle: { fontSize: 18, fontFamily: font[800], color: colors.ink },
  sheetClear: { fontSize: 16, fontFamily: font[500], color: colors.muted },
  sheetChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 18 },
  sheetChip: { minWidth: 48, height: 46, paddingHorizontal: 16, borderRadius: 14, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'transparent' },
  sheetChipOn: { borderColor: colors.ink },
  sheetChipText: { fontSize: 16, fontFamily: font[600], color: colors.ink },
  sheetChipTextOn: { color: colors.ink },
  lTile: { width: TILE.w, height: TILE.h, borderRadius: 16, backgroundColor: colors.sunken, padding: TILE.pad, overflow: 'hidden' },
  lTileText: { fontSize: 13.5, lineHeight: 17, fontFamily: font[700], color: colors.ink, maxWidth: TILE.text.narrow },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13 },
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontSize: 15, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  priceRow: { flexDirection: 'row', gap: 8 },
  // как .landing-input сайта: 13 / 14 внутри, скругление 13, рамка, 16 / 600
  priceInput: { flex: 1, flexBasis: 0, minWidth: 0, height: 48, borderRadius: 16, borderWidth: 0, borderColor: colors.border, backgroundColor: colors.sunken, paddingHorizontal: 14, fontSize: 16, fontFamily: font[600], color: colors.ink },
  sorts: { gap: 6 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  // как .landing-label сайта: 13 / 700, ink-soft
  fieldLabel: { fontSize: 13, fontFamily: font[700], color: colors.inkSoft, marginTop: 6 },
  // как .landing-select сайта: 48, рамка, скругление 13, значение 16 / 600 слева
  selectField: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 48, borderRadius: 16, borderWidth: 0, borderColor: colors.border, backgroundColor: colors.sunken, paddingHorizontal: 14 },
  subAll: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  selectLabel: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  selectValue: { flex: 1, fontSize: 16, fontFamily: font[600], color: colors.ink },
  pickSheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8, paddingBottom: 24 },
  pickHandle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: 8 },
  pickTitle: { fontSize: 18, fontFamily: font[800], color: colors.ink, paddingHorizontal: 20, paddingBottom: 8 },
  pickSearch: { marginHorizontal: 16, marginBottom: 6, height: 44, borderRadius: 12, backgroundColor: colors.sunken, paddingHorizontal: 13, fontSize: 15.5, fontFamily: font[500], color: colors.ink },
  pickRow: { minHeight: 48, paddingHorizontal: 20, justifyContent: 'center', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  pickText: { fontSize: 16, fontFamily: font[600], color: colors.ink },
  sortChip: { height: 34, paddingHorizontal: 12, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  sortOn: { backgroundColor: colors.inverse },
  sortText: { fontSize: 13, fontFamily: font[700], color: colors.inkSoft },
  sortTextOn: { color: colors.onInverse },
  show: { height: 48, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  showText: { color: colors.onInverse, fontSize: 15.5, fontFamily: font[800] },
  row: { gap: space.gap, paddingHorizontal: space.page },
  empty: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 24, paddingHorizontal: 32 },
})
