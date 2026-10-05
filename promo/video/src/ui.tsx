import React from 'react'
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion'
import '@fontsource/plus-jakarta-sans/600.css'
import '@fontsource/plus-jakarta-sans/700.css'
import '@fontsource/plus-jakarta-sans/800.css'
import '@fontsource/inter/cyrillic-500.css'
import '@fontsource/inter/cyrillic-600.css'
import '@fontsource/inter/cyrillic-700.css'
import '@fontsource/inter/cyrillic-800.css'

// цвета и шрифт — как у plonk.rs (styles.css)
export const C = {
  bg: '#FAFAF9', card: '#FFFFFF', sunken: '#F2F2EF', ink: '#1C2620', soft: '#4B554E', muted: '#8D958E', line: '#EEEEE9',
  g: '#0E9F6E', gd: '#0B5C42', gs: '#E4F6EE', o: '#FF6A3D', heart: '#FF3B5C',
}
export const FONT = "'Plus Jakarta Sans', 'Inter', sans-serif"
export const cat = (s: string) => staticFile(`cat/${s}.png`)

/** Плавное появление снизу с пружиной. */
export const usePop = (delay = 0, damping = 14) => {
  const f = useCurrentFrame()
  const { fps } = useVideoConfig()
  return spring({ frame: f - delay, fps, config: { damping, mass: 0.7 } })
}

/** Подпись сверху — крупно, как в TikTok: слово за словом. */
export const Caption: React.FC<{ text: string; sub?: string; dark?: boolean; top?: number }> = ({ text, sub, dark, top = 120 }) => {
  const f = useCurrentFrame()
  // «|» — перенос строки: чтобы не оставлять одно слово на второй строке
  const words = text.split(' ')
  return (
    <div style={{ position: 'absolute', top, left: 70, right: 70, textAlign: 'center', fontFamily: FONT }}>
      <div style={{ fontSize: 66, fontWeight: 800, lineHeight: 1.12, color: dark ? '#fff' : C.ink, letterSpacing: -1, textShadow: dark ? '0 2px 14px rgba(0,0,0,.35)' : 'none' }}>
        {words.map((w, i) => {
          const p = interpolate(f, [i * 3, i * 3 + 8], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
          if (w === '|') return <br key={i} />
          return <span key={i} style={{ display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 24}px)`, marginRight: 16 }}>{w}</span>
        })}
      </div>
      {sub && (
        <div style={{ marginTop: 18, fontSize: 36, fontWeight: 600, color: dark ? 'rgba(255,255,255,.8)' : C.soft, opacity: interpolate(f, [words.length * 3 + 4, words.length * 3 + 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>{sub}</div>
      )}
    </div>
  )
}

/** Телефон: экран 393×852 (как iPhone), масштабируется под кадр. */
export const Phone: React.FC<{ children: React.ReactNode; dark?: boolean; y?: number; scale?: number }> = ({ children, dark, y = 0, scale = 1.72 }) => (
  <div style={{ position: 'absolute', left: '50%', top: 430 + y, width: 393, height: 852, transform: `translateX(-50%) scale(${scale})`, transformOrigin: 'top center' }}>
    <div style={{ position: 'absolute', inset: -10, borderRadius: 62, background: '#111', boxShadow: '0 40px 80px rgba(20,30,25,.28)' }} />
    <div style={{ position: 'absolute', inset: 0, borderRadius: 54, overflow: 'hidden', background: dark ? '#000' : C.bg, fontFamily: FONT }}>
      {children}
      <div style={{ position: 'absolute', top: 11, left: '50%', transform: 'translateX(-50%)', width: 120, height: 34, borderRadius: 20, background: '#000' }} />
      <div style={{ position: 'absolute', top: 18, left: 34, fontSize: 15, fontWeight: 700, color: dark ? '#fff' : C.ink }}>9:41</div>
    </div>
  </div>
)

/** Нижнее меню PLONK; active — 'home' | 'shops'. */
export const Nav: React.FC<{ active: 'home' | 'shops'; dark?: boolean }> = ({ active, dark }) => {
  const it = (key: string, label: string, icon: React.ReactNode) => {
    const on = key === active
    const color = dark ? (on ? '#fff' : 'rgba(255,255,255,.6)') : on ? C.gd : C.muted
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, color, fontSize: 11, fontWeight: on ? 700 : 600 }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">{icon}</svg>
        {label}
      </div>
    )
  }
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 84, paddingTop: 10, display: 'flex', background: dark ? '#000' : '#fff', borderTop: `1px solid ${dark ? 'rgba(255,255,255,.12)' : C.line}` }}>
      {it('home', 'Главная', <><path d="M3 11l9-8 9 8" /><path d="M5 10v10h14V10" /></>)}
      {it('shops', 'Шопсы', <><rect x="4" y="3" width="16" height="18" rx="4" /><path d="m10 9 5 3-5 3z" /></>)}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color: dark ? 'rgba(255,255,255,.6)' : C.muted }}>
        <div style={{ width: 34, height: 34, marginTop: -6, borderRadius: 17, background: C.o, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
        </div>
        Разместить
      </div>
      {it('chats', 'Сообщения', <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />)}
      {it('profile', 'Профиль', <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" /></>)}
    </div>
  )
}

/** Фон кадра: светлый с мягкими мятными пятнами. */
export const Backdrop: React.FC<{ dark?: boolean }> = ({ dark }) => {
  const f = useCurrentFrame()
  return (
    <AbsoluteFill style={{ background: dark ? '#0F1612' : C.bg, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', left: -380 + Math.sin(f / 40) * 30, top: -260, background: dark ? 'rgba(14,159,110,.22)' : C.gs, filter: 'blur(40px)' }} />
      <div style={{ position: 'absolute', width: 700, height: 700, borderRadius: '50%', right: -300, bottom: -200 + Math.cos(f / 50) * 30, background: dark ? 'rgba(255,106,61,.14)' : '#FFEDE6', filter: 'blur(50px)', opacity: 0.8 }} />
    </AbsoluteFill>
  )
}

export const Logo: React.FC<{ size?: number }> = ({ size = 90 }) => <Img src={staticFile('logo-mark.png')} style={{ width: size, height: size, borderRadius: size / 2 }} />

export const Price: React.FC<{ v: string }> = ({ v }) => <span style={{ fontWeight: 800 }}>{v}</span>
