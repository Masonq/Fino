import * as Clipboard from 'expo-clipboard'
import { Image } from 'expo-image'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { Pressable, ScrollView, Share, StyleSheet, Text, View } from 'react-native'
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
        <Image source={{ uri: `${SITE}/invite/hero.webp` }} style={styles.hero} contentFit="contain" />
        <Text style={styles.heroTitle}>{tr('Приглашайте друзей')}</Text>
        <Text style={styles.heroText}>{tr('Друг разместит первое объявление — вам обоим по {n} RSD', { n: bonus })}</Text>

        {([['you', 'Вам', '{n} RSD — это поднятие объявления с запасом'], ['friend', 'Другу', 'Столько же — начнёт не с пустого счёта']] as const).map(([img, label, text]) => (
          <View key={img} style={styles.card}>
            <Image source={{ uri: `${SITE}/invite/${img}.webp` }} style={styles.cardImg} contentFit="contain" />
            <View style={{ flex: 1 }}>
              <Text style={styles.cardLabel}>{tr(label)}</Text>
              <Text style={styles.cardText}>{tr(text, { n: bonus })}</Text>
            </View>
          </View>
        ))}

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

        <Pressable style={styles.link} onPress={async () => { await Clipboard.setStringAsync(link).catch(() => {}); success(); setCopied(true); setTimeout(() => setCopied(false), 1600) }}>
          <Text style={styles.linkText} numberOfLines={1}>{link.replace(/^https?:\/\//, '')}</Text>
          <Text style={styles.copy}>{tr(copied ? 'Ссылка скопирована' : 'Копировать')}</Text>
        </Pressable>
        <Pressable style={styles.cta} onPress={() => Share.share({ message: `${tr('Заходи на PLONK — барахолка Сербии')}\n${link}` }).catch(() => {})}>
          <Text style={styles.ctaText}>{tr('Поделиться ссылкой')}</Text>
        </Pressable>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  body: { paddingHorizontal: 16 },
  hero: { width: '70%', aspectRatio: 1.45, alignSelf: 'center' },
  heroTitle: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center', marginTop: 6 },
  heroText: { fontSize: 14, lineHeight: 20, fontFamily: font[600], color: colors.muted, textAlign: 'center', marginTop: 6, marginBottom: 14, paddingHorizontal: 12 },
  card: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, marginBottom: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, shadowColor: '#14201A', shadowOpacity: 0.06, shadowRadius: 10, shadowOffset: { width: 0, height: 2 } },
  cardImg: { width: 52, height: 52 },
  cardLabel: { fontSize: 12.5, fontFamily: font[700], color: colors.muted },
  cardText: { fontSize: 14.5, lineHeight: 19, fontFamily: font[800], color: colors.ink, marginTop: 1 },
  h2: { fontSize: 16, fontFamily: font[800], color: colors.ink, marginTop: 14, marginBottom: 10 },
  step: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 },
  stepNum: { width: 24, height: 24, borderRadius: 12, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  stepNumText: { fontSize: 12.5, fontFamily: font[800], color: colors.primaryDeep },
  stepText: { flex: 1, fontSize: 14, lineHeight: 19, fontFamily: font[700], color: colors.ink },
  people: { marginTop: 6, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden' },
  person: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  personName: { flex: 1, fontSize: 14.5, fontFamily: font[700], color: colors.ink },
  personState: { fontSize: 12.5, fontFamily: font[700], color: colors.muted },
  link: { flexDirection: 'row', alignItems: 'center', gap: 10, height: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, marginTop: 18 },
  linkText: { flex: 1, fontSize: 14.5, fontFamily: font[600], color: colors.ink },
  copy: { fontSize: 14, fontFamily: font[800], color: colors.primaryDeep },
  cta: { marginTop: 10, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
})
