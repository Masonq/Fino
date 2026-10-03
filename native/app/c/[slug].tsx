import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native'
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
              <Pressable key={o.value} onPress={() => { select(); setVal(f.key, on ? '' : o.value) }} style={[styles.sortChip, on && styles.sortOn]}>
                <Text style={[styles.sortText, on && styles.sortTextOn]}>{t3(o.label)}</Text>
              </Pressable>
            )
          })}
        </ScrollView>
      </View>
    )
  }
  if (f.type === 'select' || f.type === 'car-model') {
    const isModel = f.type === 'car-model'
    const disabled = isModel && (!values.brand || values.brand === CAR_OTHER || !CAR_MODELS[values.brand])
    const value = values[isModel ? 'model' : 'brand']
    return (
      <Pressable disabled={disabled} onPress={() => onPick(isModel ? 'model' : 'brand')} style={[styles.selectField, disabled && { opacity: 0.5 }]}>
        <Text style={styles.selectLabel}>{t3(f.label)}</Text>
        <Text style={[styles.selectValue, !value && { color: colors.muted }]} numberOfLines={1}>{value ? (value === CAR_OTHER ? t3(LUI.other) : value) : tr('Любая')}</Text>
        <Icon name="down" size={13} color={colors.inkSoft} />
      </Pressable>
    )
  }
  if (f.type === 'range') {
    const unit = f.key === 'price' ? ', €' : ''
    return (
      <View style={{ gap: 6 }}>
        <Text style={styles.fieldLabel}>{t3(f.label)}{unit}</Text>
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
    setItems(null)
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

  const dirty = q !== applied.q || sort !== applied.sort || deal !== applied.deal || JSON.stringify(values) !== JSON.stringify(applied.values)
  const apply = () => setApplied({ q, sort, deal, values })
  const subs = node?.children ?? []
  const head = (
    <View>
      <View style={[styles.top, { paddingTop: insets.top + 6 }]}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.title} numberOfLines={1}>{nameOf(node) || ' '}</Text>
          <Text style={styles.count}>{items ? `${total} ${plural(total, { ru: ['предложение', 'предложения', 'предложений'], en: ['offer', 'offers'], sr: ['ponuda', 'ponude', 'ponuda'] })}` : ' '}</Text>
        </View>
      </View>

      {subs.length > 0 && (
        <View style={styles.subs}>
          {subs.map((c) => (
            <Pressable key={c.id} style={styles.sub} onPress={() => { select(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
              <SubArt slug={c.slug} fallback={node?.slug ?? root?.slug} />
              <Text style={styles.subName} numberOfLines={2} adjustsFontSizeToFit minimumFontScale={0.8}>{nameOf(c)}</Text>
              <View style={{ flexShrink: 0 }}><Icon name="forward" size={14} color={colors.muted} /></View>
            </Pressable>
          ))}
        </View>
      )}

      <View style={styles.form}>
        <View style={styles.search}>
          <Icon name="search" size={17} color={colors.muted} />
          <TextInput value={q} onChangeText={setQ} placeholder={landing?.fields.find((f) => f.type === 'text')?.hint ? t3(landing.fields.find((f) => f.type === 'text')?.hint) : tr('Поиск в разделе')} placeholderTextColor={colors.muted} style={styles.searchInput} returnKeyType="search" onSubmitEditing={apply} />
        </View>
        {!!landing?.deal && (
          <View style={styles.chipsRow}>
            {landing.deal.options.map((o) => (
              <Pressable key={o.value} onPress={() => { select(); setDeal(deal === o.value ? '' : o.value) }} style={[styles.sortChip, deal === o.value && styles.sortOn]}>
                <Text style={[styles.sortText, deal === o.value && styles.sortTextOn]}>{t3(o.label)}</Text>
              </Pressable>
            ))}
          </View>
        )}
        {landing?.fields.filter((f) => f.type !== 'text').map((f) => <FieldView key={f.key} f={f} values={values} setVal={setVal} onPick={(k) => { setPickQ(''); setPicker(k) }} />)}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.sorts}>
          {SORTS.map(([k, l]) => (
            <Pressable key={k || 'def'} onPress={() => { select(); setSort(k) }} style={[styles.sortChip, sort === k && styles.sortOn]}>
              <Text style={[styles.sortText, sort === k && styles.sortTextOn]}>{tr(l)}</Text>
            </Pressable>
          ))}
        </ScrollView>
        {dirty && (
          <Pressable style={styles.show} onPress={apply}><Text style={styles.showText}>{tr('Показать')}</Text></Pressable>
        )}
      </View>
      {items === null && <ActivityIndicator style={{ marginTop: 20 }} color={colors.primary} />}
    </View>
  )

  const pickList = picker === 'brand' ? CAR_BRANDS : picker === 'model' ? [...(CAR_MODELS[values.brand] ?? []), CAR_OTHER] : []
  const pickShown = pickList.filter((x) => x.toLowerCase().includes(pickQ.trim().toLowerCase()))
  return (
    <View style={styles.page}>
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
  subs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingHorizontal: space.page, marginBottom: 12 },
  sub: { width: '48.8%', flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 56, paddingLeft: 6, paddingRight: 10, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  subArt: { width: 42, height: 42 },
  // minWidth 0 — длинное слово («электротранспорт») не выталкивает стрелку за край плитки
  subName: { flex: 1, minWidth: 0, flexShrink: 1, fontSize: 13, lineHeight: 16, fontFamily: font[700], color: colors.ink },
  form: { paddingHorizontal: space.page, gap: 8, marginBottom: 12 },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13 },
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontSize: 15, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  priceRow: { flexDirection: 'row', gap: 8 },
  priceInput: { flex: 1, flexBasis: 0, minWidth: 0, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13, fontSize: 15, fontFamily: font[500], color: colors.ink },
  sorts: { gap: 6 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  fieldLabel: { fontSize: 13.5, fontFamily: font[800], color: colors.ink, marginTop: 2 },
  selectField: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 13 },
  selectLabel: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  selectValue: { flex: 1, textAlign: 'right', fontSize: 15, fontFamily: font[700], color: colors.ink },
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
