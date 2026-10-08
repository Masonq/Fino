import { useLocalSearchParams } from 'expo-router'
import { useEffect, useState } from 'react'
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { teamChat, teamReply } from '../../../src/admin'
import { useAuth } from '../../../src/auth'
import { tr } from '../../../src/i18n'
import { Header } from '../../../src/components/Kit'
import Icon from '../../../src/components/Icon'
import { colors, font } from '../../../src/theme'

/** Переписка человека с командой и ответ от имени команды. */
export default function TeamThread() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { token } = useAuth()
  const [data, setData] = useState<Awaited<ReturnType<typeof teamChat>> | null>(null)
  const [text, setText] = useState('')
  const load = () => { if (token) teamChat(token, id).then(setData).catch(() => {}) }
  useEffect(load, [token, id]) // eslint-disable-line react-hooks/exhaustive-deps
  const send = () => {
    const v = text.trim()
    if (!v || !token) return
    setText('')
    setData((d) => (d ? { ...d, messages: [...d.messages, { text: v, from_team: true }] } : d))
    teamReply(token, id, v).then(load).catch(load)
  }
  return (
    <KeyboardAvoidingView style={st.page} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 20, gap: 8 }}>
        <Header bleed={16} bleedTop={0} title={data?.person?.name || tr('Письмо')} fallback="/admin/team" />
        {(data?.messages ?? []).map((m, i) => (
          <View key={m.id || i} style={[st.bubble, m.from_team ? st.mine : st.their]}><Text style={[st.t, m.from_team && { color: colors.onInverse }]}>{m.text}</Text></View>
        ))}
      </ScrollView>
      <View style={st.bar}>
        <TextInput style={st.input} value={text} onChangeText={setText} placeholder={tr('Ответ от команды…')} placeholderTextColor={colors.muted} multiline />
        <Pressable style={st.send} onPress={send}><Icon name="send" size={19} color={colors.onInverse} /></Pressable>
      </View>
    </KeyboardAvoidingView>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  bubble: { maxWidth: '82%', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 18 },
  mine: { alignSelf: 'flex-end', backgroundColor: colors.inverse },
  their: { alignSelf: 'flex-start', backgroundColor: colors.surface },
  t: { fontFamily: font[400], fontSize: 15, color: colors.ink, lineHeight: 20 },
  bar: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 10, paddingBottom: 28, backgroundColor: colors.surface },
  input: { flex: 1, minHeight: 44, maxHeight: 120, borderRadius: 22, backgroundColor: colors.sunken, paddingHorizontal: 16, paddingTop: 12, fontFamily: font[400], fontSize: 15, color: colors.ink },
  send: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
})
