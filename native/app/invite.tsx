import * as Clipboard from 'expo-clipboard'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ScrollView, Share, StyleSheet, Text, View } from 'react-native'
import Pressable from '../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { myReferrals } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { SITE } from '../src/config'
import { success } from '../src/haptics'
import { tr } from '../src/i18n'
import { colors, font } from '../src/theme'

type Ref = { invited: number; posted: number; rewarded: number; earned: number; bonus: number; people?: { name?: string | null; state?: string }[] }

/**
 * «Пригласить друга» — как /profile/invite сайта: иллюстрация, «Приглашайте друзей», карточки «Вам» и «Другу»
 * с картинками сайта, «Как это работает» в три шага, ссылка (/?ref=первые 8 символов id) — копировать
 * и поделиться; приглашённые — с этапом.
 */
export default function Invite() {
  const insets = useSafeAreaInsets()
  const { user, token } = useAuth()
  const [ref, setRef] = useState<Ref | null>(null)
  const [copied, setCopied] = useState(false)
  useFocusEffect(useCallback(() => { if (token) myReferrals(token).then((r) => setRef(r as Ref)).catch(() => {}) }, [token]))
  const link = user ? `${SITE}/?ref=${user.id.slice(0, 8)}` : SITE
  const bonus = ref?.bonus ?? 200
  const STATE: Record<string, string> = { joined: 'Зарегистрировался', posted: 'Разместил объявление', rewarded: 'Бонус начислен' }

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Пригласить друга')}</Text>
      </View>
      <ScrollView contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 24 }]}>
        {/* PLONK 2.0, как на сайте: большой мятно-лаймовый блок — картинка, «+N RSD вам / другу», ссылка и «Поделиться» прямо в нём */}
        <View style={styles.heroCard}>
          <Image source={{ uri: `${SITE}/invite/hero.webp` }} style={styles.hero} contentFit="contain" />
          <View style={styles.badges}>
            <View style={styles.badge}><Text style={styles.badgeT}>+{bonus} RSD</Text><Text style={styles.badgeS}>{tr('Вам')}</Text></View>
            <View style={[styles.badge, { backgroundColor: '#FFE3D6' }]}><Text style={[styles.badgeT, { color: '#9A3412' }]}>+{bonus} RSD</Text><Text style={[styles.badgeS, { color: '#9A3412' }]}>{tr('Другу')}</Text></View>
          </View>
          <Text style={styles.heroTitle}>{tr('Приглашайте друзей')}</Text>
          <Text style={styles.heroText}>{tr('Друг разместит первое объявление — вам обоим по {n} RSD', { n: bonus })}</Text>
          <View style={styles.share}>
            <Pressable style={{ flex: 1 }} onPress={async () => { await Clipboard.setStringAsync(link).catch(() => {}); success(); setCopied(true); setTimeout(() => setCopied(false), 1600) }}>
              <Text style={styles.linkText} numberOfLines={1}>{copied ? tr('Ссылка скопирована') : link.replace(/^https?:\/\//, '')}</Text>
            </Pressable>
            <Pressable style={styles.shareBtn} onPress={() => Share.share({ message: `${tr('Заходи на PLONK — барахолка Сербии')}\n${link}` }).catch(() => {})}>
              <Text style={styles.ctaText}>{tr('Поделиться')}</Text>
            </Pressable>
          </View>
        </View>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          {([['you', 'Вам', '{n} RSD — это поднятие объявления с запасом', '#E2F1E6'], ['friend', 'Другу', 'Столько же — начнёт не с пустого счёта', '#FFE8DD']] as const).map(([img, label, text, bg]) => (
            <View key={img} style={[styles.card, { backgroundColor: bg }]}>
              <Image source={{ uri: `${SITE}/invite/${img}.webp` }} style={styles.cardImg} contentFit="contain" />
              <Text style={styles.cardLabel}>{tr(label)}</Text>
              <Text style={styles.cardText}>{tr(text, { n: bonus })}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.h2}>{tr('Как это работает')}</Text>
        {['Отправьте другу свою ссылку', 'Он заходит по ней и размещает объявление', 'Объявление проходит проверку — деньги на балансе у обоих'].map((s, i) => (
          <View key={s} style={styles.step}>
            <View style={styles.stepNum}><Text style={styles.stepNumText}>{i + 1}</Text></View>
            <Text style={styles.stepText}>{tr(s)}</Text>
          </View>
        ))}

        {!!ref?.people?.length && (
          <View style={styles.people}>
            {ref.people.map((p, i) => (
              <View key={i} style={[styles.person, i === ref.people!.length - 1 && { borderBottomWidth: 0 }]}>
                <Text style={styles.personName} numberOfLines={1}>{p.name || tr('Собеседник')}</Text>
                <Text style={[styles.personState, p.state === 'rewarded' && { color: colors.primaryDeep }]}>{tr(STATE[p.state ?? 'joined'] ?? STATE.joined)}</Text>
              </View>
            ))}
          </View>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  heroCard: { borderRadius: 28, padding: 16, backgroundColor: '#E9F5EC', gap: 8, alignItems: 'center', marginBottom: 10 },
  badges: { flexDirection: 'row', gap: 8 },
  badge: { flexDirection: 'row', alignItems: 'baseline', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, backgroundColor: colors.inverse },
  badgeT: { fontFamily: font[800], fontSize: 18, color: colors.onInverse, letterSpacing: -0.4 },
  badgeS: { fontFamily: font[800], fontSize: 12, color: colors.onInverse, opacity: 0.85 },
  share: { flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'stretch', padding: 6, borderRadius: 18, backgroundColor: colors.surface, marginTop: 4 },
  shareBtn: { height: 44, paddingHorizontal: 18, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, minHeight: 56 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  body: { paddingHorizontal: 16 },
  hero: { width: '70%', aspectRatio: 1.45, alignSelf: 'center' },
  heroTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center', marginTop: 6 },
  heroText: { fontSize: 14, lineHeight: 20, fontFamily: font[600], color: colors.muted, textAlign: 'center', marginTop: 6, marginBottom: 14, paddingHorizontal: 12 },
  card: { flex: 1, flexDirection: 'column', alignItems: 'flex-start', borderRadius: 22, padding: 14, gap: 6 },   // плитка «вам / другу» — колонкой, две рядом
  cardImg: { width: 52, height: 52 },
  cardLabel: { fontSize: 12, fontFamily: font[800], color: '#434B46', textTransform: 'uppercase', letterSpacing: 0.5 },
  cardText: { fontSize: 14, lineHeight: 19, fontFamily: font[700], color: '#0F1512' },
  h2: { fontSize: 16, fontFamily: font[800], color: colors.ink, marginTop: 14, marginBottom: 10 },
  step: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 },
  stepNum: { width: 24, height: 24, borderRadius: 12, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  stepNumText: { fontSize: 12.5, fontFamily: font[800], color: colors.primaryDeep },
  stepText: { flex: 1, fontSize: 14, lineHeight: 19, fontFamily: font[700], color: colors.ink },
  people: { marginTop: 6, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 0, overflow: 'hidden' },
  person: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  personName: { flex: 1, fontSize: 14.5, fontFamily: font[700], color: colors.ink },
  personState: { fontSize: 12.5, fontFamily: font[700], color: colors.muted },
  link: { flexDirection: 'row', alignItems: 'center', gap: 10, height: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 0, paddingHorizontal: 14, marginTop: 18 },
  linkText: { paddingLeft: 10, fontFamily: font[700], fontSize: 13.5, color: colors.inkSoft },
  copy: { fontSize: 14, fontFamily: font[800], color: colors.primaryDeep },
  cta: { marginTop: 10, height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
})
