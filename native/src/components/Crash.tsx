import * as Updates from 'expo-updates'
import { Component, type ReactNode, useEffect, useState } from 'react'
import { DevSettings, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

/**
 * Вместо молчаливого закрытия приложения — экран с текстом ошибки и «Перезапустить»: по скриншоту видно
 * причину. Ловит и ошибки отрисовки (граница), и ошибки вне отрисовки (глобальный обработчик JS) —
 * в релизной сборке такие иначе закрывают приложение. Тексты — без перевода: экран должен работать,
 * даже если сломался сам перевод.
 */
type Err = { message: string; stack?: string }
let listener: ((e: Err) => void) | null = null
let pending: Err | null = null

const g = globalThis as unknown as { ErrorUtils?: { getGlobalHandler: () => (e: unknown, fatal?: boolean) => void; setGlobalHandler: (h: (e: unknown, fatal?: boolean) => void) => void } }
if (g.ErrorUtils) {
  const prev = g.ErrorUtils.getGlobalHandler()
  g.ErrorUtils.setGlobalHandler((e, fatal) => {
    const err = { message: e instanceof Error ? e.message : String(e), stack: e instanceof Error ? e.stack : undefined }
    if (fatal) { if (listener) listener(err); else pending = err; return }
    prev(e, fatal)
  })
}

function CrashScreen({ error }: { error: Err }) {
  return (
    <View style={styles.page}>
      <Text style={styles.title}>Приложение споткнулось</Text>
      <Text style={styles.text}>Сделайте скриншот этого экрана и пришлите — по нему видно, что сломалось.</Text>
      <ScrollView style={styles.box}>
        <Text selectable style={styles.mono}>{error.message}{'\n\n'}{(error.stack ?? '').split('\n').slice(0, 12).join('\n')}</Text>
      </ScrollView>
      <Pressable style={styles.btn} onPress={() => (Updates.isEnabled ? Updates.reloadAsync().catch(() => {}) : DevSettings.reload())}>
        <Text style={styles.btnText}>Перезапустить</Text>
      </Pressable>
    </View>
  )
}

class Boundary extends Component<{ children: ReactNode; onError: (e: Err) => void }, { error: Err | null }> {
  state = { error: null as Err | null }
  static getDerivedStateFromError(e: unknown) { return { error: { message: e instanceof Error ? e.message : String(e), stack: e instanceof Error ? e.stack : undefined } } }
  render() { return this.state.error ? <CrashScreen error={this.state.error} /> : this.props.children }
}

export default function CrashGuard({ children }: { children: ReactNode }) {
  const [error, setError] = useState<Err | null>(pending)
  useEffect(() => { listener = setError; return () => { listener = null } }, [])
  if (error) return <CrashScreen error={error} />
  return <Boundary onError={setError}>{children}</Boundary>
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#FAFAF9', paddingTop: 80, paddingHorizontal: 20, gap: 12 },
  title: { fontSize: 22, fontWeight: '800', color: '#1C2620' },
  text: { fontSize: 15, lineHeight: 21, color: '#4B554E' },
  box: { maxHeight: 360, backgroundColor: '#F2F2EF', borderRadius: 12, padding: 12 },
  mono: { fontFamily: 'Menlo', fontSize: 12, color: '#1C2620' },
  btn: { height: 50, borderRadius: 14, backgroundColor: '#0E9F6E', alignItems: 'center', justifyContent: 'center' },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
})
