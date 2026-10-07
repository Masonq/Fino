import { TINTS } from '../tints'
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
import { HOME_TILE, TILE, artLayout, catPath, tileFor } from '../artFit'
import { TileLabelArt } from './TileArt'

// плитки главной — как на сайте (HOME_TILE): 112×80, широкие — 156 и 200; картинка в углу, чуть за краем
const W = HOME_TILE.w
const H = HOME_TILE.h
// плитка и колонка надписи — вместе с картинкой (как на сайте): надпись может уйти в колонку поуже ради картинки
const widthFor = (name: string, slug = '') => artLayout(name, tileFor(name, HOME_TILE), slug).fit

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
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} style={{ width: W, height: H, borderRadius: 16 }} />)}
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
          <Text style={[styles.label, { color: colors.onInverse }]}>{tr('Все')}</Text>
          <View style={styles.allIcon}><Icon name="grid" size={30} color={colors.onInverse} /></View>
        </Pressable>
      )
    }
    const on = value === c.slug
    return (
      <Pressable key={c.slug} style={[styles.tile, { width: widthFor(nameOf(c), c.slug).tile, backgroundColor: TINT[c.slug] ?? colors.tile }, on && styles.tileOn, c.ready === false && styles.soon]} onPress={() => { select(); router.push(`/c/${c.slug}`) }}
        accessibilityRole="button" accessibilityState={{ selected: on }}>
        {/* Одно длинное слово («Недвижимость») не переносим посреди слова — слегка ужимаем */}
        <TileLabelArt uri={`${SITE}${catPath(c.slug)}`} name={nameOf(c)} fit={widthFor(nameOf(c), c.slug)} style={[styles.label, on && styles.labelOn]} />
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

/** Мягкие цвета плиток разделов — как на сайте (картинки вырезаны, фон любой). «Все» — тёмная плитка-якорь. */
// цвета разделов — общие (src/tints.ts): в тёмной теме приглушённые; свой список здесь не переключался и в тёмной
// теме плитки оставались светлыми с белыми, нечитаемыми подписями
const TINT: Record<string, string> = TINTS

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: 12, gap: 8 },
  scroll: { paddingHorizontal: 12 },
  wrapInner: { gap: 8 },
  row: { flexDirection: 'row', gap: 8 },
  // Размеры — как .cat-tile-2row на сайте: 118×86, отступы 9/8/6/11, подпись 12 полужирная, картинка 58×58 в углу
  tile: { width: W, height: H, borderRadius: 18, backgroundColor: colors.tile, borderWidth: 2, borderColor: 'transparent', padding: TILE.pad, overflow: 'hidden' },
  allTile: { backgroundColor: colors.inverse },
  tileOn: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  soon: { opacity: 0.55 },
  label: { fontSize: 13.5, lineHeight: 17, fontFamily: font[700], color: colors.onTile, zIndex: 2 },
  labelOn: { color: colors.primaryDeep },
  allIcon: { position: 'absolute', right: 10, bottom: 8 },
})
