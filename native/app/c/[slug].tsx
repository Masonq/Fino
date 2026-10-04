import { Image } from 'expo-image'
import { LinearGradient } from 'expo-linear-gradient'
import Segmented from '../../src/components/Segmented'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, ImageBackground, Pressable, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type Category, fetchCategories, fetchFeed, type FeedItem, type Filters } from '../../src/api'
import Icon from '../../src/components/Icon'
import SheetFrame from '../../src/components/SheetFrame'
import { CAR_BRANDS, CAR_MODELS, CAR_OTHER, LANDINGS, type LandingField, landingParams, LUI, t3 } from '../../src/landings'
import ListingCard from '../../src/components/ListingCard'
import { SITE } from '../../src/config'
import { select } from '../../src/haptics'
import { getLang, plural, tr } from '../../src/i18n'
import { colors, font, space } from '../../src/theme'

/** Картинка подраздела; своей нет — картинка родительского раздела, как CategoryArt на сайте. */
function SubArt({ slug, fallback }: { slug: string; fallback?: string }) {
  const [src, setSrc] = useState(slug)
  return <Image source={{ uri: `${SITE}/cat/${src}.png` }} style={styles.subArt} contentFit="contain" onError={() => { if (fallback && src !== fallback) setSrc(fallback) }} />
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
export default function CategoryScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>()
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const [node, setNode] = useState<Category | null>(null)
  const [root, setRoot] = useState<Category | null>(null)
  const [deal, setDeal] = useState('')
  const [values, setValues] = useState<Record<string, string>>({})
  const [picker, setPicker] = useState<'brand' | 'model' | null>(null)
  const [pickQ, setPickQ] = useState('')
  const [allSubs, setAllSubs] = useState(false)
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
  const setVal = (k: string, v: string) => setValues((prev) => ({ ...prev, [k]: v }))

  const load = useCallback(async () => {
    const id = ++req.current
    // старые результаты не убираем, пока не пришли новые: иначе страница становилась короче экрана
    // и «Показать» было некуда прокрутить
    try {
      const res = await fetchFeed({ tab: 'all', offset: 0, q: applied.q, category: String(slug), filters: { sort: applied.sort }, extra: landingParams(applied.deal, applied.values) })
      if (id === req.current) { setItems(res.items); setTotal(res.total) }
    } catch { if (id === req.current) setItems([]) }
  }, [slug, applied])
  useEffect(() => { load() }, [load])

  const loadMore = async () => {
    if (!items || more || items.length >= total) return
    setMore(true)
    try {
      const res = await fetchFeed({ tab: 'all', offset: items.length, q: applied.q, category: String(slug), filters: { sort: applied.sort }, extra: landingParams(applied.deal, applied.values) })
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
  const head = (
    <View>
      {/* Баннер раздела — как .landing-hero сайта: картинка /hero/<раздел>.webp, затемнение снизу, сверху «назад» и поиск */}
      <ImageBackground source={{ uri: `${SITE}/hero/${heroSlug}.webp` }} style={styles.hero} resizeMode="cover">
        <LinearGradient colors={['rgba(0,0,0,0)', 'rgba(0,0,0,0.16)', 'rgba(0,0,0,0.46)']} locations={[0, 0.45, 1]} style={StyleSheet.absoluteFill} />
        <Text style={styles.heroTitle} numberOfLines={1}>{nameOf(node) || ' '}</Text>
        <Text style={styles.heroCount}>{items ? `${total} ${countWord(total)}` : ' '}</Text>
      </ImageBackground>

      {subs.length > 0 && (
        <View style={styles.subs}>
          {(subs.length > 6 ? subs.slice(0, 5) : subs).map((c) => (
            <Pressable key={c.id} style={styles.sub} onPress={() => { select(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
              <Text style={styles.subName} numberOfLines={2} adjustsFontSizeToFit minimumFontScale={0.85}>{nameOf(c)}</Text>
              <SubArt slug={c.slug} fallback={node?.slug ?? root?.slug} />
            </Pressable>
          ))}
          {subs.length > 6 && (
            <Pressable style={[styles.sub, styles.subAll]} onPress={() => setAllSubs(true)} accessibilityRole="button">
              <Text style={[styles.subName, { maxWidth: '85%' }]}>{tr('Все категории')}</Text>
              <Icon name="forward" size={16} color={colors.muted} />
            </Pressable>
          )}
        </View>
      )}

      <View style={styles.form}>
        {!!landing?.deal && (
          <View style={styles.deal}>
            <Segmented options={landing.deal.options.map((o) => ({ key: o.value, label: t3(o.label) }))} value={deal} onChange={(v) => setDeal(v === deal ? '' : v)} stretch />
          </View>
        )}
        {landing?.fields.filter((f) => f.type !== 'text').map((f) => <FieldView key={f.key} f={f} values={values} setVal={setVal} onPick={(k) => { setPickQ(''); setPicker(k) }} />)}
        <Pressable style={styles.go} onPress={apply} accessibilityRole="button">
          <Text style={styles.goText}>{preview != null ? tr('Показать {n} {word}', { n: preview, word: countWord(preview) }) : tr('Показать')}</Text>
        </Pressable>
      </View>
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
        ListFooterComponent={more ? <ActivityIndicator style={{ marginVertical: 16 }} color={colors.primary} /> : null}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingBottom: 10 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 21, fontFamily: font[800], letterSpacing: -0.3, color: colors.ink },
  count: { fontSize: 13, fontFamily: font[600], color: colors.muted, marginTop: 1 },
  hero: { height: 132, paddingHorizontal: 12, paddingBottom: 12, justifyContent: 'flex-end', overflow: 'hidden', borderBottomLeftRadius: 18, borderBottomRightRadius: 18, backgroundColor: '#D8DED9' },
  heroBar: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 12, paddingBottom: 10, backgroundColor: colors.bg },
  heroBack: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surface, shadowColor: '#101828', shadowOpacity: 0.12, shadowRadius: 4, shadowOffset: { width: 0, height: 1 }, elevation: 2, alignItems: 'center', justifyContent: 'center' },
  heroSearch: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8, height: 42, borderRadius: 13, backgroundColor: colors.surface, paddingHorizontal: 12, shadowColor: '#101828', shadowOpacity: 0.12, shadowRadius: 10, shadowOffset: { width: 0, height: 2 }, elevation: 3 },
  heroTitle: { fontSize: 24, fontFamily: font[800], color: '#fff', textShadowColor: 'rgba(0,0,0,0.35)', textShadowRadius: 10 },
  heroCount: { fontSize: 13, lineHeight: 17, fontFamily: font[600], color: 'rgba(255,255,255,0.92)', marginTop: 2, textShadowColor: 'rgba(0,0,0,0.35)', textShadowRadius: 8 },
  deal: { marginTop: 2 },
  roundChip: { minWidth: 44, height: 38, paddingHorizontal: 14, borderRadius: 19, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  roundChipOn: { borderColor: colors.primary, borderWidth: 1.5, backgroundColor: colors.primarySoft },
  roundChipText: { fontSize: 14, fontFamily: font[600], color: colors.ink },
  roundChipTextOn: { color: colors.primaryDeep, fontFamily: font[800] },
  go: { marginTop: 10, height: 50, borderRadius: 14, backgroundColor: colors.ink, alignItems: 'center', justifyContent: 'center' },
  goText: { color: '#fff', fontSize: 15, fontFamily: font[700] },
  fresh: { fontSize: 16, fontFamily: font[800], color: colors.ink, paddingHorizontal: 12, paddingTop: 14, paddingBottom: 10 },
  subs: { flexDirection: 'row', flexWrap: 'wrap', gap: 9, paddingHorizontal: 12, paddingTop: 20, paddingBottom: 4 },
  // как .landing-sub сайта: 68 высотой, название слева (не шире 60 %), картинка 74 справа, чуть за краем
  sub: { width: '48.6%', height: 68, paddingVertical: 10, paddingHorizontal: 12, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden', justifyContent: 'center' },
  subArt: { position: 'absolute', right: -10, top: -3, width: 74, height: 74 },
  // minWidth 0 — длинное слово («электротранспорт») не выталкивает стрелку за край плитки
  subName: { maxWidth: '60%', fontSize: 12.5, lineHeight: 15.5, fontFamily: font[700], color: colors.ink, zIndex: 2 },
  form: { paddingHorizontal: 12, gap: 8, paddingTop: 12 },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13 },
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontSize: 15, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  priceRow: { flexDirection: 'row', gap: 8 },
  // как .landing-input сайта: 13 / 14 внутри, скругление 13, рамка, 16 / 600
  priceInput: { flex: 1, flexBasis: 0, minWidth: 0, height: 48, borderRadius: 13, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.sunken, paddingHorizontal: 14, fontSize: 16, fontFamily: font[600], color: colors.ink },
  sorts: { gap: 6 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  // как .landing-label сайта: 13 / 700, ink-soft
  fieldLabel: { fontSize: 13, fontFamily: font[700], color: colors.inkSoft, marginTop: 6 },
  // как .landing-select сайта: 48, рамка, скругление 13, значение 16 / 600 слева
  selectField: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 48, borderRadius: 13, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.sunken, paddingHorizontal: 14 },
  subAll: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  selectLabel: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  selectValue: { flex: 1, fontSize: 16, fontFamily: font[600], color: colors.ink },
  pickSheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8, paddingBottom: 24 },
  pickHandle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: '#D8DCD8', marginBottom: 8 },
  pickTitle: { fontSize: 18, fontFamily: font[800], color: colors.ink, paddingHorizontal: 20, paddingBottom: 8 },
  pickSearch: { marginHorizontal: 16, marginBottom: 6, height: 44, borderRadius: 12, backgroundColor: colors.sunken, paddingHorizontal: 13, fontSize: 15.5, fontFamily: font[500], color: colors.ink },
  pickRow: { minHeight: 48, paddingHorizontal: 20, justifyContent: 'center', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  pickText: { fontSize: 16, fontFamily: font[600], color: colors.ink },
  sortChip: { height: 34, paddingHorizontal: 12, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  sortOn: { backgroundColor: colors.primary },
  sortText: { fontSize: 13, fontFamily: font[700], color: colors.inkSoft },
  sortTextOn: { color: '#fff' },
  show: { height: 48, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  showText: { color: '#fff', fontSize: 15.5, fontFamily: font[800] },
  row: { gap: space.gap, paddingHorizontal: space.page },
  empty: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 24, paddingHorizontal: 32 },
})
