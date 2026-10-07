import { tr } from '../src/i18n'
import { router } from 'expo-router'
import { useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { ApiError, requestCode, verifyCode } from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { API, SITE } from '../src/config'
import * as WebBrowser from 'expo-web-browser'
import Svg, { Path } from 'react-native-svg'
import * as Crypto from 'expo-crypto'
import * as Linking from 'expo-linking'
import { Image } from 'expo-image'
import { colors, font } from '../src/theme'

const LEN = 6
const base64url = (b: Uint8Array) => btoa(String.fromCharCode(...Array.from(b))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
const RESEND = 60

/**
 * Вход по коду из почты — как на сайте. Почта → код из письма (шесть цифр; вводится в одно поле, рисуется
 * клетками, отправляется сам на шестой цифре). Похоже на опечатку в адресе — предлагаем исправленный.
 * Повторная отправка — через минуту. Ошибки — человеческими словами.
 */
/** Фирменная «G» Google — как на кнопке входа Google на сайте. */
function GoogleG() {
  return (
    <Svg width={19} height={19} viewBox="0 0 48 48">
      <Path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <Path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <Path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2c-2 1.5-4.5 2.4-7.2 2.4-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <Path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </Svg>
  )
}

export default function Login() {
  const insets = useSafeAreaInsets()
  const { signIn } = useAuth()
  // Как на сайте: сначала выбор способа входа, затем почта → код или Telegram
  const [step, setStep] = useState<'choose' | 'email' | 'code' | 'telegram'>('choose')
  const [tgKey, setTgKey] = useState('')
  const [tgFailed, setTgFailed] = useState(false)
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

  // Вход через Google — через сайт: ключи Google у нас только для сайта, поэтому приложение открывает страницу входа
  // plonk.rs в защищённом окне браузера (ASWebAuthenticationSession / Custom Tabs); там — настоящая кнопка Google,
  // а готовый вход сайт возвращает по ссылке plonk://auth?token=…
  const [googleBusy, setGoogleBusy] = useState(false)
  const startGoogle = async () => {
    setGoogleBusy(true); setError('')
    try {
      const res = await WebBrowser.openAuthSessionAsync(`${SITE}/login?app=google`, 'plonk://auth')
      if (res.type !== 'success') return
      const token = decodeURIComponent((res.url.match(/[?&]token=([^&#]+)/) ?? [])[1] ?? '')
      if (!token) return
      const r = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) throw new Error('me')
      await signIn(token, await r.json())
      router.back()
    } catch {
      setError(tr('Не удалось войти через Google. Попробуйте ещё раз.'))
    } finally { setGoogleBusy(false) }
  }

  // Вход через Telegram: свой одноразовый ключ → бот подтверждает → забираем вход (/auth/telegram/enter)
  const startTelegram = async () => {
    setTgFailed(false)
    const key = tgKey || base64url(Crypto.getRandomBytes(24))
    setTgKey(key)
    setStep('telegram')
    let bot = 'Baraholka_plonk_bot'
    try { const r = await fetch(`${API}/auth/telegram/link`); const j = await r.json(); bot = String(j.url).split('t.me/')[1]?.split('?')[0] || bot } catch { /* имя по умолчанию */ }
    Linking.openURL(`https://t.me/${bot}?start=applogin_${key}`).catch(() => {})
  }
  useEffect(() => {
    if (step !== 'telegram' || !tgKey) return undefined
    let stop = false
    const started = Date.now()
    const tick = async () => {
      if (stop) return
      if (Date.now() - started > 5 * 60 * 1000) { setTgFailed(true); return }
      try {
        const r = await fetch(`${API}/auth/telegram/enter`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: tgKey }) })
        if (r.ok) {
          const j = await r.json()
          const me = await (await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${j.access_token}` } })).json()
          await signIn(j.access_token, me)
          router.back()
          return
        }
      } catch { /* нет сети — попробуем снова */ }
      setTimeout(tick, 2000)
    }
    tick()
    return () => { stop = true }
  }, [step, tgKey]) // eslint-disable-line react-hooks/exhaustive-deps

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
    <KeyboardAvoidingView style={[styles.page, { paddingTop: Platform.OS === 'ios' ? 10 : insets.top + 8 }]} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.top}>
        <Pressable onPress={() => (step === 'code' ? (setStep('email'), setError('')) : step === 'email' || step === 'telegram' ? (setStep('choose'), setError(''), setTgKey('')) : router.back())} hitSlop={10}
          accessibilityLabel={step === 'choose' ? tr('Закрыть') : tr('Назад')} style={styles.iconBtn}>
          <Icon name={step === 'choose' ? 'close' : 'back'} size={22} color={colors.ink} />
        </Pressable>
      </View>

      <View style={styles.body}>
        {step === 'choose' ? (
          <View style={styles.choose}>
            <Image source={require('../assets/logo-mark.png')} style={styles.logo} contentFit="contain" />
            <Text style={styles.chooseTitle}>{tr('Вход в PLONK')}</Text>
            <Text style={styles.chooseSub}>{tr('Чтобы писать продавцам, публиковать объявления и сохранять избранное')}</Text>
            <Pressable style={[styles.cta, styles.method, styles.methodPrimary]} onPress={() => setStep('email')} accessibilityRole="button">
              <Icon name="mail" size={18} color="#fff" />
              <Text style={[styles.ctaText, { fontSize: 15.5, fontFamily: font[700] }]}>{tr('Войти по почте')}</Text>
            </Pressable>
            <Pressable style={[styles.method, styles.methodTg]} onPress={startTelegram} accessibilityRole="button">
              <Icon name="telegram" size={20} color="#229ED9" filled />
              <Text style={styles.methodTgText}>{tr('Войти через Telegram')}</Text>
            </Pressable>
            <Pressable style={[styles.method, styles.methodTg, googleBusy && { opacity: 0.6 }]} disabled={googleBusy} onPress={startGoogle} accessibilityRole="button">
              <GoogleG />
              <Text style={styles.methodTgText}>{tr('Войти через Google')}</Text>
            </Pressable>
            {!!error && <Text style={styles.error}>{error}</Text>}
            <Text style={styles.consent}>
              {tr('Продолжая, вы принимаете')} <Text style={styles.consentLink} onPress={() => router.push('/legal/terms')}>{tr('условия')}</Text> {tr('и')} <Text style={styles.consentLink} onPress={() => router.push('/legal/privacy')}>{tr('политику конфиденциальности')}</Text>.
            </Text>
          </View>
        ) : step === 'telegram' ? (
          <View style={styles.choose}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={[styles.title, { textAlign: 'center' }]}>{tr('Подтвердите вход в Telegram')}</Text>
            <Text style={[styles.text, { textAlign: 'center' }]}>{tr('Откройте бота PLONK, нажмите «Запустить» и вернитесь сюда — вход выполнится сам.')}</Text>
            {tgFailed && <Text style={styles.error}>{tr('Время вышло. Попробуйте ещё раз.')}</Text>}
            <Pressable style={[styles.method, styles.methodTg]} onPress={startTelegram}><Text style={styles.methodTgText}>{tr('Открыть Telegram ещё раз')}</Text></Pressable>
          </View>
        ) : step === 'email' ? (
          <View style={styles.center}>
            <View style={styles.authIcon}><Icon name="mail" size={28} color={colors.primaryDeep} /></View>
            <Text style={styles.authTitle}>{tr('Ваша почта')}</Text>
            <Text style={styles.authSub}>{tr('Отправим код подтверждения на этот адрес')}</Text>
            <View style={styles.inputWrap}>
            <Icon name="mail" size={20} color={colors.muted} />
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
              style={styles.inputBare}
              autoFocus
            />
            </View>
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
              {busy ? <ActivityIndicator color={colors.onInverse} /> : <Text style={styles.ctaText}>{tr('Получить код')}</Text>}
            </Pressable>
          </View>
        ) : (
          <View style={styles.center}>
            <View style={styles.authIcon}><Icon name="lock" size={28} color={colors.primaryDeep} /></View>
            <Text style={styles.authTitle}>{tr('Введите код')}</Text>
            <Text style={styles.authSub}>{tr('Код отправлен на')} <Text style={styles.bold}>{email.trim()}</Text>{'\n'}{tr('Письмо может прийти в «Спам».')}</Text>
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
                {left > 0 ? `${tr('Отправить заново через')} ${left} ${tr('с')}` : tr('Отправить код заново')}
              </Text>
            </Pressable>
          </View>
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
  title: { fontSize: 26, fontFamily: font[800], color: colors.ink },
  text: { fontFamily: font[400], fontSize: 15.5, lineHeight: 22, color: colors.inkSoft },
  bold: { fontFamily: font[800], color: colors.ink },
  input: { height: 52, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 16, fontFamily: font[400], fontSize: 17, color: colors.ink, marginTop: 6 },
  hint: { backgroundColor: colors.accentSoft, borderRadius: 14, padding: 12, gap: 10 },
  hintText: { fontFamily: font[400], fontSize: 15, color: colors.ink },
  hintRow: { flexDirection: 'row', gap: 8 },
  hintBtn: { height: 40, paddingHorizontal: 14, borderRadius: 10, backgroundColor: colors.inverse, justifyContent: 'center' },
  hintBtnText: { color: colors.onInverse, fontFamily: font[800], fontSize: 14 },
  hintGhost: { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: colors.ink },
  hintGhostText: { color: colors.ink, fontFamily: font[800], fontSize: 14 },
  error: { fontFamily: font[400], fontSize: 14.5, color: colors.danger, lineHeight: 20 },
  cta: { height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center', marginTop: 6, alignSelf: 'center', width: '100%', maxWidth: 340 },
  ctaOff: { opacity: 0.45 },
  ctaText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  cells: { flexDirection: 'row', gap: 8, marginTop: 10 },
  cell: { flex: 1, height: 56, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  cellOn: { borderColor: colors.primary },
  cellText: { fontSize: 24, fontFamily: font[800], color: colors.ink },
  hidden: { position: 'absolute', opacity: 0, width: 1, height: 1 },
  // как .auth-icon / .auth-input-wrap сайта
  center: { alignItems: 'center', paddingTop: 24, gap: 6 },
  authIcon: { width: 64, height: 64, borderRadius: 18, marginBottom: 12, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  authTitle: { fontSize: 21, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  authSub: { fontSize: 13.5, lineHeight: 19.5, fontFamily: font[500], color: colors.muted, textAlign: 'center', maxWidth: 300, marginBottom: 14 },
  // как .auth-input-wrap сайта: не шире 340, по центру
  inputWrap: { flexDirection: 'row', alignItems: 'center', gap: 11, alignSelf: 'center', width: '100%', maxWidth: 340, paddingHorizontal: 16, height: 54, borderRadius: 14, borderWidth: 1.5, borderColor: 'rgba(20,30,25,0.09)', backgroundColor: colors.surface, marginBottom: 6 },
  inputBare: { flex: 1, minWidth: 0, fontSize: 16, fontFamily: font[500], color: colors.ink, paddingVertical: 0 },
  choose: { alignItems: 'center', gap: 10, paddingTop: 24 },
  // как .auth-logo / .auth-sub / .auth-method сайта
  logo: { width: 52, height: 52, borderRadius: 26, alignSelf: 'center', marginBottom: 6 },
  method: { flexDirection: 'row', gap: 10, alignSelf: 'stretch', maxWidth: 340, width: '100%', marginHorizontal: 'auto', height: 52, borderRadius: 14 },
  methodPrimary: { shadowColor: '#0E9F6E', shadowOpacity: 0.26, shadowRadius: 18, shadowOffset: { width: 0, height: 6 }, elevation: 4 },
  chooseTitle: { fontSize: 21, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  chooseSub: { fontSize: 13.5, lineHeight: 19.5, fontFamily: font[500], color: colors.muted, textAlign: 'center', maxWidth: 300, marginTop: -2, marginBottom: 16 },
  methodTg: { height: 52, borderRadius: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  methodTgText: { fontSize: 15.5, fontFamily: font[700], color: colors.ink },
  consent: { fontSize: 12.5, lineHeight: 18, fontFamily: font[500], color: colors.muted, textAlign: 'center', marginTop: 4 },
  consentLink: { color: colors.primaryDeep, fontFamily: font[700] },
  resend: { marginTop: 8, height: 44, justifyContent: 'center' },
  resendText: { fontSize: 15, fontFamily: font[700], color: colors.primaryDeep },
})
