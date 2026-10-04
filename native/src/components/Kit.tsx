import { router } from 'expo-router'
import type { ReactNode } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, type TextInputProps, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { tr } from '../i18n'
import { colors, font } from '../theme'
import Icon from './Icon'

/** Шапка экрана — как у «Вы смотрели»: назад, заголовок, справа — своё. */
export function Header({ title, right, fallback = '/profile' }: { title: string; right?: ReactNode; fallback?: string }) {
  const insets = useSafeAreaInsets()
  return (
    <View style={[k.top, { paddingTop: insets.top + 6 }]}>
      <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace(fallback as never))} hitSlop={10} style={k.back} accessibilityLabel={tr('Назад')}>
        <Icon name="back" size={22} color={colors.ink} />
      </Pressable>
      <Text style={k.title} numberOfLines={1}>{title}</Text>
      {right}
    </View>
  )
}

type BtnKind = 'primary' | 'ghost' | 'danger'
export function Btn({ label, onPress, kind = 'primary', small, wide, disabled, busy }: { label: string; onPress: () => void; kind?: BtnKind; small?: boolean; wide?: boolean; disabled?: boolean; busy?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={disabled || busy} accessibilityRole="button"
      style={({ pressed }) => [k.btn, small && k.btnSm, wide && k.btnWide, k[kind], (disabled || busy) && { opacity: 0.55 }, pressed && { opacity: 0.8 }]}>
      {busy ? <ActivityIndicator color={kind === 'primary' ? '#fff' : colors.primary} /> : (
        <Text style={[k.btnText, small && k.btnTextSm, { color: kind === 'primary' ? '#fff' : kind === 'danger' ? '#C93C3C' : colors.ink }]}>{label}</Text>
      )}
    </Pressable>
  )
}

export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={k.field}>
      <Text style={k.fieldLabel}>{label}</Text>
      <TextInput placeholderTextColor={colors.muted} {...props} style={[k.input, props.multiline && { minHeight: 90, textAlignVertical: 'top' }, props.style]} />
    </View>
  )
}

export function Tabs<T extends string>({ value, items, onChange }: { value: T; items: { key: T; label: string; n?: number }[]; onChange: (v: T) => void }) {
  return (
    <View style={k.tabs}>
      {items.map((it) => {
        const on = it.key === value
        return (
          <Pressable key={it.key} onPress={() => onChange(it.key)} style={[k.tab, on && k.tabOn]} accessibilityRole="tab" accessibilityState={{ selected: on }}>
            <Text style={[k.tabText, on && { color: '#fff' }]}>{it.label}</Text>
            {!!it.n && <View style={[k.tabN, on && { backgroundColor: 'rgba(255,255,255,0.2)' }]}><Text style={[k.tabNText, on && { color: '#fff' }]}>{it.n}</Text></View>}
          </Pressable>
        )
      })}
    </View>
  )
}

export const Empty = ({ text, children }: { text: string; children?: ReactNode }) => (
  <View style={k.empty}><Text style={k.emptyText}>{text}</Text>{children}</View>
)

export const k = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 12, paddingBottom: 8, backgroundColor: colors.bg },
  back: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  title: { flex: 1, fontFamily: font[800], fontSize: 22, color: colors.ink },
  btn: { height: 44, paddingHorizontal: 16, borderRadius: 12, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: 'transparent' },
  btnSm: { height: 36, paddingHorizontal: 12 },
  btnWide: { alignSelf: 'stretch', height: 50 },
  primary: { backgroundColor: colors.primary },
  ghost: { backgroundColor: colors.surface, borderColor: colors.border },
  danger: { backgroundColor: colors.surface, borderColor: '#F1D2D2' },
  btnText: { fontFamily: font[700], fontSize: 15 },
  btnTextSm: { fontSize: 13 },
  field: { marginBottom: 12, gap: 6 },
  fieldLabel: { fontFamily: font[600], fontSize: 13, color: colors.inkSoft },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontFamily: font[500], fontSize: 16, color: colors.ink, backgroundColor: colors.surface },
  tabs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingVertical: 8 },
  tab: { flexDirection: 'row', alignItems: 'center', gap: 6, height: 36, paddingHorizontal: 14, borderRadius: 18, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  tabOn: { backgroundColor: colors.ink, borderColor: colors.ink },
  tabText: { fontFamily: font[600], fontSize: 14, color: colors.ink },
  tabN: { minWidth: 20, height: 20, paddingHorizontal: 6, borderRadius: 10, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  tabNText: { fontFamily: font[700], fontSize: 12, color: colors.primaryDeep },
  card: { padding: 14, marginBottom: 10, borderRadius: 16, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginTop: 12 },
  muted: { fontFamily: font[500], fontSize: 13, color: colors.muted },
  name: { fontFamily: font[700], fontSize: 15, color: colors.ink },
  body: { fontFamily: font[500], fontSize: 15, lineHeight: 21, color: colors.ink },
  section: { fontFamily: font[800], fontSize: 17, color: colors.ink, marginTop: 20, marginBottom: 10 },
  err: { fontFamily: font[600], fontSize: 14, color: '#C93C3C', marginVertical: 6 },
  hint: { fontFamily: font[500], fontSize: 13, color: colors.muted, lineHeight: 18, marginVertical: 8 },
  empty: { alignItems: 'center', gap: 14, paddingVertical: 40, paddingHorizontal: 24 },
  emptyText: { fontFamily: font[500], fontSize: 15, color: colors.inkSoft, textAlign: 'center', lineHeight: 21 },
  thumb: { width: 48, height: 48, borderRadius: 10, backgroundColor: colors.photo },
  pick: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 8, marginBottom: 8, borderRadius: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface },
  sheetOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.42)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, paddingHorizontal: 16, paddingTop: 8, maxHeight: '90%' },
  grab: { width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border, alignSelf: 'center', marginBottom: 12 },
  sheetTitle: { fontFamily: font[800], fontSize: 19, color: colors.ink, marginBottom: 12 },
  status: { alignSelf: 'flex-start', paddingHorizontal: 8, height: 22, borderRadius: 11, justifyContent: 'center', backgroundColor: colors.sunken },
  statusText: { fontFamily: font[700], fontSize: 12, color: colors.inkSoft },
})
