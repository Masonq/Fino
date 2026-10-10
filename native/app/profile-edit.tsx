import { Image } from 'expo-image'
import * as ImagePicker from 'expo-image-picker'
import * as Linking from 'expo-linking'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useState } from 'react'
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import Pressable from '../src/components/Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import {
  ApiError, editProfile, linkTelegramStart, myProfile, type MyProfile, requestEmailChange, startVerification, unlinkTelegram, uploadPhoto,
  verificationStatus, verifyEmailChange,
} from '../src/api'
import { useAuth } from '../src/auth'
import Icon from '../src/components/Icon'
import { mediaUrl } from '../src/config'
import { success } from '../src/haptics'
import { getLang, tr } from '../src/i18n'
import { colors, font } from '../src/theme'

// Тексты — из словаря сайта (edit_profile.*, verify.*)
const MUST_RENAME = "Модератор сбросил ваше имя: прежнее не читалось. Введите новое — до этого нельзя выкладывать объявления и писать продавцам."
const TG_HINT = "Чтобы размещать объявления прямо в Telegram и не заводить второй аккаунт"
const TG_NEED_EMAIL = "Чтобы отвязать Telegram, добавьте почту — иначе входить будет нечем"
const TG_LINKED_HINT = "Можно размещать объявления прямо в Telegram"
const COMPANY_DESC_HINT = "Чем занимаетесь, что продаёте — покупатель увидит это на витрине"
const VERIFIED = "Проверенный пользователь"
const PENDING = "Документ на проверке"
const REJECTED = "Не получилось проверить документ"
const VERIFY_HINT = "Проверка через партнёрский сервис — потребуется снять документ (паспорт, ID-карта) и селфи на его стороне, это займёт пару минут. После проверки на профиле появится отметка «Проверенный пользователь»."

/**
 * «Мои данные» — как EditProfile сайта: фото профиля; имя, телефон (+381), почта со сменой по коду, Telegram
 * (привязать / отвязать); бизнес-аккаунт (компания — после проверки личности); «Сохранить»; проверка документа.
 */
export default function ProfileEdit() {
  const insets = useSafeAreaInsets()
  const { user, token, setUser } = useAuth()
  const [me, setMe] = useState<MyProfile | null>(null)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [avatar, setAvatar] = useState('')
  const [company, setCompany] = useState('')
  const [companyDesc, setCompanyDesc] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [photoBusy, setPhotoBusy] = useState(false)
  const [emailStep, setEmailStep] = useState<'view' | 'enter' | 'code'>('view')
  const [newEmail, setNewEmail] = useState('')
  const [code, setCode] = useState('')
  const [emailBusy, setEmailBusy] = useState(false)
  const [emailError, setEmailError] = useState('')
  const [verify, setVerify] = useState<{ status?: string; reason?: string | null } | null>(null)
  const [verifyBusy, setVerifyBusy] = useState(false)

  const load = useCallback(async () => {
    if (!token) return
    try {
      const m = await myProfile(token)
      setMe(m); setName(m.display_name ?? ''); setAvatar(m.avatar_url ?? ''); setCompany(m.company_name ?? ''); setCompanyDesc(m.company_description ?? '')
      setPhone((m.phone ?? '').replace(/^\+381/, '').replace(/\D/g, ''))
    } catch { /* сеть — покажем, что было */ }
    verificationStatus(token).then((v) => setVerify(v as { status?: string; reason?: string | null })).catch(() => setVerify({ status: 'none' }))
  }, [token])
  useFocusEffect(useCallback(() => { load() }, [load]))

  const isBusiness = me?.role === 'seller_business'
  const locked = !isBusiness && verify?.status !== 'verified'
  const canUnlinkTg = !!(me?.email && me?.email_verified)

  const pickPhoto = async () => {
    if (!token) return
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) { Alert.alert(tr('Нет доступа'), tr('Разрешите доступ к фото в настройках телефона.')); return }
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.85, allowsEditing: true, aspect: [1, 1] })
    if (res.canceled || !res.assets[0]) return
    setPhotoBusy(true)
    try { const up = await uploadPhoto(token, res.assets[0].uri, res.assets[0].mimeType || 'image/jpeg'); setAvatar(up.url) }
    catch { setError(tr('Не удалось загрузить фото')) } finally { setPhotoBusy(false) }
  }

  const save = async () => {
    if (!token || !user) return
    setError('')
    if (name.trim().length < 2) { setError(tr('Имя — хотя бы 2 буквы')); return }
    setSaving(true)
    try {
      const u = await editProfile(token, {
        display_name: name.trim(), avatar_url: avatar.trim(), company_name: company.trim(), company_description: companyDesc.trim(),
        default_language: getLang(), phone: phone.trim() ? `+381${phone.trim()}` : '',
      })
      setUser({ ...user, ...u }); setMe(u); success(); setSaved(true); setTimeout(() => setSaved(false), 1800)
    } catch (e) {
      setError(tr(e instanceof ApiError && e.message === 'phone_taken' ? 'Этот номер уже привязан к другому аккаунту' : 'Не получилось сохранить'))
    } finally { setSaving(false) }
  }

  const sendCode = async () => {
    if (!token) return
    const v = newEmail.trim().toLowerCase()
    if (!v || v === (me?.email ?? '').toLowerCase()) return
    setEmailBusy(true); setEmailError('')
    try { await requestEmailChange(token, v); setEmailStep('code') }
    catch (e) {
      const c = e instanceof ApiError ? e.message : ''
      setEmailError(tr(c === 'email_taken' ? 'Эта почта уже занята другим аккаунтом' : c === 'too_many_requests' ? 'Код уже отправлен — подождите немного перед повторной отправкой' : 'Не получилось сохранить'))
    } finally { setEmailBusy(false) }
  }
  const confirmCode = async () => {
    if (!token || !code.trim()) return
    setEmailBusy(true); setEmailError('')
    try {
      const u = await verifyEmailChange(token, newEmail.trim().toLowerCase(), code.trim())
      setMe(u); if (user) setUser({ ...user, email: u.email }); setEmailStep('view'); setNewEmail(''); setCode(''); success()
    } catch (e) {
      const c = e instanceof ApiError ? e.message : ''
      setEmailError(tr(c === 'wrong_code' ? 'Неверный код' : c === 'code_expired' ? 'Код истёк — запросите новый' : c === 'email_taken' ? 'Эта почта уже занята другим аккаунтом' : 'Не получилось сохранить'))
    } finally { setEmailBusy(false) }
  }
  const linkTg = async () => {
    if (!token) return
    setEmailError('')
    try {
      const r = await linkTelegramStart(token)
      if (r.url) Linking.openURL(r.url)
      else if (r.status === 'already_linked') setMe((m) => (m ? { ...m, telegram_linked: true } : m))
    } catch { setEmailError(tr('Не получилось начать привязку. Попробуйте ещё раз.')) }
  }
  const unlinkTg = async () => {
    if (!token) return
    setEmailError('')
    try { await unlinkTelegram(token); setMe((m) => (m ? { ...m, telegram_linked: false } : m)) }
    catch (e) { setEmailError(tr(e instanceof ApiError && e.message === 'no_other_login' ? 'Чтобы отвязать Telegram, добавьте почту и подтвердите её — иначе будет не войти.' : 'Не получилось начать привязку. Попробуйте ещё раз.')) }
  }
  const startVerify = async () => {
    if (!token) return
    setVerifyBusy(true)
    try { const r = await startVerification(token); if (r.url) Linking.openURL(r.url) }
    catch (e) {
      const c = e instanceof ApiError ? e.message : ''
      if (c === 'already_pending') setVerify({ status: 'pending' })
      else Alert.alert(tr('Не получилось'), tr(c === 'verification_not_configured' || c === 'verification_unavailable' ? 'Сервис проверки личности сейчас не отвечает. Попробуйте позже — мы уже знаем о проблеме.' : 'Проверьте интернет и попробуйте ещё раз.'))
    } finally { setVerifyBusy(false) }
  }

  const avatarUri = mediaUrl(avatar)
  const letter = (name || user?.email || '?').slice(0, 1).toUpperCase()

  return (
    <View style={[styles.page, { paddingTop: insets.top }]}>
      <View style={styles.top}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/profile'))} hitSlop={10} style={styles.back} accessibilityLabel={tr('Назад')}><Icon name="back" size={22} color={colors.ink} /></Pressable>
        <Text style={styles.title}>{tr('Мои данные')}</Text>
      </View>
      {!me ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 30 }]} keyboardShouldPersistTaps="handled">
            {me.must_rename && <Text style={styles.warn}>{tr(MUST_RENAME)}</Text>}

            <View style={[styles.card, styles.avatarCard]}>
              <View style={styles.avatar}>
                {avatarUri ? <Image source={{ uri: avatarUri }} style={styles.avatarImg} contentFit="cover" /> : <Text style={styles.avatarLetter}>{letter}</Text>}
                {photoBusy && <View style={styles.avatarBusy}><ActivityIndicator color="#fff" /></View>}
              </View>
              <View style={{ alignItems: 'center', gap: 6 }}>
                <Text style={styles.cardTitle}>{tr('Фото профиля')}</Text>
                <Pressable onPress={pickPhoto} hitSlop={6}><Text style={styles.action}>{tr('Выбрать фото')}</Text></Pressable>
              </View>
            </View>

            <View style={styles.card}>
              <View style={styles.row}>
                <Text style={styles.label}>{tr('Имя')}</Text>
                <TextInput value={name} onChangeText={setName} placeholder={tr('Как вас зовут')} placeholderTextColor={colors.muted} style={styles.input} maxLength={60} />
              </View>
              <View style={[styles.row, styles.sep]}>
                <Text style={styles.label}>{tr('Телефон')}</Text>
                <View style={styles.phoneBox}>
                  <Text style={styles.prefix}>+381</Text>
                  <TextInput value={phone} onChangeText={(v) => setPhone(v.replace(/\D/g, '').slice(0, 10))} placeholder={tr('6X XXX XXXX')} placeholderTextColor={colors.muted} keyboardType="phone-pad" style={[styles.input, { flex: 1 }]} />
                </View>
              </View>
              <View style={[styles.row, styles.sep]}>
                <Text style={styles.label}>{tr('Почта')}</Text>
                {emailStep === 'view' ? (
                  <View style={styles.valueRow}>
                    <Text style={[styles.value, !me.email && styles.valueEmpty]} numberOfLines={1}>{me.email || tr('Не указана')}</Text>
                    <Pressable onPress={() => setEmailStep('enter')} hitSlop={6}><Text style={styles.action}>{tr('Изменить')}</Text></Pressable>
                  </View>
                ) : emailStep === 'enter' ? (
                  <View style={{ gap: 8 }}>
                    <TextInput value={newEmail} onChangeText={setNewEmail} placeholder={tr('Новая почта')} placeholderTextColor={colors.muted} keyboardType="email-address" autoCapitalize="none" autoCorrect={false} autoFocus style={styles.inputBox} />
                    <View style={styles.subActions}>
                      <Pressable style={[styles.smallBtn, (emailBusy || !newEmail.trim()) && { opacity: 0.5 }]} disabled={emailBusy || !newEmail.trim()} onPress={sendCode}><Text style={styles.smallBtnText}>{tr('Отправить код')}</Text></Pressable>
                      <Pressable onPress={() => { setEmailStep('view'); setNewEmail(''); setEmailError('') }} hitSlop={6}><Text style={styles.ghost}>{tr('Отмена')}</Text></Pressable>
                    </View>
                  </View>
                ) : (
                  <View style={{ gap: 8 }}>
                    <Text style={styles.note}>{tr('Код отправлен на {email}', { email: newEmail.trim() })}</Text>
                    <TextInput value={code} onChangeText={(v) => setCode(v.replace(/\D/g, ''))} placeholder={tr('Код из письма')} placeholderTextColor={colors.muted} keyboardType="number-pad" autoFocus style={styles.inputBox} />
                    <View style={styles.subActions}>
                      <Pressable style={[styles.smallBtn, (emailBusy || !code.trim()) && { opacity: 0.5 }]} disabled={emailBusy || !code.trim()} onPress={confirmCode}><Text style={styles.smallBtnText}>{tr('Подтвердить')}</Text></Pressable>
                      <Pressable onPress={() => { setEmailStep('view'); setNewEmail(''); setCode(''); setEmailError('') }} hitSlop={6}><Text style={styles.ghost}>{tr('Отмена')}</Text></Pressable>
                    </View>
                  </View>
                )}
              </View>
              <View style={[styles.row, styles.sep]}>
                <Text style={styles.label}>Telegram</Text>
                <View style={styles.valueRow}>
                  <Text style={[styles.value, !me.telegram_linked && styles.valueEmpty]}>{tr(me.telegram_linked ? 'Привязан' : 'Не привязан')}</Text>
                  {!me.telegram_linked
                    ? <Pressable onPress={linkTg} hitSlop={6}><Text style={styles.action}>{tr('Привязать')}</Text></Pressable>
                    : canUnlinkTg && <Pressable onPress={unlinkTg} hitSlop={6}><Text style={styles.action}>{tr('Отвязать')}</Text></Pressable>}
                </View>
                <Text style={styles.hint}>{tr(!me.telegram_linked ? TG_HINT : !canUnlinkTg ? TG_NEED_EMAIL : TG_LINKED_HINT)}</Text>
              </View>
              {!!emailError && <Text style={styles.error}>{emailError}</Text>}
            </View>

            <View style={styles.card}>
              <Text style={styles.groupTitle}>{tr('Бизнес-аккаунт')}</Text>
              <View style={styles.row}>
                <Text style={styles.label}>{tr('Компания')}</Text>
                <View style={styles.phoneBox}>
                  <TextInput value={company} onChangeText={setCompany} editable={!locked} placeholder={tr(locked ? 'Доступно после проверки личности' : 'Если продаёте как бизнес')} placeholderTextColor={colors.muted} style={[styles.input, { flex: 1 }, locked && { color: colors.muted }]} maxLength={120} />
                  {locked && <Icon name="lock" size={16} color={colors.muted} />}
                </View>
              </View>
              {!!company.trim() && !locked && (
                <View style={[styles.row, styles.sep]}>
                  <Text style={styles.label}>{tr('О компании')}</Text>
                  <TextInput value={companyDesc} onChangeText={setCompanyDesc} placeholder={tr(COMPANY_DESC_HINT)} placeholderTextColor={colors.muted} multiline maxLength={2000} textAlignVertical="top" style={[styles.input, { minHeight: 90 }]} />
                </View>
              )}
            </View>

            {!!error && <Text style={styles.error}>{error}</Text>}
            <Pressable style={[styles.save, saving && { opacity: 0.6 }]} disabled={saving} onPress={save} accessibilityRole="button">
              {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveText}>{tr(saved ? 'Сохранено' : 'Сохранить')}</Text>}
            </Pressable>

            <View style={[styles.card, { padding: 14, gap: 8 }]}>
              <Text style={[styles.groupTitle, { padding: 0 }]}>{tr('Проверка документа')}</Text>
              {!verify ? <Text style={styles.note}>{tr('Загружаем…')}</Text>
                : verify.status === 'verified' ? <Text style={[styles.status, { color: colors.primaryDeep }]}>{tr(VERIFIED)}</Text>
                : verify.status === 'pending' ? <Text style={[styles.status, { color: '#8A6A1F' }]}>{tr(PENDING)}</Text>
                : (
                  <>
                    {verify.status === 'rejected' && <Text style={[styles.status, { color: colors.danger }]}>{tr(REJECTED)}{verify.reason ? `\n${verify.reason}` : ''}</Text>}
                    <Text style={styles.note}>{tr(VERIFY_HINT)}</Text>
                    <Pressable style={[styles.secondary, verifyBusy && { opacity: 0.6 }]} disabled={verifyBusy} onPress={startVerify}><Text style={styles.secondaryText}>{verifyBusy ? '…' : tr('Пройти проверку')}</Text></Pressable>
                  </>
                )}
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  groupTitle: { padding: 14, paddingBottom: 0, fontFamily: font[800], fontSize: 12.5, color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.7 },
  page: { flex: 1, backgroundColor: colors.bg },
  top: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingHorizontal: 16, minHeight: 56 },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  title: { flex: 1, fontFamily: font[800], fontSize: 27, lineHeight: 32, letterSpacing: -0.6, color: colors.ink },
  body: { paddingHorizontal: 12, gap: 12 },
  warn: { padding: 12, borderRadius: 14, backgroundColor: colors.warmBg, color: '#8A6A1F', fontSize: 13.5, lineHeight: 19, fontFamily: font[700] },
  card: { borderRadius: 22, backgroundColor: colors.surface, overflow: 'hidden' },
  avatarCard: { flexDirection: 'column', alignItems: 'center', gap: 10, padding: 20, backgroundColor: '#E9F5EC' },
  avatar: { width: 84, height: 84, borderRadius: 42, borderWidth: 4, borderColor: colors.surface, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  avatarImg: { width: 64, height: 64 },
  avatarLetter: { color: '#fff', fontSize: 24, fontFamily: font[800] },
  avatarBusy: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(20,26,22,0.4)', alignItems: 'center', justifyContent: 'center' },
  cardTitle: { fontSize: 15.5, fontFamily: font[800], color: colors.ink },
  row: { paddingHorizontal: 14, paddingVertical: 12, gap: 6 },
  sep: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  label: { fontSize: 12.5, fontFamily: font[700], color: colors.inkSoft },
  input: { fontSize: 16, fontFamily: font[500], color: colors.ink, paddingVertical: 2 },
  inputBox: { height: 46, borderRadius: 12, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, fontSize: 16, fontFamily: font[500], color: colors.ink },
  phoneBox: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  prefix: { fontSize: 16, fontFamily: font[700], color: colors.inkSoft },
  valueRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  value: { flex: 1, fontSize: 16, fontFamily: font[500], color: colors.ink },
  valueEmpty: { color: colors.muted },
  action: { fontSize: 14.5, fontFamily: font[800], color: colors.primaryDeep },
  subActions: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  smallBtn: { paddingHorizontal: 14, paddingVertical: 9, borderRadius: 11, backgroundColor: colors.primary },
  smallBtnText: { color: '#fff', fontSize: 14, fontFamily: font[800] },
  ghost: { fontSize: 14, fontFamily: font[700], color: colors.muted },
  hint: { fontSize: 12.5, lineHeight: 17, fontFamily: font[500], color: colors.muted },
  note: { fontSize: 13, lineHeight: 18, fontFamily: font[500], color: colors.inkSoft },
  error: { fontSize: 13.5, fontFamily: font[600], color: colors.danger, paddingHorizontal: 14, paddingBottom: 12 },
  save: { height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  saveText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
  status: { fontSize: 14, lineHeight: 19, fontFamily: font[700] },
  secondary: { height: 46, borderRadius: 13, borderWidth: 0, alignItems: 'center', justifyContent: 'center' },
  secondaryText: { fontSize: 15, fontFamily: font[800], color: colors.ink },
})
