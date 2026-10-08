import * as Haptics from 'expo-haptics'
import * as Clipboard from 'expo-clipboard'
import { success, tap } from '../../src/haptics'
import { tr } from '../../src/i18n'
import { Image } from 'expo-image'
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, Alert, AppState, FlatList, Modal, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View, Linking, ScrollView } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { allowCall, blockChat, cancelReservation, type Chat, chatInfo, chatMessages, chatWsUrl, declineCall, markChatRead, type Message, requestCall, reserveListing, respondOffer, revokeCall, sendMessage, sendOffer, isOffer, reactMessage, translateMessage, deleteMessage, editMessage } from '../../src/api'
import Icon from '../../src/components/Icon'
import { VoiceButton, VoicePlayer } from '../../src/components/Voice'
import TeamLetter from '../../src/components/TeamLetter'
import Sheet, { SheetAction } from '../../src/components/Sheet'
import { useAuth } from '../../src/auth'
import { useChats } from '../../src/chats'
import { mediaUrl } from '../../src/config'
import { formatPrice, parseTime, plainText } from '../../src/format'
import { colors, font } from '../../src/theme'

const hhmm = (iso: string) => { const d = parseTime(iso); return d ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : '' }

/**
 * Переписка: шапка с собеседником и объявлением (нажатие — открыть объявление), сообщения пузырями (мои справа,
 * зелёные), служебные — по центру. Новые подтягиваются раз в 5 секунд, пока чат открыт; отправленное появляется
 * сразу, не дожидаясь сервера, а при ошибке — помечается «Не отправлено, нажмите, чтобы повторить».
 */
const QUICK_BUYER = ['Ещё продаётся?', 'Торг возможен?', 'Когда можно посмотреть?', 'Где забрать?']
const QUICK_SELLER = ['Да, продаётся', 'Можно посмотреть вечером', 'Цена окончательная']

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const chatId = String(id)
  const insets = useSafeAreaInsets()
  const { token, user } = useAuth()
  const { refresh: refreshList, chats } = useChats()
  const [chat, setChat] = useState<Chat | null>(null)
  const [msgs, setMsgs] = useState<(Message & { pending?: boolean; failed?: boolean })[] | null>(null)
  // как на сайте: долгое нажатие на сообщение — реакции, «Ответить», «Перевести», «Копировать»
  const [replyTo, setReplyTo] = useState<Message | null>(null)
  const [menuFor, setMenuFor] = useState<Message | null>(null)
  const [translated, setTranslated] = useState<Record<string, string>>({})
  const [voiceNote, setVoiceNote] = useState('')
  useEffect(() => { if (!voiceNote) return; const t = setTimeout(() => setVoiceNote(''), 2600); return () => clearTimeout(t) }, [voiceNote])
  const [text, setText] = useState('')
  const lastCount = useRef(0)
  const [menu, setMenu] = useState(false)
  const [offerOpen, setOfferOpen] = useState(false)
  const [offer, setOffer] = useState('')
  const [blocked, setBlocked] = useState(false)
  const [typing, setTyping] = useState(false)
  const [callDismissed, setCallDismissed] = useState(false)
  const [offerPillDismissed, setOfferPillDismissed] = useState(false)
  const [busy, setBusy] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const typingTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const lastTypingSent = useRef(0)

  const load = useCallback(async () => {
    if (!token) return
    try {
      const list = await chatMessages(token, chatId)
      setMsgs((prev) => [...list, ...(prev ?? []).filter((m) => m.pending || m.failed)])
      if (list.length !== lastCount.current) {
        lastCount.current = list.length
        markChatRead(token, chatId).then(() => refreshList()).catch(() => {})
      }
    } catch { /* следующий опрос попробует снова */ }
  }, [token, chatId, refreshList])

  // Имя собеседника и объявление: из отдельного запроса, а чего в нём нет — из списка переписок
  const fromList = chats?.find((c) => c.id === chatId) ?? null
  const refreshInfo = useCallback(() => { if (token) chatInfo(token, chatId).then(setChat).catch(() => {}) }, [token, chatId])
  useEffect(() => { refreshInfo() }, [refreshInfo])
  // новый запрос звонка — плашку показываем снова, даже если прошлую закрывали
  useEffect(() => { if (chat?.call_request_pending) setCallDismissed(false) }, [chat?.call_request_pending])

  // Постоянное соединение — как на сайте: новые сообщения сразу и «… печатает…»; обрыв — переподключаемся сами
  useEffect(() => {
    if (!token) return undefined
    let ws: WebSocket | null = null
    let closed = false
    let retry: ReturnType<typeof setTimeout> | undefined
    const connect = () => {
      ws = new WebSocket(chatWsUrl(token, chatId))
      wsRef.current = ws
      ws.onmessage = (e) => {
        let d: { type?: string; message?: Message; user_id?: string }
        try { d = JSON.parse(String(e.data)) } catch { return }
        if (d.type === 'message' && d.message) {
          const m = d.message
          setMsgs((prev) => (prev?.some((x) => x.id === m.id) ? prev : [...(prev ?? []).filter((x) => !(x.pending && x.text === m.text && m.sender_id === user?.id)), m]))
          if (m.sender_id !== user?.id) { setTyping(false); markChatRead(token, chatId).then(() => refreshList()).catch(() => {}) }
          refreshInfo()
        } else if (d.type === 'message_edited' && (d as { message_id?: string }).message_id) {
          const e = d as unknown as { message_id: string; text: string; edited_at: string }
          setMsgs((prev) => (prev ?? []).map((x) => (x.id === e.message_id ? { ...x, text: e.text, edited_at: e.edited_at } : x)))
        } else if (d.type === 'message_deleted' && (d as { message_id?: string }).message_id) {
          const mid = (d as unknown as { message_id: string }).message_id
          setMsgs((prev) => (prev ?? []).map((x) => (x.id === mid ? { ...x, kind: 'deleted', text: null, audio_url: null, reactions: null } : x)))
        } else if (d.type === 'reaction' && (d as { message_id?: string }).message_id) {
          const rd = d as unknown as { message_id: string; reactions: Record<string, string[]> }
          setMsgs((prev) => (prev ?? []).map((x) => (x.id === rd.message_id ? { ...x, reactions: rd.reactions } : x)))
        } else if (d.type === 'typing' && d.user_id !== user?.id) {
          setTyping(true)
          clearTimeout(typingTimer.current)
          typingTimer.current = setTimeout(() => setTyping(false), 3000)
        } else if (d.type === 'typing_stop' && d.user_id !== user?.id) setTyping(false)
      }
      ws.onclose = () => { if (!closed) retry = setTimeout(connect, 3000) }
    }
    connect()
    return () => { closed = true; clearTimeout(retry); clearTimeout(typingTimer.current); ws?.close(); wsRef.current = null }
  }, [token, chatId, user?.id, refreshInfo, refreshList])
  const sendTyping = (v: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== 1) return
    if (!v) { ws.send('typing_stop'); return }
    if (Date.now() - lastTypingSent.current > 2000) { lastTypingSent.current = Date.now(); ws.send('typing') }
  }
  const info: Chat | null = chat || fromList ? { ...(fromList ?? {}), ...Object.fromEntries(Object.entries(chat ?? {}).filter(([, v]) => v != null)) } as Chat : null

  useFocusEffect(useCallback(() => {
    load()
    const timer = setInterval(() => { if (AppState.currentState === 'active') { load(); refreshInfo() } }, wsRef.current?.readyState === 1 ? 15000 : 5000)
    return () => clearInterval(timer)
  }, [load, refreshInfo]))

  const send = async (body: string, retryId?: string) => {
    const value = body.trim()
    if (!value || !token) return
    tap()
    const localId = retryId ?? `local-${Date.now()}`
    const optimistic = { id: localId, kind: 'text', text: value, sender_id: user?.id, created_at: new Date().toISOString(), pending: true }
    setMsgs((prev) => [...(prev ?? []).filter((m) => m.id !== localId), optimistic])
    if (!retryId) setText('')
    const replyId = retryId ? null : replyTo?.id ?? null
    if (!retryId) setReplyTo(null)
    try {
      await sendMessage(token, chatId, value, replyId)
      setMsgs((prev) => (prev ?? []).filter((m) => m.id !== localId))
      await load()
      refreshList()
    } catch {
      setMsgs((prev) => (prev ?? []).map((m) => (m.id === localId ? { ...m, pending: false, failed: true } : m)))
    }
  }

  const mine = (m: Message) => !!user && m.sender_id === user.id
  // Служебные записи без текста (карточка объявления и т.п.) — не рисуем пустым пузырём
  const data = [...(msgs ?? [])].filter((m) => isOffer(m.kind) || m.kind === 'safety_note' || plainText(m.text)).reverse()
  const photo = mediaUrl(info?.listing_photo)
  const title = info?.is_team ? tr('Команда PLONK') : (info?.other_name || tr('Переписка'))

  const bubble = ({ item }: { item: Message & { pending?: boolean; failed?: boolean } }) => {
    if (item.kind === 'safety_note') {
      return (
        <View style={styles.safety}>
          <Icon name="shield" size={17} color={colors.primary} />
          <Text style={styles.safetyText}>{tr('Встречайтесь лично и передавайте деньги при получении вещи. Просьба перевести задаток вперёд — самый частый способ обмана.')}</Text>
        </View>
      )
    }
    if (isOffer(item.kind)) {
      const me = mine(item)
      const status = item.offer_status === 'accepted' ? tr('Принято') : item.offer_status === 'declined' ? tr('Отклонено') : me ? tr('Ждёт ответа продавца') : ''
      return (
        <View style={[styles.bubbleRow, me && styles.bubbleRowMe]}>
          <View style={styles.offer}>
            <Text style={styles.offerTitle}>{tr('Предложение:')} {formatPrice(item.offer_price ?? null, info?.currency)}</Text>
            {!!status && <Text style={[styles.offerStatus, item.offer_status === 'accepted' && { color: colors.primaryDeep }]}>{status}</Text>}
            {!me && (!item.offer_status || item.offer_status === 'pending') && (
              <View style={styles.offerBtns}>
                <Pressable style={[styles.offerBtn, styles.offerYes]} onPress={async () => { if (token) { await respondOffer(token, chatId, item.id, 'accepted').catch(() => {}); load() } }}><Text style={styles.offerYesText}>{tr('Принять')}</Text></Pressable>
                <Pressable style={styles.offerBtn} onPress={async () => { if (token) { await respondOffer(token, chatId, item.id, 'declined').catch(() => {}); load() } }}><Text style={styles.offerNoText}>{tr('Отклонить')}</Text></Pressable>
              </View>
            )}
          </View>
        </View>
      )
    }
    if (item.kind === 'team' || item.kind === 'system') {
      // письмо команды — разметка как на сайте (заголовки, пункты, кнопки, ссылки), по левому краю
      return <View style={styles.teamBubble}><TeamLetter text={item.text || ''} /></View>
    }
    const me = mine(item)
    const body = isOffer(item.kind)
      ? tr('Предлагаю {price}', { price: formatPrice(item.offer_price ?? null, info?.currency) }) + (item.offer_status === 'accepted' ? tr(' — принято') : item.offer_status === 'declined' ? tr(' — отклонено') : '')
      : plainText(item.text)
    return (
      <Pressable onPress={item.failed ? () => send(item.text || '', item.id) : undefined}
        onLongPress={item.pending || item.failed ? undefined : () => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {}); setMenuFor(item) }}
        delayLongPress={420} style={[styles.bubbleRow, me && styles.bubbleRowMe]}>
        <View style={[styles.bubble, me ? styles.bubbleMe : styles.bubbleThem, item.failed && styles.bubbleFailed]}>
          {!!item.reply_text && (
            <View style={[styles.quote, me && styles.quoteMe]}>
              <Text style={[styles.quoteWho, me && styles.bubbleTextMe]} numberOfLines={1}>{item.reply_sender_id === user?.id ? tr('Вы') : (info?.other_name || tr('Собеседник'))}</Text>
              <Text style={[styles.quoteText, me && styles.bubbleTextMe]} numberOfLines={1}>{item.reply_text}</Text>
            </View>
          )}
          {item.kind === 'deleted' ? <Text style={[styles.bubbleText, me && styles.bubbleTextMe, { fontStyle: 'italic', opacity: 0.65 }]}>{tr('Сообщение удалено')}</Text>
            : item.audio_url ? <VoicePlayer url={item.audio_url} seconds={item.audio_seconds} mine={me} /> : <Text style={[styles.bubbleText, me && styles.bubbleTextMe]}>{body}{!!(item as { edited_at?: string }).edited_at && <Text style={{ fontSize: 11, opacity: 0.55, fontStyle: 'italic' }}>{'  '}{tr('изменено')}</Text>}</Text>}
          {!!translated[item.id] && <Text style={[styles.translated, me && styles.bubbleTextMe]}>{translated[item.id]}</Text>}
          {isOffer(item.kind) && !me && (!item.offer_status || item.offer_status === 'pending') && (
            <View style={styles.offerBtns}>
              <Pressable style={[styles.offerBtn, styles.offerYes]} onPress={async () => { if (token) { await respondOffer(token, chatId, item.id, 'accepted').catch(() => {}); load() } }}><Text style={styles.offerYesText}>{tr('Принять')}</Text></Pressable>
              <Pressable style={styles.offerBtn} onPress={async () => { if (token) { await respondOffer(token, chatId, item.id, 'declined').catch(() => {}); load() } }}><Text style={styles.offerNoText}>{tr('Отклонить')}</Text></Pressable>
            </View>
          )}
          <Text style={[styles.meta, me && styles.metaMe]}>
            {item.failed ? tr('Не отправлено — нажмите, чтобы повторить') : item.pending ? tr('Отправляется…') : hhmm(item.created_at)}
          </Text>
          {!!item.reactions && Object.keys(item.reactions).length > 0 && (
            <View style={[styles.reacts, me && { alignSelf: 'flex-end' }]}>
              {Object.entries(item.reactions).map(([e, who]) => (
                <Pressable key={e} style={[styles.react, who.includes(user?.id || '') && styles.reactMine]} onPress={() => token && reactMessage(token, chatId, item.id, e).then((r) => setMsgs((prev) => (prev ?? []).map((x) => (x.id === item.id ? { ...x, reactions: r.reactions } : x)))).catch(() => {})}>
                  <Text style={styles.reactText}>{e}{who.length > 1 ? ` ${who.length}` : ''}</Text>
                </Pressable>
              ))}
            </View>
          )}
        </View>
      </Pressable>
    )
  }

  const isSeller = info?.is_seller ?? (!!user && info?.seller?.id === user.id)
  const act = async (fn: () => Promise<unknown>) => { setBusy(true); try { await fn() } catch { /* состояние обновится с сервера */ } finally { setBusy(false); refreshInfo() } }
  const lastMine = !!msgs?.length && msgs[msgs.length - 1].sender_id === user?.id
  const quick = !info || info.is_team || !info.listing_id || text || lastMine ? [] : isSeller ? QUICK_SELLER : QUICK_BUYER
  const offerPill = !isSeller && !info?.is_team && !!info?.listing_price_negotiable && !offerPillDismissed && !info?.blocked_by_them

  return (
    <KeyboardAvoidingView style={styles.page} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={[styles.head, { paddingTop: insets.top + 6 }]}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/chats'))} hitSlop={10} style={styles.backCircle} accessibilityLabel={tr('Назад')}>
          <Icon name="back" size={20} color={colors.ink} />
        </Pressable>
        <Text style={[styles.headName, { flex: 1 }]} numberOfLines={1}>{title}</Text>
        {!isSeller && info?.phone_revealed && !!info?.other_phone && (
          <Pressable onPress={() => Linking.openURL(`tel:${info.other_phone}`)} hitSlop={8} style={styles.callBtn} accessibilityLabel={tr('Позвонить: {phone}', { phone: info.other_phone })}>
            <Icon name="phone" size={18} color={colors.primaryDeep} />
          </Pressable>
        )}
        {!info?.is_team && (
          <Pressable onPress={() => setMenu(true)} hitSlop={8} style={styles.back} accessibilityLabel={tr('Ещё')}>
            <Icon name="dots" size={20} color={colors.ink} />
          </Pressable>
        )}
      </View>
      {/* Объявление — отдельной строкой под шапкой, как на сайте: фото, название, цена зелёным, стрелка */}
      {!!info?.listing_title && (
        <Pressable style={styles.strip} onPress={() => info?.listing_id && router.push(`/listing/${info.listing_id}`)} accessibilityRole="button">
          <View style={styles.headThumb}>{photo ? <Image source={{ uri: photo }} style={styles.headThumbImg} contentFit="cover" /> : null}</View>
          <View style={{ flex: 1 }}>
            <Text style={styles.stripTitle} numberOfLines={1}>{info.listing_title}</Text>
            <Text style={styles.stripPrice}>{info.listing_price != null ? formatPrice(info.listing_price, info.currency) : ''}{info.listing_sold ? <Text style={styles.stripState}>{'  · '}{tr('продано')}</Text> : info.listing_archived ? <Text style={styles.stripState}>{'  · '}{tr('снято')}</Text> : null}</Text>
          </View>
          <Icon name="forward" size={16} color={colors.muted} />
        </Pressable>
      )}

      {!!info?.call_request_pending && !callDismissed && (
        <View style={styles.callToast}>
          <Icon name="phone" size={17} color={colors.primaryDeep} />
          <Text style={styles.callToastText}>{tr(isSeller ? 'Просят разрешить звонок' : 'Звонок запрошен — ждём ответа')}</Text>
          {isSeller ? (
            <View style={styles.callToastBtns}>
              <Pressable style={[styles.callYes, busy && { opacity: 0.6 }]} disabled={busy} onPress={() => token && act(() => allowCall(token, chatId))}><Text style={styles.callYesText}>{tr('Да')}</Text></Pressable>
              <Pressable style={styles.callNo} disabled={busy} onPress={() => token && act(() => declineCall(token, chatId))}><Text style={styles.callNoText}>{tr('Нет')}</Text></Pressable>
            </View>
          ) : (
            <Pressable onPress={() => setCallDismissed(true)} hitSlop={8} accessibilityLabel={tr('Закрыть')}><Icon name="close" size={14} color={colors.muted} /></Pressable>
          )}
        </View>
      )}
      {!!info?.listing_is_reserved && (
        <View style={styles.reserved}><Text style={styles.reservedText}>{tr(isSeller ? 'Забронировано вами на 48 часов' : info.listing_reserved_for_me ? 'Продавец забронировал это для вас' : 'Объявление забронировано другим покупателем')}</Text></View>
      )}

      <Sheet visible={menu} onClose={() => setMenu(false)}>
        {!isSeller && info?.seller_has_phone && !info?.phone_revealed && (info?.call_request_pending
          ? <SheetAction label={tr('Звонок запрошен — ждём ответа')} icon={<Icon name="phone" size={20} color={colors.muted} />} onPress={() => setMenu(false)} />
          : <SheetAction label={tr('Запросить звонок')} icon={<Icon name="phone" size={20} color={colors.ink} />} onPress={() => { setMenu(false); if (token) act(() => requestCall(token, chatId)) }} />)}
        {isSeller && info?.seller_has_phone && !info?.phone_revealed && <SheetAction label={tr('Разрешить звонок')} icon={<Icon name="phone" size={20} color={colors.ink} />} onPress={() => { setMenu(false); if (token) act(() => allowCall(token, chatId)) }} />}
        {isSeller && info?.phone_revealed && <SheetAction label={tr('Запретить звонок')} icon={<Icon name="phone" size={20} color={colors.ink} />} onPress={() => { setMenu(false); if (token) act(() => revokeCall(token, chatId)) }} />}
        {isSeller && !!info?.listing_id && !info?.listing_sold && !info?.listing_archived && !!info?.buyer?.id && (info?.listing_is_reserved
          ? <SheetAction label={tr('Снять бронь')} icon={<Icon name="lock" size={20} color={colors.ink} />} onPress={() => { setMenu(false); if (token && info?.listing_id) act(() => cancelReservation(token, info.listing_id as string)) }} />
          : <SheetAction label={tr('Забронировать для покупателя')} icon={<Icon name="lock" size={20} color={colors.ink} />} onPress={() => { setMenu(false); if (token && info?.listing_id && info?.buyer?.id) act(() => reserveListing(token, info.listing_id as string, info.buyer!.id, 48)) }} />)}
        {!isSeller && <SheetAction label={tr('Предложить цену')} icon={<Icon name="wallet" size={20} color={colors.ink} />} onPress={() => { setMenu(false); setOffer(''); setOfferOpen(true) }} />}
        <SheetAction label={tr(blocked ? 'Разблокировать' : 'Заблокировать')} danger={!blocked} icon={<Icon name="lock" size={20} color={blocked ? colors.ink : colors.danger} />}
          onPress={async () => { setMenu(false); if (!token) return; const next = !blocked; setBlocked(next); try { await blockChat(token, chatId, next) } catch { setBlocked(!next) } }} />
      </Sheet>
      <Sheet visible={offerOpen} title={tr('Ваша цена')} onClose={() => setOfferOpen(false)}>
        <View style={{ paddingHorizontal: 20, gap: 12 }}>
          {info?.listing_price != null && <Text style={styles.offerHint}>{tr('Цена в объявлении: {p}', { p: formatPrice(info.listing_price, info.currency) })}</Text>}
          <TextInput value={offer} onChangeText={(v) => setOffer(v.replace(/\D/g, '').slice(0, 9))} keyboardType="number-pad" placeholder="0" placeholderTextColor={colors.muted} style={styles.offerInput} autoFocus />
          <Pressable style={[styles.offerSend, !offer && { opacity: 0.45 }]} disabled={!offer} onPress={async () => {
            if (!token || !offer) return
            setOfferOpen(false)
            try { await sendOffer(token, chatId, Number(offer)); success(); await load() } catch { /* сеть */ }
          }}><Text style={styles.offerSendText}>{tr('Предложить')}</Text></Pressable>
        </View>
      </Sheet>

      {msgs === null
        ? <View style={styles.loading}><ActivityIndicator color={colors.primary} /></View>
        : (
          <FlatList
            data={data}
            inverted
            keyExtractor={(m) => m.id}
            renderItem={bubble}
            contentContainerStyle={styles.list}
            keyboardDismissMode="interactive"
            ListEmptyComponent={<View style={styles.emptyWrap}><Text style={styles.emptyText}>{tr('Напишите первое сообщение — например, уточните, актуально ли объявление.')}</Text></View>}
          />
        )}

      {typing && <Text style={styles.typing}>{tr('{name} печатает…', { name: info?.other_name || tr('Собеседник') })}</Text>}
      {offerPill && (
        <View style={styles.offerPill}>
          <Pressable style={styles.offerPillBtn} onPress={() => { setOffer(''); setOfferOpen(true) }}><Icon name="wallet" size={15} color={colors.primaryDeep} /><Text style={styles.offerPillText}>{tr('Предложить свою цену')}</Text></Pressable>
          <Pressable onPress={() => setOfferPillDismissed(true)} hitSlop={8} accessibilityLabel={tr('Закрыть')}><Icon name="close" size={12} color={colors.muted} /></Pressable>
        </View>
      )}
      {quick.length > 0 && !info?.blocked_by_them && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.quickRow} contentContainerStyle={styles.quick} keyboardShouldPersistTaps="handled" accessibilityLabel={tr('Быстрые ответы')}>
          {quick.map((q) => <Pressable key={q} style={styles.quickBtn} onPress={() => send(tr(q))}><Text style={styles.quickText}>{tr(q)}</Text></Pressable>)}
        </ScrollView>
      )}
      {info?.blocked_by_them ? (
        <Text style={[styles.blockedNote, { paddingBottom: Math.max(insets.bottom, 10) + 6 }]}>{tr('Этот пользователь заблокировал вас — писать ему нельзя.')}</Text>
      ) : (
      <>
      {/* меню сообщения: реакции и действия (как на сайте) */}
      <Modal visible={!!menuFor} transparent animationType="fade" onRequestClose={() => setMenuFor(null)}>
        <Pressable style={styles.menuBack} onPress={() => setMenuFor(null)}>
          <View style={styles.menu}>
            <View style={styles.menuReacts}>
              {['👍', '❤️', '😂', '😮', '🙏', '🔥'].map((e) => (
                <Pressable key={e} style={styles.menuReact} onPress={() => {
                  const m = menuFor; setMenuFor(null)
                  if (m && token) reactMessage(token, chatId, m.id, e).then((r) => setMsgs((prev) => (prev ?? []).map((x) => (x.id === m.id ? { ...x, reactions: r.reactions } : x)))).catch(() => {})
                }}><Text style={{ fontSize: 26 }}>{e}</Text></Pressable>
              ))}
            </View>
            <Pressable style={styles.menuItem} onPress={() => { setReplyTo(menuFor); setMenuFor(null) }}><Icon name="back" size={18} color={colors.ink} /><Text style={styles.menuText}>{tr('Ответить')}</Text></Pressable>
            {!!menuFor?.text && (
              <Pressable style={styles.menuItem} onPress={() => {
                const m = menuFor; setMenuFor(null)
                if (m && token) translateMessage(token, chatId, m.id).then((r) => setTranslated((p) => ({ ...p, [m.id]: r.text }))).catch(() => {})
              }}><Icon name="globe" size={18} color={colors.ink} /><Text style={styles.menuText}>{tr('Перевести')}</Text></Pressable>
            )}
            {!!menuFor?.text && (
              <Pressable style={styles.menuItem} onPress={() => { Clipboard.setStringAsync(menuFor?.text || '').catch(() => {}); setMenuFor(null) }}><Icon name="copy" size={18} color={colors.ink} /><Text style={styles.menuText}>{tr('Копировать')}</Text></Pressable>
            )}
            {/* своё текстовое сообщение можно исправить — в течение суток */}
            {!!menuFor && menuFor.sender_id === user?.id && (menuFor.kind === 'user' || !menuFor.kind) && !!menuFor.text && Date.now() - new Date(menuFor.created_at).getTime() < 864e5 && (
              <Pressable style={styles.menuItem} onPress={() => {
                const m = menuFor; setMenuFor(null)
                Alert.prompt(tr('Исправить сообщение'), undefined, [
                  { text: tr('Отмена'), style: 'cancel' },
                  { text: tr('Сохранить'), onPress: (v?: string) => {
                    const next = (v || '').trim()
                    if (!next || next === m.text || !token) return
                    setMsgs((prev) => (prev ?? []).map((x) => (x.id === m.id ? { ...x, text: next, edited_at: new Date().toISOString() } : x)))
                    editMessage(token, chatId, m.id, next).catch(() => setMsgs((prev) => (prev ?? []).map((x) => (x.id === m.id ? { ...x, text: m.text } : x))))
                  } },
                ], 'plain-text', m.text || '')
              }}><Icon name="edit" size={18} color={colors.ink} /><Text style={styles.menuText}>{tr('Изменить')}</Text></Pressable>
            )}
            {/* своё сообщение можно удалить — у обоих */}
            {!!menuFor && menuFor.sender_id === user?.id && (menuFor.kind === 'user' || menuFor.kind === 'voice' || !menuFor.kind) && (
              <Pressable style={[styles.menuItem, { borderBottomWidth: 0 }]} onPress={() => {
                const m = menuFor; setMenuFor(null)
                Alert.alert(tr('Удалить сообщение у вас и у собеседника?'), undefined, [
                  { text: tr('Отмена'), style: 'cancel' },
                  { text: tr('Удалить'), style: 'destructive', onPress: () => {
                    setMsgs((prev) => (prev ?? []).map((x) => (x.id === m.id ? { ...x, kind: 'deleted', text: null, audio_url: null, reactions: null } : x)))
                    if (token) deleteMessage(token, chatId, m.id).catch(() => {})
                  } },
                ])
              }}><Icon name="trash" size={18} color={colors.danger} /><Text style={[styles.menuText, { color: colors.danger }]}>{tr('Удалить')}</Text></Pressable>
            )}
          </View>
        </Pressable>
      </Modal>

      {!!voiceNote && <Text style={styles.voiceNote}>{voiceNote}</Text>}
      {/* ответ на сообщение — полоска над полем ввода */}
      {!!replyTo && (
        <View style={styles.replyBar}>
          <View style={styles.replyLine} />
          <View style={{ flex: 1 }}>
            <Text style={styles.quoteWho}>{tr('Ответ')}: {replyTo.sender_id === user?.id ? tr('Вы') : (info?.other_name || tr('Собеседник'))}</Text>
            <Text style={styles.quoteText} numberOfLines={1}>{replyTo.text}</Text>
          </View>
          <Pressable onPress={() => setReplyTo(null)} hitSlop={10}><Icon name="close" size={16} color={colors.muted} /></Pressable>
        </View>
      )}
      <View style={[styles.inputBar, { paddingBottom: Math.max(insets.bottom, 10) }]}>
        <TextInput
          value={text}
          onChangeText={(v) => { setText(v); sendTyping(v) }}
          placeholder={tr('Написать сообщение…')}
          placeholderTextColor={colors.muted}
          multiline
          style={styles.input}
          maxLength={2000}
        />
        {/* Как .chat-send-btn сайта: самолётик; пусто — серая кнопка с серым значком */}
{/* пустое поле — микрофон (удерживать — голосовое), есть текст — «отправить» */}
        {!text.trim() && !!token ? (
          <VoiceButton token={token} chatId={chatId} replyTo={replyTo?.id}
            onSent={(m) => { setReplyTo(null); const msg = m as Message; setMsgs((prev) => (prev?.some((x) => x.id === msg.id) ? prev : [...(prev ?? []), msg])) }}
            onError={(e) => setVoiceNote(e)} />
        ) : (
                <Pressable style={[styles.sendBtn, !text.trim() && styles.sendOff]} disabled={!text.trim()} onPress={() => send(text)} accessibilityLabel={tr('Отправить')}>
          <Icon name="send" size={19} color={text.trim() ? colors.onInverse : colors.muted} />
        </Pressable>
        )}
      </View>
      </>
      )}
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  voiceNote: { alignSelf: 'center', marginBottom: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, backgroundColor: colors.surface, overflow: 'hidden', fontFamily: font[600], fontSize: 13, color: colors.ink },
  quote: { borderLeftWidth: 3, borderLeftColor: colors.primary, paddingLeft: 8, marginBottom: 6, borderRadius: 3 },
  quoteMe: { borderLeftColor: 'rgba(255,255,255,0.7)' },
  quoteWho: { fontFamily: font[800], fontSize: 12.5, color: colors.primaryDeep },
  quoteText: { fontFamily: font[400], fontSize: 13, color: colors.inkSoft },
  translated: { marginTop: 6, paddingTop: 6, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border, fontFamily: font[400], fontSize: 14.5, color: colors.inkSoft },
  reacts: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 6 },
  react: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  reactMine: { borderColor: colors.primary },
  reactText: { fontSize: 13, color: colors.ink },
  menuBack: { flex: 1, backgroundColor: 'rgba(15,21,18,0.32)', justifyContent: 'flex-end', padding: 12, paddingBottom: 40 },
  menu: { backgroundColor: colors.surface, borderRadius: 22, overflow: 'hidden' },
  menuReacts: { flexDirection: 'row', justifyContent: 'space-around', paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  menuReact: { width: 46, height: 46, alignItems: 'center', justifyContent: 'center', borderRadius: 23 },
  menuItem: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 18, height: 54, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  menuText: { fontFamily: font[600], fontSize: 16, color: colors.ink },
  replyBar: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 16, paddingVertical: 8, backgroundColor: colors.surface, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border },
  replyLine: { width: 3, alignSelf: 'stretch', borderRadius: 2, backgroundColor: colors.primary },
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingBottom: 10, backgroundColor: colors.surface, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  backCircle: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', marginRight: 6 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  headBody: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  callBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginRight: 4 },
  callToast: { flexDirection: 'row', alignItems: 'center', gap: 10, marginHorizontal: 12, marginTop: 8, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 14, backgroundColor: colors.primarySoft },
  callToastText: { flex: 1, fontSize: 13.5, lineHeight: 18, fontFamily: font[700], color: colors.primaryDeep },
  callToastBtns: { flexDirection: 'row', gap: 6 },
  callYes: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 10, backgroundColor: colors.primary },
  callYesText: { color: '#fff', fontSize: 13.5, fontFamily: font[800] },
  callNo: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 10, backgroundColor: colors.surface },
  callNoText: { color: colors.ink, fontSize: 13.5, fontFamily: font[700] },
  reserved: { marginHorizontal: 12, marginTop: 8, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 12, backgroundColor: colors.warmBg },
  reservedText: { fontSize: 13, lineHeight: 18, fontFamily: font[700], color: '#8A6A1F' },
  typing: { fontSize: 12.5, fontFamily: font[600], color: colors.muted, paddingHorizontal: 16, paddingBottom: 4 },
  offerPill: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', gap: 10, marginLeft: 12, marginBottom: 6, paddingLeft: 12, paddingRight: 10, paddingVertical: 7, borderRadius: 12, backgroundColor: colors.primarySoft },
  offerPillBtn: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  offerPillText: { fontSize: 13.5, fontFamily: font[700], color: colors.primaryDeep },
  // лента быстрых ответов — по своей высоте: не растягивается на свободное место и не сжимается
  quickRow: { flexGrow: 0, flexShrink: 0 },
  quick: { gap: 6, paddingHorizontal: 12, paddingBottom: 8, alignItems: 'center' },
  quickBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  quickText: { fontSize: 13.5, fontFamily: font[600], color: colors.ink },
  blockedNote: { fontSize: 13.5, lineHeight: 19, fontFamily: font[600], color: colors.muted, textAlign: 'center', paddingHorizontal: 24, paddingTop: 12, backgroundColor: colors.surface },
  stripState: { color: colors.muted, fontFamily: font[700] },
  teamBubble: { marginHorizontal: 4, marginVertical: 6, padding: 14, borderRadius: 18, backgroundColor: colors.sunken },
  strip: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 8, backgroundColor: colors.surface, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  stripTitle: { fontSize: 14, fontFamily: font[700], color: colors.ink },
  stripPrice: { fontSize: 13.5, fontFamily: font[800], color: colors.primaryDeep, marginTop: 1 },
  safety: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', marginHorizontal: 4, marginVertical: 6, padding: 12, borderRadius: 14, backgroundColor: colors.sunken },
  safetyText: { flex: 1, fontSize: 13, lineHeight: 18, fontFamily: font[600], color: colors.inkSoft },
  offer: { maxWidth: '80%', paddingHorizontal: 13, paddingVertical: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1.5, borderColor: colors.primary, gap: 2 },
  offerTitle: { fontSize: 15, fontFamily: font[800], color: colors.ink },
  offerStatus: { fontSize: 12.5, fontFamily: font[600], color: colors.muted },
  headThumb: { width: 40, height: 40, borderRadius: 9, backgroundColor: colors.photo, overflow: 'hidden' },
  headThumbImg: { width: 40, height: 40 },
  headName: { fontSize: 16, fontFamily: font[800], color: colors.ink },
  headListing: { fontFamily: font[400], fontSize: 13, color: colors.inkSoft, marginTop: 1 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  // Список перевёрнут (новые снизу); короткая переписка — у верха экрана, как на сайте, а не прижата к низу
  list: { paddingHorizontal: 12, paddingVertical: 12, gap: 6, flexGrow: 1, justifyContent: 'flex-end' },
  bubbleRow: { flexDirection: 'row', justifyContent: 'flex-start' },
  bubbleRowMe: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '80%', paddingHorizontal: 12, paddingTop: 8, paddingBottom: 6, borderRadius: 18 },
  bubbleThem: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderBottomLeftRadius: 6 },
  bubbleMe: { backgroundColor: colors.primary, borderBottomRightRadius: 6 },
  bubbleFailed: { backgroundColor: colors.danger },
  bubbleText: { fontFamily: font[400], fontSize: 16, lineHeight: 21, color: colors.ink },
  bubbleTextMe: { color: '#fff' },
  meta: { fontFamily: font[400], fontSize: 11, color: colors.muted, marginTop: 3, alignSelf: 'flex-end' },
  metaMe: { color: 'rgba(255,255,255,0.8)' },
  system: { alignSelf: 'center', maxWidth: '88%', backgroundColor: colors.sunken, borderRadius: 14, paddingHorizontal: 12, paddingVertical: 8, marginVertical: 4 },
  systemText: { fontFamily: font[400], fontSize: 13.5, lineHeight: 19, color: colors.inkSoft, textAlign: 'center' },
  emptyWrap: { transform: [{ scaleY: -1 }], paddingHorizontal: 40, paddingVertical: 24 },
  emptyText: { fontFamily: font[400], fontSize: 14.5, lineHeight: 20, color: colors.muted, textAlign: 'center' },
  // как .chat-input-row сайта: белая полоса с тенью вверх, поле 12/16, скругление 20, рамка
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, paddingHorizontal: 16, paddingTop: 12, backgroundColor: colors.surface, shadowColor: '#14201A', shadowOpacity: 0.08, shadowRadius: 20, shadowOffset: { width: 0, height: -4 }, elevation: 6 },
  input: { flex: 1, minHeight: 44, maxHeight: 120, borderRadius: 20, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, paddingHorizontal: 16, paddingTop: 11, paddingBottom: 11, fontSize: 16, fontFamily: font[400], color: colors.ink },
  sendBtn: { width: 42, height: 42, borderRadius: 21, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  sendOff: { backgroundColor: colors.border },
  dots: { fontSize: 24, lineHeight: 26, color: colors.ink, fontFamily: font[800] },
  offerBtns: { flexDirection: 'row', gap: 8, marginTop: 8 },
  offerBtn: { height: 34, paddingHorizontal: 14, borderRadius: 10, backgroundColor: colors.sunken, justifyContent: 'center' },
  offerYes: { backgroundColor: colors.primary },
  offerYesText: { color: '#fff', fontSize: 13.5, fontFamily: font[800] },
  offerNoText: { color: colors.ink, fontSize: 13.5, fontFamily: font[700] },
  offerHint: { fontSize: 14, fontFamily: font[600], color: colors.muted },
  offerInput: { height: 56, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 16, fontSize: 24, fontFamily: font[800], color: colors.ink },
  offerSend: { height: 52, borderRadius: 16, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  offerSendText: { color: colors.onInverse, fontSize: 16, fontFamily: font[800] },
})
