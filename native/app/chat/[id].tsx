import { success, tap } from '../../src/haptics'
import { tr } from '../../src/i18n'
import { Image } from 'expo-image'
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator, AppState, FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { blockChat, type Chat, chatInfo, chatMessages, markChatRead, type Message, respondOffer, sendMessage, sendOffer, isOffer } from '../../src/api'
import Icon from '../../src/components/Icon'
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
export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const chatId = String(id)
  const insets = useSafeAreaInsets()
  const { token, user } = useAuth()
  const { refresh: refreshList, chats } = useChats()
  const [chat, setChat] = useState<Chat | null>(null)
  const [msgs, setMsgs] = useState<(Message & { pending?: boolean; failed?: boolean })[] | null>(null)
  const [text, setText] = useState('')
  const lastCount = useRef(0)
  const [menu, setMenu] = useState(false)
  const [offerOpen, setOfferOpen] = useState(false)
  const [offer, setOffer] = useState('')
  const [blocked, setBlocked] = useState(false)

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
  useEffect(() => { if (token) chatInfo(token, chatId).then(setChat).catch(() => {}) }, [token, chatId])
  const info: Chat | null = chat || fromList ? { ...(fromList ?? {}), ...Object.fromEntries(Object.entries(chat ?? {}).filter(([, v]) => v != null)) } as Chat : null

  useFocusEffect(useCallback(() => {
    load()
    const timer = setInterval(() => { if (AppState.currentState === 'active') load() }, 5000)
    return () => clearInterval(timer)
  }, [load]))

  const send = async (body: string, retryId?: string) => {
    const value = body.trim()
    if (!value || !token) return
    tap()
    const localId = retryId ?? `local-${Date.now()}`
    const optimistic = { id: localId, kind: 'text', text: value, sender_id: user?.id, created_at: new Date().toISOString(), pending: true }
    setMsgs((prev) => [...(prev ?? []).filter((m) => m.id !== localId), optimistic])
    if (!retryId) setText('')
    try {
      await sendMessage(token, chatId, value)
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
      return <View style={styles.system}><Text style={styles.systemText}>{plainText(item.text)}</Text></View>
    }
    const me = mine(item)
    const body = isOffer(item.kind)
      ? tr('Предлагаю {price}', { price: formatPrice(item.offer_price ?? null, info?.currency) }) + (item.offer_status === 'accepted' ? tr(' — принято') : item.offer_status === 'declined' ? tr(' — отклонено') : '')
      : plainText(item.text)
    return (
      <Pressable disabled={!item.failed} onPress={() => send(item.text || '', item.id)} style={[styles.bubbleRow, me && styles.bubbleRowMe]}>
        <View style={[styles.bubble, me ? styles.bubbleMe : styles.bubbleThem, item.failed && styles.bubbleFailed]}>
          <Text style={[styles.bubbleText, me && styles.bubbleTextMe]}>{body}</Text>
          {isOffer(item.kind) && !me && (!item.offer_status || item.offer_status === 'pending') && (
            <View style={styles.offerBtns}>
              <Pressable style={[styles.offerBtn, styles.offerYes]} onPress={async () => { if (token) { await respondOffer(token, chatId, item.id, 'accepted').catch(() => {}); load() } }}><Text style={styles.offerYesText}>{tr('Принять')}</Text></Pressable>
              <Pressable style={styles.offerBtn} onPress={async () => { if (token) { await respondOffer(token, chatId, item.id, 'declined').catch(() => {}); load() } }}><Text style={styles.offerNoText}>{tr('Отклонить')}</Text></Pressable>
            </View>
          )}
          <Text style={[styles.meta, me && styles.metaMe]}>
            {item.failed ? tr('Не отправлено — нажмите, чтобы повторить') : item.pending ? tr('Отправляется…') : hhmm(item.created_at)}
          </Text>
        </View>
      </Pressable>
    )
  }

  return (
    <KeyboardAvoidingView style={styles.page} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={[styles.head, { paddingTop: insets.top + 6 }]}>
        <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace('/chats'))} hitSlop={10} style={styles.backCircle} accessibilityLabel={tr('Назад')}>
          <Icon name="back" size={20} color={colors.ink} />
        </Pressable>
        <Text style={[styles.headName, { flex: 1 }]} numberOfLines={1}>{title}</Text>
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
            {info.listing_price != null && <Text style={styles.stripPrice}>{formatPrice(info.listing_price, info.currency)}</Text>}
          </View>
          <Icon name="forward" size={16} color={colors.muted} />
        </Pressable>
      )}

      <Sheet visible={menu} onClose={() => setMenu(false)}>
        {!info?.is_seller && <SheetAction label={tr('Предложить цену')} icon={<Icon name="wallet" size={20} color={colors.ink} />} onPress={() => { setMenu(false); setOffer(''); setOfferOpen(true) }} />}
        <SheetAction label={tr(blocked ? 'Разблокировать' : 'Заблокировать')} danger={!blocked} icon={<Icon name="lock" size={20} color={blocked ? colors.ink : '#B42318'} />}
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

      <View style={[styles.inputBar, { paddingBottom: Math.max(insets.bottom, 10) }]}>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder={tr('Написать сообщение…')}
          placeholderTextColor={colors.muted}
          multiline
          style={styles.input}
          maxLength={2000}
        />
        {/* Как .chat-send-btn сайта: самолётик; пусто — серая кнопка с серым значком */}
        <Pressable style={[styles.sendBtn, !text.trim() && styles.sendOff]} disabled={!text.trim()} onPress={() => send(text)} accessibilityLabel={tr('Отправить')}>
          <Icon name="send" size={19} color={text.trim() ? '#fff' : colors.muted} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  head: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingBottom: 10, backgroundColor: colors.surface, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  backCircle: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', marginRight: 6 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  headBody: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
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
  bubbleFailed: { backgroundColor: '#B42318' },
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
  sendBtn: { width: 42, height: 42, borderRadius: 21, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  sendOff: { backgroundColor: colors.border },
  dots: { fontSize: 24, lineHeight: 26, color: colors.ink, fontFamily: font[800] },
  offerBtns: { flexDirection: 'row', gap: 8, marginTop: 8 },
  offerBtn: { height: 34, paddingHorizontal: 14, borderRadius: 10, backgroundColor: colors.sunken, justifyContent: 'center' },
  offerYes: { backgroundColor: colors.primary },
  offerYesText: { color: '#fff', fontSize: 13.5, fontFamily: font[800] },
  offerNoText: { color: colors.ink, fontSize: 13.5, fontFamily: font[700] },
  offerHint: { fontSize: 14, fontFamily: font[600], color: colors.muted },
  offerInput: { height: 56, borderRadius: 14, backgroundColor: colors.sunken, paddingHorizontal: 16, fontSize: 24, fontFamily: font[800], color: colors.ink },
  offerSend: { height: 52, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  offerSendText: { color: '#fff', fontSize: 16, fontFamily: font[800] },
})
