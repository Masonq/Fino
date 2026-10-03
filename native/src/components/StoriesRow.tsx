import { Ionicons } from '@expo/vector-icons'
import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

import { type FeedItem, freshListings } from '../api'
import { mediaUrl } from '../config'
import { formatPrice } from '../format'
import { colors } from '../theme'
import Skeleton from './Skeleton'

const D = 64

/** Истории, как на сайте: «Продать» и свежие объявления кружками с оранжевым кольцом и ценой под ними. */
export default function StoriesRow({ city }: { city: string | null }) {
  const [items, setItems] = useState<FeedItem[] | null>(null)
  useEffect(() => { setItems(null); freshListings(city).then((r) => setItems(r.items)).catch(() => setItems([])) }, [city])

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      <Pressable style={styles.item} onPress={() => router.navigate('/post')} accessibilityRole="button" accessibilityLabel="Продать">
        <View style={styles.sell}><Ionicons name="add" size={30} color="#fff" /></View>
        <Text style={styles.label}>Продать</Text>
      </Pressable>
      {items === null
        ? Array.from({ length: 5 }).map((_, i) => (
          <View key={i} style={styles.item}><Skeleton style={{ width: D + 8, height: D + 8, borderRadius: (D + 8) / 2 }} /><Skeleton style={{ width: 44, height: 11, marginTop: 6 }} /></View>
        ))
        : items.map((i) => {
          const photo = mediaUrl(i.cover_photo)
          return (
            <Pressable key={i.id} style={styles.item} onPress={() => router.push(`/listing/${i.id}`)} accessibilityRole="button" accessibilityLabel={i.title}>
              <View style={styles.ring}>
                <View style={styles.inner}>{photo ? <Image source={{ uri: photo }} style={styles.img} contentFit="cover" transition={150} /> : null}</View>
              </View>
              <Text style={styles.label} numberOfLines={1}>{formatPrice(i.price, i.currency, i.is_free)}</Text>
            </Pressable>
          )
        })}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  row: { paddingHorizontal: 12, gap: 12 },
  item: { width: D + 10, alignItems: 'center' },
  ring: { width: D + 8, height: D + 8, borderRadius: (D + 8) / 2, borderWidth: 2.5, borderColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  inner: { width: D, height: D, borderRadius: D / 2, overflow: 'hidden', backgroundColor: colors.photo },
  img: { width: D, height: D },
  // «Продать» — того же размера, что кольца историй (72), чтобы ряд был ровным
  sell: { width: D + 8, height: D + 8, borderRadius: (D + 8) / 2, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  label: { fontSize: 12.5, fontWeight: '800', color: colors.ink, marginTop: 5, maxWidth: D + 10 },
})
