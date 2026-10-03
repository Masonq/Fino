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

const W = 118
const H = 86

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
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} style={{ width: W, height: H, borderRadius: 15 }} />)}
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
        <Pressable key="all" style={[styles.tile, styles.allTile, on && styles.tileOn]} onPress={() => { select(); onPick(null) }} accessibilityRole="button" accessibilityState={{ selected: on }}>
          <Text style={[styles.label, styles.labelOn]}>{tr('Все')}</Text>
          <View style={styles.allIcon}><Icon name="grid" size={34} color={colors.primary} /></View>
        </Pressable>
      )
    }
    const on = value === c.slug
    return (
      <Pressable key={c.slug} style={[styles.tile, on && styles.tileOn, c.ready === false && styles.soon]} onPress={() => { select(); router.push(`/c/${c.slug}`) }}
        accessibilityRole="button" accessibilityState={{ selected: on }}>
        {/* Одно длинное слово («Недвижимость») не переносим посреди слова — слегка ужимаем */}
        <Text style={[styles.label, on && styles.labelOn]} numberOfLines={nameOf(c).includes(' ') ? 2 : 1} adjustsFontSizeToFit={!nameOf(c).includes(' ')} minimumFontScale={0.8}>{nameOf(c)}</Text>
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
  tile: { width: W, height: H, borderRadius: 15, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingTop: 9, paddingRight: 8, paddingBottom: 6, paddingLeft: 11, overflow: 'hidden' },
  allTile: { backgroundColor: colors.primarySoft, borderColor: 'rgba(14,159,110,0.3)' },
  tileOn: { borderColor: colors.primary, borderWidth: 1.5, backgroundColor: colors.primarySoft },
  soon: { opacity: 0.55 },
  label: { fontSize: 12, lineHeight: 14, fontFamily: font[700], letterSpacing: -0.12, color: colors.ink, zIndex: 2 },
  labelOn: { color: colors.primaryDeep },
  art: { position: 'absolute', right: 2, bottom: 0, width: 58, height: 58 },
  allIcon: { position: 'absolute', right: 14, bottom: 12 },
})
