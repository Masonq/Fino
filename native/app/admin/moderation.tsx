import { Image } from 'expo-image'
import * as Haptics from 'expo-haptics'
import { useCallback, useEffect, useState } from 'react'
import { Alert, FlatList, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { type ModItem, modApprove, modQueue, modReject } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { mediaUrl } from '../../src/config'
import { formatPrice } from '../../src/format'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Skeleton from '../../src/components/Skeleton'
import { colors, font } from '../../src/theme'

const REASONS = ['Непонятный заголовок', 'Плохие или чужие фото', 'Запрещённый товар', 'Дубль объявления', 'Не тот раздел']

/** Модерация — как на сайте: крупная лента фото, название, цена, продавец, «Одобрить» / «Отклонить» с причиной. */
export default function Moderation() {
  const { token } = useAuth()
  const [items, setItems] = useState<ModItem[] | null>(null)
  const load = useCallback(() => { if (token) modQueue(token).then((r) => setItems(r.items)).catch(() => setItems([])) }, [token])
  useEffect(() => { load() }, [load])
  const drop = (id: string) => setItems((p) => (p ?? []).filter((x) => x.id !== id))
  const approve = (it: ModItem) => { if (!token) return; Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {}); drop(it.id); modApprove(token, it.id).catch(load) }
  const reject = (it: ModItem) => {
    if (!token) return
    Alert.alert(tr('Причина отказа'), undefined, [...REASONS.map((r) => ({ text: tr(r), onPress: () => { drop(it.id); modReject(token, it.id, tr(r)).catch(load) } })), { text: tr('Отмена'), style: 'cancel' as const }])
  }
  return (
    <View style={styles.page}>
      <Header title={tr('Модерация')} kicker={items ? tr('{n} в очереди', { n: items.length }) : ' '} fallback="/admin" />
      {!items ? <View style={{ padding: 16, gap: 12 }}><Skeleton style={{ height: 380, borderRadius: 24 }} /></View> : (
        <FlatList
          data={items}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 60 }}
          ListEmptyComponent={<View style={styles.calm}><Text style={styles.calmT}>{tr('Очередь пуста — всё проверено')}</Text></View>}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6, padding: 10, paddingBottom: 0 }}>
                {item.photos.map((p) => <Image key={p} source={{ uri: mediaUrl(p) || p }} style={styles.photo} contentFit="cover" />)}
              </ScrollView>
              <View style={{ padding: 14, gap: 4 }}>
                {!!item.category_name && <Text style={styles.cat}>{item.category_name}</Text>}
                <Text style={styles.title}>{item.title || tr('Без названия')}</Text>
                <Text style={styles.price}>{formatPrice(item.price ?? null, item.currency)}</Text>
                {!!item.description && <Text style={styles.desc} numberOfLines={4}>{item.description}</Text>}
                <Text style={styles.meta}>{[item.city, item.owner_name, item.owner_verified ? tr('проверен') : null, tr('{n} в ленте', { n: item.owner_active ?? 0 }), item.owner_rejected ? tr('{n} отклонено', { n: item.owner_rejected }) : null].filter(Boolean).join(' · ')}</Text>
                {item.looks_duplicate && <Text style={styles.dup}>{tr('Похоже на дубль')}</Text>}
              </View>
              <View style={styles.actions}>
                <Pressable style={[styles.btn, styles.ok]} onPress={() => approve(item)}><Text style={styles.okT}>{tr('Одобрить')}</Text></Pressable>
                <Pressable style={[styles.btn, styles.no]} onPress={() => reject(item)}><Text style={styles.noT}>{tr('Отклонить')}</Text></Pressable>
              </View>
            </View>
          )}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  card: { borderRadius: 24, backgroundColor: colors.surface, overflow: 'hidden' },
  photo: { width: 160, height: 200, borderRadius: 16, backgroundColor: colors.sunken },
  cat: { fontFamily: font[700], fontSize: 12.5, color: colors.primaryDeep },
  title: { fontFamily: font[800], fontSize: 18, letterSpacing: -0.3, color: colors.ink },
  price: { fontFamily: font[800], fontSize: 17, color: colors.ink },
  desc: { fontFamily: font[400], fontSize: 14.5, lineHeight: 20, color: colors.inkSoft, marginTop: 2 },
  meta: { fontFamily: font[600], fontSize: 12.5, color: colors.muted, marginTop: 4 },
  dup: { alignSelf: 'flex-start', marginTop: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, overflow: 'hidden', backgroundColor: colors.dangerBg, color: colors.danger, fontFamily: font[800], fontSize: 12 },
  actions: { flexDirection: 'row', gap: 8, padding: 14, paddingTop: 4 },
  btn: { flex: 1, height: 50, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  ok: { backgroundColor: colors.primary },
  okT: { fontFamily: font[800], fontSize: 16, color: '#FFFFFF' },
  no: { backgroundColor: colors.dangerBg },
  noT: { fontFamily: font[800], fontSize: 16, color: colors.danger },
  calm: { padding: 20, borderRadius: 22, backgroundColor: colors.surface, alignItems: 'center' },
  calmT: { fontFamily: font[700], fontSize: 15, color: colors.inkSoft },
})
