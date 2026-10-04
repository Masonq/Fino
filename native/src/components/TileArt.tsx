import { Image } from 'expo-image'
import { useState } from 'react'

import { artLayout, ART_POSITION, type TileFit } from '../artFit'

// код раздела из адреса картинки (…/cat/<код>.png) — по нему форма и заполненность из catArt.json
const slugOf = (uri: string) => (String(uri).match(/\/cat\/([^/?]+)\.png/) || [])[1] || ''

/** Картинка плитки: размер — по её форме (artBox), прижата к правому нижнему углу, целиком внутри плитки. */
export default function TileArt({ uri, name, fit }: { uri: string; name: string; fit: TileFit }) {
  const [aspect, setAspect] = useState(1.3)
  return (
    <Image
      source={{ uri }}
      style={artLayout(name, fit, slugOf(uri), aspect).box}
      contentFit="contain"
      contentPosition={ART_POSITION}
      transition={150}
      onLoad={(e) => { const { width, height } = e.source; if (width && height) setAspect(width / height) }}
    />
  )
}
