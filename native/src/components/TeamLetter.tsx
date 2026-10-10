import { router } from 'expo-router'
import type { ReactElement } from 'react'
import { Linking, StyleSheet, Text, View } from 'react-native'
import Pressable from './Pressable'

import { colors, font } from '../theme'

/**
 * Письмо команды — как teamText сайта: «# заголовок», «- пункт» (зелёные точки), «[[Подпись|/путь]]» — кнопка
 * (только внутренние пути), ссылки нажимаются, **жирный**. Выравнивание — по левому краю.
 */
function Inline({ text, style }: { text: string; style?: object }) {
  const parts = text.split(/(https?:\/\/\S+)/g)
  return (
    <Text style={style}>
      {parts.map((chunk, i) => (/^https?:\/\//.test(chunk)
        ? <Text key={i} style={styles.link} onPress={() => Linking.openURL(chunk)}>{chunk}</Text>
        : chunk.split(/\*\*(.+?)\*\*/g).map((p, j) => (j % 2 ? <Text key={`${i}-${j}`} style={styles.bold}>{p}</Text> : p))))}
    </Text>
  )
}

export default function TeamLetter({ text }: { text: string }) {
  const lines = String(text || '').split('\n')
  const blocks: ReactElement[] = []
  let list: ReactElement[] | null = null
  const flush = () => { if (list) { blocks.push(<View key={`u${blocks.length}`} style={styles.list}>{list}</View>); list = null } }
  lines.forEach((raw, i) => {
    const line = raw.trimEnd()
    if (/^[-•*]\s+/.test(line)) {
      list = list || []
      list.push(<View key={`i${i}`} style={styles.li}><View style={styles.dot} /><Inline text={line.replace(/^[-•*]\s+/, '')} style={styles.p} /></View>)
      return
    }
    flush()
    const button = line.match(/^\[\[(.+?)\|(\/[A-Za-z0-9_\-/]*)\]\]$/)
    if (button) {
      blocks.push(<Pressable key={`b${i}`} style={styles.btn} onPress={() => router.push(button[2] as never)} accessibilityRole="button"><Text style={styles.btnText}>{button[1]}</Text></Pressable>)
      return
    }
    if (!line) return
    if (/^#{1,3}\s+/.test(line)) { blocks.push(<Inline key={`h${i}`} text={line.replace(/^#{1,3}\s+/, '')} style={styles.head} />); return }
    blocks.push(<Inline key={`p${i}`} text={line} style={styles.p} />)
  })
  flush()
  return <View style={styles.letter}>{blocks}</View>
}

const styles = StyleSheet.create({
  letter: { gap: 8 },
  head: { fontSize: 15, lineHeight: 20, fontFamily: font[800], color: colors.ink, letterSpacing: -0.15 },
  p: { flex: 1, fontSize: 14.5, lineHeight: 21, fontFamily: font[400], color: colors.ink },
  bold: { fontFamily: font[800] },
  link: { color: colors.primaryDeep, fontFamily: font[700] },
  list: { gap: 7 },
  li: { flexDirection: 'row', gap: 10, paddingLeft: 2 },
  dot: { width: 5, height: 5, borderRadius: 3, backgroundColor: colors.primary, marginTop: 8 },
  btn: { alignSelf: 'flex-start', minHeight: 44, paddingHorizontal: 24, borderRadius: 999, marginTop: 2, backgroundColor: colors.primary, justifyContent: 'center' },
  btnText: { color: '#fff', fontSize: 15, fontFamily: font[800] },
})
