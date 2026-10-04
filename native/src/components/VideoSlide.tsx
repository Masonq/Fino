import { useVideoPlayer, VideoView } from 'expo-video'
import { useEffect, useState } from 'react'
import { Pressable, StyleSheet, View } from 'react-native'

import { tr } from '../i18n'
import Icon from './Icon'

/**
 * Видео в галерее объявления — как на сайте: играет само, без звука, по кругу; кнопка звука в углу.
 * active — видно ли это фото сейчас: невидимое видео ставим на паузу, чтобы не тратить батарею и трафик.
 */
export default function VideoSlide({ uri, active, width, height, top }: { uri: string; active: boolean; width: number; height: number; top: number }) {
  const [muted, setMuted] = useState(true)
  const player = useVideoPlayer(uri, (p) => { p.loop = true; p.muted = true })
  useEffect(() => { if (active) player.play(); else player.pause() }, [active, player])
  useEffect(() => { player.muted = muted }, [muted, player])
  return (
    <View style={{ position: 'absolute', left: 0, top, width, height }}>
      <VideoView player={player} style={StyleSheet.absoluteFill} contentFit="contain" nativeControls={false} allowsPictureInPicture={false} />
      <Pressable style={styles.sound} onPress={() => setMuted(!muted)} hitSlop={8} accessibilityLabel={tr(muted ? 'Включить звук' : 'Выключить звук')}>
        <Icon name={muted ? 'soundOff' : 'soundOn'} size={18} color="#fff" />
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  sound: { position: 'absolute', right: 12, bottom: 12, width: 38, height: 38, borderRadius: 19, backgroundColor: 'rgba(20,26,22,0.55)', alignItems: 'center', justifyContent: 'center' },
})
