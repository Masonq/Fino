import { Pressable, StyleSheet, Text } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { tr } from '../i18n'
import { retryAll, useOffline } from '../net'
import { colors, font } from '../theme'

/** Нет связи с сервером — плашка сверху: показываем сохранённое; «Повторить» перезагружает экраны. */
export default function OfflineBanner() {
  const offline = useOffline()
  const insets = useSafeAreaInsets()
  if (!offline) return null
  return (
    <Pressable style={[styles.bar, { top: insets.top + 6 }]} onPress={retryAll} accessibilityRole="button">
      <Text style={styles.text}>{tr('Нет интернета — показываем сохранённое')}</Text>
      <Text style={styles.retry}>{tr('Повторить')}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  bar: {
    position: 'absolute', left: 12, right: 12, zIndex: 50, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 10,
    borderRadius: 14, backgroundColor: '#1C2620', shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 6,
  },
  text: { flex: 1, color: '#fff', fontSize: 13.5, fontFamily: font[700] },
  retry: { color: colors.accent, fontSize: 13.5, fontFamily: font[800] },
})
