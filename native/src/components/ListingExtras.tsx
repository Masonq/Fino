import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { KeyboardAvoidingView, Modal, Platform, ScrollView, StyleSheet, Text, View } from 'react-native'
import Pressable from './Pressable'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { myListings, type MyListing } from '../api'
import { useAuth } from '../auth'
import { mediaUrl } from '../config'
import { plural, tr } from '../i18n'
import { jobMyResponse, jobRespond, jobResponses, type JobResp, sfByOwner } from '../social'
import { colors, font } from '../theme'
import Icon from './Icon'
import { Btn, Field, k } from './Kit'

export const JOB_ST: Record<string, string> = {
  new: 'Отклик отправлен', viewed: 'Работодатель посмотрел', selected: 'Вы в отобранных', invited: 'Приглашение на собеседование', rejected: 'Отказ',
}
export const JOB_DOT: Record<string, string> = { new: colors.muted, viewed: colors.muted, selected: '#E0A800', invited: colors.primary, rejected: '#D64545' }
export const when = (iso: string) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

/** «Откликнуться» на вакансии (как на сайте): резюме с PLONK или короткая анкета; отклик уходит работодателю в чат. */
export function JobRespond({ listingId, ownerId }: { listingId: string; ownerId?: string }) {
  const { token, user } = useAuth()
  const insets = useSafeAreaInsets()
  const mine = !!(user && ownerId && user.id === ownerId)
  const [resp, setResp] = useState<JobResp | null>(null)
  const [counts, setCounts] = useState<Record<string, number> | null>(null)
  const [open, setOpen] = useState(false)
  const [resumes, setResumes] = useState<MyListing[]>([])
  const [form, setForm] = useState({ name: '', phone: '', about: '', resume: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!token) return
    if (mine) jobResponses(token, listingId, 'new').then((r) => setCounts(r.counts)).catch(() => {})
    else jobMyResponse(token, listingId).then((r) => setResp(r.response)).catch(() => {})
  }, [token, listingId, mine])

  const openForm = () => {
    if (!token) { router.push('/login'); return }
    setForm((f) => ({ ...f, name: f.name || user?.display_name || '', phone: f.phone || user?.phone || '' }))
    myListings(token).then((r) => {
      const list = r.items.filter((l) => ((l as unknown as { attributes?: Record<string, unknown> }).attributes)?.listing_kind === 'resume' && l.status === 'active')
      setResumes(list)
      if (list.length) setForm((f) => ({ ...f, resume: f.resume || list[0].id }))
    }).catch(() => {})
    setErr(''); setOpen(true)
  }
  const send = async () => {
    if (!token) return
    if (form.name.trim().length < 2) { setErr(tr('Укажите имя')); return }
    setBusy(true)
    try {
      setResp(await jobRespond(token, listingId, { name: form.name.trim(), phone: form.phone.trim(), about: form.about.trim(), resume_listing_id: form.resume || null }))
      setOpen(false)
    } catch (e) { setErr((e as { message?: string }).message === 'already_responded' ? tr('Вы уже откликались на эту вакансию') : tr('Не получилось отправить. Попробуйте ещё раз')) }
    setBusy(false)
  }

  if (mine) {
    const total = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : 0
    return (
      <Pressable style={s.bar} onPress={() => router.push(`/jobs/${listingId}` as never)} accessibilityRole="button">
        <Text style={s.barText}>{tr('Отклики на вакансию')}</Text>
        {counts?.new ? <View style={s.badge}><Text style={s.badgeText}>{tr('{n} новых', { n: counts.new })}</Text></View> : <Text style={k.muted}>{total}</Text>}
        <Icon name="forward" size={18} color={colors.muted} />
      </Pressable>
    )
  }
  if (resp) {
    return (
      <Pressable style={s.bar} onPress={() => router.push('/jobs/my' as never)} accessibilityRole="button">
        <View style={[s.dot, { backgroundColor: JOB_DOT[resp.status] }]} />
        <Text style={s.barText}>{tr(JOB_ST[resp.status])}</Text>
        {resp.status === 'invited' && !!resp.interview_at && <Text style={k.muted}>{when(resp.interview_at)}</Text>}
      </Pressable>
    )
  }
  return (
    <>
      <Btn label={tr('Откликнуться')} onPress={openForm} wide />
      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <Pressable style={k.sheetOverlay} onPress={() => setOpen(false)}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
            <Pressable style={[k.sheet, { paddingBottom: insets.bottom + 16 }]} onPress={() => {}}>
              <View style={k.grab} />
              <Text style={k.sheetTitle}>{tr('Отклик на вакансию')}</Text>
              <ScrollView keyboardShouldPersistTaps="handled">
                {resumes.length > 0 && (
                  <View style={k.field}>
                    <Text style={k.fieldLabel}>{tr('Резюме')}</Text>
                    {[...resumes.map((r) => ({ id: r.id, title: r.title })), { id: '', title: tr('Без резюме — заполню анкету') }].map((r) => (
                      <Pressable key={r.id || 'none'} style={[k.pick, form.resume === r.id && { borderColor: colors.primary }]} onPress={() => setForm({ ...form, resume: r.id })}>
                        <Text style={[k.name, { flex: 1 }]} numberOfLines={1}>{r.title}</Text>
                        {form.resume === r.id && <Icon name="check" size={18} color={colors.primary} />}
                      </Pressable>
                    ))}
                  </View>
                )}
                <Field label={tr('Имя')} value={form.name} maxLength={120} onChangeText={(v) => setForm({ ...form, name: v })} />
                <Field label={tr('Телефон')} value={form.phone} maxLength={40} keyboardType="phone-pad" onChangeText={(v) => setForm({ ...form, phone: v })} />
                <Field label={tr('О себе')} value={form.about} maxLength={2000} multiline placeholder={tr('Опыт, когда можете выйти, удобный график')} onChangeText={(v) => setForm({ ...form, about: v })} />
                {!!err && <Text style={k.err}>{err}</Text>}
                <Btn label={busy ? tr('Отправляем…') : tr('Отправить отклик')} onPress={send} busy={busy} wide />
                <Text style={[k.hint, { textAlign: 'center' }]}>{tr('Работодатель получит отклик в чат и сможет пригласить вас на собеседование')}</Text>
              </ScrollView>
            </Pressable>
          </KeyboardAvoidingView>
        </Pressable>
      </Modal>
    </>
  )
}

/** «Ещё N товаров у продавца → Витрина» — вход в витрину из объявления. */
export function StorefrontLink({ ownerId }: { ownerId: string }) {
  const [sf, setSf] = useState<{ slug: string; name: string; cover_url?: string | null; count: number } | null>(null)
  useEffect(() => { sfByOwner(ownerId).then((r) => setSf(r.storefront)).catch(() => {}) }, [ownerId])
  if (!sf || sf.count - 1 < 1) return null
  const more = sf.count - 1
  return (
    <Pressable style={s.sf} onPress={() => router.push(`/s/${sf.slug}` as never)} accessibilityRole="link">
      <View style={s.sfCover}>{!!sf.cover_url && <Image source={{ uri: mediaUrl(sf.cover_url) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />}</View>
      <View style={{ flex: 1 }}>
        <Text style={k.name}>{tr('Ещё {n} {w} у продавца', { n: more, w: plural(more, { ru: ['товар', 'товара', 'товаров'], en: ['item', 'items'], sr: ['stvar', 'stvari', 'stvari'] }) })}</Text>
        <Text style={k.muted} numberOfLines={1}>{tr('Витрина «{name}»', { name: sf.name })}</Text>
      </View>
      <Icon name="forward" size={18} color={colors.muted} />
    </Pressable>
  )
}

const s = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 50, paddingHorizontal: 16, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 0 },
  barText: { flex: 1, fontFamily: font[600], fontSize: 15, color: colors.ink },
  badge: { height: 22, paddingHorizontal: 8, borderRadius: 11, backgroundColor: colors.accent, justifyContent: 'center' },
  badgeText: { fontFamily: font[700], fontSize: 12, color: '#fff' },
  dot: { width: 8, height: 8, borderRadius: 4 },
  sf: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 12, padding: 10, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 0 },
  sfCover: { width: 44, height: 44, borderRadius: 10, overflow: 'hidden', backgroundColor: colors.primarySoft },
})
