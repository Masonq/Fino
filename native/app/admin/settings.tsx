import { useEffect, useState } from 'react'
import { ScrollView, StyleSheet, Switch, Text, View } from 'react-native'
import { adminSettings, setCardPayments } from '../../src/admin'
import { useAuth } from '../../src/auth'
import { tr } from '../../src/i18n'
import { Header } from '../../src/components/Kit'
import Skeleton from '../../src/components/Skeleton'
import { colors, font } from '../../src/theme'

/** Настройки сайта (только владелец): оплата картой. */
export default function Settings() {
  const { token } = useAuth()
  const [on, setOn] = useState<boolean | null>(null)
  useEffect(() => { if (token) adminSettings(token).then((s) => setOn(s.card_payments_enabled)).catch(() => {}) }, [token])
  const toggle = (v: boolean) => { if (!token) return; setOn(v); setCardPayments(token, v).then((s) => setOn(s.card_payments_enabled)).catch(() => setOn(!v)) }
  return (
    <View style={st.page}>
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 60 }}>
        <Header bleed={16} bleedTop={0} title={tr('Настройки')} fallback="/admin" />
        {on === null ? <Skeleton style={{ height: 150, borderRadius: 22 }} /> : (
          <View style={st.card}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={{ flex: 1 }}><Text style={st.t}>{tr('Оплата картой')}</Text><Text style={st.s}>{on ? tr('Включена') : tr('Выключена')}</Text></View>
              <Switch value={on} onValueChange={toggle} trackColor={{ true: colors.primary, false: colors.sunken }} />
            </View>
            <Text style={st.h}>{tr('Пополнение баланса и оплата продвижения картой. Когда выключено, продвижение — только за бонусы и уже внесённый баланс, кнопка «Пополнить» скрыта.')}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}

const st = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  card: { padding: 16, borderRadius: 22, backgroundColor: colors.surface, gap: 10 },
  t: { fontFamily: font[800], fontSize: 16, color: colors.ink },
  s: { fontFamily: font[600], fontSize: 13, color: colors.muted, marginTop: 2 },
  h: { fontFamily: font[400], fontSize: 13.5, color: colors.inkSoft, lineHeight: 19 },
})
