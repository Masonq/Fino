/**
 * Покупка продвижения через магазин (App Store / Google Play) — так требуют правила обоих магазинов для цифровых услуг.
 * Хватает бесплатных бонусов — платим ими, без магазина. Не хватает — системное окно оплаты Apple / Google; купленное
 * сервер сам проверяет у магазина (/api/iap/verify) и только тогда включает продвижение; после этого покупка
 * «закрывается» (расходуемый товар — можно купить снова).
 * Отдельный файл, подключается только на телефоне: в веб-сборке модуля магазина нет.
 */
import { useEffect, useState } from 'react'
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native'
import { useIAP } from 'expo-iap'
import { IAP_SKU, iapVerify, type PromoInfo, startPromotion } from '../api'
import { tr } from '../i18n'
import { colors, font } from '../theme'

type Kind = 'bump' | 'highlight' | 'xl_card'
const TYPES: { key: Kind; title: string; desc: string }[] = [
  { key: 'bump', title: 'Поднятие в поиске', desc: 'Поднимает объявление на самый верх выдачи — покупатели увидят его первым' },
  { key: 'highlight', title: 'Выделение цветом', desc: 'Цветной фон в ленте — мимо такой карточки сложнее пролистать не заметив. 7 дней' },
  { key: 'xl_card', title: 'Крупная карточка', desc: 'Крупное фото во всю ширину экрана — выделяется среди соседей с первого взгляда. 7 дней' },
]
const rsd = (n: number) => Math.round(n).toLocaleString('ru-RU')

export default function PromoteStore({ token, listingId, info, onDone }: { token: string; listingId: string; info: PromoInfo; onDone: () => void }) {
  const [pick, setPick] = useState<Kind>('bump')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const { connected, products, fetchProducts, requestPurchase, finishTransaction } = useIAP({
    onPurchaseSuccess: async (purchase) => {
      try {
        const type = (Object.keys(IAP_SKU) as Kind[]).find((k) => IAP_SKU[k] === purchase.productId) ?? pick
        await iapVerify(token, Platform.OS === 'ios'
          ? { platform: 'ios', listing_id: listingId, type, transaction_id: purchase.id }
          : { platform: 'android', listing_id: listingId, type, purchase_token: purchase.purchaseToken ?? '' })
        await finishTransaction({ purchase, isConsumable: true })
        setMsg({ ok: true, text: tr('Продвижение подключено!') })
        onDone()
      } catch {
        // покупка не закрыта — магазин передаст её снова при следующем открытии, и продвижение включится тогда
        setMsg({ ok: false, text: tr('Оплата прошла, но подключение задержалось — включим автоматически') })
      } finally { setBusy(false) }
    },
    onPurchaseError: (e) => { setBusy(false); if (!/cancel/i.test(String(e.code))) setMsg({ ok: false, text: tr('Не получилось, попробуйте ещё раз') }) },
  })
  useEffect(() => { if (connected) fetchProducts({ skus: Object.values(IAP_SKU), type: 'in-app' }).catch(() => {}) }, [connected, fetchProducts])

  const price = info.prices[pick]
  const byBonus = info.bonus >= price
  const storePrice = (k: Kind) => products.find((p) => p.id === IAP_SKU[k])?.displayPrice
  const active = (k: string) => info.items.find((i) => i.type === k && i.active !== false)

  const pay = async () => {
    setBusy(true); setMsg(null)
    if (byBonus) {
      try { await startPromotion(token, listingId, pick); setMsg({ ok: true, text: tr('Продвижение подключено!') }); onDone() } catch { setMsg({ ok: false, text: tr('Не получилось, попробуйте ещё раз') }) }
      setBusy(false)
      return
    }
    try {
      await requestPurchase({ type: 'in-app', request: { apple: { sku: IAP_SKU[pick] }, google: { skus: [IAP_SKU[pick]] } } })
    } catch { setBusy(false) }
  }

  return (
    <>
      <Text style={st.bal}>{tr('Бонусы')}: <Text style={{ color: colors.primaryDeep }}>{rsd(info.bonus)} RSD</Text></Text>
      {TYPES.map((t) => {
        const on = pick === t.key, act = active(t.key)
        return (
          <Pressable key={t.key} style={[st.opt, on && st.optOn, !!act && { opacity: 0.55 }]} disabled={!!act} onPress={() => { setPick(t.key); setMsg(null) }}>
            <View style={{ flex: 1 }}>
              <Text style={st.optT}>{tr(t.title)}</Text>
              <Text style={st.optD}>{act ? tr('Уже активно') : tr(t.desc)}</Text>
            </View>
            <Text style={st.price}>{info.bonus >= info.prices[t.key] ? `${rsd(info.prices[t.key])} RSD` : (storePrice(t.key) ?? `${rsd(info.prices[t.key])} RSD`)}</Text>
          </Pressable>
        )
      })}
      {!!msg && <Text style={[st.warn, msg.ok && { color: colors.primaryDeep }]}>{msg.text}</Text>}
      <Pressable style={[st.pay, busy && { opacity: 0.5 }]} disabled={busy || (!byBonus && !connected)} onPress={pay}>
        {busy ? <ActivityIndicator color={colors.onInverse} /> : (
          <Text style={st.payT}>{byBonus ? tr('Оплатить бонусами — {n} RSD', { n: rsd(price) }) : tr('Купить — {p}', { p: storePrice(pick) ?? `${rsd(price)} RSD` })}</Text>
        )}
      </Pressable>
      {!byBonus && <Text style={st.note}>{Platform.OS === 'ios' ? tr('Оплата через App Store') : tr('Оплата через Google Play')}</Text>}
    </>
  )
}

const st = StyleSheet.create({
  bal: { fontFamily: font[600], fontSize: 13.5, color: colors.muted },
  opt: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 18, backgroundColor: colors.bg, borderWidth: 2, borderColor: 'transparent' },
  optOn: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  optT: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  optD: { fontFamily: font[400], fontSize: 12.5, color: colors.inkSoft, marginTop: 2, lineHeight: 17 },
  price: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  warn: { fontFamily: font[600], fontSize: 13.5, color: colors.danger },
  pay: { height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  payT: { fontFamily: font[800], fontSize: 15.5, color: colors.onInverse },
  note: { fontFamily: font[500], fontSize: 12, color: colors.muted, textAlign: 'center' },
})
