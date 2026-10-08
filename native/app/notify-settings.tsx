import { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Switch, Text, View } from 'react-native'
import { type NotifyPrefs, notifyPrefs, setNotifyPrefs } from '../src/api'
import { useAuth } from '../src/auth'
import { tr } from '../src/i18n'
import { Header } from '../src/components/Kit'
import Skeleton from '../src/components/Skeleton'
import { colors, font } from '../src/theme'

const KINDS: { key: keyof NotifyPrefs; title: string; hint: string }[] = [
  { key: 'messages', title: 'Сообщения', hint: 'Новые сообщения и ответы в переписке' },
  { key: 'price_drop', title: 'Снижение цены', hint: 'Подешевело то, что у вас в избранном' },
  { key: 'searches', title: 'Сохранённые поиски', hint: 'Появились новые объявления по вашему поиску' },
  { key: 'following', title: 'Подписки', hint: 'Новое у продавцов и витрин, на которые вы подписаны, комментарии к шопсам' },
  { key: 'digest', title: 'Сводка продавца', hint: 'Как идут ваши объявления: просмотры, избранное' },
]

/** Профиль → Уведомления: что присылать в Telegram, на почту и на телефон (в колокольчике видно всё). */
export default function NotifySettings() {
  const { token } = useAuth()
  const [prefs, setPrefs] = useState<NotifyPrefs | null>(null)
  useEffect(() => { if (token) notifyPrefs(token).then(setPrefs).catch(() => {}) }, [token])
  const toggle = (k: keyof NotifyPrefs, v: boolean) => {
    if (!prefs || !token) return
    const prev = prefs
    setPrefs({ ...prefs, [k]: v })
    setNotifyPrefs(token, { [k]: v }).then(setPrefs).catch(() => setPrefs(prev))
  }
  return (
    <View style={st.page}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60 }}>
        <Header bleed={16} bleedTop={0} title={tr('Уведомления')} />
        <Text style={st.hint}>{tr('Что присылать в Telegram, на почту и на телефон. В колокольчике на сайте видно всё.')}</Text>
        <View style={st.group}>
          {!prefs ? <Skeleton style={{ height: 300, borderRadius: 22 }} /> : KINDS.map((k, i) => (
            <View key={k.key} style={[st.row, i === KINDS.length - 1 && { borderBottomWidth: 0 }]}>
              <View style={{ flex: 1 }}>
                <Text style={st.title}>{tr(k.title)}</Text>
                <Text style={st.sub}>{tr(k.hint)}</Text>
              </View>
              <Switch value={!!prefs[k.key]} onValueChange={(v) => toggle(k.key, v)} trackColor={{ true: colors.primary, false: colors.sunken }} />
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  hint: { fontFamily: font[400], fontSize: 14, color: colors.muted, marginBottom: 12 },
  group: { borderRadius: 22, backgroundColor: colors.surface, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  title: { fontFamily: font[700], fontSize: 15.5, color: colors.ink },
  sub: { fontFamily: font[400], fontSize: 12.5, color: colors.muted, marginTop: 2 },
})
