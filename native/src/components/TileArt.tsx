import { Image } from 'expo-image'
import { useState } from 'react'

import { artBox, ART_POSITION, type TileFit } from '../artFit'

/** Картинка плитки: размер — по её форме (artBox), прижата к правому нижнему углу, целиком внутри плитки. */
export default function TileArt({ uri, name, fit }: { uri: string; name: string; fit: TileFit }) {
  const [aspect, setAspect] = useState(1.3)
  return (
    <Image
      source={{ uri }}
      style={artBox(name, fit, aspect)}
      contentFit="contain"
      contentPosition={ART_POSITION}
      transition={150}
      onLoad={(e) => { const { width, height } = e.source; if (width && height) setAspect(width / height) }}
    />
  )
}
