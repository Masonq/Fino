import { Image } from 'expo-image'
import { router, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useAuth } from '../../src/auth'
import { mediaUrl } from '../../src/config'
import { tr } from '../../src/i18n'
import Icon from '../../src/components/Icon'
import { Btn, Empty, Field, Header, k, Tabs } from '../../src/components/Kit'
import { when } from '../../src/components/ListingExtras'
import { jobResponses, jobSetStatus, type JobResp } from '../../src/social'
import { colors, font } from '../../src/theme'

type Folder = 'new' | 'selected' | 'invited' | 'rejected'
const pad = (n: number) => String(n).padStart(2, '0')

/** Отклики одной вакансии по папкам — как на сайте: позвонить, написать, отобрать, пригласить, отказать. */
export default function VacancyResponses() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const [folder, setFolder] = useState<Folder>('new')
  const [data, setData] = useState<{ vacancy: { title: string }; counts: Record<string, number>; items: JobResp[] } | null>(null)
  const [invite, setInvite] = useState<{ id: string; date: string; time: string; note: string } | null>(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    if (!token || !id) return
    jobResponses(token, id, folder).then((r) => {
      setData(r)
      if (folder === 'new') r.items.filter((x) => x.status === 'new').forEach((x) => jobSetStatus(token, x.id, { status: 'viewed' }).catch(() => {}))
    }).catch(() => setData({ vacancy: { title: '' }, counts: {}, items: [] }))
  }, [token, id, folder])
  useEffect(() => { setData(null); load() }, [load])

  const act = async (r: JobResp, status: string, extra: Record<string, string> = {}) => {
    if (!token) return
    setBusy(r.id); setErr('')
    try { await jobSetStatus(token, r.id, { status, ...extra }); setInvite(null); load() } catch { setErr(tr('Не получилось сохранить')) }
    setBusy('')
  }
  const sendInvite = (r: JobResp) => {
    if (!invite) return
    const m = invite.date.match(/^(\d{1,2})\.(\d{1,2})\.?(\d{4})?$/), t = invite.time.match(/^(\d{1,2})[:.](\d{2})$/)
    if (!m || !t) { setErr(tr('Дата — ДД.ММ, время — ЧЧ:ММ')); return }
    const year = m[3] ? Number(m[3]) : new Date().getFullYear()
    act(r, 'invited', { interview_at: `${year}-${pad(Number(m[2]))}-${pad(Number(m[1]))}T${pad(Number(t[1]))}:${t[2]}:00`, note: invite.note })
  }

  const tabs = (['new', 'selected', 'invited', 'rejected'] as Folder[]).map((f) => ({
    key: f, n: data?.counts?.[f], label: tr({ new: 'Новые', selected: 'Отобраны', invited: 'Приглашены', rejected: 'Отказ' }[f]),
  }))
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Header title={data?.vacancy?.title || tr('Отклики')} />
      <ScrollView contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: insets.bottom + 24 }}>
        <Tabs value={folder} items={tabs} onChange={setFolder} />
        {!!err && <Text style={k.err}>{err}</Text>}
        {data === null ? <ActivityIndicator style={{ marginTop: 30 }} color={colors.primary} /> : !data.items.length ? <Empty text={tr('Здесь пока никого')} /> : data.items.map((r) => (
          <View key={r.id} style={k.card}>
            <View style={k.row}>
              <View style={s.ava}>{r.avatar ? <Image source={{ uri: mediaUrl(r.avatar) ?? undefined }} style={StyleSheet.absoluteFill} /> : <Text style={s.avaText}>{(r.name || '?')[0]}</Text>}</View>
              <View style={{ flex: 1 }}><Text style={k.name}>{r.name}</Text><Text style={k.muted}>{when(r.created_at)}</Text></View>
              {!!r.phone && <Pressable style={s.call} onPress={() => Linking.openURL(`tel:${r.phone}`)} accessibilityLabel={tr('Позвонить')}><Icon name="phone" size={18} color={colors.primaryDeep} /></Pressable>}
            </View>
            {!!r.resume && <Pressable onPress={() => router.push(`/listing/${r.resume!.id}` as never)}><Text style={s.link}>📄 {r.resume.title}</Text></Pressable>}
            {!!r.about && <Text style={[k.body, { marginTop: 10 }]}>{r.about}</Text>}
            {r.status === 'invited' && !!r.interview_at && <Text style={s.inv}>✅ {tr('Собеседование {when}', { when: when(r.interview_at) })}</Text>}
            {invite?.id === r.id ? (
              <View style={{ marginTop: 12 }}>
                <View style={{ flexDirection: 'row', gap: 10 }}>
                  <View style={{ flex: 1 }}><Field label={tr('Дата')} value={invite.date} placeholder="08.10" keyboardType="numbers-and-punctuation" onChangeText={(v) => setInvite({ ...invite, date: v })} /></View>
                  <View style={{ flex: 1 }}><Field label={tr('Время')} value={invite.time} placeholder="14:30" keyboardType="numbers-and-punctuation" onChangeText={(v) => setInvite({ ...invite, time: v })} /></View>
                </View>
                <Field label={tr('Адрес или ссылка')} value={invite.note} onChangeText={(v) => setInvite({ ...invite, note: v })} />
                <View style={k.actions}>
                  <Btn small kind="ghost" label={tr('Отмена')} onPress={() => setInvite(null)} />
                  <Btn small label={tr('Отправить приглашение')} busy={busy === r.id} onPress={() => sendInvite(r)} />
                </View>
              </View>
            ) : (
              <View style={k.actions}>
                {!!r.chat_id && <Btn small kind="ghost" label={tr('Написать')} onPress={() => router.push(`/chat/${r.chat_id}` as never)} />}
                {!['selected', 'invited', 'rejected'].includes(r.status) && <Btn small kind="ghost" label={tr('Отобрать')} busy={busy === r.id} onPress={() => act(r, 'selected')} />}
                {r.status !== 'rejected' && <Btn small label={r.status === 'invited' ? tr('Перенести') : tr('Пригласить')} onPress={() => setInvite({ id: r.id, date: '', time: '', note: '' })} />}
                {r.status !== 'rejected' && <Btn small kind="danger" label={tr('Отказать')} busy={busy === r.id} onPress={() => act(r, 'rejected')} />}
              </View>
            )}
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  ava: { width: 40, height: 40, borderRadius: 20, overflow: 'hidden', backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  avaText: { fontFamily: font[800], fontSize: 16, color: colors.primaryDeep },
  call: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  link: { marginTop: 10, fontFamily: font[600], fontSize: 15, color: colors.primaryDeep },
  inv: { marginTop: 10, padding: 10, borderRadius: 12, overflow: 'hidden', backgroundColor: colors.primarySoft, fontFamily: font[600], fontSize: 14, color: colors.primaryDeep },
})
