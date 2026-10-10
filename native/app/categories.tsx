import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import Pressable from '../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type Category, fetchCategories } from '../src/api'
import Icon from '../src/components/Icon'
import { SITE } from '../src/config'
import { TILE, catPath, type TileFit } from '../src/artFit'
import { TileLabelArt } from '../src/components/TileArt'
import { getLang, tr } from '../src/i18n'
import { colors, font } from '../src/theme'
import { TINTS } from '../src/tints'

/** «Все разделы» — как /categories сайта: сетка разделов с картинками; ещё не готовые — «Скоро». */
export default function Categories() {
  const insets = useSafeAreaInsets()
  const [cats, setCats] = useState<Category[] | null>(null)
  useEffect(() => { fetchCategories().then(setCats).catch(() => setCats([])) }, [])
  // плитки как у Авито и как на сайте: два столбца, высота 96, надпись сверху слева, картинка в углу чуть за краем
  const { width } = useWindowDimensions()
  const colW = Math.floor((width - 24 - 8) / 2)
  const fit: TileFit = { kind: '', tile: colW, text: colW - 26, art: 'big', h: 96 }
  const nameOf = (c: Category) => (typeof c.name === 'string' ? c.name : c.name?.[getLang()] || c.name?.ru || c.slug)
  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Все разделы')}</Text>
      </View>
      {cats === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <ScrollView contentContainerStyle={styles.grid}>
          {cats.map((c) => (
            <Pressable key={c.id} style={[styles.item, { width: colW, backgroundColor: TINTS[c.slug] ?? colors.sunken }, c.ready === false && { opacity: 0.55 }]} onPress={() => router.push(`/c/${c.slug}`)} accessibilityRole="button">
              <TileLabelArt uri={`${SITE}${catPath(c.slug)}`} name={nameOf(c)} fit={fit} style={styles.label} />
              {c.ready === false && <Text style={styles.soon}>{tr('Скоро')}</Text>}
            </Pressable>
          ))}
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, minHeight: 56 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingHorizontal: 12, paddingBottom: 32, paddingTop: 4 },
  item: { height: 96, borderRadius: 16, padding: TILE.pad, backgroundColor: colors.sunken, borderWidth: 2, borderColor: 'transparent', overflow: 'hidden' },
  label: { fontSize: 13.5, lineHeight: 17, fontFamily: font[700], color: colors.ink, zIndex: 2 },
  soon: { position: 'absolute', left: 11, bottom: 9, zIndex: 2, fontSize: 10, fontFamily: font[800], color: colors.muted, backgroundColor: colors.sunken, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
})
