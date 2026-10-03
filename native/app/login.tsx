import { tr } from '../src/i18n'
import { Ionicons } from '@expo/vector-icons'
import { router } from 'expo-router'
import { useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { ApiError, requestCode, verifyCode } from '../src/api'
import { useAuth } from '../src/auth'
import { colors } from '../src/theme'

const LEN = 6
const RESEND = 60

/**
 * Вход по коду из почты — как на сайте. Почта → код из письма (шесть цифр; вводится в одно поле, рисуется
 * клетками, отправляется сам на шестой цифре). Похоже на опечатку в адресе — предлагаем исправленный.
 * Повторная отправка — через минуту. Ошибки — человеческими словами.
 */
export default function Login() {
  const insets = useSafeAreaInsets()
  const { signIn } = useAuth()
  const [step, setStep] = useState<'email' | 'code'>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [suggestion, setSuggestion] = useState('')
  const [left, setLeft] = useState(0)
  const codeRef = useRef<TextInput>(null)

  useEffect(() => {
    if (left <= 0) return undefined
    const t = setTimeout(() => setLeft((n) => n - 1), 1000)
    return () => clearTimeout(t)
  }, [left])

  const valid = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())

  const send = async (address = email.trim(), force = false) => {
    setBusy(true); setError(''); setSuggestion('')
    try {
      const res = await requestCode(address)
      if (res.status === 'typo_suspected' && res.suggestion && !force) {
        setSuggestion(res.suggestion)
        return
      }
      setEmail(address); setStep('code'); setCode(''); setLeft(RESEND)
      setTimeout(() => codeRef.current?.focus(), 250)
    } catch (e) {
      setError(e instanceof ApiError && e.status === 429 ? tr('Слишком много попыток. Подождите немного и попробуйте снова.') : tr('Не удалось отправить код. Проверьте адрес и интернет.'))
    } finally {
      setBusy(false)
    }
  }

  const confirm = async (value: string) => {
    setBusy(true); setError('')
    try {
      const res = await verifyCode(email.trim(), value)
      await signIn(res.token, res.user)
      router.back()
    } catch (e) {
      setCode('')
      setError(e instanceof ApiError && e.status === 429 ? tr('Слишком много попыток. Подождите немного.') : tr('Код не подошёл. Проверьте письмо или запросите новый.'))
    } finally {
      setBusy(false)
    }
  }

  const onCode = (v: string) => {
    const digits = v.replace(/\D/g, '').slice(0, LEN)
    setCode(digits)
    if (digits.length === LEN && !busy) confirm(digits)
  }

  return (
    <KeyboardAvoidingView style={[styles.page, { paddingTop: insets.top + 8 }]} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.top}>
        <Pressable onPress={() => (step === 'code' ? (setStep('email'), setError('')) : router.back())} hitSlop={10}
          accessibilityLabel={step === 'code' ? tr('Изменить почту') : tr('Закрыть')} style={styles.iconBtn}>
          <Ionicons name={step === 'code' ? 'chevron-back' : 'close'} size={24} color={colors.ink} />
        </Pressable>
      </View>

      <View style={styles.body}>
        {step === 'email' ? (
          <>
            <Text style={styles.title}>{tr('Вход в PLONK')}</Text>
            <Text style={styles.text}>{tr('Пришлём код на почту — пароль не нужен. Если аккаунта ещё нет, он создастся сам.')}</Text>
            <TextInput
              value={email}
              onChangeText={(v) => { setEmail(v); setSuggestion(''); setError('') }}
              placeholder="you@example.com"
              placeholderTextColor={colors.muted}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              textContentType="emailAddress"
              returnKeyType="send"
              onSubmitEditing={() => valid && !busy && send()}
              style={styles.input}
              autoFocus
            />
            {!!suggestion && (
              <View style={styles.hint}>
                <Text style={styles.hintText}>{tr('Может быть,')} <Text style={styles.bold}>{suggestion}</Text>?</Text>
                <View style={styles.hintRow}>
                  <Pressable style={styles.hintBtn} onPress={() => send(suggestion)}><Text style={styles.hintBtnText}>{tr('Да, исправить')}</Text></Pressable>
                  <Pressable style={[styles.hintBtn, styles.hintGhost]} onPress={() => send(email.trim(), true)}><Text style={styles.hintGhostText}>{tr('Нет, всё верно')}</Text></Pressable>
                </View>
              </View>
            )}
            {!!error && <Text style={styles.error}>{error}</Text>}
            <Pressable style={[styles.cta, (!valid || busy) && styles.ctaOff]} disabled={!valid || busy} onPress={() => send()}>
              {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.ctaText}>{tr('Получить код')}</Text>}
            </Pressable>
          </>
        ) : (
          <>
            <Text style={styles.title}>{tr('Код из письма')}</Text>
            <Text style={styles.text}>{tr('Отправили на')} <Text style={styles.bold}>{email.trim()}</Text>{tr('. Письмо может прийти в «Спам».')}</Text>
            <Pressable onPress={() => codeRef.current?.focus()} style={styles.cells} accessibilityLabel={tr('Поле для кода')}>
              {Array.from({ length: LEN }).map((_, i) => (
                <View key={i} style={[styles.cell, i === code.length && !busy && styles.cellOn]}>
                  <Text style={styles.cellText}>{code[i] ?? ''}</Text>
                </View>
              ))}
            </Pressable>
            <TextInput
              ref={codeRef}
              value={code}
              onChangeText={onCode}
              keyboardType="number-pad"
              textContentType="oneTimeCode"
              autoComplete="one-time-code"
              maxLength={LEN}
              style={styles.hidden}
              caretHidden
            />
            {busy && <ActivityIndicator style={{ marginTop: 16 }} color={colors.primary} />}
            {!!error && <Text style={styles.error}>{error}</Text>}
            <Pressable disabled={left > 0 || busy} onPress={() => send(email.trim(), true)} style={styles.resend}>
              <Text style={[styles.resendText, left > 0 && { color: colors.muted }]}>
                {left > 0 ? tr('Отправить снова через {n} с', { n: left }) : tr('Отправить код снова')}
              </Text>
            </Pressable>
          </>
        )}
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  top: { paddingHorizontal: 12, height: 44, justifyContent: 'center' },
  iconBtn: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  body: { paddingHorizontal: 20, paddingTop: 8, gap: 12 },
  title: { fontSize: 26, fontWeight: '800', color: colors.ink },
  text: { fontSize: 15.5, lineHeight: 22, color: colors.inkSoft },
  bold: { fontWeight: '800', color: colors.ink },
  input: { height: 52, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 16, fontSize: 17, color: colors.ink, marginTop: 6 },
  hint: { backgroundColor: colors.accentSoft, borderRadius: 14, padding: 12, gap: 10 },
  hintText: { fontSize: 15, color: colors.ink },
  hintRow: { flexDirection: 'row', gap: 8 },
  hintBtn: { height: 40, paddingHorizontal: 14, borderRadius: 10, backgroundColor: colors.ink, justifyContent: 'center' },
  hintBtnText: { color: '#fff', fontWeight: '800', fontSize: 14 },
  hintGhost: { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: colors.ink },
  hintGhostText: { color: colors.ink, fontWeight: '800', fontSize: 14 },
  error: { fontSize: 14.5, color: '#B42318', lineHeight: 20 },
  cta: { height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', marginTop: 6 },
  ctaOff: { opacity: 0.45 },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  cells: { flexDirection: 'row', gap: 8, marginTop: 10 },
  cell: { flex: 1, height: 56, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  cellOn: { borderColor: colors.primary },
  cellText: { fontSize: 24, fontWeight: '800', color: colors.ink },
  hidden: { position: 'absolute', opacity: 0, width: 1, height: 1 },
  resend: { marginTop: 8, height: 44, justifyContent: 'center' },
  resendText: { fontSize: 15, fontWeight: '700', color: colors.primaryDeep },
})
