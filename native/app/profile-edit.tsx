import { router } from 'expo-router'
import { useState } from 'react'
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { ApiError, updateMe } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { tr } from '../src/i18n'
import { prefs } from '../src/prefs'
import { colors, font } from '../src/theme'

/** Правка профиля: имя и телефон (покупатели смогут позвонить). Сохраняется на сервере — тот же профиль, что на сайте. */
export default function ProfileEdit() {
  const insets = useSafeAreaInsets()
  const { user, token, setUser } = useAuth()
  const [name, setName] = useState(user?.display_name ?? '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const phoneOk = !phone.trim() || /^\+?[\d\s()-]{8,20}$/.test(phone.trim())
  const save = async () => {
    if (!token || !user) return
    setError('')
    if (name.trim().length < 2) { setError(tr('Имя — хотя бы 2 буквы')); return }
    if (!phoneOk) { setError(tr('Проверьте номер: например, +381 64 123 4567')); return }
    setSaving(true)
    try {
      const u = await updateMe(token, { display_name: name.trim(), phone: phone.trim() || null })
      setUser({ ...user, ...u })
      if (phone.trim()) prefs.set('plonk_phone_hint', 'hidden')
      router.back()
    } catch (e) {
      setError(e instanceof ApiError && e.message ? e.message : tr('Не удалось сохранить. Проверьте интернет и попробуйте ещё раз.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Редактировать профиль')}</Text>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
          <Text style={styles.label}>{tr('Имя')}</Text>
          <TextInput value={name} onChangeText={setName} style={styles.input} maxLength={60} autoCapitalize="words" />
          <Text style={styles.label}>{tr('Телефон')}</Text>
          <TextInput value={phone} onChangeText={setPhone} style={styles.input} keyboardType="phone-pad" placeholder="+381 64 123 4567" placeholderTextColor={colors.muted} maxLength={20} textContentType="telephoneNumber" />
          <Text style={styles.note}>{tr('Покупатели смогут попросить звонок в переписке — номер виден только тем, кому вы его откроете.')}</Text>
          {!!error && <Text style={styles.error}>{error}</Text>}
          <Pressable style={[styles.cta, saving && { opacity: 0.6 }]} disabled={saving} onPress={save} accessibilityRole="button">
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Сохранить')}</Text>}
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 52 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, marginLeft: 4 },
  form: { paddingHorizontal: 16, paddingBottom: 40 },
  label: { fontSize: 15, fontFamily: font[800], color: colors.ink, marginTop: 18, marginBottom: 8 },
  input: { minHeight: 50, borderRadius: 13, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, fontSize: 16, fontFamily: font[500], color: colors.ink },
  note: { fontSize: 13, lineHeight: 18, fontFamily: font[500], color: colors.muted, marginTop: 8 },
  error: { fontSize: 13.5, fontFamily: font[600], color: '#B42318', marginTop: 14 },
  cta: { marginTop: 24, height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
})
