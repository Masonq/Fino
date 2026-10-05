/**
 * PLONK — ролик v4, 16 с (480 кадров, 30 к/с, 90 BPM: доля = 20 кадров).
 * По рекомендациям TikTok: зацепка с движением в первые 3 с и суть продукта до 3-й секунды, 9–16 с длины,
 * текст 5–10 слов в секунду и только в безопасной зоне, монтаж в долю, «врезки» на элементы интерфейса,
 * переход-совпадение (фото вещи «влетает» в экран телефона), плитки, собирающиеся в сетку, призыв в конце.
 */
import React from 'react'
import { AbsoluteFill, Easing, Img, interpolate, Sequence, spring, useCurrentFrame } from 'remotion'
import { FakeVideo, real, ShopCard, Side } from './PromoReal'
import { C, Film, FONT, LightLeaks, Logo, Nav } from './ui'

const clamp = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const }
const out3 = Easing.bezier(0.16, 1, 0.3, 1)
const sp = (f: number, d = 12, m = 0.6) => spring({ frame: f, fps: 30, config: { damping: d, mass: m } })

/** Слово-«удар»: влетает крупно и садится на место в долю музыки. */
const Slam: React.FC<{ text: string; at: number; size?: number; color?: string; bg?: string; rot?: number }> = ({ text, at, size = 150, color = '#fff', bg, rot = 0 }) => {
  const f = useCurrentFrame()
  if (f < at) return null
  const s = sp(f - at, 10, 0.5)
  return (
    <div style={{ display: 'inline-block', fontSize: size, fontWeight: 800, letterSpacing: -size * 0.035, lineHeight: 1, color, background: bg, padding: bg ? '10px 28px 16px' : 0, borderRadius: bg ? 28 : 0,
      transform: `scale(${1.6 - 0.6 * s}) rotate(${rot}deg)`, opacity: Math.min(1, s * 2), filter: `blur(${(1 - s) * 6}px)` }}>{text}</div>
  )
}

// ---------- 0–1,3 с: «Продаёшь вещь?» поверх быстрой смены настоящих вещей ----------
const STROBE = ['8d82e428-0', '353db02c-0', 'f5d3c313-0-crop', 'cb2d407d-0', '2c893f74-1', 'd0ca9165-0', '8d82e428-1', '353db02c-1']
const Hook: React.FC = () => {
  const f = useCurrentFrame()
  const ph = STROBE[Math.floor(f / 5) % STROBE.length]
  return (
    <AbsoluteFill style={{ background: '#000', fontFamily: FONT }}>
      <Img src={real(ph)} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.15 - (f % 5) * 0.02})`, filter: 'brightness(.55) saturate(1.1)' }} />
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(14,159,110,.55), rgba(14,159,110,.15) 45%, rgba(0,0,0,.35))' }} />
      <div style={{ position: 'absolute', top: 250, left: 0, right: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 18 }}>
        <Logo size={64} /><span style={{ color: '#fff', fontSize: 52, fontWeight: 800, letterSpacing: -1 }}>PLONK</span>
      </div>
      <div style={{ position: 'absolute', top: 720, left: 0, right: 0, textAlign: 'center' }}>
        <div><Slam text="Продаёшь" at={0} /></div>
        <div style={{ marginTop: 16 }}><Slam text="вещь?" at={10} size={190} bg={C.o} rot={-3} /></div>
      </div>
    </AbsoluteFill>
  )
}

// ---------- 1,3–3,3 с: «Покажи её на видео» → фото влетает в экран телефона ----------
const PH_W = 393 * 1.42, PH_H = 852 * 1.42, PH_TOP = 400
const Reveal: React.FC = () => {
  const f = useCurrentFrame()
  // фото на весь кадр сжимается ровно в экран телефона (переход-совпадение)
  const m = interpolate(f, [16, 40], [0, 1], { ...clamp, easing: out3 })
  const W = interpolate(m, [0, 1], [1080, PH_W]), H = interpolate(m, [0, 1], [1920, PH_H - 84 * 1.42])
  const L = (1080 - W) / 2, T = interpolate(m, [0, 1], [0, PH_TOP])
  const R = interpolate(m, [0, 1], [0, 54 * 1.42])
  const frame = interpolate(f, [34, 42], [0, 1], clamp)
  const badge = sp(f - 34, 11)
  return (
    <AbsoluteFill style={{ background: '#0F1612', fontFamily: FONT, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', left: -380, top: -260, background: 'rgba(14,159,110,.3)', filter: 'blur(60px)' }} />
      {/* корпус телефона проявляется вокруг фото */}
      <div style={{ position: 'absolute', left: (1080 - PH_W) / 2 - 14, top: PH_TOP - 14, width: PH_W + 28, height: PH_H + 28, borderRadius: 62 * 1.42, background: '#111', opacity: frame, boxShadow: '0 40px 90px rgba(0,0,0,.5)' }} />
      <div style={{ position: 'absolute', left: (1080 - PH_W) / 2, top: PH_TOP, width: PH_W, height: PH_H, borderRadius: 54 * 1.42, background: '#000', opacity: frame }} />
      <div style={{ position: 'absolute', left: L, top: T, width: W, height: H, borderRadius: R, overflow: 'hidden' }}>
        <Img src={real('8d82e428-0')} style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.12 - m * 0.06})` }} />
      </div>
      <div style={{ position: 'absolute', left: (1080 - PH_W) / 2, top: PH_TOP + PH_H - 84 * 1.42, width: PH_W, height: 84 * 1.42, overflow: 'hidden', borderRadius: `0 0 ${54 * 1.42}px ${54 * 1.42}px`, opacity: frame }}>
        <div style={{ position: 'absolute', left: 0, top: 0, width: 393, height: 84, transform: 'scale(1.42)', transformOrigin: 'top left' }}><div style={{ position: 'relative', width: 393, height: 84 }}><Nav active="shops" dark /></div></div>
      </div>
      <div style={{ position: 'absolute', top: 230, left: 60, right: 60, textAlign: 'center', opacity: interpolate(f, [0, 6, 30, 36], [0, 1, 1, 0], clamp) }}>
        <div style={{ fontSize: 96, fontWeight: 800, color: '#fff', letterSpacing: -3, lineHeight: 1.05 }}>Покажи её<br /><span style={{ color: '#7BE3B5' }}>на видео</span></div>
      </div>
      <div style={{ position: 'absolute', top: 240, left: 0, right: 0, display: 'flex', justifyContent: 'center', transform: `scale(${badge})`, opacity: badge }}>
        <div style={{ padding: '20px 34px', borderRadius: 30, background: '#fff', color: C.ink, fontSize: 50, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 16, boxShadow: '0 16px 40px rgba(0,0,0,.35)' }}>
          <Logo size={58} />Объявления с видео
        </div>
      </div>
    </AbsoluteFill>
  )
}

// ---------- 3,3–7,3 с: шопсы — двойной тап, свайп, «врезка» на карточку, «Написать» ----------
const Shops: React.FC = () => {
  const f = useCurrentFrame()
  const tap = 18
  const liked = f >= tap
  const burst = sp(f - tap, 9, 0.7)
  const burstOut = interpolate(f, [tap + 10, tap + 24], [1, 0], clamp)
  const swipe = interpolate(f, [40, 52], [0, -768], { ...clamp, easing: out3 })
  const card1 = sp(f - 2, 13, 0.7)
  const card2 = sp(f - 56, 13, 0.7)
  // «врезка»: камера наезжает на карточку товара и возвращается
  const zin = interpolate(f, [72, 86, 108, 120], [0, 1, 1, 0], { ...clamp, easing: Easing.inOut(Easing.cubic) })
  const shade = <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '48%', background: 'linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.18) 35%,rgba(0,0,0,.62))' }} />
  return (
    <AbsoluteFill style={{ background: '#0F1612', fontFamily: FONT, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', left: -380, top: -260, background: 'rgba(14,159,110,.3)', filter: 'blur(60px)' }} />
      <div style={{ position: 'absolute', width: 700, height: 700, borderRadius: '50%', right: -300, bottom: -100, background: 'rgba(255,106,61,.16)', filter: 'blur(60px)' }} />
      <div style={{ position: 'absolute', top: 230, left: 60, right: 60, textAlign: 'center', fontSize: 74, fontWeight: 800, color: '#fff', letterSpacing: -2, lineHeight: 1.1, opacity: 1 - zin }}>
        {f < 60 ? <>Нравится — <span style={{ color: C.heart }}>лайк</span></> : <>Хочешь — <span style={{ color: '#7BE3B5' }}>пиши</span></>}
      </div>
      <div style={{ position: 'absolute', left: (1080 - PH_W) / 2, top: PH_TOP, width: 393, height: 852, transformOrigin: 'top left',
        transform: `translate(${-zin * 245}px, ${-zin * 1050}px) scale(${1.42 + zin * 0.95})` }}>
        <div style={{ position: 'absolute', inset: -10, borderRadius: 62, background: '#111' }} />
        <div style={{ position: 'absolute', inset: 0, borderRadius: 54, overflow: 'hidden', background: '#000' }}>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 768, overflow: 'hidden' }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: swipe, height: 768, overflow: 'hidden' }}>
              <FakeVideo photos={['8d82e428-0', '8d82e428-1', '8d82e428-3', '8d82e428-4']} every={10} />
              {shade}
              {liked && <div style={{ position: 'absolute', left: '50%', top: '40%', transform: `translate(-50%,-50%) scale(${burst * 1.15})`, opacity: burstOut }}>
                <svg width="120" height="120" viewBox="0 0 24 24"><path fill={C.heart} d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
              </div>}
              <Side who="А" liked={liked} likes={liked ? 214 : 213} pulse={liked ? Math.max(0, 1 - (f - tap) / 8) : 0} />
              <div style={{ position: 'absolute', left: 12, right: 74, bottom: 20, color: '#fff' }}>
                <div style={{ fontSize: 15, fontWeight: 700 }}>Алекс</div>
                <ShopCard photo="8d82e428-0" title="Оригинальные кеды Trussardi" price="5 000 RSD" t={card1} />
              </div>
            </div>
            <div style={{ position: 'absolute', left: 0, right: 0, top: swipe + 768, height: 768, overflow: 'hidden' }}>
              <FakeVideo photos={['353db02c-0', '353db02c-1', '353db02c-2']} every={12} />
              {shade}
              <Side who="Н" liked={false} likes={87} pulse={0} />
              <div style={{ position: 'absolute', left: 12, right: 74, bottom: 20, color: '#fff' }}>
                <div style={{ fontSize: 15, fontWeight: 700 }}>Никола</div>
                <ShopCard photo="353db02c-0" title="LAVA ME 4 Carbon" price="650 €" t={card2} press={f >= 98 && f < 106} />
              </div>
            </div>
          </div>
          <Nav active="shops" dark />
          <div style={{ position: 'absolute', top: 11, left: '50%', transform: 'translateX(-50%)', width: 120, height: 34, borderRadius: 20, background: '#000' }} />
        </div>
        {f >= 96 && f < 108 && <div style={{ position: 'absolute', left: 300, top: 719, width: 44, height: 44, marginLeft: -22, marginTop: -22, borderRadius: 22, background: 'rgba(255,255,255,.4)', border: '2px solid #fff' }} />}
      </div>
    </AbsoluteFill>
  )
}

// ---------- 7,3–9,3 с: чат — сообщения сыплются в долю ----------
const Chat: React.FC = () => {
  const f = useCurrentFrame()
  const msgs: [string, boolean, number][] = [['Здравствуйте! Гитара ещё продаётся?', true, 4], ['Да! Могу показать сегодня 🙌', false, 20], ['Отлично, буду в 18:00', true, 36]]
  const enter = interpolate(f, [0, 10], [0, 1], { ...clamp, easing: out3 })
  return (
    <AbsoluteFill style={{ background: C.bg, fontFamily: FONT, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', left: -380, top: -300, background: C.gs, filter: 'blur(40px)' }} />
      <div style={{ position: 'absolute', top: 230, left: 60, right: 60, textAlign: 'center', fontSize: 74, fontWeight: 800, color: C.ink, letterSpacing: -2, lineHeight: 1.1 }}>
        Договорились <span style={{ color: C.g }}>в чате</span>
      </div>
      <div style={{ position: 'absolute', left: 90, right: 90, top: 600, display: 'flex', flexDirection: 'column', gap: 26, transform: `translateY(${(1 - enter) * 80}px)`, opacity: enter }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, padding: 18, borderRadius: 28, background: '#fff', boxShadow: '0 10px 30px rgba(20,30,25,.08)' }}>
          <Img src={real('353db02c-0')} style={{ width: 90, height: 90, borderRadius: 18, objectFit: 'cover' }} />
          <div><div style={{ fontSize: 34, fontWeight: 700, color: C.ink }}>LAVA ME 4 Carbon</div><div style={{ fontSize: 34, fontWeight: 800, color: C.ink }}>650 €</div></div>
        </div>
        {msgs.map(([t, mine, at]) => {
          const s = sp(f - at, 12, 0.6)
          return f >= at ? (
            <div key={t} style={{ alignSelf: mine ? 'flex-end' : 'flex-start', maxWidth: 720, padding: '24px 32px', fontSize: 40, lineHeight: 1.25, borderRadius: mine ? '36px 36px 10px 36px' : '36px 36px 36px 10px',
              background: mine ? C.g : '#fff', color: mine ? '#fff' : C.ink, boxShadow: '0 10px 26px rgba(20,30,25,.1)', transform: `scale(${s})`, transformOrigin: mine ? 'right bottom' : 'left bottom' }}>{t}</div>
          ) : null
        })}
      </div>
    </AbsoluteFill>
  )
}

// ---------- 9,3–12,7 с: вещи собираются в сетку, слова — в долю ----------
const GRID: [string, string][] = [['f5d3c313-0-crop', '15 000 RSD'], ['8d82e428-0', '5 000 RSD'], ['353db02c-0', '650 €'], ['cb2d407d-0', '5 500 RSD'], ['2c893f74-1', '400 €'], ['d0ca9165-0', '8 000 RSD']]
const WORDS: [string, number][] = [['Платья', 0], ['Кеды', 10], ['Гитары', 20], ['Техника', 30]]
const Grid: React.FC = () => {
  const f = useCurrentFrame()
  const word = [...WORDS].reverse().find(([, at]) => f >= at)
  const fin = f >= 52
  return (
    <AbsoluteFill style={{ background: C.bg, fontFamily: FONT, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 800, height: 800, borderRadius: '50%', right: -300, top: -200, background: '#FFEDE6', filter: 'blur(50px)' }} />
      <div style={{ position: 'absolute', top: 230, left: 0, right: 0, textAlign: 'center' }}>
        {fin ? <Slam text="Всё рядом с тобой" at={52} size={84} color={C.ink} /> : word && <Slam key={word[0]} text={word[0]} at={word[1]} size={120} color={C.ink} />}
      </div>
      <div style={{ position: 'absolute', left: 60, right: 60, top: 470, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {GRID.map(([p, price], i) => {
          const s = sp(f - i * 7, 13, 0.6)
          const fromX = (i % 2 ? 1 : -1) * 700, fromY = 300
          return (
            <div key={p} style={{ position: 'relative', height: 330, borderRadius: 30, overflow: 'hidden', background: '#fff', boxShadow: '0 14px 34px rgba(20,30,25,.14)',
              transform: `translate(${(1 - s) * fromX}px, ${(1 - s) * fromY}px) rotate(${(1 - s) * (i % 2 ? 12 : -12)}deg)` }}>
              <Img src={real(p)} style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.1 - Math.min(1, f / 90) * 0.08})` }} />
              <div style={{ position: 'absolute', left: 14, bottom: 14, padding: '8px 16px', borderRadius: 16, background: '#fff', fontSize: 32, fontWeight: 800, color: C.ink }}>{price}</div>
            </div>
          )
        })}
      </div>
    </AbsoluteFill>
  )
}

// ---------- 12,7–16 с: призыв ----------
const End: React.FC = () => {
  const f = useCurrentFrame()
  const btn = sp(f - 12, 10, 0.6)
  const pulse = 1 + Math.max(0, Math.sin((f - 30) / 20 * Math.PI)) * 0.04 * (f > 30 ? 1 : 0)
  return (
    <AbsoluteFill style={{ background: C.g, fontFamily: FONT, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 1300, height: 1300, borderRadius: '50%', left: -600, top: -700, background: 'rgba(255,255,255,.08)' }} />
      <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', right: -500, bottom: -300, background: 'rgba(0,0,0,.08)' }} />
      <div style={{ transform: `scale(${sp(f, 11)})` }}><Logo size={150} /></div>
      <div style={{ marginTop: 34 }}><Slam text="plonk.rs" at={4} size={170} /></div>
      <div style={{ marginTop: 30, fontSize: 52, fontWeight: 700, color: 'rgba(255,255,255,.92)', textAlign: 'center', lineHeight: 1.2, opacity: interpolate(f, [10, 20], [0, 1], clamp) }}>Объявления, которые<br />можно посмотреть</div>
      <div style={{ marginTop: 70, padding: '30px 70px', borderRadius: 34, background: '#fff', color: C.gd, fontSize: 56, fontWeight: 800, transform: `scale(${btn * pulse})`, boxShadow: '0 20px 50px rgba(0,0,0,.2)' }}>Смотреть вещи →</div>
      <div style={{ marginTop: 34, fontSize: 36, fontWeight: 600, color: 'rgba(255,255,255,.85)', opacity: interpolate(f, [24, 34], [0, 1], clamp) }}>Русский · English · Srpski</div>
    </AbsoluteFill>
  )
}

export const PromoV4: React.FC = () => (
  <AbsoluteFill style={{ background: '#000' }}>
    <Sequence durationInFrames={40}><Hook /></Sequence>
    <Sequence from={40} durationInFrames={60}><Reveal /></Sequence>
    <Sequence from={100} durationInFrames={120}><Shops /></Sequence>
    <Sequence from={220} durationInFrames={60}><Chat /></Sequence>
    <Sequence from={280} durationInFrames={100}><Grid /></Sequence>
    <Sequence from={380} durationInFrames={100}><End /></Sequence>
    <LightLeaks at={[40, 100, 220, 280, 380]} dur={12} />
    <Film />
  </AbsoluteFill>
)
