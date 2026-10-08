/**
 * «Поднять просмотры» — продвижение объявления, как на сайте: поднятие в поиске, выделение цветом, крупная карточка.
 * Оплата с баланса: сначала бонусами, остаток — внесёнными деньгами (тогда нужно согласие на немедленное начало
 * услуги, как на сайте). Пополнения картой в приложении нет — если не хватает, так и говорим.
 */
import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Switch, Text, View } from 'react-native'
import { ApiError, type PromoInfo, promotions, startPromotion } from '../api'
import { tr } from '../i18n'
import { colors, font } from '../theme'
import SheetFrame from './SheetFrame'

const TYPES: { key: 'bump' | 'highlight' | 'xl_card'; title: string; desc: string }[] = [
  { key: 'bump', title: 'Поднятие в поиске', desc: 'Поднимает объявление на самый верх выдачи — покупатели увидят его первым' },
  { key: 'highlight', title: 'Выделение цветом', desc: 'Цветной фон в ленте — мимо такой карточки сложнее пролистать не заметив. 7 дней' },
  { key: 'xl_card', title: 'Крупная карточка', desc: 'Крупное фото во всю ширину экрана — выделяется среди соседей с первого взгляда. 7 дней' },
]
const rsd = (n: number) => Math.round(n).toLocaleString('ru-RU')

export default function PromoteSheet({ token, listingId, onClose }: { token: string; listingId: string; onClose: () => void }) {
  const [info, setInfo] = useState<PromoInfo | null>(null)
  const [pick, setPick] = useState<'bump' | 'highlight' | 'xl_card'>('bump')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => { promotions(token, listingId).then(setInfo).catch(() => setMsg({ ok: false, text: tr('Продвижение временно недоступно, попробуйте позже') })) }, [token, listingId])
  const price = info?.prices[pick] ?? 0
  const active = (k: string) => info?.items.find((i) => i.type === k && i.active !== false)
  const enough = !!info && info.balance >= price
  const needsMoney = !!info && info.bonus < price
  const pay = async () => {
    if (needsMoney && !consent) { setMsg({ ok: false, text: tr('Отметьте согласие: без него услугу за деньги не оформить.') }); return }
    setBusy(true); setMsg(null)
    try {
      await startPromotion(token, listingId, pick, consent)
      setMsg({ ok: true, text: tr('Продвижение подключено!') })
      promotions(token, listingId).then(setInfo).catch(() => {})
    } catch (e) {
      const code = e instanceof ApiError ? (e as unknown as { code?: string }).code : ''
      setMsg({ ok: false, text: code === 'consent_required' ? tr('Отметьте согласие: без него услугу за деньги не оформить.') : tr('Не получилось, попробуйте ещё раз') })
    } finally { setBusy(false) }
  }
  return (
    <SheetFrame visible onClose={onClose}>
      <View style={st.sheet}>
        <View style={st.handle} />
        <Text style={st.title}>{tr('Продвижение объявления')}</Text>
        {!info ? <ActivityIndicator style={{ margin: 30 }} color={colors.primary} /> : (
          <>
            <Text style={st.bal}>{tr('Баланс')}: <Text style={{ color: colors.ink }}>{rsd(info.money)} RSD</Text> · {tr('бонусы')} <Text style={{ color: colors.primaryDeep }}>{rsd(info.bonus)} RSD</Text></Text>
            {TYPES.map((t) => {
              const on = pick === t.key; const act = active(t.key)
              return (
                <Pressable key={t.key} style={[st.opt, on && st.optOn, !!act && { opacity: 0.55 }]} disabled={!!act} onPress={() => { setPick(t.key); setMsg(null) }}>
                  <View style={{ flex: 1 }}>
                    <Text style={st.optT}>{tr(t.title)}</Text>
                    <Text style={st.optD}>{act ? tr('Уже активно') : tr(t.desc)}</Text>
                  </View>
                  <Text style={st.price}>{rsd(info.prices[t.key])} RSD</Text>
                </Pressable>
              )
            })}
            {needsMoney && enough && (
              <View style={st.consent}>
                <Text style={st.consentT}>{tr('Хочу, чтобы услуга началась сразу, и знаю, что после её полного оказания право отказаться от договора теряется')}</Text>
                <Switch value={consent} onValueChange={setConsent} trackColor={{ true: colors.primary, false: colors.sunken }} />
              </View>
            )}
            {!enough && <Text style={st.warn}>{tr('На балансе {n} RSD — не хватает. Пополнение картой пока недоступно.', { n: rsd(info.balance) })}</Text>}
            {!!msg && <Text style={[st.warn, msg.ok && { color: colors.primaryDeep }]}>{msg.text}</Text>}
            <Pressable style={[st.pay, (!enough || busy) && { opacity: 0.5 }]} disabled={!enough || busy} onPress={pay}>
              {busy ? <ActivityIndicator color={colors.onInverse} /> : <Text style={st.payT}>{tr('Оплатить с баланса — {n} RSD', { n: rsd(price) })}</Text>}
            </Pressable>
          </>
        )}
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
