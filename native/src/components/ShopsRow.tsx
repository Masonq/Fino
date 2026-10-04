import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

import { mediaUrl } from '../config'
import { tr } from '../i18n'
import { money, type Shop, shopsFeed } from '../social'
import { colors, font } from '../theme'
import Icon from './Icon'

let cache: Shop[] | null = null

/** Шопсы на главной вместо историй: превью роликов 9:16, первой — «Снять шопс». */
export default function ShopsRow() {
  const [items, setItems] = useState<Shop[] | null>(cache)
  useEffect(() => { if (!cache) shopsFeed({ limit: 12 }).then((r) => { cache = r.items; setItems(r.items) }).catch(() => setItems([])) }, [])
  if (items === null) return <View style={s.row}>{[0, 1, 2, 3, 4].map((i) => <View key={i} style={[s.tile, { backgroundColor: colors.sunken }]} />)}</View>
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.row}>
      <Pressable style={[s.tile, s.new]} onPress={() => router.push('/shops/new' as never)} accessibilityRole="button">
        <View style={s.plus}><Icon name="plus" size={22} color="#fff" /></View>
        <Text style={s.newText}>{items.length ? tr('Снять шопс') : tr('Снимите первый шопс')}</Text>
      </Pressable>
      {items.map((sh) => (
        <Pressable key={sh.id} style={s.tile} onPress={() => router.push(`/shops?start=${sh.id}` as never)} accessibilityLabel={sh.caption || sh.author?.name}>
          {!!sh.poster_url && <Image source={{ uri: mediaUrl(sh.poster_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}
          <View style={s.shade} />
          {sh.items[0]?.price != null && <View style={s.price}><Text style={s.priceText}>{money(sh.items[0].price, sh.items[0].currency)}</Text></View>}
          <Text style={s.author} numberOfLines={2}>{sh.author?.name}</Text>
        </Pressable>
      ))}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  row: { flexDirection: 'row', gap: 8, paddingHorizontal: 12, paddingTop: 4, paddingBottom: 6 },
  tile: { width: 92, height: 140, borderRadius: 14, overflow: 'hidden', backgroundColor: '#1c2620' },
  shade: { position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.22)' },
  new: { backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', gap: 8, paddingHorizontal: 8 },
  plus: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  newText: { fontFamily: font[700], fontSize: 12, lineHeight: 15, color: colors.primaryDeep, textAlign: 'center' },
  price: { position: 'absolute', left: 8, top: 8, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, backgroundColor: 'rgba(255,255,255,0.92)' },
  priceText: { fontFamily: font[800], fontSize: 11, color: colors.ink },
  author: { position: 'absolute', left: 8, right: 8, bottom: 8, fontFamily: font[700], fontSize: 12, lineHeight: 15, color: '#fff' },
})
