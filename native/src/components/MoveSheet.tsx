import SheetFrame from './SheetFrame'
/** «Перенести в раздел» для сотрудников — как на сайте: поиск по всем разделам с путём, список листается. */
import { useEffect, useMemo, useState } from 'react'
import { FlatList, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { type Category, fetchCategories } from '../api'
import { modMove } from '../admin'
import { getLang, tr } from '../i18n'
import { colors, font } from '../theme'

const nameOf = (c: Category) => (typeof c.name === 'string' ? c.name : c.name?.[getLang()] || c.name?.ru || c.slug)

export default function MoveSheet({ token, listingId, current, onClose, onMoved, onPick, title }: {
  token: string; listingId: string; current?: string | null; onClose: () => void; onMoved: (name: string) => void
  // выбор раздела владельцем при правке: только конечные разделы, без переноса на сервере — решает экран правки
  onPick?: (c: Category, name: string, path: string) => void; title?: string
}) {
  const [tree, setTree] = useState<Category[] | null>(null)
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { fetchCategories().then(setTree).catch(() => setTree([])) }, [])
  // все разделы, кроме верхнего уровня (класть в корень нельзя), с путём родителей
  const all = useMemo(() => {
    const out: { c: Category; path: string }[] = []
    const walk = (n: Category, trail: string[]) => {
      if (trail.length && (!onPick || !(n.children || []).length)) out.push({ c: n, path: trail.join(' → ') })
      ;(n.children || []).forEach((k) => walk(k, [...trail, nameOf(n)]))
    }
    ;(tree || []).forEach((r) => walk(r, []))
    return out
  }, [tree])
  const shown = q.trim() ? all.filter(({ c }) => `${nameOf(c)} ${c.slug}`.toLowerCase().includes(q.trim().toLowerCase())) : all
  const pick = async (c: Category) => {
    if (onPick) { onPick(c, nameOf(c), all.find((x) => x.c.id === c.id)?.path || ''); return }
    setBusy(true)
    try { await modMove(token, listingId, c.id); onMoved(nameOf(c)) } catch { /* остаётся открытым */ } finally { setBusy(false) }
  }
  return (
    <SheetFrame visible onClose={onClose}>
      <View style={st.sheet}>
        <View style={st.handle} />
        <Text style={st.title}>{title || tr('Перенести в раздел')}</Text>
        {!!current && <Text style={st.now}>{tr('Сейчас')}: <Text style={{ fontFamily: font[800], color: colors.ink }}>{current}</Text></Text>}
        <TextInput style={st.input} value={q} onChangeText={setQ} placeholder={tr('Найти раздел')} placeholderTextColor={colors.muted} autoCorrect={false} />
        <FlatList
          data={shown}
          keyExtractor={(x) => x.c.id}
          style={{ maxHeight: 420 }}
          keyboardShouldPersistTaps="handled"
          ListEmptyComponent={<Text style={st.empty}>{tree ? tr('Ничего не нашлось') : tr('Загружаем…')}</Text>}
          renderItem={({ item }) => (
            <Pressable style={st.row} disabled={busy} onPress={() => pick(item.c)}>
              <Text style={st.name}>{nameOf(item.c)}</Text>
              <Text style={st.path} numberOfLines={1}>{item.path}</Text>
            </Pressable>
          )}
        />
        <Pressable style={st.cancel} onPress={onClose}><Text style={st.cancelT}>{tr('Отмена')}</Text></Pressable>
      </View>
    </SheetFrame>
  )
}

const st = StyleSheet.create({
  back: { flex: 1, backgroundColor: 'rgba(15,21,18,0.4)' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 26, borderTopRightRadius: 26, padding: 16, paddingBottom: 34 },
  handle: { width: 40, height: 5, borderRadius: 3, backgroundColor: colors.sunken, alignSelf: 'center', marginBottom: 12 },
  title: { fontFamily: font[800], fontSize: 18, color: colors.ink },
  now: { fontFamily: font[400], fontSize: 14, color: colors.inkSoft, marginTop: 4 },
  input: { height: 48, borderRadius: 16, backgroundColor: colors.sunken, paddingHorizontal: 16, marginVertical: 12, fontFamily: font[400], fontSize: 16, color: colors.ink },
  row: { paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  name: { fontFamily: font[800], fontSize: 16, color: colors.ink },
  path: { fontFamily: font[600], fontSize: 13, color: colors.muted, marginTop: 2 },
  empty: { textAlign: 'center', padding: 20, fontFamily: font[600], color: colors.muted },
  cancel: { marginTop: 12, height: 50, borderRadius: 16, backgroundColor: colors.sunken, alignItems: 'center', justifyContent: 'center' },
  cancelT: { fontFamily: font[800], fontSize: 15, color: colors.ink },
})
