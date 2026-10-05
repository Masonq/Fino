import Icon, { Star } from '../../src/components/Icon'
import SheetFrame from '../../src/components/SheetFrame'
import { API } from '../../src/config'
import { tr, getLang } from '../../src/i18n'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, useWindowDimensions, View, ScrollView, Keyboard, LayoutAnimation } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { fetchFeed, type FeedItem, type FeedTab, type Filters, saveSearch } from '../../src/api'
import { useAuth } from '../../src/auth'
import { useChats } from '../../src/chats'
import CategoryTiles from '../../src/components/CategoryTiles'
import CityPicker from '../../src/components/CityPicker'
import FiltersSheet, { activeCount } from '../../src/components/FiltersSheet'
import ListingCard from '../../src/components/ListingCard'
import Segmented from '../../src/components/Segmented'
import Skeleton from '../../src/components/Skeleton'
import ShopsRow from '../../src/components/ShopsRow'
import { useTabInset } from '../../src/tabInset'
import HomeSections from '../../src/components/HomeSections'
import { cityName } from '../../src/format'
import { prefs } from '../../src/prefs'
import * as Location from 'expo-location'
import { LinearGradient } from 'expo-linear-gradient'
import { nearestCity } from '../../src/format'
import { readCache, writeCache } from '../../src/cache'
import { onRetry } from '../../src/net'
import { select, tap } from '../../src/haptics'
import { colors, radius, space, font } from '../../src/theme'

const TABS: { key: FeedTab; label: string }[] = [
  { key: 'all', label: 'Все' }, { key: 'new', label: 'Новое' }, { key: 'free', label: 'Даром' },
]

/**
 * Главная: поиск, «Все / Новое / Даром» с переезжающей плашкой и лента карточек в две колонки.
 * Подгружает дальше при прокрутке, обновляется жестом вниз. Пока грузится — заготовки карточек той же формы.
 */
const SUGGEST: Record<string, string> = { 'real-estate': 'Недвижимость', auto: 'Авто', electronics: 'Электроника', 'home-garden': 'Дом и сад', fashion: 'Одежда и обувь', services: 'Услуги' }
const SORT_NAME: Record<string, string> = { '': 'По умолчанию', new: 'Сначала новые', cheap: 'Дешевле', expensive: 'Дороже' }

/** Активный фильтр плашкой с крестиком — как .active-filter-chip на странице поиска сайта. */
function ActiveChip({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={styles.activeChip} accessibilityRole="button" accessibilityLabel={label}>
      <Text style={styles.activeChipText} numberOfLines={1}>{label}</Text>
      <View style={{ opacity: 0.7 }}><Icon name="close" size={12} color={colors.primaryDeep} /></View>
    </Pressable>
  )
}

const HINTS: Record<'ru' | 'en' | 'sr', string[]> = {
  ru: ['Найти холодильник', 'Найти квартиру', 'Найти велосипед', 'Найти работу', 'Найти коляску', 'Найти что-нибудь даром'],
  en: ['Find a fridge', 'Find an apartment', 'Find a bike', 'Find a job', 'Find a stroller', 'Find free stuff'],
  sr: ['Pronađi frižider', 'Pronađi stan', 'Pronađi bicikl', 'Pronađi posao', 'Pronađi kolica', 'Pronađi besplatno'],
}

export default function Feed() {
  const tabInset = useTabInset()
  const { width } = useWindowDimensions()
  // Колонки ленты — как переключатель на сайте: 2 или 1; выбор запоминается
  const [cols, setCols] = useState<1 | 2>(2)
  useEffect(() => { prefs.get('plonk_cols').then((v) => { if (v === '1') setCols(1) }) }, [])
  const pickCols = (n: 1 | 2) => { setCols(n); prefs.set('plonk_cols', String(n)) }
  const cardW = cols === 1 ? Math.floor(width - space.page * 2) : Math.floor((width - space.page * 2 - space.gap) / 2)
  const [tab, setTab] = useState<FeedTab>('all')
  const [query, setQuery] = useState('')
  const [q, setQ] = useState('')
  // Подсказки поиска — как у Авито: разделы и продолжения запроса по мере ввода
  const [focused, setFocused] = useState(false)
  // плашка города сжимается и разворачивается плавно, а не скачком
  useEffect(() => { LayoutAnimation.configureNext(LayoutAnimation.create(220, 'easeInEaseOut', 'opacity')) }, [focused])
  const [headBottom, setHeadBottom] = useState(0)
  const [sug, setSug] = useState<{ categories: { slug: string; name: string; path: string }[]; completions: string[] }>({ categories: [], completions: [] })
  useEffect(() => {
    const v = query.trim()
    if (!focused || v.length < 2) { setSug({ categories: [], completions: [] }); return undefined }
    let alive = true
    const t = setTimeout(() => {
      fetch(`${API}/search/suggest?q=${encodeURIComponent(v)}&lang=${getLang()}`).then((r) => r.json())
        .then((d) => { if (alive) setSug({ categories: d.categories ?? [], completions: d.completions ?? [] }) }).catch(() => {})
    }, 200)
    return () => { alive = false; clearTimeout(t) }
  }, [query, focused])
  const showSug = focused && query.trim().length >= 2 && (sug.categories.length > 0 || sug.completions.length > 0)
  const applyQuery = (v: string) => { setQuery(v); setQ(v.trim()); setFocused(false); Keyboard.dismiss() }
  const [city, setCity] = useState<string | null>(null)
  const [cityReady, setCityReady] = useState(false)
  const [category, setCategory] = useState<string | null>(null)
  const [cityOpen, setCityOpen] = useState(false)
  const [filters, setFilters] = useState<Filters>({ currency: 'EUR' })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [sortOpen, setSortOpen] = useState(false)
  // Подсказка поиска — как на сайте: «Найти холодильник / квартиру / велосипед…» с эффектом набора
  const [hint, setHint] = useState('')
  useEffect(() => {
    const words = HINTS[getLang()] ?? HINTS.ru
    let w = 0, c = 0, timer: ReturnType<typeof setTimeout>
    const step = () => {
      const word = words[w % words.length]
      c += 1
      setHint(word.slice(0, c))
      if (c >= word.length) { timer = setTimeout(() => { c = 0; w += 1; step() }, 1800) } else timer = setTimeout(step, 75)
    }
    step()
    return () => clearTimeout(timer)
  }, [])
  const { token, user } = useAuth()
  const { notices } = useChats()
  const [savedState, setSavedState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const params = useLocalSearchParams<{ q?: string; city?: string; category?: string; price_min?: string; price_max?: string; with_photo?: string; applied?: string }>()

  // Открыли сохранённый поиск — применяем его к ленте
  useEffect(() => {
    if (!params.applied) return
    setQuery(params.q ?? ''); setQ(params.q ?? '')
    setCategory(params.category || null)
    if (params.city !== undefined) { setCity(params.city || null) }
    setFilters({ currency: 'EUR', priceMin: params.price_min || undefined, priceMax: params.price_max || undefined, withPhoto: params.with_photo === '1' })
  }, [params.applied]) // eslint-disable-line react-hooks/exhaustive-deps
  const searchActive = !!(q || category || filters.priceMin || filters.priceMax || filters.withPhoto || filters.delivery || filters.sort)
  const chipCount = [q, category, filters.priceMin || filters.priceMax, filters.withPhoto, filters.delivery].filter(Boolean).length
  useEffect(() => { setSavedState('idle') }, [q, category, city, filters])
  const onSave = async () => {
    if (!token) { router.push('/login'); return }
    setSavedState('saving')
    try {
      await saveSearch(token, { q: q || undefined, category_slug: category || undefined, city: city || undefined, price_min: filters.priceMin || undefined, price_max: filters.priceMax || undefined, with_photo: filters.withPhoto || undefined })
      setSavedState('saved')
    } catch { setSavedState('idle') }
  }
  const [items, setItems] = useState<FeedItem[]>([])
  const [total, setTotal] = useState(0)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [more, setMore] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const req = useRef(0)
  const listRef = useRef<FlatList<FeedItem>>(null)

  // Город помним на телефоне: открыл приложение — лента сразу своего города
  useEffect(() => {
    prefs.get('plonk_city').then((v) => { setCity(v || null); setCityReady(true) })
  }, [])
  const pickCity = (slug: string | null) => { setCity(slug); prefs.set('plonk_city', slug ?? '') }

  // «Показать объявления рядом с вами?» — как на сайте: над лентой, а не окном; пока город не выбран и не отказались
  const [geoAsk, setGeoAsk] = useState(false)
  const [geoBusy, setGeoBusy] = useState(false)
  useEffect(() => { prefs.get('plonk_geo_ask').then((v) => setGeoAsk(v !== 'no')) }, [])
  const dismissGeo = () => { setGeoAsk(false); prefs.set('plonk_geo_ask', 'no') }
  const detectCity = async () => {
    setGeoBusy(true)
    try {
      const perm = await Location.requestForegroundPermissionsAsync()
      if (perm.status === 'granted') {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced })
        pickCity(nearestCity(pos.coords.latitude, pos.coords.longitude))
      }
      dismissGeo()
    } catch { dismissGeo() } finally { setGeoBusy(false) }
  }

  useEffect(() => {
    const t = setTimeout(() => setQ(query.trim()), 350)
    return () => clearTimeout(t)
  }, [query])

  const load = useCallback(async (mode: 'first' | 'refresh') => {
    const id = ++req.current
    // Первая страница каждой выборки сохраняется: сначала показываем её мгновенно, свежую подгружаем следом
    const key = `feed:${JSON.stringify({ tab, q, city, category, filters })}`
    let shown = false
    if (mode === 'first') {
      const cached = await readCache<{ items: FeedItem[]; total: number }>(key)
      if (id !== req.current) return
      if (cached) { setItems(cached.items); setTotal(cached.total); setState('ready'); shown = true } else setState('loading')
    }
    try {
      const res = await fetchFeed({ tab: searchActive ? 'all' : tab, offset: 0, q, city, category, filters })
      if (id !== req.current) return
      setItems(res.items)
      setTotal(res.total)
      setState('ready')
      writeCache(key, { items: res.items, total: res.total })
    } catch {
      if (id === req.current && !shown) setState('error')
    } finally {
      if (mode === 'refresh') setRefreshing(false)
    }
  }, [tab, q, city, category, filters])

  useEffect(() => onRetry(() => load('first')), [load])

  useEffect(() => {
    if (!cityReady) return
    listRef.current?.scrollToOffset({ offset: 0, animated: false })
    load('first')
  }, [load, cityReady])

  const loadMore = async () => {
    if (more || state !== 'ready' || items.length >= total) return
    setMore(true)
    const id = req.current
    try {
      const res = await fetchFeed({ tab: searchActive ? 'all' : tab, offset: items.length, q, city, category, filters })
      if (id === req.current) setItems((prev) => [...prev, ...res.items.filter((n) => !prev.some((p) => p.id === n.id))])
    } catch {
      // подгрузка не удалась — следующая прокрутка попробует снова
    } finally {
      setMore(false)
    }
  }

  const empty = () => {
    if (state === 'loading') {
      return (
        <View style={styles.skelGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <View key={i} style={{ width: cardW, gap: 8 }}>
              <Skeleton style={{ width: cardW, height: Math.round(cardW * 0.95), borderRadius: radius.card }} />
              <Skeleton style={{ width: cardW * 0.85, height: 14 }} />
              <Skeleton style={{ width: cardW * 0.5, height: 18 }} />
            </View>
          ))}
        </View>
      )
    }
    if (state === 'error') {
      return (
        <View style={styles.center}>
          <Text style={styles.emptyTitle}>{tr('Не удалось загрузить ленту')}</Text>
          <Text style={styles.emptyText}>{tr('Проверьте интернет и попробуйте ещё раз.')}</Text>
          <Pressable style={styles.retry} onPress={() => load('first')}><Text style={styles.retryText}>{tr('Повторить')}</Text></Pressable>
        </View>
      )
    }
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>{q ? tr('Ничего не нашлось') : tr('Здесь пока пусто')}</Text>
        {!!q && <Text style={styles.emptyText}>{tr('Попробуйте сказать иначе или убрать часть слов.')}</Text>}
        {searchActive && (
          <>
            <Text style={[styles.emptyText, { marginTop: 10 }]}>{tr('Или посмотрите разделы:')}</Text>
            <View style={styles.suggest}>
              {['real-estate', 'auto', 'electronics', 'home-garden', 'fashion', 'services'].map((slug) => (
                <Pressable key={slug} style={styles.chip} onPress={() => router.push(`/c/${slug}`)}><Text style={styles.chipText}>{tr(SUGGEST[slug])}</Text></Pressable>
              ))}
            </View>
          </>
        )}
      </View>
    )
  }

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <View style={[styles.head, styles.headRow]} onLayout={(e) => setHeadBottom(e.nativeEvent.layout.y + e.nativeEvent.layout.height)}>
        <View style={[styles.search, { flex: 1 }]}>
          {/* пока ищут — плашка города сжимается до значка, место отдаётся полю поиска; поиск закрыли — разворачивается */}
          <Pressable style={[styles.city, focused && styles.cityCompact]} onPress={() => setCityOpen(true)} accessibilityRole="button"
            accessibilityLabel={`${tr('Выбрать город')}: ${city ? cityName(city) : tr('Все города')}`}>
            <Icon name="pin" size={15} color={colors.ink} />
            {!focused && <Text style={styles.cityText} numberOfLines={1}>{city ? cityName(city) : tr('Все города')}</Text>}
            {!focused && <Icon name="down" size={13} color={colors.inkSoft} />}
          </Pressable>
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder={hint}
            placeholderTextColor={colors.muted}
            style={styles.searchInput}
            returnKeyType="search"
            clearButtonMode="never"
            autoCorrect={false}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 180)}
            onSubmitEditing={() => applyQuery(query)}
          />
          {!!query && (
            <Pressable onPress={() => setQuery('')} hitSlop={10} accessibilityLabel={tr('Очистить поиск')}>
              <Icon name="close" size={16} color={colors.muted} />
            </Pressable>
          )}
          <Pressable onPress={() => setFiltersOpen(true)} hitSlop={8} style={styles.filterBtn} accessibilityRole="button" accessibilityLabel={tr('Фильтры')}>
            <Icon name="filter" size={21} color={colors.ink} />
            {activeCount(filters) > 0 && <View style={styles.filterDot}><Text style={styles.filterDotText}>{activeCount(filters)}</Text></View>}
          </Pressable>
        </View>
        {/* «Избранное» ушло из меню (там теперь «Шопсы») — сердечко рядом с профилем, как на сайте */}
        <Pressable style={styles.avatarPill} onPress={() => router.push('/favorites' as never)} accessibilityRole="button" accessibilityLabel={tr('Избранное')}>
          <Icon name="heart" size={22} color={colors.ink} />
        </Pressable>
        {/* Как на сайте: вошёл — аватар (в профиль), гость — «Войти»; непрочитанное — точкой на аватаре */}
        {user ? (
          <Pressable style={styles.avatarPill} onPress={() => router.navigate('/profile')} accessibilityRole="button" accessibilityLabel={tr('Профиль')}>
            <LinearGradient colors={['#7C6CF0', '#9B8FFF']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.avatarMini}>
              <Text style={styles.avatarMiniText}>{(user.display_name || user.email || '?').slice(0, 1).toUpperCase()}</Text>
            </LinearGradient>
            {notices > 0 && <View style={styles.avatarDot} />}
          </Pressable>
        ) : (
          <Pressable style={styles.loginPill} onPress={() => router.push('/login')} accessibilityRole="button"><Text style={styles.loginPillText}>{tr('Войти')}</Text></Pressable>
        )}
      </View>
      {showSug && (
        <View style={[styles.sugBox, { top: headBottom }]}>
          <ScrollView keyboardShouldPersistTaps="handled">
            {sug.categories.map((c) => (
              <Pressable key={c.slug} style={styles.sugRow} onPress={() => { setFocused(false); Keyboard.dismiss(); router.push(`/c/${c.slug}`) }} accessibilityRole="button">
                <Icon name="list" size={18} color={colors.ink} />
                <View style={styles.sugBody}>
                  <Text style={styles.sugText} numberOfLines={1}>{query.trim().toLowerCase()}</Text>
                  <Text style={styles.sugSub} numberOfLines={1}>{c.path}</Text>
                </View>
                <Icon name="forward" size={15} color={colors.muted} />
              </Pressable>
            ))}
            {/* как у Авито: сам набранный запрос — искать ровно его */}
            <Pressable style={styles.sugRow} onPress={() => applyQuery(query)} accessibilityRole="button">
              <Icon name="search" size={18} color={colors.ink} />
              <Text style={[styles.sugText, styles.sugBody]} numberOfLines={1}>{query.trim().toLowerCase()}</Text>
              <Icon name="forward" size={15} color={colors.muted} />
            </Pressable>
            {sug.completions.filter((c) => c !== query.trim().toLowerCase()).map((c) => {
              const typed = query.trim().toLowerCase()
              const rest = c.startsWith(typed) ? c.slice(typed.length) : ''
              return (
                <Pressable key={c} style={styles.sugRow} onPress={() => applyQuery(c)} accessibilityRole="button">
                  <Icon name="search" size={18} color={colors.ink} />
                  <Text style={[styles.sugText, styles.sugBody]} numberOfLines={1}>{rest ? typed : c}<Text style={styles.sugBold}>{rest}</Text></Text>
                  <Icon name="forward" size={15} color={colors.muted} />
                </Pressable>
              )
            })}
          </ScrollView>
        </View>
      )}
      <CityPicker visible={cityOpen} value={city} onPick={pickCity} onClose={() => setCityOpen(false)} />
      <SheetFrame visible={sortOpen} onClose={() => setSortOpen(false)}>
        <View style={styles.sortSheet}>
          <View style={styles.sortHandle} />
          {(['', 'new', 'cheap', 'expensive'] as const).map((k) => (
            <Pressable key={k || 'def'} style={styles.sortRow} onPress={() => { setFilters({ ...filters, sort: k }); setSortOpen(false) }}>
              <Text style={[styles.sortRowText, (filters.sort || '') === k && { color: colors.primaryDeep, fontFamily: font[800] }]}>{tr(SORT_NAME[k])}</Text>
              {(filters.sort || '') === k && <Icon name="check" size={16} color={colors.primary} />}
            </Pressable>
          ))}
        </View>
      </SheetFrame>
      <FiltersSheet visible={filtersOpen} value={filters} onApply={setFilters} onClose={() => setFiltersOpen(false)} />

      <FlatList
        ref={listRef}
        data={state === 'ready' ? items : []}
        keyExtractor={(it) => it.id}
        key={`cols-${cols}`}
        // Подгрузка порциями по 6 с паузой — меньше перерисовок при быстрой прокрутке
        maxToRenderPerBatch={6}
        updateCellsBatchingPeriod={40}
        numColumns={cols}
        renderItem={({ item }) => (cols === 1
          ? <View style={{ paddingHorizontal: space.page }}><ListingCard item={item} width={cardW} large /></View>
          : <ListingCard item={item} width={cardW} />)}
        columnWrapperStyle={cols === 2 ? styles.row : undefined}
        contentContainerStyle={[styles.list, { paddingBottom: 24 + tabInset }]}
        ListHeaderComponent={
          <View style={styles.listHead}>
            {!q && <CategoryTiles value={category} onPick={setCategory} />}
            {/* шопсы — под разделами, как на сайте */}
            {!q && <View style={{ marginTop: 12 }}><ShopsRow /></View>}
            {/* PLONK 2.0: подборки между плитками и лентой, как на сайте */}
            {!q && !category && cityReady && <HomeSections city={city} />}
            {!q && cityReady && !city && geoAsk && (
              <View style={styles.geo}>
                <Text style={styles.geoText}>{tr('Показать объявления рядом с вами?')}</Text>
                <Pressable style={styles.geoYes} disabled={geoBusy} onPress={detectCity}><Text style={styles.geoYesText}>{geoBusy ? '…' : tr('Показать')}</Text></Pressable>
                <Pressable style={styles.geoNo} onPress={dismissGeo}><Text style={styles.geoNoText}>{tr('Не надо')}</Text></Pressable>
              </View>
            )}
            {/* Поиск — как страница поиска сайта: плашки фильтров (+ «Сбросить»), ниже сортировка и «Сохранить поиск»;
                «Все / Новое / Даром» при поиске нет */}
            {searchActive ? (
              <View style={styles.searchHead}>
                {chipCount > 0 && (
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
                    {!!q && <ActiveChip label={`«${q}»`} onPress={() => { setQuery(''); setQ('') }} />}
                    {!!category && <ActiveChip label={tr('Раздел')} onPress={() => setCategory(null)} />}
                    {!!(filters.priceMin || filters.priceMax) && <ActiveChip label={`${filters.priceMin || '0'}–${filters.priceMax || '∞'} ${filters.currency === 'RSD' ? 'RSD' : '€'}`} onPress={() => setFilters({ ...filters, priceMin: undefined, priceMax: undefined })} />}
                    {!!filters.withPhoto && <ActiveChip label={tr('с фото')} onPress={() => setFilters({ ...filters, withPhoto: false })} />}
                    {!!filters.delivery && <ActiveChip label={tr('С доставкой')} onPress={() => setFilters({ ...filters, delivery: false })} />}
                    {chipCount > 1 && (
                      <Pressable style={styles.clearAll} onPress={() => { setQuery(''); setQ(''); setCategory(null); setFilters({ currency: filters.currency, sort: filters.sort }) }} accessibilityRole="button">
                        <Text style={styles.clearAllText}>{tr('Сбросить')}</Text>
                      </Pressable>
                    )}
                  </ScrollView>
                )}
                <View style={styles.resultsHead}>
                  <Pressable style={styles.sortBtn} onPress={() => setSortOpen(true)} accessibilityRole="button">
                    <Text style={styles.sortBtnText}>{tr(SORT_NAME[filters.sort || ''])}</Text>
                    <Icon name="down" size={12} color={colors.ink} />
                  </Pressable>
                  <Pressable style={[styles.saveBtn, savedState === 'saved' && styles.saveBtnOn]} disabled={savedState !== 'idle'} onPress={onSave} accessibilityRole="button">
                    <Text style={[styles.saveText, savedState === 'saved' && { color: '#fff' }]}>{savedState === 'saved' ? tr('Сохранено') : tr('Сохранить поиск')}</Text>
                  </Pressable>
                </View>
              </View>
            ) : (
              <View style={styles.tabsRow}>
                <Segmented options={TABS} value={tab} onChange={setTab} />
                <View style={styles.colsToggle}>
                  {([2, 1] as const).map((n) => (
                    <Pressable key={n} onPress={() => pickCols(n)} style={[styles.colBtn, cols === n && styles.colBtnOn]} accessibilityLabel={tr(n === 2 ? '2 колонки' : '1 колонка')} accessibilityState={{ selected: cols === n }}>
                      <Icon name={n === 2 ? 'cols2' : 'cols1'} size={16} color={cols === n ? '#fff' : colors.inkSoft} />
                    </Pressable>
                  ))}
                </View>
              </View>
            )}
          </View>
        }
        ListEmptyComponent={empty}
        onEndReached={loadMore}
        onEndReachedThreshold={0.6}
        ListFooterComponent={more ? <ActivityIndicator style={{ marginVertical: 16 }} color={colors.primary} /> : null}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { tap(); setRefreshing(true); load('refresh') }} tintColor={colors.primary} colors={[colors.primary]} />}
        keyboardDismissMode="on-drag"
        removeClippedSubviews
        initialNumToRender={6}
        windowSize={7}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  // подсказки — поверх ленты, сразу под шапкой
  sugBox: { position: 'absolute', left: 0, right: 0, bottom: 0, zIndex: 20, backgroundColor: colors.bg },
  sugRow: { flexDirection: 'row', alignItems: 'center', gap: 14, minHeight: 54, paddingHorizontal: 18, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  sugBody: { flex: 1, minWidth: 0 },
  sugText: { fontSize: 16, fontFamily: font[500], color: colors.ink },
  sugBold: { fontFamily: font[800] },
  sugSub: { fontSize: 13, fontFamily: font[500], color: colors.muted, marginTop: 1 },
  page: { flex: 1, backgroundColor: colors.bg },
  head: { paddingHorizontal: space.page, paddingTop: 6, paddingBottom: 10 },
  listHead: { gap: 12, paddingBottom: 2 },
  searchHead: { gap: 0 },
  chipsRow: { gap: 7, paddingHorizontal: space.page, paddingTop: 2, alignItems: 'center' },
  clearAll: { paddingVertical: 7, paddingHorizontal: 12, borderRadius: 11, borderWidth: 1, borderColor: 'rgba(20,30,25,0.12)' },
  clearAllText: { fontSize: 12.5, fontFamily: font[600], color: colors.muted },
  // как .results-head сайта: слева сортировка, справа «Сохранить поиск»
  resultsHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: space.page, paddingTop: 12, paddingBottom: 2 },
  sortBtn: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingVertical: 7, paddingHorizontal: 11, borderRadius: 10, backgroundColor: colors.sunken },
  sortBtnText: { fontSize: 12.5, fontFamily: font[700], color: colors.ink },
  sortSheet: { backgroundColor: colors.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingTop: 8, paddingBottom: 28 },
  sortHandle: { alignSelf: 'center', width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border, marginBottom: 6 },
  sortRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 52, paddingHorizontal: 20, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  sortRowText: { fontSize: 16, fontFamily: font[600], color: colors.ink },
  found: { gap: 8, paddingHorizontal: space.page },
  foundText: { fontSize: 14, fontFamily: font[800], color: colors.ink },
  // как .active-filter-chip сайта: 7/12, скругление 11, 12,5/600, крестик приглушённый
  activeChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 7, paddingLeft: 13, paddingRight: 11, borderRadius: 11, backgroundColor: colors.primarySoft, maxWidth: 220 },
  activeChipText: { fontSize: 12.5, fontFamily: font[600], color: colors.primaryDeep, flexShrink: 1 },
  suggest: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginTop: 8 },
  chip: { height: 34, paddingHorizontal: 12, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  chipText: { fontSize: 13.5, fontFamily: font[700], color: colors.ink },
  geo: { flexDirection: 'row', alignItems: 'center', gap: 8, marginHorizontal: space.page, padding: 10, paddingLeft: 14, borderRadius: 14, backgroundColor: colors.primarySoft },
  geoText: { flex: 1, fontSize: 14, lineHeight: 18, fontFamily: font[700], color: colors.primaryDeep },
  geoYes: { height: 34, paddingHorizontal: 12, borderRadius: 10, backgroundColor: colors.primary, justifyContent: 'center' },
  geoYesText: { color: '#fff', fontSize: 13.5, fontFamily: font[800] },
  geoNo: { height: 34, paddingHorizontal: 8, justifyContent: 'center' },
  geoNoText: { color: colors.primaryDeep, fontSize: 13.5, fontFamily: font[700] },
  headRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  // как .avito-login-pill / .avatar-mini сайта: серая подложка 48, аватар 38 с фиолетовым градиентом
  avatarPill: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  avatarMini: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
  avatarMiniText: { color: '#fff', fontSize: 15, fontFamily: font[800] },
  avatarDot: { position: 'absolute', top: 4, right: 4, width: 11, height: 11, borderRadius: 6, backgroundColor: colors.accent, borderWidth: 2, borderColor: colors.bg },
  loginPill: { height: 48, paddingHorizontal: 15, borderRadius: 15, backgroundColor: colors.sunken, justifyContent: 'center' },
  loginPillText: { fontSize: 13.5, fontFamily: font[600], color: colors.ink },
  bell: { width: 44, height: 46, alignItems: 'center', justifyContent: 'center' },
  bellDot: { position: 'absolute', top: 6, right: 4, minWidth: 17, height: 17, borderRadius: 9, paddingHorizontal: 4, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: colors.bg },
  bellDotText: { color: '#fff', fontSize: 10, fontFamily: font[800] },
  tabsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, paddingHorizontal: space.page },
  colsToggle: { flexDirection: 'row', gap: 2, padding: 3, borderRadius: 12, backgroundColor: colors.sunken },
  colBtn: { width: 34, height: 30, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  colBtnOn: { backgroundColor: colors.primary },
  // как .save-search сайта: 8/13, скругление 11, 12,5/700; сохранено — зелёная
  saveBtn: { paddingVertical: 8, paddingHorizontal: 13, borderRadius: 11, backgroundColor: colors.primarySoft },
  saveBtnOn: { backgroundColor: colors.primary },
  saveText: { fontSize: 12.5, fontFamily: font[700], color: colors.primaryDeep },
  filterBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  filterDot: { position: 'absolute', top: 2, right: 0, minWidth: 16, height: 16, borderRadius: 8, paddingHorizontal: 4, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  filterDotText: { color: '#fff', fontSize: 10, fontFamily: font[800] },
  city: { flexDirection: 'row', alignItems: 'center', gap: 4, height: 36, paddingHorizontal: 10, borderRadius: 11, backgroundColor: colors.surface, maxWidth: 150, flexShrink: 0 },
  cityCompact: { width: 36, paddingHorizontal: 0, justifyContent: 'center' },
  cityText: { fontSize: 13.5, fontFamily: font[800], color: colors.ink, flexShrink: 1 },
  search: {
    flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, paddingHorizontal: 14,
    borderRadius: radius.field, backgroundColor: colors.sunken, paddingLeft: 5,
  },
  // flexBasis 0 и minWidth 0 — поле сжимается, и кнопка фильтров остаётся внутри строки поиска
  searchInput: { flex: 1, flexBasis: 0, minWidth: 0, fontFamily: font[400], fontSize: 15.5, color: colors.ink, paddingVertical: 0 },
  list: { paddingHorizontal: 0, paddingBottom: 24, gap: space.gap },
  row: { gap: space.gap, paddingHorizontal: space.page },
  skelGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.gap, paddingHorizontal: space.page },
  center: { alignItems: 'center', paddingTop: 80, paddingHorizontal: 32, gap: 8 },
  emptyTitle: { fontSize: 18, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  emptyText: { fontFamily: font[400], fontSize: 14.5, color: colors.inkSoft, textAlign: 'center', lineHeight: 20 },
  retry: { marginTop: 8, height: 44, paddingHorizontal: 20, borderRadius: 12, backgroundColor: colors.primary, justifyContent: 'center' },
  retryText: { color: '#fff', fontFamily: font[800], fontSize: 15 },
})
