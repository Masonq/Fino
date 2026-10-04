import { select } from '../haptics'
import Icon, { Star } from './Icon'
import { getLang, tr } from '../i18n'
import { Image } from 'expo-image'
import { Ionicons } from '@expo/vector-icons'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

import { type Category, fetchCategories } from '../api'
import { SITE } from '../config'
import { colors, font } from '../theme'
import Skeleton from './Skeleton'

// как плитки внутри разделов (JobsLanding, c/[slug]): 142×100, широкие — 196 и 240
const W = 142
const H = 100
const widthFor = (name: string) => {
  const longest = Math.max(...name.split(/\s+/).map((w) => w.length))
  return longest > 13 ? { tile: 240, text: 196 } : name.length > 13 || longest > 8 ? { tile: 196, text: 150 } : { tile: W, text: 92 }
}

const nameOf = (c: Category) => (typeof c.name === 'string' ? c.name : c.name?.[getLang()] || c.name?.ru || c.slug)

/**
 * Плитки разделов в две строки с прокруткой вбок — как на главной сайта: название сверху, объёмная картинка
 * раздела снизу справа (те же /cat/<раздел>.png). Нажатие выбирает раздел для ленты, повторное — снимает.
 */
export default function CategoryTiles({ value, onPick }: { value: string | null; onPick: (slug: string | null) => void }) {
  const [cats, setCats] = useState<Category[] | null>(null)
  useEffect(() => { fetchCategories().then(setCats).catch(() => setCats([])) }, [])

  if (cats === null) {
    return (
      <View style={styles.wrap}>
        {[0, 1].map((r) => (
          <View key={r} style={styles.row}>
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} style={{ width: W, height: H, borderRadius: 18 }} />)}
          </View>
        ))}
      </View>
    )
  }
  if (cats.length === 0) return null

  const tiles: (Category | 'all')[] = ['all', ...cats]
  // Как на сайте — по столбцам сверху вниз: «Все / Недвижимость», «Авто / Услуги», «Работа / Электроника»…
  const rows = [tiles.filter((_, i) => i % 2 === 0), tiles.filter((_, i) => i % 2 === 1)]

  const tile = (c: Category | 'all') => {
    if (c === 'all') {
      const on = value === null
      return (
        <Pressable key="all" style={[styles.tile, styles.allTile]} onPress={() => { select(); onPick(null); router.push('/categories') }} accessibilityRole="button" accessibilityState={{ selected: on }}>
          <Text style={[styles.label, styles.labelOn]}>{tr('Все')}</Text>
          <View style={styles.allIcon}><Icon name="grid" size={34} color={colors.primary} /></View>
        </Pressable>
      )
    }
    const on = value === c.slug
    return (
      <Pressable key={c.slug} style={[styles.tile, { width: widthFor(nameOf(c)).tile }, on && styles.tileOn, c.ready === false && styles.soon]} onPress={() => { select(); router.push(`/c/${c.slug}`) }}
        accessibilityRole="button" accessibilityState={{ selected: on }}>
        {/* Одно длинное слово («Недвижимость») не переносим посреди слова — слегка ужимаем */}
        <Text style={[styles.label, { maxWidth: widthFor(nameOf(c)).text }, on && styles.labelOn]}>{nameOf(c)}</Text>
        <Image source={{ uri: `${SITE}/cat/${c.slug}.png` }} style={styles.art} contentFit="contain" transition={200} />
      </Pressable>
    )
  }

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scroll}>
      <View style={styles.wrapInner}>
        {rows.map((row, i) => <View key={i} style={styles.row}>{row.map(tile)}</View>)}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: 12, gap: 8 },
  scroll: { paddingHorizontal: 12 },
  wrapInner: { gap: 8 },
  row: { flexDirection: 'row', gap: 8 },
  // Размеры — как .cat-tile-2row на сайте: 118×86, отступы 9/8/6/11, подпись 12 полужирная, картинка 58×58 в углу
  tile: { width: W, height: H, borderRadius: 18, backgroundColor: colors.sunken, borderWidth: 2, borderColor: 'transparent', padding: 13, overflow: 'hidden' },
  allTile: { backgroundColor: colors.primarySoft },
  tileOn: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  soon: { opacity: 0.55 },
  label: { fontSize: 14.5, lineHeight: 18, fontFamily: font[700], color: colors.ink, zIndex: 2 },
  labelOn: { color: colors.primaryDeep },
  art: { position: 'absolute', right: -2, bottom: -4, width: 66, height: 66 },
  allIcon: { position: 'absolute', right: 12, bottom: 10 },
})
