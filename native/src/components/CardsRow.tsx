import { ScrollView, StyleSheet, Text, View } from 'react-native'

import type { FeedItem } from '../api'
import { colors, font } from '../theme'
import ListingCard from './ListingCard'

/** Заголовок и горизонтальная лента карточек — для «Похожие» и «Ещё у продавца». */
export default function CardsRow({ title, items, exclude }: { title: string; items: FeedItem[] | null; exclude?: string }) {
  const list = (items ?? []).filter((i) => i.id !== exclude)
  if (list.length === 0) return null
  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {list.slice(0, 12).map((i) => <ListingCard key={i.id} item={i} width={164} />)}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { marginTop: 26, gap: 12 },
  title: { fontSize: 19, fontFamily: font[800], color: colors.ink, paddingHorizontal: 16 },
  row: { gap: 10, paddingHorizontal: 16 },
})
