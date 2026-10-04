import { Image } from 'expo-image'
import { useState } from 'react'
import { Text, type StyleProp, type TextStyle } from 'react-native'

import { artLayout, ART_POSITION, TILE, type TextLine, type TileFit } from '../artFit'

// код раздела из адреса картинки (…/cat/<код>.png) — по нему форма и заполненность из catArt.json
const slugOf = (uri: string) => (String(uri).match(/\/cat\/([^/?]+)\.png/) || [])[1] || ''

/** Картинка плитки: размер — по её форме и строкам надписи (lines — настоящие, если уже известны), в правом нижнем углу. */
export default function TileArt({ uri, name, fit, lines = null }: { uri: string; name: string; fit: TileFit; lines?: TextLine[] | null }) {
  const [aspect, setAspect] = useState(1.3)
  return (
    <Image
      source={{ uri }}
      style={artLayout(name, fit, slugOf(uri), aspect, lines).box}
      contentFit="contain"
      contentPosition={ART_POSITION}
      transition={150}
      onLoad={(e) => { const { width, height } = e.source; if (width && height) setAspect(width / height) }}
    />
  )
}

/**
 * Надпись и картинка плитки вместе: строки надписи берутся из настоящей раскладки текста (onTextLayout), и картинка
 * поднимается рядом с короткими строками. Оценка по самому широкому шрифту осторожнее настоящего текста —
 * картинка по ней выходила мельче, чем позволяет место.
 */
export function TileLabelArt({ uri, name, fit, style }: { uri: string; name: string; fit: TileFit; style: StyleProp<TextStyle> }) {
  const [lines, setLines] = useState<TextLine[] | null>(null)
  const narrowed = artLayout(name, fit, slugOf(uri)).fit
  return (
    <>
      <Text style={[style, { maxWidth: narrowed.text }]}
        onTextLayout={(e) => {
          const next = e.nativeEvent.lines.map((l) => ({ right: Math.ceil(TILE.pad + l.x + l.width), bottom: Math.ceil(TILE.pad + l.y + l.height - 1) }))
          setLines((prev) => (prev && JSON.stringify(prev) === JSON.stringify(next) ? prev : next))
        }}>{name}</Text>
      <TileArt uri={uri} name={name} fit={narrowed} lines={lines} />
    </>
  )
}
