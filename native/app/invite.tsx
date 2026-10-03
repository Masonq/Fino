import * as Clipboard from 'expo-clipboard'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { Pressable, ScrollView, Share, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { myReferrals } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { SITE } from '../src/config'
import { tr } from '../src/i18n'
import { colors, font } from '../src/theme'

/** «Пригласите друга» — как на сайте: личная ссылка (/?ref=первые 8 символов id), бонус за первое объявление друга, счётчики. */
export default function Invite() {
  const insets = useSafeAreaInsets()
  const { user, token } = useAuth()
  const [stats, setStats] = useState<{ invited: number; posted: number; rewarded: number; earned: number; bonus: number } | null>(null)
  const [copied, setCopied] = useState(false)
  useFocusEffect(useCallback(() => { if (token) myReferrals(token).then(setStats).catch(() => {}) }, [token]))
  const link = user ? `${SITE}/?ref=${user.id.slice(0, 8)}` : SITE
  const bonus = stats?.bonus ?? 200

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Пригласите друга')}</Text>
      </View>
      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.hero}>
          <View style={styles.heroIcon}><Icon name="gift" size={30} color={colors.accent} /></View>
          <Text style={styles.heroTitle}>{tr('+{n} RSD за друга', { n: bonus })}</Text>
          <Text style={styles.heroText}>{tr('Друг регистрируется по вашей ссылке и размещает первое объявление — вам приходит бонус на продвижение.')}</Text>
        </View>
        <Text style={styles.label}>{tr('Ваша ссылка')}</Text>
        <Pressable style={styles.link} onPress={async () => { await Clipboard.setStringAsync(link).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1600) }}>
          <Text style={styles.linkText} numberOfLines={1}>{link}</Text>
          <Text style={styles.copy}>{tr(copied ? 'Скопировано' : 'Копировать')}</Text>
        </Pressable>
        <Pressable style={styles.cta} onPress={() => Share.share({ message: tr('Объявления в Сербии — на русском, английском и сербском: {link}', { link }) }).catch(() => {})}>
          <Text style={styles.ctaText}>{tr('Поделиться ссылкой')}</Text>
        </Pressable>
        {stats && (
          <View style={styles.stats}>
            {([['invited', 'пришли по ссылке'], ['posted', 'разместили объявление'], ['earned', 'RSD получено']] as const).map(([k, label]) => (
              <View key={k} style={styles.stat}><Text style={styles.statValue}>{stats[k]}</Text><Text style={styles.statLabel}>{tr(label)}</Text></View>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  body: { paddingHorizontal: 16, paddingBottom: 40, paddingTop: 6 },
  hero: { alignItems: 'center', padding: 20, borderRadius: 18, backgroundColor: colors.accentSoft, gap: 8 },
  heroIcon: { width: 60, height: 60, borderRadius: 30, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  heroTitle: { fontSize: 22, fontFamily: font[800], color: '#A2401D' },
  heroText: { fontSize: 14.5, lineHeight: 20, fontFamily: font[500], color: '#7A3A20', textAlign: 'center' },
  label: { fontSize: 15, fontFamily: font[800], color: colors.ink, marginTop: 20, marginBottom: 8 },
  link: { flexDirection: 'row', alignItems: 'center', gap: 10, height: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14 },
  linkText: { flex: 1, fontSize: 15, fontFamily: font[600], color: colors.ink },
  copy: { fontSize: 14, fontFamily: font[800], color: colors.primaryDeep },
  cta: { marginTop: 14, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  stats: { flexDirection: 'row', gap: 8, marginTop: 20 },
  stat: { flex: 1, padding: 12, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  statValue: { fontSize: 20, fontFamily: font[800], color: colors.ink },
  statLabel: { fontSize: 11.5, lineHeight: 15, fontFamily: font[600], color: colors.muted, marginTop: 2 },
})
