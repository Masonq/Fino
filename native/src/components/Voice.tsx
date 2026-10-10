/**
 * Голосовые в переписке — как на сайте: удерживать кнопку — запись (до 2 минут), отпустить — отправить,
 * увести палец влево — отмена. Проигрывание — кнопка, полоска прогресса и длительность.
 */
import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioPlayer, useAudioPlayerStatus, useAudioRecorder } from 'expo-audio'
import * as Haptics from 'expo-haptics'
import { useRef, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import Pressable from './Pressable'
import { API } from '../config'
import { tr } from '../i18n'
import { colors, font } from '../theme'
import Icon from './Icon'
import { mediaUrl } from '../config'

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

export function VoicePlayer({ url, seconds, mine }: { url: string; seconds?: number | null; mine: boolean }) {
  const player = useAudioPlayer({ uri: mediaUrl(url) || url })
  const st = useAudioPlayerStatus(player)
  const dur = st.duration || seconds || 0
  const pos = st.currentTime || 0
  const toggle = () => {
    if (st.playing) player.pause()
    else { if (dur && pos >= dur - 0.1) player.seekTo(0); setAudioModeAsync({ playsInSilentMode: true }).catch(() => {}); player.play() }
  }
  const fg = mine ? '#FFFFFF' : colors.ink
  return (
    <View style={s.player}>
      <Pressable onPress={toggle} style={[s.play, { backgroundColor: mine ? 'rgba(255,255,255,0.22)' : colors.sunken }]} hitSlop={6} accessibilityLabel={st.playing ? tr('Пауза') : tr('Слушать')}>
        <Icon name={st.playing ? 'pause' : 'play'} size={16} color={fg} />
      </Pressable>
      <View style={[s.track, { backgroundColor: mine ? 'rgba(255,255,255,0.3)' : colors.sunken }]}>
        <View style={[s.fill, { width: `${dur ? Math.min(100, (pos / dur) * 100) : 0}%`, backgroundColor: mine ? '#FFFFFF' : colors.primary }]} />
      </View>
      <Text style={[s.time, { color: fg }]}>{mmss(st.playing || pos > 0 ? pos : dur)}</Text>
    </View>
  )
}

export function VoiceButton({ token, chatId, replyTo, onSent, onError }: {
  token: string; chatId: string; replyTo?: string | null; onSent: (m: unknown) => void; onError: (msg: string) => void
}) {
  const rec = useAudioRecorder(RecordingPresets.HIGH_QUALITY)
  const [on, setOn] = useState(false)
  const [secs, setSecs] = useState(0)
  const pressed = useRef(false)
  const cancel = useRef(false)
  const started = useRef(0)
  const tick = useRef<ReturnType<typeof setInterval> | null>(null)

  const start = async () => {
    pressed.current = true; cancel.current = false
    const perm = await AudioModule.requestRecordingPermissionsAsync()
    if (!perm.granted) { pressed.current = false; onError(tr('Нет доступа к микрофону — разрешите его в настройках iPhone')); return }
    // пока спрашивали разрешение, палец могли отпустить — тогда только подсказка
    if (!pressed.current) { onError(tr('Удерживайте кнопку, пока говорите')); return }
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true })
    await rec.prepareToRecordAsync()
    rec.record()
    started.current = Date.now()
    setOn(true); setSecs(0)
    tick.current = setInterval(() => { const n = (Date.now() - started.current) / 1000; setSecs(n); if (n >= 120) stop() }, 250)
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {})
  }
  const stop = async () => {
    pressed.current = false
    if (tick.current) clearInterval(tick.current)
    if (!on && !rec.isRecording) return
    setOn(false)
    await rec.stop().catch(() => {})
    await setAudioModeAsync({ allowsRecording: false }).catch(() => {})
    const dur = (Date.now() - started.current) / 1000
    if (cancel.current) return
    if (dur < 0.8 || !rec.uri) { onError(tr('Удерживайте кнопку, пока говорите')); return }
    const fd = new FormData()
    fd.append('file', { uri: rec.uri, name: 'voice.m4a', type: 'audio/mp4' } as unknown as Blob)
    fd.append('seconds', String(Math.round(dur)))
    if (replyTo) fd.append('reply_to_id', replyTo)
    try {
      const r = await fetch(`${API}/chats/${encodeURIComponent(chatId)}/voice`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd })
      if (!r.ok) throw new Error(String(r.status))
      onSent(await r.json())
    } catch { onError(tr('Не удалось отправить голосовое')) }
  }

  return (
    <>
      {on && (
        <View style={s.recBar} pointerEvents="none">
          <View style={s.dot} /><Text style={s.recText}>{mmss(secs)}</Text><Text style={s.recHint}>{tr('Отпустите — отправится, влево — отмена')}</Text>
        </View>
      )}
      <Pressable onPressIn={start} onPressOut={stop}
        onTouchMove={(e) => { if (on && e.nativeEvent.locationX < -80) { cancel.current = true; stop() } }}
        style={[s.mic, on && s.micOn]} accessibilityLabel={tr('Удерживайте, чтобы записать голосовое')}>
        <Icon name="mic" size={22} color={on ? '#FFFFFF' : colors.ink} />
      </Pressable>
    </>
  )
}

const s = StyleSheet.create({
  player: { flexDirection: 'row', alignItems: 'center', gap: 10, minWidth: 190 },
  play: { width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center' },
  track: { flex: 1, height: 4, borderRadius: 2, overflow: 'hidden' },
  fill: { height: 4, borderRadius: 2 },
  time: { fontFamily: font[600], fontSize: 12.5, minWidth: 34, textAlign: 'right' },
  mic: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.sunken },
  micOn: { backgroundColor: '#E5533D', transform: [{ scale: 1.15 }] },
  recBar: { position: 'absolute', left: 0, right: 56, bottom: 4, height: 44, borderRadius: 22, backgroundColor: colors.surface, flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#E5533D' },
  recText: { fontFamily: font[800], fontSize: 15, color: colors.ink },
  recHint: { flex: 1, fontFamily: font[400], fontSize: 12.5, color: colors.muted },
})
