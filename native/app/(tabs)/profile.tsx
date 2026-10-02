import { Ionicons } from '@expo/vector-icons'
import * as Linking from 'expo-linking'
import { router } from 'expo-router'
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { useAuth } from '../../src/auth'
import { SITE } from '../../src/config'
import { colors } from '../../src/theme'

/** Профиль: гость — «Войти»; вошедший — кто он, ссылка на полный профиль на сайте (пока) и «Выйти». */
export default function Profile() {
  const { user, ready, signOut } = useAuth()

  if (!ready) {
    return <SafeAreaView style={[styles.page, styles.center]}><ActivityIndicator color={colors.primary} /></SafeAreaView>
  }

  if (!user) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <View style={styles.circle}><Ionicons name="person-outline" size={30} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>Войдите в PLONK</Text>
        <Text style={styles.text}>Чтобы сохранять объявления, писать продавцам и размещать свои.</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>Войти</Text></Pressable>
      </SafeAreaView>
    )
  }

  const name = user.display_name || user.email?.split('@')[0] || 'Профиль'
  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <View style={styles.head}>
        <View style={styles.avatar}><Text style={styles.avatarLetter}>{name.slice(0, 1).toUpperCase()}</Text></View>
        <View style={{ flex: 1 }}>
          <Text style={styles.name} numberOfLines={1}>{name}</Text>
          {!!user.email && <Text style={styles.email} numberOfLines={1}>{user.email}</Text>}
        </View>
      </View>
      <View style={styles.list}>
        <Pressable style={styles.row} onPress={() => Linking.openURL(`${SITE}/profile`)}>
          <Ionicons name="open-outline" size={20} color={colors.inkSoft} />
          <Text style={styles.rowText}>Баланс и мои объявления — на сайте</Text>
          <Ionicons name="chevron-forward" size={18} color={colors.muted} />
        </Pressable>
        <Pressable style={styles.row} onPress={signOut}>
          <Ionicons name="log-out-outline" size={20} color="#B42318" />
          <Text style={[styles.rowText, { color: '#B42318' }]}>Выйти</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontWeight: '800', color: colors.ink, textAlign: 'center' },
  text: { fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 40, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  head: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 16, paddingTop: 16, paddingBottom: 18 },
  avatar: { width: 60, height: 60, borderRadius: 30, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center' },
  avatarLetter: { color: '#fff', fontSize: 24, fontWeight: '800' },
  name: { fontSize: 21, fontWeight: '800', color: colors.ink },
  email: { fontSize: 14.5, color: colors.inkSoft, marginTop: 2 },
  list: { marginHorizontal: 12, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, height: 56, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  rowText: { flex: 1, fontSize: 16, color: colors.ink, fontWeight: '600' },
})
