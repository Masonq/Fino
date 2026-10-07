import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { type AdminUser, adminUsers } from '../../../src/admin'
import { useAuth } from '../../../src/auth'
import { timeAgo } from '../../../src/format'
import { tr } from '../../../src/i18n'
import { Header } from '../../../src/components/Kit'
import Icon from '../../../src/components/Icon'
import Skeleton from '../../../src/components/Skeleton'
import { colors, font } from '../../../src/theme'

const ROLE: Record<string, string> = { admin: 'Владелец', moderator: 'Модератор', seller_business: 'Компания', buyer: 'Покупатель', seller: 'Продавец' }

/** Пользователи — как на сайте: поиск по имени, почте, телефону; карточки с ролью, отметками и числом объявлений. */
export default function Users() {
  const { token } = useAuth()
  const [q, setQ] = useState('')
  const [items, setItems] = useState<AdminUser[] | null>(null)
  useEffect(() => {
    if (!token) return
    const t = setTimeout(() => { adminUsers(token, q.trim()).then((r) => setItems(r.items)).catch(() => setItems([])) }, 300)
    return () => clearTimeout(t)
  }, [token, q])
  return (
    <View style={st.page}>
      <View style={st.search}>
        <Icon name="search" size={17} color={colors.muted} />
        <TextInput style={st.input} value={q} onChangeText={setQ} placeholder={tr('Имя, почта или телефон')} placeholderTextColor={colors.muted} autoCorrect={false} autoCapitalize="none" />
      </View>
      {!items ? <View style={{ padding: 16, gap: 10 }}>{[0, 1, 2, 3].map((i) => <Skeleton key={i} style={{ height: 76, borderRadius: 20 }} />)}</View> : (
        <FlatList
          ListHeaderComponent={<Header bleed={16} bleedTop={4} title={tr('Пользователи')} kicker={items ? tr('{n} человек', { n: items.length }) : ' '} fallback="/admin" />}
          data={items}
          keyExtractor={(u) => u.id}
          contentContainerStyle={{ padding: 16, paddingTop: 4, gap: 8, paddingBottom: 60 }}
          renderItem={({ item: u }) => (
            <Pressable style={st.row} onPress={() => router.push(`/admin/users/${u.id}` as never)}>
              <View style={st.ava}><Text style={st.avaT}>{(u.display_name || u.email || '?').slice(0, 1).toUpperCase()}</Text></View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Text style={st.name} numberOfLines={1}>{u.company_name || u.display_name || '—'}</Text>
                  {u.role !== 'buyer' && u.role !== 'seller' && <Text style={st.badge}>{tr(ROLE[u.role] || u.role)}</Text>}
                  {u.is_blocked && <Text style={[st.badge, st.bad]}>{tr('Заблокирован')}</Text>}
                </View>
                <Text style={st.meta} numberOfLines={1}>{u.email || u.phone || '—'}</Text>
                <Text style={st.meta}>{tr('зарег.')} {timeAgo(u.created_at)} · {u.last_seen_at ? `${tr('был')} ${timeAgo(u.last_seen_at)}` : tr('не заходил')}</Text>
              </View>
              <Text style={st.count}>{u.listings_active ?? 0}</Text>
            </Pressable>
          )}
        />
      )}
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, marginHorizontal: 16, marginBottom: 8, height: 46, borderRadius: 18, backgroundColor: colors.surface, paddingHorizontal: 14 },
  input: { flex: 1, fontFamily: font[400], fontSize: 16, color: colors.ink },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 20, backgroundColor: colors.surface },
  ava: { width: 46, height: 46, borderRadius: 23, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  avaT: { fontFamily: font[800], fontSize: 18, color: colors.ink },
  name: { flexShrink: 1, fontFamily: font[800], fontSize: 15.5, color: colors.ink },
  badge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 7, overflow: 'hidden', backgroundColor: colors.sunken, fontFamily: font[800], fontSize: 11, color: colors.inkSoft },
  bad: { backgroundColor: colors.dangerBg, color: colors.danger },
  meta: { fontFamily: font[400], fontSize: 12.5, color: colors.muted, marginTop: 1 },
  count: { fontFamily: font[800], fontSize: 17, color: colors.ink },
})
