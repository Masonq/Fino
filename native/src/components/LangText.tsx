/**
 * Заголовок, который после смены языка проявляется волной — как на сайте: слова по очереди всплывают снизу.
 * Экраны после смены языка пересоздаются, поэтому смотрим на время смены (langChangedAt), а не на изменение текста.
 * mode="scramble" — буквы перемешиваются и собираются слева направо (подводки, приветствие).
 */
import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, type StyleProp, Text, type TextStyle, View } from 'react-native'
import { langChangedAt } from '../i18n'

const CH = 'абвгдежзиклмнопрстуabcdefghijklmnopršđžčć'

export default function LangText({ children, style, mode = 'wave', numberOfLines }: { children: string; style?: StyleProp<TextStyle>; mode?: 'wave' | 'scramble'; numberOfLines?: number }) {
  const fresh = useRef(Date.now() - langChangedAt < 1800).current
  const words = String(children).split(' ')
  const vals = useRef(words.map(() => new Animated.Value(fresh && mode === 'wave' ? 0 : 1))).current
  const [shown, setShown] = useState(fresh && mode === 'scramble' ? '' : String(children))
  useEffect(() => {
    if (!fresh) return undefined
    if (mode === 'wave') {
      Animated.stagger(55, vals.map((v) => Animated.spring(v, { toValue: 1, stiffness: 260, damping: 16, useNativeDriver: true }))).start()
      return undefined
    }
    const text = String(children), t0 = Date.now(), ms = 600
    const id = setInterval(() => {
      const p = Math.min(1, (Date.now() - t0) / ms)
      setShown([...text].map((c, i) => (i / text.length < p || c === ' ' ? c : CH[Math.floor(Math.random() * CH.length)])).join(''))
      if (p >= 1) clearInterval(id)
    }, 30)
    return () => clearInterval(id)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!fresh || mode === 'scramble') return <Text style={style} numberOfLines={numberOfLines}>{mode === 'scramble' && fresh ? shown : children}</Text>
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap' }} accessible accessibilityLabel={String(children)}>
      {words.map((w, i) => (
        <Animated.Text key={i} style={[style, { opacity: vals[i], transform: [{ translateY: vals[i].interpolate({ inputRange: [0, 1], outputRange: [14, 0] }) }] }]}>
          {w}{i < words.length - 1 ? ' ' : ''}
        </Animated.Text>
      ))}
    </View>
  )
}
