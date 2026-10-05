import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

import { type FeedItem, freshListings } from '../api'
import { mediaUrl } from '../config'
import { formatPrice } from '../format'
import { plural, tr } from '../i18n'
import { sfDiscover } from '../social'
import { colors, font } from '../theme'

type Store = { slug: string; name: string; count: number; city?: string | null; previews: string[] }

/** PLONK 2.0: подборки на главной — «Новое сегодня» и «Витрины продавцов», как на сайте. */
export default function HomeSections({ city }: { city?: string | null }) {
  const [fresh, setFresh] = useState<(FeedItem & { fresh?: boolean })[]>([])
  const [stores, setStores] = useState<Store[]>([])
  useEffect(() => {
    let alive = true
    freshListings(city).then((r) => alive && setFresh(r.items)).catch(() => {})
    sfDiscover(city).then((r) => alive && setStores(r.items)).catch(() => {})
    return () => { alive = false }
  }, [city])
  return (
    <View>
      {fresh.length > 2 && (
        <View style={s.section}>
          <Text style={s.title}>{tr('Новое сегодня')}</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.row}>
            {fresh.slice(0, 12).map((l) => (
              <Pressable key={l.id} style={s.card} onPress={() => router.push(`/listing/${l.id}` as never)}>
                <View style={s.photo}>
                  {!!l.cover_photo && <Image source={{ uri: mediaUrl(l.cover_photo) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}
                  {l.fresh && <View style={s.new}><Text style={s.newText}>{tr('Новое')}</Text></View>}
                </View>
                <Text style={s.price} numberOfLines={1}>{formatPrice(l.price, l.currency, l.is_free)}</Text>
                <Text style={s.name} numberOfLines={2}>{l.title}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}
      {stores.length > 0 && (
        <View style={s.section}>
          <View style={s.head}>
            <Text style={s.title}>{tr('Витрины продавцов')}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.row}>
            {stores.map((st) => (
              <Pressable key={st.slug} style={s.store} onPress={() => router.push(`/s/${st.slug}` as never)}>
                <View style={s.grid}>
                  <Image source={{ uri: mediaUrl(st.previews[0]) ?? undefined }} style={s.big} contentFit="cover" />
                  <View style={{ flex: 1, gap: 4 }}>
                    {st.previews.slice(1, 3).map((p) => <Image key={p} source={{ uri: mediaUrl(p) ?? undefined }} style={{ flex: 1, borderRadius: 4, backgroundColor: colors.photo }} contentFit="cover" />)}
                  </View>
                </View>
                <Text style={s.storeName} numberOfLines={1}>{st.name}</Text>
                <Text style={s.storeSub} numberOfLines={1}>{st.count} {plural(st.count, { ru: ['товар', 'товара', 'товаров'], en: ['item', 'items'], sr: ['stvar', 'stvari', 'stvari'] })}{st.city ? ` · ${st.city}` : ''}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}
    </View>
  )
}

const s = StyleSheet.create({
  section: { marginTop: 16, marginBottom: 4 },
  head: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' },
  title: { fontFamily: font[800], fontSize: 21, letterSpacing: -0.5, color: colors.ink, paddingHorizontal: 12, marginBottom: 10 },
  row: { gap: 12, paddingHorizontal: 12, paddingBottom: 6 },
  card: { width: 140 },
  photo: { width: 140, height: 175, borderRadius: 18, overflow: 'hidden', backgroundColor: colors.photo },
  new: { position: 'absolute', left: 8, bottom: 8, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 9, backgroundColor: colors.lime },
  newText: { fontFamily: font[700], fontSize: 11, color: colors.ink },
  price: { marginTop: 8, fontFamily: font[800], fontSize: 16, color: colors.ink, letterSpacing: -0.3 },
  name: { marginTop: 1, fontFamily: font[500], fontSize: 13, lineHeight: 17, color: colors.inkSoft },
  store: { width: 220, padding: 10, borderRadius: 22, backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 2 },
  grid: { flexDirection: 'row', gap: 4, height: 150, borderRadius: 14, overflow: 'hidden' },
  big: { flex: 2, borderRadius: 4, backgroundColor: colors.photo },
  storeName: { marginTop: 9, fontFamily: font[800], fontSize: 15.5, color: colors.ink, letterSpacing: -0.3 },
  storeSub: { marginTop: 1, fontFamily: font[500], fontSize: 12.5, color: colors.muted },
})
