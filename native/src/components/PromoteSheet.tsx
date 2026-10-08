/**
 * «Поднять просмотры» — продвижение объявления, как на сайте: поднятие в поиске, выделение цветом, крупная карточка.
 * Оплата с баланса: сначала бонусами, остаток — внесёнными деньгами (тогда нужно согласие на немедленное начало
 * услуги, как на сайте). Пополнения картой в приложении нет — если не хватает, так и говорим.
 */
import { useEffect, useState } from 'react'
import { ActivityIndicator, Platform, StyleSheet, Text, View } from 'react-native'
import type React from 'react'
import { type PromoInfo, promotions } from '../api'
import { tr } from '../i18n'
import { colors, font } from '../theme'
import SheetFrame from './SheetFrame'

// модуль магазина есть только в сборке для телефона — в веб-просмотре его нет
const Store: React.ComponentType<{ token: string; listingId: string; info: PromoInfo; onDone: () => void }> | null =
  Platform.OS === 'web' ? null : require('./PromoteStore').default


export default function PromoteSheet({ token, listingId, onClose }: { token: string; listingId: string; onClose: () => void }) {
  const [info, setInfo] = useState<PromoInfo | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => { promotions(token, listingId).then(setInfo).catch(() => setFailed(true)) }, [token, listingId])

  return (
    <SheetFrame visible onClose={onClose}>
      <View style={st.sheet}>
        <View style={st.handle} />
        <Text style={st.title}>{tr('Продвижение объявления')}</Text>
        {/* на телефоне — бонусы или покупка через App Store / Google Play (правила магазинов для цифровых услуг) */}
        {failed ? <Text style={st.warn}>{tr('Продвижение временно недоступно, попробуйте позже')}</Text>
          : !info ? <ActivityIndicator style={{ margin: 30 }} color={colors.primary} />
          : Store ? <Store token={token} listingId={listingId} info={info} onDone={() => promotions(token, listingId).then(setInfo).catch(() => {})} />
          : <Text style={st.warn}>{tr('Продвижение доступно в приложении на телефоне')}</Text>}
      </View>
    </SheetFrame>
  )
}

const st = StyleSheet.create({
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 26, borderTopRightRadius: 26, padding: 16, paddingBottom: 34, gap: 10 },
  handle: { width: 40, height: 5, borderRadius: 3, backgroundColor: colors.sunken, alignSelf: 'center' },
  title: { fontFamily: font[800], fontSize: 19, color: colors.ink },
  bal: { fontFamily: font[600], fontSize: 13.5, color: colors.muted },
  opt: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 18, backgroundColor: colors.bg, borderWidth: 2, borderColor: 'transparent' },
  optOn: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  optT: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  optD: { fontFamily: font[400], fontSize: 12.5, color: colors.inkSoft, marginTop: 2, lineHeight: 17 },
  price: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  consent: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  consentT: { flex: 1, fontFamily: font[400], fontSize: 12.5, color: colors.inkSoft },
  warn: { fontFamily: font[600], fontSize: 13.5, color: colors.danger },
  pay: { height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  payT: { fontFamily: font[800], fontSize: 15.5, color: colors.onInverse },
})
