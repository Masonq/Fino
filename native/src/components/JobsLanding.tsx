import { TINTS } from '../tints'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, FlatList, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native'
import Pressable from './Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type FeedItem, fetchFeed, myListings } from '../api'
import { useAuth } from '../auth'
import { SITE } from '../config'
import { plural, tr } from '../i18n'
import { colors, font, space } from '../theme'
import Icon from './Icon'
import ListingCard from './ListingCard'
import { TILE, jobPath, tileFor } from '../artFit'
import { TileLabelArt } from './TileArt'
import Sheet from './Sheet'

/**
 * Раздел «Работа» — по образцу Авито: вкладки «Ищу работу» / «Ищу сотрудников».
 * Соискатель: «Какую работу вы ищете?», поиск, плитки-подборки (каждая — настоящий фильтр по полям вакансии:
 * занятость, формат, опыт, «нужен сербский»), «Кабинет соискателя», свежие вакансии.
 * Работодатель: «Разместить вакансию», мои вакансии, переписки, резюме, «Как нанимать», поиск по резюме.
 * Картинки плиток — /cat/jobs-<ключ>.png сайта в стиле разделов (пока новой нет — прежняя /jobs/<ключ>.webp).
 */
type Tile = { key: string; label: string; eq: Record<string, string | boolean>; wide?: boolean }
const ROW1: Tile[] = [
  { key: 'part_time', label: 'Подработка', eq: { employment_type: 'part_time' }, wide: true },
  { key: 'full_time', label: 'Полный день', eq: { employment_type: 'full_time' } },
  { key: 'remote', label: 'Удалённо', eq: { work_format: 'remote' } },
  { key: 'shift', label: 'Сменный график', eq: { employment_type: 'shift' } },
]
const ROW2: Tile[] = [
  { key: 'no_exp', label: 'Без опыта', eq: { experience: 'none' } },
  { key: 'no_serbian', label: 'Без сербского', eq: { serbian_needed: false }, wide: true },
  { key: 'one_off', label: 'Разовая работа', eq: { employment_type: 'one_off' } },
]
const TIPS = [
  'Укажите зарплату и график — это первое, на что смотрят соискатели.',
  'Отметьте, нужен ли сербский: многие ищут работу без языка.',
  'Отвечайте в сообщениях в первый день — так кандидаты не уходят к другим.',
  'Опишите задачи простыми словами и добавьте фото места работы.',
]

export default function JobsLanding() {
  const insets = useSafeAreaInsets()
  const { width } = useWindowDimensions()
  const cardW = Math.floor((width - space.page * 2 - space.gap) / 2)
  const { user, token } = useAuth()
  const [tab, setTab] = useState<'seek' | 'hire'>('seek')
  const [tile, setTile] = useState<Tile | null>(null)
  const [query, setQuery] = useState('')
  const [q, setQ] = useState('')
  const [items, setItems] = useState<FeedItem[] | null>(null)
  const [total, setTotal] = useState(0)
  const [myVac, setMyVac] = useState<number | null>(null)
  const [tipsOpen, setTipsOpen] = useState(false)
  const listRef = useRef<FlatList<FeedItem>>(null)

  useEffect(() => { const t = setTimeout(() => setQ(query.trim()), 350); return () => clearTimeout(t) }, [query])
  const sub = tab === 'seek' ? 'vacancies' : 'resumes'
  useEffect(() => {
    let alive = true
    setItems(null)
    fetchFeed({ tab: 'all', offset: 0, q, category: sub, extra: tab === 'seek' && tile ? { attr_eq: JSON.stringify(tile.eq) } : undefined })
      .then((r) => { if (alive) { setItems(r.items); setTotal(r.total) } }).catch(() => { if (alive) setItems([]) })
    return () => { alive = false }
  }, [sub, q, tile, tab])
  useFocusEffect(useCallback(() => {
    if (!token) { setMyVac(null); return }
    myListings(token).then((r) => setMyVac(r.items.filter((l) => l.status === 'active' && l.category_slug === 'vacancies').length)).catch(() => {})
  }, [token]))

  const switchTab = (t: 'seek' | 'hire') => { setTab(t); setTile(null); setQuery(''); setQ('') }
  // к результатам; если их нет — в конец, к «пока нет» (scrollToIndex на пустом списке падает)
  const itemsRef = useRef<FeedItem[] | null>(null)
  itemsRef.current = items
  const toResults = () => setTimeout(() => {
    if (itemsRef.current?.length) listRef.current?.scrollToIndex({ index: 0, viewOffset: 60, animated: true })
    else listRef.current?.scrollToEnd({ animated: true })
  }, 600)
  const needLogin = (go: () => void) => (user ? go() : router.push('/login'))

  const tileView = (t: Tile) => {
    const on = tile?.key === t.key
    return (
      <Pressable key={t.key} style={[styles.tile, { width: tileFor(tr(t.label)).tile, backgroundColor: TINTS.jobs }, on && styles.tileOn]} onPress={() => { setTile(on ? null : t); if (!on) toResults() }} accessibilityRole="button" accessibilityState={{ selected: on }}>
        <TileLabelArt uri={`${SITE}${jobPath(t.key)}`} name={tr(t.label)} fit={tileFor(tr(t.label))} style={styles.tileText} />
        {on && <View style={styles.tileCheck}><Icon name="check" size={12} color="#fff" /></View>}
      </Pressable>
    )
  }

  const seekHead = (
    <View>
      <Text style={styles.h1}>{tr('Какую работу вы ищете?')}</Text>
      <View style={styles.search}>
        <Icon name="search" size={18} color={colors.muted} />
        <TextInput value={query} onChangeText={setQuery} placeholder={tr('Профессия, должность или компания')} placeholderTextColor={colors.muted} style={styles.searchInput} returnKeyType="search" onSubmitEditing={toResults} />
        {!!query && <Pressable onPress={() => setQuery('')} hitSlop={8}><Icon name="close" size={15} color={colors.muted} /></Pressable>}
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tiles}>
        <View style={{ gap: 8 }}>
          <View style={styles.tileRow}>{ROW1.map(tileView)}</View>
          <View style={styles.tileRow}>{ROW2.map(tileView)}</View>
        </View>
      </ScrollView>
      <Pressable style={styles.h2Row} onPress={() => needLogin(() => router.push('/my'))}>
        <Text style={styles.h2}>{tr('Кабинет соискателя')}</Text>
        <View style={styles.h2Arrow}><Icon name="forward" size={13} color={colors.onInverse} /></View>
      </Pressable>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cabinet}>
        <Pressable style={styles.cabCard} onPress={() => needLogin(() => router.push({ pathname: '/post', params: { cat: 'resumes' } }))}>
          <View style={styles.cabIcon}><Icon name="list" size={22} color={colors.ink} /></View>
          <View style={{ flex: 1 }}><Text style={styles.cabTitle}>{tr('Создайте резюме')}</Text><Text style={styles.cabText}>{tr('И работа найдёт вас сама')}</Text></View>
        </Pressable>
        <Pressable style={styles.cabCard} onPress={() => needLogin(() => router.push('/chats'))}>
          <View style={styles.cabIcon}><Icon name="chat" size={22} color={colors.ink} /></View>
          <View style={{ flex: 1 }}><Text style={styles.cabTitle}>{tr('Отклики')}</Text><Text style={styles.cabText}>{tr('Переписки с работодателями')}</Text></View>
        </Pressable>
      </ScrollView>
      <Text style={styles.h2}>{tile ? tr(tile.label) : tr('Свежие вакансии')}{items ? ` · ${total}` : ''}</Text>
    </View>
  )

  const hireHead = (
    <View>
      <View style={styles.hero}>
        <View style={{ flex: 1, gap: 8 }}>
          <Text style={styles.heroTitle}>{tr('Разместить вакансию')}</Text>
          <Text style={styles.heroText}>{tr('Её увидят все соискатели на PLONK, а вы выберете из лучших')}</Text>
          <Pressable style={styles.heroBtn} onPress={() => needLogin(() => router.push({ pathname: '/post', params: { cat: 'vacancies' } }))} accessibilityRole="button">
            <Text style={styles.heroBtnText}>{tr('Разместить вакансию')}</Text>
          </Pressable>
        </View>
        <Image source={{ uri: `${SITE}${jobPath('hire')}` }} style={styles.heroImg} contentFit="contain" />
      </View>
      <View style={styles.grid}>
        <View style={styles.gridCol}>
          <Pressable style={styles.gCard} onPress={() => needLogin(() => router.push('/my'))}>
            <Text style={styles.gTitle}>{myVac ? tr('Мои вакансии') : tr('Нет активных вакансий')}</Text>
            {!!myVac && <Text style={styles.gText}>{myVac} {plural(myVac, { ru: ['активная', 'активные', 'активных'], en: ['active', 'active'], sr: ['aktivan', 'aktivna', 'aktivnih'] })}</Text>}
          </Pressable>
          <Pressable style={[styles.gCard, { minHeight: 150 }]} onPress={toResults}>
            <Text style={styles.gTitle}>{tr('Поищите среди резюме')}</Text>
            <Text style={styles.gText}>{items ? `${total} ${plural(total, { ru: ['резюме', 'резюме', 'резюме'], en: ['resume', 'resumes'], sr: ['CV', 'CV-a', 'CV-a'] })} ${tr('на PLONK')}` : ' '}</Text>
          </Pressable>
        </View>
        <View style={styles.gridCol}>
          <Pressable style={[styles.gCard, { minHeight: 150 }]} onPress={() => needLogin(() => router.push('/chats'))}>
            <Text style={styles.gTitle}>{tr('Отклики')}</Text>
            <Text style={styles.gText}>{tr('Переписки с соискателями')}</Text>
          </Pressable>
          <Pressable style={[styles.gCard, styles.gHow]} onPress={() => setTipsOpen(true)}>
            <Text style={styles.gTitle}>{tr('Как нанимать на PLONK')}</Text>
          </Pressable>
        </View>
      </View>
      <Text style={[styles.h2, { marginTop: 22 }]}>{tr('Найти сотрудника')}</Text>
      <View style={styles.search}>
        <Icon name="search" size={18} color={colors.muted} />
        <TextInput value={query} onChangeText={setQuery} placeholder={tr('Профессия или навык')} placeholderTextColor={colors.muted} style={styles.searchInput} returnKeyType="search" onSubmitEditing={toResults} />
        {!!query && <Pressable onPress={() => setQuery('')} hitSlop={8}><Icon name="close" size={15} color={colors.muted} /></Pressable>}
      </View>
      <Text style={styles.h2}>{tr('Резюме')}{items ? ` · ${total}` : ''}</Text>
    </View>
  )

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <View style={styles.tabs}>
          {(['seek', 'hire'] as const).map((t) => (
            <Pressable key={t} onPress={() => switchTab(t)} style={styles.tabBtn} accessibilityRole="tab" accessibilityState={{ selected: tab === t }}>
              <Text style={[styles.tabText, tab === t && styles.tabTextOn]}>{tr(t === 'seek' ? 'Ищу работу' : 'Ищу сотрудников')}</Text>
              <View style={[styles.tabLine, tab === t && styles.tabLineOn]} />
            </Pressable>
          ))}
        </View>
      </View>
      <FlatList
        ref={listRef}
        data={items ?? []}
        keyExtractor={(i) => i.id}
        numColumns={2}
        columnWrapperStyle={{ gap: space.gap, paddingHorizontal: space.page }}
        contentContainerStyle={{ gap: space.gap, paddingBottom: insets.bottom + 30 }}
        ListHeaderComponent={<View style={styles.head}>{tab === 'seek' ? seekHead : hireHead}</View>}
        renderItem={({ item }) => <ListingCard item={item} width={cardW} />}
        onScrollToIndexFailed={() => {}}
        ListEmptyComponent={items === null ? <ActivityIndicator style={{ marginTop: 20 }} color={colors.primary} /> : <Text style={styles.empty}>{tr(tab === 'seek' ? 'Вакансий по этому запросу пока нет' : 'Резюме по этому запросу пока нет')}</Text>}
        keyboardShouldPersistTaps="handled"
      />
      <Sheet visible={tipsOpen} title={tr('Как нанимать на PLONK')} onClose={() => setTipsOpen(false)}>
        <View style={styles.tips}>
          {TIPS.map((t) => <View key={t} style={styles.tip}><View style={styles.tipDot} /><Text style={styles.tipText}>{tr(t)}</Text></View>)}
        </View>
      </Sheet>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, paddingTop: 4 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  tabs: { flex: 1, flexDirection: 'row', gap: 22, paddingLeft: 6, borderBottomWidth: 1.5, borderBottomColor: colors.border, marginRight: 12 },
  tabBtn: { paddingTop: 8 },
  tabText: { fontSize: 18, fontFamily: font[800], color: colors.muted, letterSpacing: -0.2 },
  tabTextOn: { color: colors.ink },
  tabLine: { height: 3, borderRadius: 2, marginTop: 8, marginBottom: -1.5, backgroundColor: 'transparent' },
  tabLineOn: { backgroundColor: colors.inverse },
  head: { paddingHorizontal: space.page, paddingTop: 18, paddingBottom: 6 },
  h1: { fontSize: 26, lineHeight: 31, fontFamily: font[800], color: colors.ink, letterSpacing: -0.5 },
  search: { flexDirection: 'row', alignItems: 'center', gap: 10, height: 50, borderRadius: 16, backgroundColor: colors.sunken, paddingHorizontal: 15, marginTop: 14 },
  searchInput: { flex: 1, fontSize: 16, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  tiles: { paddingVertical: 18, paddingRight: space.page },
  tileRow: { flexDirection: 'row', gap: 8 },
  tile: { width: TILE.w, height: TILE.h, borderRadius: 16, backgroundColor: colors.sunken, padding: TILE.pad, overflow: 'hidden', borderWidth: 2, borderColor: 'transparent' },
  tileWide: { width: TILE.wide },
  tileOn: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  tileText: { fontSize: 13.5, lineHeight: 17, fontFamily: font[700], color: colors.ink, maxWidth: TILE.text.narrow },
  // крупнее (84) и чуть за правый и нижний край, как у Авито; плитка прежняя
  tileImg: { position: 'absolute', right: -10, bottom: -16, width: 84, height: 84 },
  tileCheck: { position: 'absolute', right: 8, top: 8, width: 20, height: 20, borderRadius: 10, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  h2Row: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 6 },
  h2: { fontSize: 21, fontFamily: font[800], color: colors.ink, letterSpacing: -0.3, marginTop: 6, marginBottom: 12 },
  h2Arrow: { width: 24, height: 24, borderRadius: 12, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  cabinet: { gap: 10, paddingBottom: 18, paddingRight: space.page },
  cabCard: { flexDirection: 'row', alignItems: 'center', gap: 12, width: 270, padding: 12, borderRadius: 18, backgroundColor: colors.sunken },
  cabIcon: { width: 52, height: 52, borderRadius: 14, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  cabTitle: { fontSize: 15.5, fontFamily: font[800], color: colors.ink },
  cabText: { fontSize: 13.5, fontFamily: font[500], color: colors.inkSoft, marginTop: 2 },
  hero: { flexDirection: 'row', alignItems: 'center', gap: 6, padding: 18, paddingBottom: 18, borderRadius: 24, backgroundColor: colors.sunken, overflow: 'hidden' },
  heroTitle: { fontSize: 21, fontFamily: font[800], color: colors.ink, letterSpacing: -0.3 },
  heroText: { fontSize: 14, lineHeight: 19, fontFamily: font[500], color: colors.inkSoft },
  heroBtn: { alignSelf: 'flex-start', marginTop: 6, height: 44, paddingHorizontal: 18, borderRadius: 14, backgroundColor: colors.inverse, justifyContent: 'center' },
  heroBtnText: { color: colors.onInverse, fontSize: 14.5, fontFamily: font[700] },
  // как у Авито: человек крупно, прижат к правому и нижнему краю карточки
  heroImg: { width: 116, height: 176, marginRight: -18, marginBottom: -26, alignSelf: 'flex-end' },
  grid: { flexDirection: 'row', gap: 8, marginTop: 8 },
  gridCol: { flex: 1, gap: 8 },
  gCard: { minHeight: 96, padding: 15, borderRadius: 20, backgroundColor: colors.sunken, gap: 6 },
  gHow: { minHeight: 96, backgroundColor: '#ECE9FB' },
  gTitle: { fontSize: 15.5, lineHeight: 20, fontFamily: font[800], color: colors.ink },
  gText: { fontSize: 13.5, lineHeight: 18, fontFamily: font[500], color: colors.inkSoft },
  empty: { textAlign: 'center', color: colors.muted, fontFamily: font[500], fontSize: 14, marginTop: 16, paddingHorizontal: 30 },
  tips: { paddingHorizontal: 20, paddingBottom: 10, gap: 12 },
  tip: { flexDirection: 'row', gap: 10 },
  tipDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.primary, marginTop: 8 },
  tipText: { flex: 1, fontSize: 15, lineHeight: 21, fontFamily: font[500], color: colors.ink },
})
