import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { type Category, fetchCategories } from '../src/api'
import Icon from '../src/components/Icon'
import { SITE } from '../src/config'
import { getLang, tr } from '../src/i18n'
import { colors, font } from '../src/theme'

/** «Все разделы» — как /categories сайта: сетка разделов с картинками; ещё не готовые — «Скоро». */
export default function Categories() {
  const insets = useSafeAreaInsets()
  const [cats, setCats] = useState<Category[] | null>(null)
  useEffect(() => { fetchCategories().then(setCats).catch(() => setCats([])) }, [])
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
            <Pressable key={c.id} style={[styles.item, c.ready === false && { opacity: 0.55 }]} onPress={() => router.push(`/c/${c.slug}`)} accessibilityRole="button">
              <Image source={{ uri: `${SITE}/cat/${c.slug}.png` }} style={styles.img} contentFit="contain" />
              <Text style={styles.label} numberOfLines={2}>{nameOf(c)}</Text>
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
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingHorizontal: 12, paddingBottom: 32, paddingTop: 4 },
  item: { width: '31.9%', height: 124, borderRadius: 16, paddingTop: 10, paddingHorizontal: 6, paddingBottom: 9, alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  img: { width: 70, height: 70 },
  label: { fontSize: 11.5, lineHeight: 14, fontFamily: font[700], color: colors.ink, textAlign: 'center' },
  soon: { position: 'absolute', top: 6, right: 6, fontSize: 10, fontFamily: font[800], color: colors.muted, backgroundColor: colors.sunken, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, overflow: 'hidden' },
})
