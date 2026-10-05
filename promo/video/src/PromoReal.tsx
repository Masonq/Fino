import React from 'react'
import { AbsoluteFill, Easing, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame } from 'remotion'
import { linearTiming, springTiming, TransitionSeries } from '@remotion/transitions'
import { slide } from '@remotion/transitions/slide'
import { wipe } from '@remotion/transitions/wipe'
import { C, Caption, Film, FONT, LightLeaks, Logo, Nav, Phone } from './ui'

const clamp = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const }
const out3 = Easing.bezier(0.16, 1, 0.3, 1)
const real = (f: string) => staticFile(`real/${f}.jpg`)

// Настоящие объявления с plonk.rs (выбраны вручную); у платья — кадр без лица
const ITEMS = [
  { photo: 'f5d3c313-0-crop', title: 'Свадебное платье', price: '15 000 RSD', city: 'Белград', land: false },
  { photo: '8d82e428-0', title: 'Кеды Trussardi', price: '5 000 RSD', city: 'Белград', land: false },
  { photo: '353db02c-0', title: 'Гитара LAVA ME 4 Carbon', price: '650 €', city: 'Белград', land: false },
  { photo: 'cb2d407d-0', title: 'Геймпад DualSense', price: '5 500 RSD', city: 'Белград', land: true },
  { photo: '2c893f74-1', title: 'iPhone 14 Pro 256 ГБ', price: '400 €', city: 'Нови-Сад', land: true },
  { photo: 'd0ca9165-0', title: 'Apple Magic Keyboard', price: '8 000 RSD', city: 'Белград', land: true },
]

/** Фото на весь кадр с медленным наездом; горизонтальное — поверх размытого себя, без грубой обрезки. */
const KenBurns: React.FC<{ src: string; land?: boolean; dir?: number; dur?: number }> = ({ src, land, dir = 1, dur = 40 }) => {
  const f = useCurrentFrame()
  const z = interpolate(f, [0, dur], [1.04, 1.16], clamp)
  const x = interpolate(f, [0, dur], [0, 24 * dir], clamp)
  if (!land) return <Img src={src} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z}) translateX(${x}px)` }} />
  return (
    <AbsoluteFill style={{ overflow: 'hidden', background: '#111' }}>
      <Img src={src} style={{ position: 'absolute', inset: -60, width: 'calc(100% + 120px)', height: 'calc(100% + 120px)', objectFit: 'cover', filter: 'blur(40px) brightness(.7)' }} />
      <Img src={src} style={{ position: 'absolute', left: 40, right: 40, top: '50%', width: 1000, transform: `translateY(-58%) scale(${z}) translateX(${x}px)`, borderRadius: 36, boxShadow: '0 30px 80px rgba(0,0,0,.45)' }} />
    </AbsoluteFill>
  )
}

/** Кадр монтажа: вещь, ценник-стикер, название и город. */
const ItemShot: React.FC<{ i: number }> = ({ i }) => {
  const f = useCurrentFrame()
  const it = ITEMS[i]
  const tag = spring({ frame: f - 6, fps: 30, config: { damping: 10, mass: 0.6 } })
  const txt = interpolate(f, [8, 18], [0, 1], { ...clamp, easing: out3 })
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <KenBurns src={real(it.photo)} land={it.land} dir={i % 2 ? -1 : 1} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: '28%', background: 'linear-gradient(180deg,rgba(0,0,0,.55),rgba(0,0,0,0))' }} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '55%', background: 'linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.25) 40%,rgba(0,0,0,.72))' }} />
      <div style={{ position: 'absolute', left: 70, bottom: 590, transform: `scale(${tag}) rotate(${-4 + i % 2 * 7 + Math.sin(f / 4) * 1.5 * Math.max(0, 1 - f / 24)}deg)`, transformOrigin: 'left bottom', padding: '18px 34px', borderRadius: 26, background: '#fff', color: C.ink, fontSize: 76, fontWeight: 800, letterSpacing: -1, boxShadow: '0 16px 40px rgba(0,0,0,.3)' }}>{it.price}</div>
      <div style={{ position: 'absolute', left: 70, right: 200, bottom: 470, color: '#fff', fontSize: 58, fontWeight: 800, lineHeight: 1.1, opacity: txt, transform: `translateY(${(1 - txt) * 30}px)` }}>{it.title}</div>
      <div style={{ position: 'absolute', left: 70, bottom: 405, display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,.9)', fontSize: 36, fontWeight: 600, opacity: txt }}>
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2"><path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" /></svg>{it.city}
      </div>
    </AbsoluteFill>
  )
}

// ---------- 1. Зацепка: зелёный кадр, вещи вылетают карточками ----------
const Hook: React.FC = () => {
  const f = useCurrentFrame()
  const cards = [['8d82e428-0', -12, 60, 760, '5 000 RSD'], ['353db02c-0', 10, 600, 820, '650 €'], ['f5d3c313-1-crop', -4, 330, 1010, '15 000 RSD']] as const
  const l1 = 0.8 + 0.2 * spring({ frame: f, fps: 30, config: { damping: 11 } })
  const l2 = spring({ frame: f - 8, fps: 30, config: { damping: 11 } })
  return (
    <AbsoluteFill style={{ background: C.g, fontFamily: FONT, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 1200, height: 1200, borderRadius: '50%', left: -500, top: -520, background: 'rgba(255,255,255,.08)' }} />
      <div style={{ position: 'absolute', top: 250, left: 60, right: 60, textAlign: 'center', color: '#fff' }}>
        <div style={{ fontSize: 112, fontWeight: 800, letterSpacing: -3, lineHeight: 1, transform: `scale(${l1})` }}>Продаёшь<br />вещь?</div>
        <div style={{ marginTop: 34, display: 'inline-block', padding: '14px 30px', borderRadius: 24, background: C.o, fontSize: 54, fontWeight: 800, transform: `scale(${l2}) rotate(-2deg)` }}>Покажи её на видео</div>
      </div>
      {cards.map(([p, r, x, y, price], i) => {
        const s = spring({ frame: f - 4 - i * 4, fps: 30, config: { damping: 12 } })
        return (
          <div key={p} style={{ position: 'absolute', left: x, top: y + (1 - s) * 900 + Math.sin((f + i * 15) / 14) * 8, width: 420, height: 540, borderRadius: 34, overflow: 'hidden', transform: `rotate(${r}deg)`, boxShadow: '0 30px 60px rgba(0,0,0,.3)', border: '8px solid #fff' }}>
            <Img src={real(p)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            <div style={{ position: 'absolute', left: 14, bottom: 14, padding: '6px 14px', borderRadius: 14, background: '#fff', fontSize: 30, fontWeight: 800, color: C.ink }}>{price}</div>
          </div>
        )
      })}
    </AbsoluteFill>
  )
}

// ---------- 2. Монтаж настоящих вещей ----------
const Montage: React.FC = () => {
  const t = (i: number) => (i % 2 ? wipe({ direction: 'from-right' }) : slide({ direction: 'from-bottom' }))
  return (
    <AbsoluteFill>
      <TransitionSeries>
        {ITEMS.map((_, i) => (
          <React.Fragment key={i}>
            {i > 0 && <TransitionSeries.Transition presentation={t(i)} timing={springTiming({ config: { damping: 200 }, durationInFrames: 8 })} />}
            <TransitionSeries.Sequence durationInFrames={28}><ItemShot i={i} /></TransitionSeries.Sequence>
          </React.Fragment>
        ))}
      </TransitionSeries>
      <Caption dark top={230} hl={[1, 2, 3]} text="Продают рядом с тобой" sub="Белград · Нови-Сад · вся Сербия" />
    </AbsoluteFill>
  )
}

/** «Ролик» шопса из фото объявления: быстрые кадры с наездом — как видео, снятое на телефон. */
const FakeVideo: React.FC<{ photos: string[]; every?: number }> = ({ photos, every = 14 }) => {
  const f = useCurrentFrame()
  const i = Math.floor(f / every) % photos.length
  const local = f % every
  const z = 1.06 + local * 0.006
  return <Img src={real(photos[i])} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z})` }} />
}

const Side: React.FC<{ liked: boolean; likes: number; pulse: number; who: string }> = ({ liked, likes, pulse, who }) => (
  <div style={{ position: 'absolute', right: 4, width: 64, bottom: 30, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, color: '#fff', fontSize: 12, fontWeight: 700, textShadow: '0 1px 2px rgba(0,0,0,.5)' }}>
    <div style={{ width: 44, height: 44, borderRadius: 22, border: '2px solid #fff', background: C.gs, color: C.gd, fontSize: 17, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{who}</div>
    <div style={{ textAlign: 'center' }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill={liked ? C.heart : 'none'} stroke={liked ? C.heart : '#fff'} strokeWidth="2" style={{ transform: `scale(${1 + pulse * 0.3})` }}><path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
      <div>{likes}</div>
    </div>
    <div style={{ textAlign: 'center' }}>
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" /></svg>
      <div>9</div>
    </div>
    <div style={{ textAlign: 'center' }}>
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round"><path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" /><path d="m16 6-4-4-4 4" /><path d="M12 2v13" /></svg>
      <div style={{ fontSize: 10 }}>Поделиться</div>
    </div>
  </div>
)

const ShopCard: React.FC<{ photo: string; title: string; price: string; t: number; press?: boolean }> = ({ photo, title, price, t, press }) => (
  <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8, padding: 6, borderRadius: 14, background: 'rgba(255,255,255,.96)', color: C.ink, transform: `translateY(${(1 - t) * 40}px)`, opacity: t }}>
    <Img src={real(photo)} style={{ width: 46, height: 46, borderRadius: 10, objectFit: 'cover' }} />
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 14, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
      <div style={{ fontSize: 14, fontWeight: 800 }}>{price}</div>
    </div>
    <div style={{ height: 36, padding: '0 12px', borderRadius: 10, background: C.g, color: '#fff', fontSize: 13, fontWeight: 700, display: 'flex', alignItems: 'center', transform: `scale(${press ? 0.92 : 1})` }}>Написать</div>
  </div>
)

// ---------- 3. Вкладка «Шопсы»: кеды → двойной тап → свайп → гитара → «Написать» ----------
const Shops: React.FC = () => {
  const f = useCurrentFrame()
  const tap = 60
  const liked = f >= tap
  const burst = spring({ frame: f - tap, fps: 30, config: { damping: 9 } })
  const burstOut = interpolate(f, [tap + 12, tap + 28], [1, 0], clamp)
  const swipe = interpolate(f, [100, 114], [0, -768], { ...clamp, easing: out3 })
  const card1 = spring({ frame: f - 22, fps: 30, config: { damping: 13 } })
  const card2 = spring({ frame: f - 122, fps: 30, config: { damping: 13 } })
  const shade = <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '48%', background: 'linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.18) 35%,rgba(0,0,0,.62))' }} />
  return (
    <div style={{ position: 'absolute', inset: 0, background: '#000' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 768, overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, top: swipe, height: 768, overflow: 'hidden' }}>
          <FakeVideo photos={['8d82e428-0', '8d82e428-1', '8d82e428-3', '8d82e428-4']} />
          {shade}
          {liked && <div style={{ position: 'absolute', left: '50%', top: '40%', transform: `translate(-50%,-50%) scale(${burst * 1.1})`, opacity: burstOut }}>
            <svg width="120" height="120" viewBox="0 0 24 24"><path fill={C.heart} d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
          </div>}
          {f >= tap - 7 && f < tap + 4 && <div style={{ position: 'absolute', left: '50%', top: '40%', width: 64, height: 64, marginLeft: -32, marginTop: -32, borderRadius: 32, background: 'rgba(255,255,255,.35)', border: '2px solid rgba(255,255,255,.75)' }} />}
          <Side who="А" liked={liked} likes={liked ? 214 : 213} pulse={liked ? Math.max(0, 1 - (f - tap) / 8) : 0} />
          <div style={{ position: 'absolute', left: 12, right: 74, bottom: 20, color: '#fff' }}>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Алекс</div>
            <div style={{ fontSize: 13, marginTop: 5 }}>Оригинал, носил пару раз 👟</div>
            <ShopCard photo="8d82e428-0" title="Оригинальные кеды Trussardi" price="5 000 RSD" t={card1} />
          </div>
        </div>
        <div style={{ position: 'absolute', left: 0, right: 0, top: swipe + 768, height: 768, overflow: 'hidden' }}>
          <FakeVideo photos={['353db02c-0', '353db02c-1', '353db02c-2']} every={16} />
          {shade}
          <Side who="Н" liked={false} likes={87} pulse={0} />
          <div style={{ position: 'absolute', left: 12, right: 74, bottom: 20, color: '#fff' }}>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Никола</div>
            <div style={{ fontSize: 13, marginTop: 5 }}>Звук — в видео, кейс в комплекте 🎸</div>
            <ShopCard photo="353db02c-0" title="LAVA ME 4 Carbon" price="650 €" t={card2} press={f >= 176 && f < 184} />
          </div>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 12, right: 12, top: 764, height: 3, borderRadius: 2, background: 'rgba(255,255,255,.25)' }}>
        <div style={{ width: `${f < 106 ? interpolate(f, [0, 106], [0, 100], clamp) : interpolate(f, [114, 200], [0, 70], clamp)}%`, height: 3, borderRadius: 2, background: '#fff' }} />
      </div>
      <Nav active="shops" dark />
    </div>
  )
}

// ---------- 4. Чат ----------
const Chat: React.FC = () => {
  const f = useCurrentFrame()
  const enter = interpolate(f, [0, 12], [393, 0], { ...clamp, easing: out3 })
  const typed = 'Здравствуйте! Гитара ещё продаётся?'
  const n = Math.floor(interpolate(f, [12, 34], [0, typed.length], clamp))
  const sent = f >= 40
  const reply = spring({ frame: f - 60, fps: 30, config: { damping: 13 } })
  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, transform: `translateX(${enter}px)` }}>
      <div style={{ padding: '56px 14px 10px', display: 'flex', alignItems: 'center', gap: 10, background: '#fff', borderBottom: `1px solid ${C.line}` }}>
        <Img src={real('353db02c-0')} style={{ width: 40, height: 40, borderRadius: 10, objectFit: 'cover' }} />
        <div><div style={{ fontWeight: 700, fontSize: 15 }}>Никола</div><div style={{ fontSize: 12, color: C.muted }}>LAVA ME 4 Carbon · 650 €</div></div>
      </div>
      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sent && <div style={{ alignSelf: 'flex-end', maxWidth: 270, padding: '10px 14px', borderRadius: '18px 18px 4px 18px', background: C.g, color: '#fff', fontSize: 15 }}>{typed}</div>}
        {f >= 60 && <div style={{ alignSelf: 'flex-start', maxWidth: 270, padding: '10px 14px', borderRadius: '18px 18px 18px 4px', background: '#fff', color: C.ink, fontSize: 15, transform: `scale(${reply})`, transformOrigin: 'left bottom', boxShadow: '0 1px 2px rgba(0,0,0,.05)' }}>Да! Могу показать сегодня, с 18:00 🙌</div>}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '10px 12px 30px', background: '#fff', borderTop: `1px solid ${C.line}`, display: 'flex', gap: 8 }}>
        <div style={{ flex: 1, height: 42, borderRadius: 21, background: C.sunken, padding: '0 14px', display: 'flex', alignItems: 'center', fontSize: 15, color: sent ? C.muted : C.ink, whiteSpace: 'nowrap', overflow: 'hidden' }}>{sent ? 'Сообщение' : typed.slice(0, n)}{!sent && f % 16 < 8 && <span style={{ color: C.g }}>|</span>}</div>
        <div style={{ width: 42, height: 42, borderRadius: 21, background: C.g, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${f >= 36 && f < 40 ? 0.86 : 1})` }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" /></svg>
        </div>
      </div>
    </div>
  )
}

// ---------- 5. Витрина ----------
const Store: React.FC = () => {
  const f = useCurrentFrame()
  const enter = interpolate(f, [0, 12], [393, 0], { ...clamp, easing: out3 })
  const follow = f >= 60
  const grid = [['2c893f74-1', 'iPhone 14 Pro 256 ГБ', '400 €'], ['d0ca9165-0', 'Apple Magic Keyboard', '8 000 RSD'], ['cb2d407d-0', 'Геймпад DualSense', '5 500 RSD'], ['353db02c-1', 'LAVA ME 4 Carbon', '650 €']]
  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, transform: `translateX(${enter}px)` }}>
      <div style={{ height: 160, overflow: 'hidden', position: 'relative' }}>
        <Img src={real('cb2d407d-0')} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'saturate(1.05)' }} />
      </div>
      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', marginTop: -34 }}>
        <div style={{ width: 68, height: 68, margin: '0 auto', borderRadius: 34, border: `4px solid ${C.bg}`, background: C.gs, color: C.gd, fontSize: 26, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Т</div>
        <div style={{ fontSize: 21, fontWeight: 800, marginTop: 6 }}>Tech Corner</div>
        <div style={{ fontSize: 13, color: C.muted, marginTop: 2 }}>18 товаров · {follow ? 241 : 240} подписчиков</div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 12 }}>
          <div style={{ minWidth: 136, height: 40, borderRadius: 12, background: follow ? '#fff' : C.g, border: `1px solid ${follow ? C.line : 'transparent'}`, color: follow ? C.ink : '#fff', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${f >= 54 && f < 60 ? 0.92 : 1})` }}>{follow ? 'Вы подписаны ✓' : 'Подписаться'}</div>
          <div style={{ minWidth: 110, height: 40, borderRadius: 12, background: '#fff', border: `1px solid ${C.line}`, fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Поделиться</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, padding: '14px 12px 8px' }}>
        {['Все', 'Apple · 6', 'Игры · 4'].map((t, i) => <div key={t} style={{ height: 32, padding: '0 12px', borderRadius: 16, background: i === 0 ? C.ink : '#fff', color: i === 0 ? '#fff' : C.ink, border: `1px solid ${i === 0 ? C.ink : C.line}`, fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center' }}>{t}</div>)}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, padding: '4px 12px' }}>
        {grid.map(([p, t, pr], i) => {
          const pop = spring({ frame: f - 14 - i * 4, fps: 30, config: { damping: 13 } })
          return (
            <div key={p} style={{ width: 'calc((100% - 10px) / 2)', borderRadius: 14, background: '#fff', overflow: 'hidden', transform: `scale(${pop})` }}>
              <Img src={real(p)} style={{ width: '100%', height: 130, objectFit: 'cover' }} />
              <div style={{ padding: '8px 10px' }}><div style={{ fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t}</div><div style={{ fontSize: 16, fontWeight: 800, marginTop: 2 }}>{pr}</div></div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------- 6. Финал ----------
const Final: React.FC = () => {
  const f = useCurrentFrame()
  const p = spring({ frame: f, fps: 30, config: { damping: 11 } })
  const btn = spring({ frame: f - 18, fps: 30, config: { damping: 12 } })
  const thumbs = ['f5d3c313-0-crop', '8d82e428-0', '353db02c-0', 'cb2d407d-0', '2c893f74-1']
  return (
    <AbsoluteFill style={{ background: C.bg, alignItems: 'center', justifyContent: 'center', fontFamily: FONT }}>
      <div style={{ position: 'absolute', width: 1000, height: 1000, borderRadius: '50%', left: -420, top: -380, background: C.gs, filter: 'blur(40px)' }} />
      <div style={{ position: 'absolute', width: 800, height: 800, borderRadius: '50%', right: -340, bottom: -260, background: '#FFEDE6', filter: 'blur(50px)' }} />
      <div style={{ position: 'relative', transform: `scale(${p})`, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Logo size={170} />
        <div style={{ marginTop: 28, fontSize: 128, fontWeight: 800, letterSpacing: -4, color: 'transparent', backgroundImage: `linear-gradient(110deg, ${C.ink} 40%, #7BE3B5 50%, ${C.ink} 60%)`, backgroundSize: '300% 100%', backgroundPosition: `${interpolate(f, [20, 50], [100, 0], clamp)}% 0`, WebkitBackgroundClip: 'text', backgroundClip: 'text' }}>PLONK</div>
        <div style={{ marginTop: 8, fontSize: 50, fontWeight: 700, color: C.soft, textAlign: 'center', lineHeight: 1.2 }}>Объявления,<br />которые можно посмотреть</div>
      </div>
      <div style={{ position: 'relative', marginTop: 60, display: 'flex', gap: 14 }}>
        {thumbs.map((t, i) => {
          const s = spring({ frame: f - 8 - i * 3, fps: 30, config: { damping: 12 } })
          return <Img key={t} src={real(t)} style={{ width: 150, height: 190, objectFit: 'cover', borderRadius: 22, transform: `scale(${s}) rotate(${(i - 2) * 3}deg)`, boxShadow: '0 12px 28px rgba(20,30,25,.18)', border: '5px solid #fff' }} />
        })}
      </div>
      <div style={{ position: 'relative', marginTop: 70, padding: '30px 96px', borderRadius: 30, background: C.g, color: '#fff', fontSize: 66, fontWeight: 800, transform: `scale(${btn})`, boxShadow: '0 18px 40px rgba(14,159,110,.35)' }}>plonk.rs</div>
      <div style={{ position: 'relative', marginTop: 26, fontSize: 34, fontWeight: 600, color: C.soft, opacity: interpolate(f, [24, 36], [0, 1], clamp) }}>Русский · English · Srpski</div>
    </AbsoluteFill>
  )
}

// ---------- монтаж: 0–2 с зацепка, 2–7,6 вещи, 7,6–14,6 шопсы, 14,6–18 чат, 18–22 витрина, 22–25,5 финал ----------
export const MONTAGE = 6 * 28 - 5 * 8 // 128 кадров: склейка каждые 20 кадров = доля при 90 BPM
export const PromoReal: React.FC = () => {
  const f = useCurrentFrame()
  const P0 = 200 // телефон — на долю (10-я)
  const phoneIn = spring({ frame: f - P0, fps: 30, config: { damping: 16 } })
  const phoneOut = interpolate(f, [580, 592], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) })
  const dark = f < P0 + 200
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence durationInFrames={84}><Hook /></Sequence>
      <Sequence from={80} durationInFrames={MONTAGE + 4}>
        <AbsoluteFill style={{ opacity: interpolate(f, [80, 86], [0, 1], clamp) }}><Montage /></AbsoluteFill>
      </Sequence>
      {f >= P0 && f < 594 && (
        <AbsoluteFill>
          <AbsoluteFill style={{ background: dark ? '#0F1612' : C.bg }}>
            <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', left: -380, top: -260, background: dark ? 'rgba(14,159,110,.25)' : C.gs, filter: 'blur(40px)' }} />
            <div style={{ position: 'absolute', width: 700, height: 700, borderRadius: '50%', right: -300, bottom: -200, background: dark ? 'rgba(255,106,61,.15)' : '#FFEDE6', filter: 'blur(50px)' }} />
          </AbsoluteFill>
          <Sequence from={P0} durationInFrames={200}><Caption dark top={230} text="Шопсы — | видео вместо фото" hl={[3, 4, 5]} /></Sequence>
          <Sequence from={P0 + 200} durationInFrames={90}><Caption top={230} text="Пишешь продавцу | прямо из видео" hl={[3, 4, 5]} /></Sequence>
          <Sequence from={P0 + 290} durationInFrames={110}><Caption top={230} text="Своя витрина — | все вещи по одной ссылке" hl={[6, 7, 8]} /></Sequence>
          <div style={{ position: 'absolute', inset: 0, transform: `perspective(2200px) translateY(${(1 - phoneIn) * 1000 + phoneOut * 1300}px) rotateX(${(1 - phoneIn) * 28}deg) rotateZ(${(1 - phoneIn) * -6}deg)`, transformOrigin: '50% 100%' }}>
            <Phone dark={dark} y={-20} scale={1.42}>
              <Sequence from={P0} durationInFrames={214}><Shops /></Sequence>
              <Sequence from={P0 + 200} durationInFrames={104}><Chat /></Sequence>
              <Sequence from={P0 + 290} durationInFrames={112}><Store /></Sequence>
            </Phone>
          </div>
        </AbsoluteFill>
      )}
      <Sequence from={588}><Final /></Sequence>
      <LightLeaks at={[80, 128, 168, 200, 400, 490, 590]} />
      <Film />
    </AbsoluteFill>
  )
}
