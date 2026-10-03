import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { volunteerApply, type VolunteerApp, volunteerMine } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { tr } from '../src/i18n'
import { colors, font } from '../src/theme'

const ROLES: [string, string][] = [['support', 'Отвечать на вопросы'], ['moderation', 'Проверять объявления'], ['both', 'И то и другое']]
const LANGS: [string, string][] = [['ru', 'Русский'], ['en', 'English'], ['sr', 'Srpski']]

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
    if (about.trim().length < 20) { setError(tr('Расскажите о себе хотя бы парой предложений (от 20 символов).')); return }
    if (!agree) { setError(tr('Нужно согласие на конфиденциальность.')); return }
    setBusy(true)
    try { setApp((await volunteerApply(token, { role, languages: langs, hours_per_week: hours.trim(), about: about.trim(), accept_confidentiality: true })).application) }
    catch { setError(tr('Не удалось отправить. Проверьте интернет и попробуйте ещё раз.')) } finally { setBusy(false) }
  }

  const status = app ? { new: 'Заявка на рассмотрении', accepted: 'Вы в команде помощников', rejected: 'Заявку пока не приняли' }[app.status] : ''
  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Волонтёрство')}</Text>
      </View>
      {app === undefined ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            <Text style={styles.lead}>{tr('Помогайте сообществу: отвечайте на вопросы и проверяйте объявления. Пара часов в неделю — уже много.')}</Text>
            {app ? (
              <View style={styles.status}><Text style={styles.statusTitle}>{tr(status)}</Text>{!!app.note && <Text style={styles.statusNote}>{app.note}</Text>}</View>
            ) : (
              <>
                <Text style={styles.label}>{tr('Чем хотите помогать')}</Text>
                <View style={styles.chips}>{ROLES.map(([k, l]) => <Pressable key={k} onPress={() => setRole(k)} style={[styles.chip, role === k && styles.chipOn]}><Text style={[styles.chipText, role === k && styles.chipTextOn]}>{tr(l)}</Text></Pressable>)}</View>
                <Text style={styles.label}>{tr('Языки')}</Text>
                <View style={styles.chips}>{LANGS.map(([k, l]) => { const on = langs.includes(k); return <Pressable key={k} onPress={() => setLangs(on ? langs.filter((x) => x !== k) : [...langs, k])} style={[styles.chip, on && styles.chipOn]}><Text style={[styles.chipText, on && styles.chipTextOn]}>{l}</Text></Pressable> })}</View>
                <Text style={styles.label}>{tr('Часов в неделю')}</Text>
                <TextInput value={hours} onChangeText={setHours} style={styles.input} maxLength={16} placeholder="2–3" placeholderTextColor={colors.muted} />
                <Text style={styles.label}>{tr('О себе')}</Text>
                <TextInput value={about} onChangeText={setAbout} style={[styles.input, styles.area]} multiline textAlignVertical="top" maxLength={2000} placeholder={tr('Почему хотите помогать и какой у вас опыт')} placeholderTextColor={colors.muted} />
                <View style={styles.agree}>
                  <Text style={styles.agreeText}>{tr('Обязуюсь не разглашать обращения, жалобы и переписку, которые увижу как помощник.')}</Text>
                  <Switch value={agree} onValueChange={setAgree} trackColor={{ true: colors.primary, false: '#D8DCD8' }} />
                </View>
                {!!error && <Text style={styles.error}>{error}</Text>}
                <Pressable style={[styles.cta, busy && { opacity: 0.6 }]} disabled={busy} onPress={send}>{busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Отправить заявку')}</Text>}</Pressable>
              </>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  body: { paddingHorizontal: 16, paddingBottom: 40 },
  lead: { fontSize: 15, lineHeight: 21, fontFamily: font[500], color: colors.inkSoft },
  status: { marginTop: 18, padding: 16, borderRadius: 16, backgroundColor: colors.primarySoft, gap: 6 },
  statusTitle: { fontSize: 16.5, fontFamily: font[800], color: colors.primaryDeep },
  statusNote: { fontSize: 14, lineHeight: 19, fontFamily: font[500], color: colors.ink },
  label: { fontSize: 15, fontFamily: font[800], color: colors.ink, marginTop: 18, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { height: 36, paddingHorizontal: 13, borderRadius: 11, backgroundColor: colors.sunken, justifyContent: 'center' },
  chipOn: { backgroundColor: colors.primary },
  chipText: { fontSize: 13.5, fontFamily: font[700], color: colors.inkSoft },
  chipTextOn: { color: '#fff' },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontSize: 16, fontFamily: font[500], color: colors.ink },
  area: { minHeight: 120, paddingTop: 13, paddingBottom: 13 },
  agree: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 18 },
  agreeText: { flex: 1, fontSize: 13.5, lineHeight: 19, fontFamily: font[600], color: colors.ink },
  error: { fontSize: 13.5, fontFamily: font[600], color: '#B42318', marginTop: 12 },
  cta: { marginTop: 18, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
})
