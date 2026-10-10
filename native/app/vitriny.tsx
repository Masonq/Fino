import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { FlatList, StyleSheet, Text, TextInput, View } from 'react-native'
import Pressable from '../src/components/Pressable'
import { tr } from '../src/i18n'
import { Header } from '../src/components/Kit'
import Icon from '../src/components/Icon'
import Segmented from '../src/components/Segmented'
import Skeleton from '../src/components/Skeleton'
import { API, mediaUrl } from '../src/config'
import { colors, font } from '../src/theme'

type Sf = { slug: string; name: string; count: number; city?: string | null; previews: string[]; followers?: number | null }

/** «Витрины продавцов» целиком — как на сайте (/vitriny): поиск по названию, сортировка, сетка витрин с превью. */
export default function Vitriny() {
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<'popular' | 'new'>('popular')
  const [items, setItems] = useState<Sf[] | null>(null)
  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`${API}/storefronts/discover?sort=${sort}&limit=60${q.trim() ? `&q=${encodeURIComponent(q.trim())}` : ''}`)
        .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => setItems([]))
    }, 250)
    return () => clearTimeout(t)
  }, [q, sort])
  return (
    <View style={st.page}>
      <FlatList
        data={items ?? []}
        keyExtractor={(s) => s.slug}
        numColumns={2}
        columnWrapperStyle={{ gap: 10 }}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60, gap: 10 }}
        ListHeaderComponent={<>
          <Header bleed={16} bleedTop={0} title={tr('Витрины продавцов')} kicker={tr('Магазины и частные продавцы')} fallback="/" />
          <View style={st.search}>
            <Icon name="search" size={17} color={colors.muted} />
            <TextInput style={st.input} value={q} onChangeText={setQ} placeholder={tr('Найти витрину')} placeholderTextColor={colors.muted} autoCorrect={false} />
          </View>
          <View style={{ marginBottom: 12 }}><Segmented options={[{ key: 'popular', label: tr('Популярные') }, { key: 'new', label: tr('Новые') }]} value={sort} onChange={(v) => setSort(v as 'popular' | 'new')} /></View>
        </>}
        ListEmptyComponent={items === null
          ? <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>{[0, 1, 2, 3].map((i) => <Skeleton key={i} style={{ width: '48%', height: 200, borderRadius: 22 }} />)}</View>
          : <Text style={st.empty}>{tr('Ничего не нашлось')}</Text>}
        renderItem={({ item: s }) => (
          <Pressable style={st.card} onPress={() => router.push(`/s/${s.slug}` as never)}>
            <View style={st.grid}>
              <View style={st.big}>{!!s.previews[0] && <Image source={{ uri: mediaUrl(s.previews[0]) || undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}</View>
              <View style={{ flex: 1, gap: 4 }}>
                {[1, 2].map((k) => <View key={k} style={st.small}>{!!s.previews[k] && <Image source={{ uri: mediaUrl(s.previews[k]) || undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}</View>)}
              </View>
            </View>
            <Text style={st.name} numberOfLines={1}>{s.name}</Text>
            <Text style={st.meta} numberOfLines={1}>{tr('{n} шт.', { n: s.count })}{s.city ? ` · ${s.city}` : ''}</Text>
          </Pressable>
        )}
      />
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 46, borderRadius: 18, backgroundColor: colors.surface, paddingHorizontal: 14, marginBottom: 10 },
  input: { flex: 1, fontFamily: font[400], fontSize: 16, color: colors.ink },
  card: { flex: 1, maxWidth: '50%', padding: 8, borderRadius: 22, backgroundColor: colors.surface },
  grid: { flexDirection: 'row', gap: 4, height: 128, borderRadius: 14, overflow: 'hidden' },
  big: { flex: 2, backgroundColor: colors.sunken, overflow: 'hidden' },
  small: { flex: 1, backgroundColor: colors.sunken, overflow: 'hidden' },
  name: { fontFamily: font[800], fontSize: 14.5, color: colors.ink, marginTop: 8, marginHorizontal: 2 },
  meta: { fontFamily: font[600], fontSize: 12, color: colors.muted, marginHorizontal: 2, marginTop: 1 },
  empty: { textAlign: 'center', padding: 30, fontFamily: font[600], color: colors.muted },
})
