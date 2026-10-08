import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { authed, volunteerApply, type VolunteerApp, volunteerMine } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { tr } from '../src/i18n'
import { colors, font } from '../src/theme'

const ROLES: [string, string][] = [['support', 'Поддержка'], ['moderation', 'Модерация'], ['both', 'И то и другое']]
const LANGS: [string, string][] = [['ru', 'Русский'], ['sr', 'Сербский'], ['en', 'Английский']]

// Тексты — как на странице /volunteer сайта
const LEAD = "PLONK делают свои же люди. Как в чатах в Telegram: в поддержке отвечают не сотрудники, а те, кому не всё равно. Если у вас есть час-другой в неделю — присоединяйтесь."
const POINTS: [string, string][] = [
  ["Отвечать в поддержке", "Помогать людям, у которых не грузится фото, не приходит код или не понятно, как продлить объявление."],
  ["Проверять объявления", "Пропускать честные, останавливать подозрительные — до того, как кто-то переведёт деньги."],
  ["Что взамен", "Значок команды в профиле и наша благодарность. Денег не платим — говорим честно."],
]
const PENDING = "Заявка отправлена — ответим в течение пары дней, придёт уведомление."
const ABOUT_PH = "Кто вы, чем занимаетесь, почему хотите помогать. Пары предложений достаточно."
const CONSENT = "Я обязуюсь сохранять конфиденциальность всего, что увижу при модерации (обращения, объявления, переписку), и понимаю, что участие безвозмездно и не является работой."

/** Волонтёрство — как на сайте: роль, языки, часы в неделю, о себе, согласие на конфиденциальность; статус заявки. */
export default function Volunteer() {
  const insets = useSafeAreaInsets()
  const { token } = useAuth()
  const [app, setApp] = useState<VolunteerApp | null | undefined>(undefined)
  const [role, setRole] = useState('support')
  const [langs, setLangs] = useState<string[]>(['ru'])
  const [hours, setHours] = useState('')
  const [about, setAbout] = useState('')
  const [agree, setAgree] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => { if (token) setApp((await volunteerMine(token).catch(() => ({ application: null }))).application) }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const send = async () => {
    if (!token) return
    setError('')
    if (about.trim().length < 20) { setError(tr('Расскажите о себе чуть подробнее — хотя бы пару предложений.')); return }
    if (!agree) { setError(tr('Подтвердите, что сохраните конфиденциальность: без этого заявку не принять.')); return }
    setBusy(true)
    try { setApp((await volunteerApply(token, { role, languages: langs, hours_per_week: hours.trim(), about: about.trim(), accept_confidentiality: true })).application) }
    catch { setError(tr('Не удалось отправить. Проверьте интернет и попробуйте ещё раз.')) } finally { setBusy(false) }
  }

  const status = app ? { new: PENDING, accepted: 'Вы уже в команде. Спасибо!', rejected: 'Заявку пока не приняли' }[app.status] : ''
  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Волонтёрство')}</Text>
      </View>
      {app === undefined ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            {/* PLONK 2.0: вступление карточкой с меткой и три пункта цветными плитками со значками (как на сайте) */}
            <View style={styles.hero}>
              <View style={styles.heroTag}><Text style={styles.heroTagT}>{tr('Команда PLONK')}</Text></View>
              <Text style={styles.heroText}>{tr(LEAD)}</Text>
            </View>
            {POINTS.map(([title, text], n) => (
              <View key={title} style={[styles.tile, { backgroundColor: ['#E3ECFA', '#E2F1E6', '#FAE5EE'][n % 3] }]}>
                <View style={styles.tileIcon}><Icon name={(['chat', 'shield', 'heart'] as const)[n % 3]} size={20} color="#0F1512" /></View>
                <View style={{ flex: 1 }}><Text style={styles.tileT}>{tr(title)}</Text><Text style={styles.tileS}>{tr(text)}</Text></View>
              </View>
            ))}
            {app ? (
              <>
              <View style={styles.status}><Text style={styles.statusTitle}>{tr(status)}</Text>{!!app.note && <Text style={styles.statusNote}>{app.note}</Text>}</View>
            {/* заявка подана до появления галочки — без подтверждения её не принять (как на сайте) */}
            {app.status === 'new' && app.confidentiality_accepted === false && (
              <View style={[styles.status, { gap: 10 }]}>
                <Text style={styles.statusNote}>{tr('Я обязуюсь сохранять конфиденциальность всего, что увижу при модерации (обращения, объявления, переписку), и понимаю, что участие безвозмездно и не является работой.')}</Text>
                <Pressable style={styles.cta} onPress={() => { if (token) authed<{ application: VolunteerApp }>('/volunteer/consent', token, 'POST').then((r) => setApp(r.application)).catch(() => {}) }}><Text style={styles.ctaText}>{tr('Подтвердить')}</Text></Pressable>
              </View>
            )}
            </>
            ) : (
              <>
                <Text style={styles.label}>{tr('Чем хотите помогать')}</Text>
                <View style={styles.chips}>{ROLES.map(([k, l]) => <Pressable key={k} onPress={() => setRole(k)} style={[styles.chip, role === k && styles.chipOn]}><Text style={[styles.chipText, role === k && styles.chipTextOn]}>{tr(l)}</Text></Pressable>)}</View>
                <Text style={styles.label}>{tr('Языки')}</Text>
                <View style={styles.chips}>{LANGS.map(([k, l]) => { const on = langs.includes(k); return <Pressable key={k} onPress={() => setLangs(on ? langs.filter((x) => x !== k) : [...langs, k])} style={[styles.chip, on && styles.chipOn]}><Text style={[styles.chipText, on && styles.chipTextOn]}>{tr(l)}</Text></Pressable> })}</View>
                <Text style={styles.label}>{tr('Сколько времени в неделю')}</Text>
                <TextInput value={hours} onChangeText={setHours} style={styles.input} maxLength={16} placeholder="2–3" placeholderTextColor={colors.muted} />
                <Text style={styles.label}>{tr('О себе')}</Text>
                <TextInput value={about} onChangeText={setAbout} style={[styles.input, styles.area]} multiline textAlignVertical="top" maxLength={2000} placeholder={tr(ABOUT_PH)} placeholderTextColor={colors.muted} />
                <View style={styles.agree}>
                  <Text style={styles.agreeText}>{tr(CONSENT)}</Text>
                  <Switch value={agree} onValueChange={setAgree} trackColor={{ true: colors.primary, false: colors.sunken }} />
                </View>
                {!!error && <Text style={styles.error}>{error}</Text>}
                <Pressable style={[styles.cta, busy && { opacity: 0.6 }]} disabled={busy} onPress={send}>{busy ? <ActivityIndicator color={colors.onInverse} /> : <Text style={styles.ctaText}>{tr('Отправить заявку')}</Text>}</Pressable>
              </>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  hero: { padding: 16, borderRadius: 24, backgroundColor: colors.surface, marginBottom: 10, gap: 10 },
  heroTag: { alignSelf: 'flex-start', height: 26, paddingHorizontal: 10, borderRadius: 13, backgroundColor: colors.inverse, justifyContent: 'center' },
  heroTagT: { fontFamily: font[800], fontSize: 12, color: colors.onInverse },
  heroText: { fontFamily: font[500], fontSize: 15.5, lineHeight: 22, color: colors.ink },
  tile: { flexDirection: 'row', gap: 12, padding: 14, borderRadius: 22, marginBottom: 8, alignItems: 'flex-start' },
  tileIcon: { width: 42, height: 42, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.75)', alignItems: 'center', justifyContent: 'center' },
  tileT: { fontFamily: font[800], fontSize: 15.5, color: '#0F1512' },
  tileS: { fontFamily: font[400], fontSize: 13.5, lineHeight: 19, color: '#434B46', marginTop: 2 },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, minHeight: 56 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, shadowColor: '#0F1512', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, letterSpacing: -0.8, color: colors.ink },
  body: { paddingHorizontal: 16, paddingBottom: 40 },
  lead: { fontSize: 14.5, lineHeight: 21, fontFamily: font[500], color: colors.inkSoft, marginBottom: 6 },
  point: { flexDirection: 'row', gap: 10, marginTop: 10 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.accent, marginTop: 6 },
  pointTitle: { fontSize: 14, fontFamily: font[800], color: colors.ink },
  pointText: { fontSize: 13, lineHeight: 18, fontFamily: font[500], color: colors.inkSoft, marginTop: 1 },
  status: { marginTop: 18, padding: 14, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, gap: 6 },
  statusTitle: { fontSize: 14, lineHeight: 19, fontFamily: font[800], color: colors.ink },
  statusNote: { fontSize: 14, lineHeight: 19, fontFamily: font[500], color: colors.ink },
  label: { fontSize: 15, fontFamily: font[800], color: colors.ink, marginTop: 18, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { height: 36, paddingHorizontal: 13, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  chipOn: { backgroundColor: colors.inverse },
  chipText: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  chipTextOn: { color: colors.onInverse },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontSize: 16, fontFamily: font[500], color: colors.ink },
  area: { minHeight: 120, paddingTop: 13, paddingBottom: 13 },
  agree: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 18 },
  agreeText: { flex: 1, fontSize: 13.5, lineHeight: 19, fontFamily: font[600], color: colors.ink },
  error: { fontSize: 13.5, fontFamily: font[600], color: colors.danger, marginTop: 12 },
  cta: { marginTop: 18, height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
})
