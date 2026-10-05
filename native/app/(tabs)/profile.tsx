import { Image } from 'expo-image'
import * as Linking from 'expo-linking'
import { router, useFocusEffect } from 'expo-router'
import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { ApiError, balance as fetchBalance, deleteMe, type MyListing, startVerification, verificationStatus, myListings, type Seller, sellerProfile, waitingReviews, type FeedItem, forYouList } from '../../src/api'
import { useAuth } from '../../src/auth'
import { useChats } from '../../src/chats'
import Icon from '../../src/components/Icon'
import Segmented from '../../src/components/Segmented'
import { SITE } from '../../src/config'
import { LANGS, plural, tr, useLang } from '../../src/i18n'
import { mediaUrl } from '../../src/config'
import { formatPrice } from '../../src/format'
import { prefs } from '../../src/prefs'
import { readCache, writeCache } from '../../src/cache'
import { onRetry } from '../../src/net'
import { colors, font } from '../../src/theme'
import { useTabInset } from '../../src/tabInset'

const rsd = (n: number) => `${String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00A0')}\u00A0RSD`

/**
 * Профиль — как на сайте: заголовок с колокольчиком; «Укажите телефон…»; карточка профиля (имя, «Частное лицо ·
 * отзывы», правка, «Подтвердить личность»); «N на проверке ›»; три плитки (объявлений ›, просмотров, в избранном);
 * баланс (полоса «деньги / бонусы» и две плитки); меню со значками в зелёных квадратах. Размеры — из стилей сайта.
 */
export default function Profile() {
  const tabInset = useTabInset()
  const { user, ready, token, signOut } = useAuth()
  const { lang, setLang } = useLang()
  const { notices } = useChats()
  const [items, setItems] = useState<MyListing[] | null>(null)
  const [bal, setBal] = useState<{ balance?: number; money?: number; bonus?: number; payments_enabled?: boolean } | null>(null)
  const [pub, setPub] = useState<Seller | null>(null)
  const [forYou, setForYou] = useState<FeedItem[]>([])
  const [phoneHidden, setPhoneHidden] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [waiting, setWaiting] = useState(0)
  const [verify, setVerify] = useState<{ status: string; reason?: string | null } | null>(null)
  const [verifying, setVerifying] = useState(false)

  useEffect(() => { prefs.get('plonk_phone_hint').then((v) => setPhoneHidden(v === 'hidden')) }, [])

  const load = useCallback(async () => {
    if (!token || !user) return
    const cached = await readCache<{ items: MyListing[]; bal: typeof bal; pub: Seller }>('profile')
    if (cached) { setItems((v) => v ?? cached.items); setBal((v) => v ?? cached.bal); setPub((v) => v ?? cached.pub) }
    const [l, b, s] = await Promise.allSettled([myListings(token), fetchBalance(token), sellerProfile(user.id)])
    if (l.status === 'fulfilled') setItems(l.value.items)
    if (b.status === 'fulfilled') setBal(b.value as typeof bal)
    if (s.status === 'fulfilled') setPub(s.value)
    forYouList(token).then((r) => setForYou((r.items ?? r as unknown as FeedItem[]).slice(0, 12))).catch(() => {})
    if (l.status === 'fulfilled' && b.status === 'fulfilled' && s.status === 'fulfilled') writeCache('profile', { items: l.value.items, bal: b.value, pub: s.value })
    waitingReviews(token).then((r) => setWaiting(r.items.length)).catch(() => {})
    verificationStatus(token).then(setVerify).catch(() => {})
  }, [token, user])
  useFocusEffect(useCallback(() => { load() }, [load]))
  useEffect(() => onRetry(() => { load() }), [load])

  const langRow = (
    <View style={[styles.row, styles.rowLast]}>
      <View style={styles.rowIcon}><Icon name="globe" size={17} color={colors.primary} /></View>
      <Text style={styles.rowText}>{tr('Язык')}</Text>
      {/* обёртка: у переключателя alignSelf flex-start (для колонок) — в строке он прижимался к верху */}
      <View style={{ alignSelf: 'center' }}><Segmented options={LANGS} value={lang} onChange={setLang} /></View>
    </View>
  )

  if (!ready) return <SafeAreaView style={[styles.page, styles.center]}><ActivityIndicator color={colors.primary} /></SafeAreaView>
  if (!user) {
    return (
      <SafeAreaView style={[styles.page, styles.center]} edges={['top']}>
        <View style={styles.circle}><Icon name="user" size={30} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>{tr('Войдите в PLONK')}</Text>
        <Text style={styles.text}>{tr('Чтобы сохранять объявления, писать продавцам и размещать свои.')}</Text>
        <Pressable style={styles.cta} onPress={() => router.push('/login')}><Text style={styles.ctaText}>{tr('Войти')}</Text></Pressable>
      </SafeAreaView>
    )
  }

  const name = user.display_name || user.email?.split('@')[0] || tr('Профиль')
  const all = items ?? []
  const pending = all.filter((i) => i.status === 'pending_moderation').length
  // Как на сайте: в плитках — только активные объявления
  const active = all.filter((i) => i.status === 'active')
  const views = active.reduce((n, i) => n + (i.views_count ?? 0), 0)
  const favs = active.reduce((n, i) => n + (i.favorites_count ?? 0), 0)
  const money = bal?.money ?? 0
  const bonus = bal?.bonus ?? 0
  const total = Math.max(money + bonus, 1)
  const hasPhone = !!(user as unknown as { phone?: string | null }).phone
  const rating = (pub?.rating_count ?? 0) > 0
    ? tr('★ {avg} · отзывов: {n}', { avg: (pub?.rating_avg ?? 0).toFixed(1).replace('.', ','), n: pub?.rating_count ?? 0 })
    : tr('Пока без отзывов')

  const part = (kind: 'money' | 'bonus', amount: number) => {
    const zero = amount <= 0
    const tone = zero ? styles.partZero : kind === 'money' ? styles.partMoney : styles.partBonus
    const ink = zero ? colors.muted : kind === 'money' ? colors.primaryDeep : '#A2401D'
    return (
      <View style={[styles.part, tone]}>
        <View style={styles.partTop}>
          <Icon name={kind === 'money' ? 'wallet' : 'gift'} size={15} color={zero ? colors.muted : kind === 'money' ? colors.primary : colors.accent} />
          <Text style={[styles.partLabel, { color: ink }]}>{tr(kind === 'money' ? 'Деньги' : 'Бонусы')}</Text>
        </View>
        <Text style={[styles.partAmount, { color: zero ? colors.muted : ink }]}>{rsd(amount)}</Text>
        <Text style={[styles.partNote, { color: ink }]}>{tr(kind === 'money' ? 'внесено вами' : 'только на продвижение')}</Text>
      </View>
    )
  }

  const row = (icon: string, label: string, onPress: () => void, badge?: number, last?: boolean) => (
    <Pressable style={[styles.row, last && styles.rowLast]} onPress={onPress} accessibilityRole="button">
      <View style={styles.rowIcon}><Icon name={icon} size={17} color={colors.primary} /></View>
      <Text style={styles.rowText}>{tr(label)}</Text>
      {!!badge && <View style={styles.badge}><Text style={styles.badgeText}>{badge > 9 ? '9+' : badge}</Text></View>}
      <Icon name="forward" size={16} color={colors.muted} />
    </Pressable>
  )

  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <ScrollView contentContainerStyle={{ paddingBottom: 32 + tabInset }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} tintColor={colors.primary} colors={[colors.primary]} />}>
        <View style={styles.header}>
          <Text style={styles.h1}>{tr('Профиль')}</Text>
          <Pressable onPress={() => router.push('/notifications')} hitSlop={8} style={styles.bell} accessibilityLabel={tr('Уведомления')}>
            <Icon name="bell" size={23} color={colors.ink} />
            {notices > 0 && <View style={styles.bellDot} />}
          </Pressable>
        </View>

        {!hasPhone && !phoneHidden && (
          <View style={styles.hint}>
            <Text style={styles.hintText}>{tr('Укажите телефон — покупатели смогут звонить вам напрямую')}</Text>
            <Pressable style={styles.hintBtn} onPress={() => router.push('/profile-edit')}><Text style={styles.hintBtnText}>{tr('Указать')}</Text></Pressable>
            <Pressable onPress={() => { setPhoneHidden(true); prefs.set('plonk_phone_hint', 'hidden') }} hitSlop={8} accessibilityLabel={tr('Закрыть')}>
              <Icon name="close" size={15} color="#8A6A1F" />
            </Pressable>
          </View>
        )}

        <View style={styles.card}>
          <View style={styles.avatar}><Text style={styles.avatarLetter}>{name.slice(0, 1).toUpperCase()}</Text></View>
          <View style={styles.cardBody}>
            <Text style={styles.cardName}>{name}</Text>
            <Text style={styles.cardMeta}>{tr(pub?.is_company ? 'Компания' : 'Частное лицо')}  ·  {rating}</Text>
            {/* Подтверждение личности — сразу открываем страницу сервиса проверки; статус обновится при возвращении */}
            {pub && !pub.document_verified && verify?.status === 'pending' && (
              <View style={styles.verifyPending}><Text style={styles.verifyPendingText}>{tr('Проверка личности идёт')}</Text></View>
            )}
            {pub && !pub.document_verified && verify?.status !== 'pending' && verify?.status !== 'verified' && (
              <>
                {verify?.status === 'rejected' && !!verify.reason && <Text style={styles.verifyReason}>{tr('Проверку не прошли: {r}', { r: verify.reason })}</Text>}
                <Pressable style={[styles.verify, verifying && { opacity: 0.6 }]} disabled={verifying} onPress={async () => {
                  if (!token) return
                  setVerifying(true)
                  try {
                    const r = await startVerification(token)
                    if (r.url) await Linking.openURL(r.url)
                    else Alert.alert(tr('Заявка принята'), tr('Мы свяжемся с вами, чтобы подтвердить личность.'))
                    setVerify({ status: 'pending' })
                  } catch (e) {
                    // Свой текст на каждый ответ сервера; «проверьте интернет» — только когда сети и правда нет
                    const code = e instanceof ApiError ? e.message : ''
                    if (code === 'already_pending') setVerify({ status: 'pending' })
                    else if (code === 'already_verified') setVerify({ status: 'verified' })
                    else if (code === 'verification_not_configured' || code === 'verification_unavailable') Alert.alert(tr('Не получилось'), tr('Сервис проверки личности сейчас не отвечает. Попробуйте позже — мы уже знаем о проблеме.'))
                    else if (e instanceof ApiError) Alert.alert(tr('Не получилось'), tr('Ошибка сервера ({code}). Попробуйте позже.', { code: code || String(e.status) }))
                    else Alert.alert(tr('Не получилось'), tr('Проверьте интернет и попробуйте ещё раз.'))
                  } finally { setVerifying(false) }
                }}>
                  <Icon name="shield" size={15} color="#fff" />
                  <Text style={styles.verifyText}>{tr(verify?.status === 'rejected' ? 'Пройти ещё раз' : 'Подтвердить личность')}</Text>
                </Pressable>
              </>
            )}
          </View>
          <Pressable style={styles.edit} onPress={() => router.push('/profile-edit')} accessibilityLabel={tr('Редактировать')}>
            <Icon name="edit" size={16} color={colors.inkSoft} />
          </Pressable>
        </View>

        {pending > 0 && (
          <Pressable style={styles.pending} onPress={() => router.push({ pathname: '/my', params: { tab: 'pending' } })}>
            <View style={styles.pendingDot} />
            <Text style={styles.pendingText}>{tr('{n} {word} на проверке', { n: pending, word: plural(pending, { ru: ['объявление', 'объявления', 'объявлений'], en: ['listing', 'listings'], sr: ['oglas', 'oglasa', 'oglasa'] }) })}</Text>
            <Icon name="forward" size={15} color="#8A6A1F" />
          </Pressable>
        )}

        <View style={styles.stats}>
          <Pressable style={styles.stat} onPress={() => router.push('/my')}>
            <View style={{ flex: 1 }}>
              <Text style={styles.statValue}>{items ? active.length : '—'}</Text>
              <Text style={styles.statLabel}>{tr('объявлений')}</Text>
            </View>
            <Icon name="forward" size={15} color={colors.muted} />
          </Pressable>
          <View style={styles.stat}><View><Text style={styles.statValue}>{items ? views : '—'}</Text><Text style={styles.statLabel}>{tr('просмотров')}</Text></View></View>
          <View style={styles.stat}><View><Text style={styles.statValue}>{items ? favs : '—'}</Text><Text style={styles.statLabel}>{tr('в избранном')}</Text></View></View>
        </View>

        <View style={styles.balance}>
          <View style={styles.balanceTop}>
            <View>
              <Text style={styles.balanceLabel}>{tr('Баланс')}</Text>
              <Text style={styles.balanceValue}>{bal ? rsd(bal.balance ?? 0) : '—'}</Text>
            </View>
            <Pressable style={[styles.topup, !bal?.payments_enabled && styles.topupOff]} disabled={!bal?.payments_enabled} onPress={() => Linking.openURL(`${SITE}/profile`)}>
              <Text style={[styles.topupText, !bal?.payments_enabled && { color: colors.muted }]}>{tr('Пополнить')}</Text>
            </Pressable>
          </View>
          <View style={styles.bar}>
            {money > 0 && <View style={{ flex: money / total, backgroundColor: colors.primary }} />}
            {bonus > 0 && <View style={{ flex: bonus / total, backgroundColor: colors.accent }} />}
          </View>
          <View style={styles.parts}>{part('money', money)}{part('bonus', bonus)}</View>
          {!bal?.payments_enabled && <Text style={styles.balanceNote}>{tr('Пополнение картой пока недоступно')}</Text>}
        </View>

        {/* PLONK 2.0: профиль — панель продавца: главные действия крупными плитками, как на сайте */}
        <View style={styles.actions}>
          {([['plus', 'Разместить', '/post', true], ['grid', 'Витрина', '/vitrina', false], ['video', 'Мои шопсы', '/shops/mine', false]] as const).map(([ic, label, href, dark]) => (
            <Pressable key={href} style={[styles.action, dark && { backgroundColor: colors.inverse }]} onPress={() => router.push(href as never)} accessibilityRole="button">
              <Icon name={ic} size={24} color={dark ? colors.onInverse : colors.ink} />
              <Text style={[styles.actionText, dark && { color: colors.onInverse }]}>{tr(label)}</Text>
            </Pressable>
          ))}
        </View>

        {/* Меню — как на сайте, в том же порядке: сохранённые поиски — в приложении, остальное — страницы сайта */}
        <View style={styles.menu}>
          {row('heart', 'Избранное', () => router.push('/favorites' as never))}
          {row('doc', 'Мои отклики', () => router.push('/jobs/my' as never))}
          {row('chat', 'Отклики на вакансии', () => router.push('/jobs' as never))}
          {row('invite', 'Пригласите друга', () => router.push('/invite'))}
          {waiting > 0 && row('star', 'Ждут отзыва', () => router.push('/reviews'), waiting)}
          {row('searchrow', 'Сохранённые поиски', () => router.push('/saved'))}
          {row('history', 'Вы смотрели', () => router.push('/history'))}
          {row('help', 'Написать в поддержку', () => router.push('/support'))}
          {row('volunteer', 'Волонтёрство', () => router.push('/volunteer'), undefined, true)}
        </View>

        {/* «Может быть интересно» — как на сайте: лента карточек (фото 132, цена, название) */}
        {forYou.length > 0 && (
          <View style={styles.forYou}>
            <Text style={styles.forYouTitle}>{tr('Может быть интересно')}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 10, paddingRight: 12 }}>
              {forYou.map((l) => {
                const ph = mediaUrl(l.cover_photo)
                return (
                  <Pressable key={l.id} style={styles.forYouCard} onPress={() => router.push(`/listing/${l.id}`)}>
                    <View style={styles.forYouPhoto}>{ph ? <Image source={{ uri: ph }} style={styles.forYouImg} contentFit="cover" /> : null}</View>
                    {(l.is_free || l.price != null)
                      ? <><Text style={styles.forYouPrice} numberOfLines={1}>{formatPrice(l.price, l.currency, l.is_free)}</Text><Text style={styles.forYouName} numberOfLines={2}>{l.title}</Text></>
                      : <Text style={[styles.forYouPrice, { fontSize: 13.5 }]} numberOfLines={2}>{l.title}</Text>}
                  </Pressable>
                )
              })}
            </ScrollView>
          </View>
        )}

        <Text style={styles.sectionTitle}>{tr('Настройки')}</Text>
        <View style={styles.menu}>
          {langRow}
          {row('lock', 'Заблокированные', () => router.push('/blocked'), undefined, true)}
        </View>

        <View style={styles.menu}>
          <Pressable style={[styles.row, styles.rowLast]} onPress={signOut} accessibilityRole="button">
            <View style={[styles.rowIcon, { backgroundColor: colors.dangerBg }]}><Icon name="logout" size={17} color="#B42318" /></View>
            <Text style={[styles.rowText, { color: colors.danger }]}>{tr('Выйти')}</Text>
          </Pressable>
        </View>

        {/* Удаление аккаунта — требование App Store; два подтверждения, объясняем, что именно удалится */}
        <Pressable style={styles.delete} hitSlop={6} onPress={() => Alert.alert(
          tr('Удалить аккаунт?'),
          tr('Объявления снимутся с публикации, избранное, сохранённые поиски и личные данные удалятся. Вернуть будет нельзя.'),
          [
            { text: tr('Отмена'), style: 'cancel' },
            { text: tr('Удалить'), style: 'destructive', onPress: () => Alert.alert(tr('Точно удалить?'), tr('Это последнее подтверждение.'), [
              { text: tr('Отмена'), style: 'cancel' },
              { text: tr('Удалить навсегда'), style: 'destructive', onPress: async () => {
                try { await deleteMe(token as string); await signOut(); router.replace('/') } catch { Alert.alert(tr('Не получилось'), tr('Проверьте интернет и попробуйте ещё раз.')) }
              } },
            ]) },
          ],
        )}>
          <Text style={styles.deleteText}>{tr('Удалить аккаунт')}</Text>
        </Pressable>

        {/* Подвал — как на сайте: то, что открывают раз в жизни */}
        <View style={styles.footer}>
          <View style={styles.footerLinks}>
            <Pressable onPress={() => Linking.openURL('https://t.me/Baraholka_Plonk')}><Text style={styles.footerLink}>{tr('Чат в Telegram')}</Text></Pressable>
            <Pressable onPress={() => Linking.openURL('https://t.me/Baraholka_plonk_bot')}><Text style={styles.footerLink}>{tr('Бот')}</Text></Pressable>
          </View>
          <View style={styles.footerLinks}>
            <Pressable onPress={() => router.push('/legal/rules')}><Text style={styles.footerLink}>{tr('Правила')}</Text></Pressable>
            <Pressable onPress={() => router.push('/legal/terms')}><Text style={styles.footerLink}>{tr('Условия')}</Text></Pressable>
            <Pressable onPress={() => router.push('/legal/privacy')}><Text style={styles.footerLink}>{tr('Конфиденциальность')}</Text></Pressable>
          </View>
          <Text style={styles.footerBrand}>plonk.rs</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: 8, marginHorizontal: 12, marginBottom: 10 },
  action: { flex: 1, height: 96, padding: 14, borderRadius: 22, backgroundColor: colors.surface, justifyContent: 'space-between', shadowColor: '#0F1512', shadowOpacity: 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 2 },
  actionText: { fontFamily: font[700], fontSize: 14, color: colors.ink },
  // как .for-you-* / .profile-section-title / .profile-footer сайта
  // отступы — как у соседних блоков профиля
  forYou: { gap: 10, marginLeft: 12, marginTop: 6 },
  forYouTitle: { fontSize: 16, fontFamily: font[800], letterSpacing: -0.2, color: colors.ink },
  forYouCard: { width: 132 },
  forYouPhoto: { width: 132, height: 132, borderRadius: 14, overflow: 'hidden', backgroundColor: colors.sunken },
  forYouImg: { width: 132, height: 132 },
  forYouPrice: { marginTop: 7, fontSize: 14.5, lineHeight: 18, fontFamily: font[800], color: colors.ink },
  forYouName: { marginTop: 2, fontSize: 12.5, lineHeight: 16, fontFamily: font[600], color: colors.muted },
  sectionTitle: { fontSize: 12, fontFamily: font[700], letterSpacing: 0.5, textTransform: 'uppercase', color: colors.muted, paddingHorizontal: 16, marginTop: 14, marginBottom: 2 },
  footer: { alignItems: 'center', paddingTop: 12, paddingBottom: 6, gap: 10 },
  footerLinks: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', columnGap: 18, rowGap: 6 },
  footerLink: { fontSize: 12.5, fontFamily: font[600], color: colors.muted },
  footerBrand: { fontSize: 12, fontFamily: font[800], letterSpacing: 0.3, color: '#C3C8C4' },
  page: { flex: 1, backgroundColor: colors.bg },
  center: { alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontSize: 15, fontFamily: font[400], lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  cta: { marginTop: 10, height: 50, paddingHorizontal: 40, borderRadius: 14, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 10, paddingBottom: 12 },
  h1: { fontSize: 22, fontFamily: font[800], letterSpacing: -0.3, color: colors.ink },
  bell: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  bellDot: { position: 'absolute', top: 8, right: 9, width: 9, height: 9, borderRadius: 5, backgroundColor: colors.accent, borderWidth: 1.5, borderColor: colors.bg },
  hint: { flexDirection: 'row', alignItems: 'center', gap: 10, marginHorizontal: 12, marginBottom: 12, padding: 12, borderRadius: 14, backgroundColor: colors.warmBg },
  hintText: { flex: 1, fontSize: 13, lineHeight: 18, fontFamily: font[700], color: '#8A6A1F' },
  hintBtn: { height: 32, paddingHorizontal: 12, borderRadius: 9, backgroundColor: '#F2E2BF', justifyContent: 'center' },
  hintBtnText: { fontSize: 13, fontFamily: font[800], color: '#6B5016' },
  // .profile-card: отступы 0 12 12, внутри 14, скругление 18, аватар 56, имя 17/800, строка 12,5/600
  card: { flexDirection: 'row', alignItems: 'flex-start', gap: 13, marginHorizontal: 12, marginBottom: 12, padding: 14, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#7C6CF0', alignItems: 'center', justifyContent: 'center' },
  avatarLetter: { color: '#fff', fontSize: 21, fontFamily: font[800] },
  cardBody: { flex: 1, paddingRight: 34 },
  cardName: { fontSize: 17, lineHeight: 21, letterSpacing: -0.3, fontFamily: font[800], color: colors.ink },
  cardMeta: { marginTop: 3, fontSize: 12.5, fontFamily: font[600], color: colors.muted },
  verify: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 10, height: 34, paddingHorizontal: 12, borderRadius: 10, backgroundColor: colors.ink },
  verifyPending: { alignSelf: 'flex-start', marginTop: 10, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 9, backgroundColor: colors.warmBg },
  verifyPendingText: { fontSize: 12.5, fontFamily: font[800], color: '#8A6A1F' },
  verifyReason: { marginTop: 8, fontSize: 12.5, lineHeight: 17, fontFamily: font[600], color: colors.danger },
  verifyText: { color: '#fff', fontSize: 13, fontFamily: font[800] },
  edit: { position: 'absolute', top: 12, right: 12, width: 32, height: 32, borderRadius: 10, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  pending: { flexDirection: 'row', alignItems: 'center', gap: 9, marginHorizontal: 12, marginBottom: 12, paddingHorizontal: 14, height: 46, borderRadius: 14, backgroundColor: colors.warmBg },
  pendingDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#C08A1E' },
  pendingText: { flex: 1, fontSize: 14, fontFamily: font[800], color: '#8A6A1F' },
  stats: { flexDirection: 'row', gap: 8, marginHorizontal: 12, marginBottom: 12 },
  stat: { flex: 1, flexDirection: 'row', alignItems: 'center', minHeight: 62, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  statValue: { fontSize: 18, fontFamily: font[800], color: colors.ink },
  statLabel: { fontSize: 11.5, fontFamily: font[600], color: colors.muted, marginTop: 1 },
  // .balance-card: отступы 0 12 10, внутри 16/14/14, скругление 18; .balance-bar 10, .balance-part 10/12/11, скругление 14
  balance: { marginHorizontal: 12, marginBottom: 10, paddingTop: 16, paddingHorizontal: 14, paddingBottom: 14, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  balanceTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  balanceLabel: { fontSize: 13, fontFamily: font[700], color: colors.muted },
  balanceValue: { fontSize: 26, fontFamily: font[800], letterSpacing: -0.3, color: colors.ink, marginTop: 2 },
  topup: { height: 38, paddingHorizontal: 14, borderRadius: 11, backgroundColor: colors.primary, justifyContent: 'center' },
  topupOff: { backgroundColor: colors.sunken },
  topupText: { color: '#fff', fontSize: 14, fontFamily: font[800] },
  bar: { flexDirection: 'row', gap: 3, height: 10, marginTop: 12, borderRadius: 6, overflow: 'hidden', backgroundColor: colors.sunken },
  parts: { flexDirection: 'row', gap: 8, marginTop: 10 },
  part: { flex: 1, paddingTop: 10, paddingHorizontal: 12, paddingBottom: 11, borderRadius: 14 },
  partMoney: { backgroundColor: colors.primarySoft },
  partBonus: { backgroundColor: colors.accentSoft },
  partZero: { backgroundColor: colors.sunken },
  partTop: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  partLabel: { fontSize: 12, lineHeight: 16, fontFamily: font[700] },
  partAmount: { marginTop: 4, fontSize: 18, lineHeight: 24, fontFamily: font[800], letterSpacing: -0.2 },
  partNote: { marginTop: 2, fontSize: 11.5, lineHeight: 15, fontFamily: font[500], opacity: 0.82 },
  balanceNote: { marginTop: 10, fontSize: 12, fontFamily: font[500], color: colors.muted, textAlign: 'center' },
  menu: { marginHorizontal: 12, marginBottom: 10, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 14, minHeight: 56, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  rowLast: { borderBottomWidth: 0 },
  rowIcon: { width: 32, height: 32, borderRadius: 10, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  rowText: { flex: 1, fontSize: 15.5, fontFamily: font[700], color: colors.ink },
  delete: { alignSelf: 'center', marginTop: 6, paddingVertical: 10, paddingHorizontal: 14 },
  deleteText: { fontSize: 13.5, fontFamily: font[700], color: colors.muted },
  badge: { minWidth: 20, height: 20, borderRadius: 10, paddingHorizontal: 6, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  badgeText: { color: '#fff', fontSize: 11, fontFamily: font[800] },
})
