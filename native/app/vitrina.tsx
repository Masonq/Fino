import { Image } from 'expo-image'
import { router } from 'expo-router'
import { useEffect, useState } from 'react'
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Share, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import type { FeedItem } from '../src/api'
import { useAuth } from '../src/auth'
import { mediaUrl, SITE } from '../src/config'
import { plural, tr } from '../src/i18n'
import Icon from '../src/components/Icon'
import { Btn, Field, Header, k } from '../src/components/Kit'
import { money, sfAutobuild, sfDeleteCollection, sfEdit, sfItems, sfMe, sfSaveCollection, sfState, type StorefrontOwn } from '../src/social'
import { colors, font } from '../src/theme'
import { RowSkeletons } from '../src/components/Skeleton'

const ERR: Record<string, string> = {
  slug_format: 'Адрес: латиница, цифры и дефис, 3–40 знаков', slug_reserved: 'Этот адрес занят системой', slug_taken: 'Адрес уже занят',
  name_length: 'Название — от 2 до 60 знаков', no_active_items: 'На витрине нет активных объявлений', title_length: 'Название подборки — от 2 до 40 знаков',
}
const ST: Record<string, [string, string, string]> = {
  draft: ['Черновик', colors.sunken, colors.inkSoft], published: ['Опубликована', colors.primarySoft, colors.primaryDeep],
  paused: ['Отпуск', colors.warmBg, colors.goldDark], blocked: ['Заблокирована модератором', colors.dangerBg, '#A33232'],
}
const photo = (l: FeedItem) => l.cover_photo || l.photos?.[0] || null
type Coll = { id: string | null; title: string; description: string; status: string; sort: string; listing_ids: string[] }

/** Моя витрина: нет — собрать одним нажатием; есть — статус, оформление, товары, подборки (как на сайте). */
export default function Vitrina() {
  const { token } = useAuth()
  const insets = useSafeAreaInsets()
  const [data, setData] = useState<{ storefront: StorefrontOwn | null; active_count?: number } | null>(null)
  const [form, setForm] = useState({ name: '', description: '', slug: '' })
  const [err, setErr] = useState('')
  const [note, setNote] = useState('')
  const [coll, setColl] = useState<Coll | null>(null)
  const [pause, setPause] = useState<{ until: string; note: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const sf = data?.storefront ?? null

  const take = (r: { storefront: StorefrontOwn | null; active_count?: number }) => {
    setData(r)
    if (r.storefront) setForm({ name: r.storefront.name, description: r.storefront.description || '', slug: r.storefront.slug })
  }
  useEffect(() => { if (!token) router.replace('/login'); else sfMe(token).then(take).catch(() => setData({ storefront: null })) }, [token])

  const run = async (p: Promise<{ storefront: StorefrontOwn | null }>, msg = 'Сохранено') => {
    setErr(''); setBusy(true)
    try { take(await p); setNote(tr(msg)); setTimeout(() => setNote(''), 1800); setBusy(false); return true } catch (e) {
      setErr(tr(ERR[(e as { message?: string }).message ?? ''] ?? 'Не получилось сохранить')); setBusy(false); return false
    }
  }
  if (!data || !token) return <View style={{ flex: 1, backgroundColor: colors.bg }}><Header title={tr('Моя витрина')} /><View style={{ padding: 12 }}><RowSkeletons count={4} /></View></View>

  if (!sf) {
    const n = data.active_count ?? 0
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <Header title={tr('Моя витрина')} />
        <View style={[k.card, { margin: 12, padding: 20, alignItems: 'center' }]}>
          <Text style={s.buildTitle}>{tr('Ваша витрина на PLONK')}</Text>
          <Text style={[k.body, { textAlign: 'center', color: colors.inkSoft, marginVertical: 12 }]}>
            {n ? tr('У вас {n} {w}. Соберём из них витрину за минуту — потом всё можно поменять', { n, w: plural(n, { ru: ['объявление', 'объявления', 'объявлений'], en: ['listing', 'listings'], sr: ['oglas', 'oglasa', 'oglasa'] }) })
              : tr('Разместите хотя бы одно объявление — и соберём из него витрину')}
          </Text>
          {n > 0 ? <Btn wide busy={busy} label={tr('Собрать витрину')} onPress={() => run(sfAutobuild(token), 'Витрина собрана — проверьте и опубликуйте')} />
            : <Btn wide label={tr('Разместить объявление')} onPress={() => router.push('/post' as never)} />}
          <View style={{ alignSelf: 'stretch', marginTop: 16, gap: 6 }}>
            {['Все объявления — на одной странице с вашей ссылкой', 'Покупатели подписываются и узнают о новых товарах', 'Цены и фото обновляются сами — из объявлений'].map((t) => (
              <View key={t} style={k.row}><Icon name="check" size={16} color={colors.primary} /><Text style={[k.body, { flex: 1, fontSize: 14 }]}>{tr(t)}</Text></View>
            ))}
          </View>
          {!!err && <Text style={k.err}>{err}</Text>}
        </View>
      </View>
    )
  }

  const ids = sf.items.map((l) => l.id)
  const move = (i: number, d: number) => { const n = [...ids]; const j = i + d; if (j < 0 || j >= n.length) return; [n[i], n[j]] = [n[j], n[i]]; run(sfItems(token, n)) }
  const live = sf.status === 'published' || sf.status === 'paused'
  const [label, bg, fg] = ST[sf.status] ?? ST.draft
  const url = `${SITE}/s/${sf.slug}`

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Header title={tr('Моя витрина')} right={live ? <Btn small kind="ghost" label={tr('Открыть')} onPress={() => router.push(`/s/${sf.slug}` as never)} /> : undefined} />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ paddingHorizontal: 12, paddingBottom: insets.bottom + 40 }} keyboardShouldPersistTaps="handled">
          <View style={k.card}>
            <View style={[k.row, { justifyContent: 'space-between' }]}>
              <View style={[k.status, { backgroundColor: bg }]}><Text style={[k.statusText, { color: fg }]}>{tr(label)}</Text></View>
              <Text style={k.muted}>👁 {sf.views} · {sf.followers} {plural(sf.followers, { ru: ['подписчик', 'подписчика', 'подписчиков'], en: ['follower', 'followers'], sr: ['pratilac', 'pratioca', 'pratilaca'] })}</Text>
            </View>
            {live && (
              <View style={s.url}>
                <Text style={[k.name, { flex: 1, fontSize: 14 }]} numberOfLines={1}>{url.replace(/^https?:\/\//, '')}</Text>
                <Btn small kind="ghost" label={tr('Поделиться')} onPress={() => Share.share({ message: `${sf.name}\n${url}` }).catch(() => {})} />
              </View>
            )}
            <View style={k.actions}>
              {sf.status === 'draft' && <Btn label={tr('Опубликовать')} busy={busy} onPress={() => run(sfState(token, { action: 'publish' }), 'Витрина опубликована')} />}
              {sf.status === 'published' && <Btn kind="ghost" label={tr('Уйти в отпуск')} onPress={() => setPause({ until: '', note: '' })} />}
              {sf.status === 'paused' && <Btn label={tr('Вернуться из отпуска')} busy={busy} onPress={() => run(sfState(token, { action: 'resume' }))} />}
              {live && <Btn kind="ghost" label={tr('Снять с публикации')} onPress={() => run(sfState(token, { action: 'unpublish' }))} />}
            </View>
            {pause && (
              <View style={{ marginTop: 12 }}>
                <Field label={tr('До какого числа (ДД.ММ)')} value={pause.until} placeholder="20.10" keyboardType="numbers-and-punctuation" onChangeText={(v) => setPause({ ...pause, until: v })} />
                <Field label={tr('Сообщение покупателям')} value={pause.note} maxLength={160} placeholder={tr('Например: отвечу после 20-го')} onChangeText={(v) => setPause({ ...pause, note: v })} />
                <View style={k.actions}>
                  <Btn small kind="ghost" label={tr('Отмена')} onPress={() => setPause(null)} />
                  <Btn small label={tr('Уйти в отпуск')} onPress={async () => {
                    const m = pause.until.match(/^(\d{1,2})\.(\d{1,2})$/)
                    const until = m ? `${new Date().getFullYear()}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : null
                    if (await run(sfState(token, { action: 'pause', until, note: pause.note }))) setPause(null)
                  }} />
                </View>
              </View>
            )}
          </View>

          <Text style={k.section}>{tr('Оформление')}</Text>
          <Field label={tr('Название')} value={form.name} maxLength={60} onChangeText={(v) => setForm({ ...form, name: v })} />
          <Field label={tr('Описание')} value={form.description} maxLength={300} multiline placeholder={tr('Что продаёте и почему у вас')} onChangeText={(v) => setForm({ ...form, description: v })} />
          <Field label={tr('Адрес: plonk.rs/s/…')} value={form.slug} maxLength={40} autoCapitalize="none" autoCorrect={false} onChangeText={(v) => setForm({ ...form, slug: v.toLowerCase().replace(/[^a-z0-9-]/g, '') })} />
          {sf.cover_options.length > 0 && (
            <>
              <Text style={k.fieldLabel}>{tr('Обложка')}</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingVertical: 8 }}>
                {sf.cover_options.map((c) => (
                  <Pressable key={c} style={[s.coverOpt, sf.cover_url === c && { borderColor: colors.primary }]} onPress={() => run(sfEdit(token, { cover_url: c }))}>
                    <Image source={{ uri: mediaUrl(c) ?? undefined }} style={StyleSheet.absoluteFill} contentFit="cover" />
                  </Pressable>
                ))}
              </ScrollView>
            </>
          )}
          <Btn wide busy={busy} label={tr('Сохранить')} onPress={() => run(sfEdit(token, form))} />

          <Text style={k.section}>{tr('Товары на витрине · {n}', { n: sf.items.length })}</Text>
          {sf.items.map((l, i) => (
            <View key={l.id} style={[k.pick, { borderColor: colors.primary }]}>
              {!!photo(l) && <Image source={{ uri: mediaUrl(photo(l)) ?? undefined }} style={k.thumb} />}
              <View style={{ flex: 1 }}><Text style={k.name} numberOfLines={1}>{l.title}</Text><Text style={k.muted}>{money(l.price, l.currency)}</Text></View>
              <Pressable style={[s.arrow, i === 0 && { opacity: 0.3 }]} disabled={i === 0} onPress={() => move(i, -1)} accessibilityLabel={tr('Выше')}><Text style={s.arrowText}>↑</Text></Pressable>
              <Pressable style={[s.arrow, i === sf.items.length - 1 && { opacity: 0.3 }]} disabled={i === sf.items.length - 1} onPress={() => move(i, 1)} accessibilityLabel={tr('Ниже')}><Text style={s.arrowText}>↓</Text></Pressable>
              <Pressable style={s.arrow} onPress={() => run(sfItems(token, ids.filter((x) => x !== l.id)))} accessibilityLabel={tr('Удалить')}><Icon name="close" size={14} color={colors.ink} /></Pressable>
            </View>
          ))}
          {sf.not_added.length > 0 && <Text style={k.hint}>{tr('Не на витрине — нажмите, чтобы добавить')}</Text>}
          {sf.not_added.map((l) => (
            <Pressable key={l.id} style={k.pick} onPress={() => run(sfItems(token, [...ids, l.id]))}>
              {!!photo(l) && <Image source={{ uri: mediaUrl(photo(l)) ?? undefined }} style={k.thumb} />}
              <View style={{ flex: 1 }}><Text style={k.name} numberOfLines={1}>{l.title}</Text><Text style={k.muted}>{money(l.price, l.currency)}</Text></View>
              <View style={s.add}><Icon name="plus" size={16} color={colors.primaryDeep} /></View>
            </Pressable>
          ))}

          <Text style={k.section}>{tr('Подборки')}</Text>
          <Text style={k.hint}>{tr('Подборки помогают найти нужное: «Новинки», «До €50», «Для дома». Необязательно')}</Text>
          {sf.collections.map((c) => (
            <View key={c.id} style={[k.pick, { padding: 12 }]}>
              <View style={{ flex: 1 }}>
                <Text style={k.name}>{c.title}{c.status === 'hidden' ? ` · ${tr('скрыта')}` : ''}</Text>
                <Text style={k.muted}>{c.listing_ids.length} {plural(c.listing_ids.length, { ru: ['товар', 'товара', 'товаров'], en: ['item', 'items'], sr: ['stvar', 'stvari', 'stvari'] })}</Text>
              </View>
              <Btn small kind="ghost" label={tr('Изменить')} onPress={() => setColl({ ...c, description: c.description || '' })} />
            </View>
          ))}
          {!coll && <Btn wide kind="ghost" label={tr('+ Подборка')} onPress={() => setColl({ id: null, title: '', description: '', status: 'active', sort: 'manual', listing_ids: [] })} />}
          {coll && (
            <View style={[k.card, { borderColor: colors.primary }]}>
              <Field label={tr('Название подборки')} value={coll.title} maxLength={40} placeholder={tr('Например, До €50')} onChangeText={(v) => setColl({ ...coll, title: v })} />
              <Field label={tr('Описание')} value={coll.description} maxLength={160} onChangeText={(v) => setColl({ ...coll, description: v })} />
              <View style={[k.row, { marginBottom: 12, gap: 16 }]}>
                <Pressable style={k.row} onPress={() => setColl({ ...coll, sort: coll.sort === 'newest' ? 'manual' : 'newest' })}><View style={[s.check, coll.sort === 'newest' && s.checkOn]}>{coll.sort === 'newest' && <Icon name="check" size={12} color="#fff" />}</View><Text style={k.body}>{tr('Сначала новые')}</Text></Pressable>
                <Pressable style={k.row} onPress={() => setColl({ ...coll, status: coll.status === 'hidden' ? 'active' : 'hidden' })}><View style={[s.check, coll.status === 'hidden' && s.checkOn]}>{coll.status === 'hidden' && <Icon name="check" size={12} color="#fff" />}</View><Text style={k.body}>{tr('Скрыть')}</Text></Pressable>
              </View>
              <View style={s.grid}>
                {sf.items.map((l) => {
                  const on = coll.listing_ids.includes(l.id)
                  return (
                    <Pressable key={l.id} style={[s.gridItem, on && { borderColor: colors.primary }]} onPress={() => setColl({ ...coll, listing_ids: on ? coll.listing_ids.filter((x) => x !== l.id) : [...coll.listing_ids, l.id] })}>
                      {!!photo(l) && <Image source={{ uri: mediaUrl(photo(l)) ?? undefined }} style={s.gridImg} />}
                      <Text style={s.gridText} numberOfLines={1}>{l.title}</Text>
                      {on && <View style={s.gridCheck}><Icon name="check" size={12} color="#fff" /></View>}
                    </Pressable>
                  )
                })}
              </View>
              <View style={k.actions}>
                {!!coll.id && <Btn small kind="danger" label={tr('Удалить')} onPress={() => Alert.alert(tr('Удалить подборку? Объявления останутся'), '', [{ text: tr('Отмена'), style: 'cancel' }, { text: tr('Удалить'), style: 'destructive', onPress: async () => { if (await run(sfDeleteCollection(token, coll.id!))) setColl(null) } }])} />}
                <Btn small kind="ghost" label={tr('Отмена')} onPress={() => setColl(null)} />
                <Btn small busy={busy} label={tr('Сохранить')} onPress={async () => { if (await run(sfSaveCollection(token, coll.id, coll))) setColl(null) }} />
              </View>
            </View>
          )}
          {!!err && <Text style={k.err}>{err}</Text>}
        </ScrollView>
      </KeyboardAvoidingView>
      {!!note && <View pointerEvents="none" style={[s.toast, { bottom: insets.bottom + 24 }]}><Text style={s.toastText}>{note}</Text></View>}
    </View>
  )
}

const s = StyleSheet.create({
  buildTitle: { fontFamily: font[800], fontSize: 20, color: colors.ink },
  url: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 10, paddingLeft: 12, paddingRight: 6, paddingVertical: 6, borderRadius: 12, backgroundColor: colors.bg },
  coverOpt: { width: 96, height: 64, borderRadius: 12, overflow: 'hidden', borderWidth: 2, borderColor: 'transparent', backgroundColor: colors.photo },
  arrow: { width: 32, height: 32, borderRadius: 16, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  arrowText: { fontFamily: font[700], fontSize: 15, color: colors.ink },
  add: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  check: { width: 20, height: 20, borderRadius: 6, borderWidth: 2, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  checkOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  gridItem: { width: '31%', padding: 4, borderRadius: 12, borderWidth: 2, borderColor: 'transparent', backgroundColor: colors.bg },
  gridImg: { width: '100%', aspectRatio: 1, borderRadius: 8, backgroundColor: colors.photo },
  gridText: { marginTop: 4, fontFamily: font[600], fontSize: 12, color: colors.ink },
  gridCheck: { position: 'absolute', top: 8, right: 8, width: 22, height: 22, borderRadius: 11, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  toast: { position: 'absolute', alignSelf: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, backgroundColor: colors.inverse },
  toastText: { fontFamily: font[600], fontSize: 14, color: '#fff' },
})
