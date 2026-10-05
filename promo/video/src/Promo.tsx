import React from 'react'
import { AbsoluteFill, Img, interpolate, Sequence, spring, useCurrentFrame, useVideoConfig } from 'remotion'
import { Backdrop, C, Caption, cat, FONT, Logo, Nav, Phone, usePop } from './ui'

const clamp = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const }

// ---------- 1. Зацепка ----------
const Hook: React.FC = () => {
  const f = useCurrentFrame()
  const items = [
    ['furn-sofa', 120, 900, -8], ['bikes-city', 640, 760, 10], ['kids-cl-shoes', 160, 1340, 6], ['phones', 700, 1260, -12],
    ['cars-sale', 360, 1600, 4], ['coffee-kettles', 690, 1620, -6],
  ] as const
  return (
    <AbsoluteFill>
      <Backdrop />
      {items.map(([s, x, y, r], i) => {
        const p = spring({ frame: f - 6 - i * 3, fps: 30, config: { damping: 12 } })
        return <Img key={s} src={cat(s)} style={{ position: 'absolute', left: x, top: y + Math.sin((f + i * 20) / 18) * 12, width: 300, transform: `scale(${p}) rotate(${r}deg)`, filter: 'drop-shadow(0 18px 24px rgba(20,30,25,.18))' }} />
      })}
      <div style={{ position: 'absolute', top: 300, left: 60, right: 60, textAlign: 'center', fontFamily: FONT }}>
        <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 1.05, color: C.ink, letterSpacing: -2, transform: `scale(${spring({ frame: f, fps: 30, config: { damping: 10 } })})` }}>Продаёшь вещь<br />в Сербии?</div>
        <div style={{ marginTop: 28, fontSize: 44, fontWeight: 700, color: C.g, opacity: interpolate(f, [24, 36], [0, 1], clamp) }}>Покажи её на видео 🎬</div>
      </div>
    </AbsoluteFill>
  )
}

// ---------- 2. Главная PLONK ----------
const TILES = [['Авто', 'auto'], ['Работа', 'jobs'], ['Электроника', 'electronics'], ['Квартиры', 'real-estate'], ['Дом и сад', 'home-garden'], ['Одежда', 'fashion']]
const CARDS = [
  ['Диван угловой, как новый', '450 €', 'furn-sofa'], ['Городской велосипед', '180 €', 'bikes-city'],
  ['Кроссовки детские, 30', '2 500 RSD', 'kids-cl-shoes'], ['Кофемашина и чайник', '120 €', 'coffee-kettles'],
]
const Home: React.FC = () => {
  const f = useCurrentFrame()
  const scroll = interpolate(f, [40, 95], [0, -230], { ...clamp, easing: (t) => 1 - Math.pow(1 - t, 3) })
  return (
    <div style={{ position: 'absolute', inset: 0, paddingTop: 56 }}>
      <div style={{ transform: `translateY(${scroll}px)` }}>
        <div style={{ display: 'flex', gap: 8, padding: '6px 12px' }}>
          <div style={{ flex: 1, height: 48, borderRadius: 15, background: C.sunken, display: 'flex', alignItems: 'center', padding: '0 6px', gap: 8 }}>
            <div style={{ height: 36, padding: '0 10px', borderRadius: 11, background: '#fff', display: 'flex', alignItems: 'center', fontSize: 13, fontWeight: 700, color: C.ink }}>📍 Белград</div>
            <span style={{ fontSize: 14, color: C.muted }}>Найти холодильник</span>
          </div>
          <div style={{ width: 48, height: 48, borderRadius: 24, background: C.sunken, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={C.ink} strokeWidth="2"><path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, padding: '6px 12px' }}>
          <div style={{ width: 84, height: 128, borderRadius: 14, background: C.gs, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <div style={{ width: 36, height: 36, borderRadius: 18, background: C.g, color: '#fff', fontSize: 24, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>+</div>
            <span style={{ fontSize: 11, fontWeight: 700, color: C.gd }}>Снять шопс</span>
          </div>
          {['furn-sofa', 'consoles', 'women-dresses'].map((s, i) => (
            <div key={s} style={{ position: 'relative', width: 84, height: 128, borderRadius: 14, overflow: 'hidden', background: ['#5B4636', '#1F2A3A', '#3D4F3F'][i] }}>
              <Img src={cat(s)} style={{ position: 'absolute', left: -10, top: 30, width: 104 }} />
              <div style={{ position: 'absolute', left: 6, top: 6, padding: '1px 5px', borderRadius: 5, background: 'rgba(255,255,255,.92)', fontSize: 10, fontWeight: 800 }}>{['450 €', '230 €', '35 €'][i]}</div>
              <div style={{ position: 'absolute', left: 6, bottom: 6, color: '#fff', fontSize: 11, fontWeight: 700 }}>{['Мария', 'Игорь', 'Ана'][i]}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '8px 12px' }}>
          {TILES.map(([t, s]) => (
            <div key={s} style={{ position: 'relative', width: 'calc((100% - 16px) / 3)', height: 78, borderRadius: 14, background: C.sunken, overflow: 'hidden' }}>
              <span style={{ position: 'absolute', left: 10, top: 9, fontSize: 13, fontWeight: 700, color: C.ink }}>{t}</span>
              <Img src={cat(s)} style={{ position: 'absolute', right: -6, bottom: -6, width: 74 }} />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, padding: '8px 12px' }}>
          {CARDS.map(([t, p, s]) => (
            <div key={t} style={{ width: 'calc((100% - 10px) / 2)', borderRadius: 14, background: '#fff', overflow: 'hidden', boxShadow: '0 1px 2px rgba(0,0,0,.04)' }}>
              <div style={{ height: 150, background: C.sunken, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Img src={cat(s)} style={{ width: 150 }} /></div>
              <div style={{ padding: '8px 10px 10px' }}>
                <div style={{ fontSize: 13, color: C.ink }}>{t}</div>
                <div style={{ fontSize: 17, fontWeight: 800, marginTop: 4 }}>{p}</div>
                <div style={{ fontSize: 11, color: C.muted, marginTop: 2 }}>Белград · сегодня</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 54, background: C.bg }} />
      <Nav active="home" />
    </div>
  )
}

// ---------- 3. Вкладка «Шопсы»: свайп, двойной тап, карточка ----------
const ShopsTab: React.FC = () => {
  const f = useCurrentFrame()
  const swipe = interpolate(f, [8, 22], [852, 0], { ...clamp, easing: (t) => 1 - Math.pow(1 - t, 3) })
  const zoom = interpolate(f, [0, 200], [1, 1.12], clamp)
  const tap = 70 // двойной тап
  const burst = spring({ frame: f - tap, fps: 30, config: { damping: 9 } })
  const burstOut = interpolate(f, [tap + 14, tap + 30], [1, 0], clamp)
  const liked = f >= tap
  const card = spring({ frame: f - 40, fps: 30, config: { damping: 13 } })
  const press = f >= 160 && f < 168 ? 0.94 : 1
  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {/* главная не пропадает: ролик въезжает поверх неё снизу, как свайп в ленте */}
      <div style={{ position: 'absolute', inset: 0, bottom: 84, transform: `translateY(${swipe}px)`, overflow: 'hidden', background: '#000' }}>
        {/* «ролик»: гостиная с диваном, медленный наезд камеры */}
        <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg,#E9DCCB 0%,#D8C4AC 58%,#B89878 58%,#A9876A 100%)', transform: `scale(${zoom})` }}>
          <div style={{ position: 'absolute', left: 40, top: 120, width: 120, height: 170, borderRadius: 8, background: '#F6EFE6', boxShadow: 'inset 0 0 0 6px #C9B49B' }} />
          <div style={{ position: 'absolute', right: 50, top: 150, width: 70, height: 70, borderRadius: 35, background: '#7FA37A' }} />
          <Img src={cat('furn-sofa')} style={{ position: 'absolute', left: -40, top: 300, width: 470 }} />
          <Img src={cat('garden-plants')} style={{ position: 'absolute', right: -30, top: 250, width: 170 }} />
        </div>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '48%', background: 'linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.18) 35%,rgba(0,0,0,.62))' }} />
        {f >= tap && <div style={{ position: 'absolute', left: '50%', top: '42%', transform: `translate(-50%,-50%) scale(${burst * 1.1})`, opacity: burstOut }}>
          <svg width="120" height="120" viewBox="0 0 24 24"><path fill={C.heart} d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
        </div>}
        {/* касание пальцем */}
        {(f >= tap - 6 && f < tap + 6) && <div style={{ position: 'absolute', left: '50%', top: '42%', width: 64, height: 64, marginLeft: -32, marginTop: -32, borderRadius: 32, background: 'rgba(255,255,255,.35)', border: '2px solid rgba(255,255,255,.7)' }} />}
        <div style={{ position: 'absolute', right: 4, width: 64, bottom: 34, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, color: '#fff' }}>
          <div style={{ width: 46, height: 46, borderRadius: 23, border: '2px solid #fff', background: C.gs, color: C.gd, fontWeight: 800, fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>М</div>
          <div style={{ textAlign: 'center', fontSize: 12, fontWeight: 700 }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill={liked ? C.heart : 'none'} stroke={liked ? C.heart : '#fff'} strokeWidth="2" style={{ transform: `scale(${liked ? 1 + 0.25 * Math.max(0, 1 - (f - tap) / 8) : 1})` }}><path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" /></svg>
            <div>{liked ? 128 : 127}</div>
          </div>
          <div style={{ textAlign: 'center', fontSize: 12, fontWeight: 700 }}>
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2"><path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" /></svg>
            <div>14</div>
          </div>
          <div style={{ textAlign: 'center', fontSize: 12, fontWeight: 700 }}>
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round"><path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" /><path d="m16 6-4-4-4 4" /><path d="M12 2v13" /></svg>
            <div style={{ fontSize: 10 }}>Поделиться</div>
          </div>
        </div>
        <div style={{ position: 'absolute', left: 12, right: 74, bottom: 22, color: '#fff' }}>
          <div style={{ fontSize: 15, fontWeight: 700 }}>Мария Винтаж</div>
          <div style={{ fontSize: 13, marginTop: 6, opacity: 0.92 }}>Раскладывается за 5 секунд 👇</div>
          <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8, padding: 6, borderRadius: 14, background: 'rgba(255,255,255,.95)', color: C.ink, transform: `translateY(${(1 - card) * 40}px)`, opacity: card }}>
            <div style={{ width: 46, height: 46, borderRadius: 10, background: C.sunken, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Img src={cat('furn-sofa')} style={{ width: 44 }} /></div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Диван угловой</div>
              <div style={{ fontSize: 14, fontWeight: 800 }}>450 €</div>
            </div>
            <div style={{ height: 36, padding: '0 12px', borderRadius: 10, background: C.g, color: '#fff', fontSize: 13, fontWeight: 700, display: 'flex', alignItems: 'center', transform: `scale(${press})` }}>Написать</div>
          </div>
        </div>
        <div style={{ position: 'absolute', left: 12, right: 12, bottom: 4, height: 3, borderRadius: 2, background: 'rgba(255,255,255,.25)' }}>
          <div style={{ width: `${interpolate(f, [20, 200], [0, 100], clamp)}%`, height: 3, borderRadius: 2, background: '#fff' }} />
        </div>
      </div>
      <Nav active="shops" dark />
    </div>
  )
}

// ---------- 4. Чат ----------
const Chat: React.FC = () => {
  const f = useCurrentFrame()
  const enter = interpolate(f, [0, 12], [393, 0], { ...clamp, easing: (t) => 1 - Math.pow(1 - t, 3) })
  const typed = 'Здравствуйте! Диван ещё актуален?'
  const n = Math.floor(interpolate(f, [16, 50], [0, typed.length], clamp))
  const sent = f >= 58
  const reply = spring({ frame: f - 78, fps: 30, config: { damping: 13 } })
  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, transform: `translateX(${enter}px)` }}>
      <div style={{ paddingTop: 56, padding: '56px 14px 10px', display: 'flex', alignItems: 'center', gap: 10, background: '#fff', borderBottom: `1px solid ${C.line}` }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: C.sunken, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Img src={cat('furn-sofa')} style={{ width: 38 }} /></div>
        <div><div style={{ fontWeight: 700, fontSize: 15 }}>Мария Винтаж</div><div style={{ fontSize: 12, color: C.muted }}>Диван угловой · 450 €</div></div>
      </div>
      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sent && <div style={{ alignSelf: 'flex-end', maxWidth: 260, padding: '10px 14px', borderRadius: '18px 18px 4px 18px', background: C.g, color: '#fff', fontSize: 15 }}>{typed}</div>}
        {f >= 78 && <div style={{ alignSelf: 'flex-start', maxWidth: 260, padding: '10px 14px', borderRadius: '18px 18px 18px 4px', background: '#fff', color: C.ink, fontSize: 15, transform: `scale(${reply})`, transformOrigin: 'left bottom' }}>Да! Можно посмотреть сегодня в 18:00 👍</div>}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '10px 12px 30px', background: '#fff', borderTop: `1px solid ${C.line}`, display: 'flex', gap: 8 }}>
        <div style={{ flex: 1, height: 42, borderRadius: 21, background: C.sunken, padding: '0 14px', display: 'flex', alignItems: 'center', fontSize: 15, color: sent ? C.muted : C.ink }}>{sent ? 'Сообщение' : typed.slice(0, n)}{!sent && f % 16 < 8 && <span style={{ color: C.g }}>|</span>}</div>
        <div style={{ width: 42, height: 42, borderRadius: 21, background: C.g, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${f >= 52 && f < 58 ? 0.88 : 1})` }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" /></svg>
        </div>
      </div>
    </div>
  )
}

// ---------- 5. Витрина ----------
const Store: React.FC = () => {
  const f = useCurrentFrame()
  const follow = f >= 60
  const enter = interpolate(f, [0, 12], [393, 0], { ...clamp, easing: (t) => 1 - Math.pow(1 - t, 3) })
  const items = [['Диван угловой', '450 €', 'furn-sofa'], ['Стол обеденный', '220 €', 'furn-table'], ['Кофемашина', '120 €', 'coffee-kettles'], ['Растения', '15 €', 'garden-plants']]
  return (
    <div style={{ position: 'absolute', inset: 0, background: C.bg, transform: `translateX(${enter}px)` }}>
      <div style={{ height: 170, background: `linear-gradient(135deg,#D8C4AC,#E9DCCB)`, position: 'relative', overflow: 'hidden' }}>
        <Img src={cat('furn-sofa')} style={{ position: 'absolute', right: -20, bottom: -30, width: 260, opacity: 0.9 }} />
      </div>
      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', marginTop: -34 }}>
        <div style={{ width: 68, height: 68, margin: '0 auto', borderRadius: 34, border: `4px solid ${C.bg}`, background: C.gs, color: C.gd, fontSize: 26, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>М</div>
        <div style={{ fontSize: 21, fontWeight: 800, marginTop: 6 }}>Мария Винтаж</div>
        <div style={{ fontSize: 13, color: C.muted, marginTop: 2 }}>24 товара · {follow ? 313 : 312} подписчиков</div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 12 }}>
          <div style={{ minWidth: 130, height: 40, borderRadius: 12, background: follow ? '#fff' : C.g, border: follow ? `1px solid ${C.line}` : '1px solid transparent', color: follow ? C.ink : '#fff', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${f >= 54 && f < 60 ? 0.92 : 1})` }}>{follow ? 'Вы подписаны ✓' : 'Подписаться'}</div>
          <div style={{ minWidth: 110, height: 40, borderRadius: 12, background: '#fff', border: `1px solid ${C.line}`, fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Поделиться</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, padding: '14px 12px 8px' }}>
        {['Все', 'Мебель · 9', 'До €50 · 7'].map((t, i) => <div key={t} style={{ height: 32, padding: '0 12px', borderRadius: 16, background: i === 0 ? C.ink : '#fff', color: i === 0 ? '#fff' : C.ink, border: `1px solid ${i === 0 ? C.ink : C.line}`, fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center' }}>{t}</div>)}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, padding: '4px 12px' }}>
        {items.map(([t, p, s], i) => {
          const pop = spring({ frame: f - 14 - i * 4, fps: 30, config: { damping: 13 } })
          return (
            <div key={t} style={{ width: 'calc((100% - 10px) / 2)', borderRadius: 14, background: '#fff', overflow: 'hidden', transform: `scale(${pop})` }}>
              <div style={{ height: 120, background: C.sunken, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Img src={cat(s)} style={{ width: 120 }} /></div>
              <div style={{ padding: '8px 10px' }}><div style={{ fontSize: 13 }}>{t}</div><div style={{ fontSize: 16, fontWeight: 800, marginTop: 2 }}>{p}</div></div>
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
  const p = usePop(0, 11)
  const btn = usePop(16, 12)
  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', fontFamily: FONT }}>
      <Backdrop />
      <div style={{ transform: `scale(${p})`, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Logo size={170} />
        <div style={{ marginTop: 30, fontSize: 120, fontWeight: 800, letterSpacing: -3, color: C.ink }}>PLONK</div>
        <div style={{ marginTop: 10, fontSize: 48, fontWeight: 700, color: C.soft, textAlign: 'center', lineHeight: 1.2 }}>Объявления,<br />которые можно посмотреть</div>
      </div>
      <div style={{ position: 'relative', marginTop: 70, display: 'flex', gap: 16, opacity: interpolate(f, [10, 22], [0, 1], clamp) }}>
        {['🎬 Шопсы', '🏪 Витрины', 'RU · EN · SR'].map((t) => <div key={t} style={{ padding: '16px 26px', borderRadius: 22, background: '#fff', fontSize: 34, fontWeight: 700, color: C.ink, boxShadow: '0 6px 18px rgba(20,30,25,.08)' }}>{t}</div>)}
      </div>
      <div style={{ marginTop: 70, padding: '30px 90px', borderRadius: 30, background: C.g, color: '#fff', fontSize: 64, fontWeight: 800, transform: `scale(${btn})`, boxShadow: '0 18px 40px rgba(14,159,110,.35)' }}>plonk.rs</div>
    </AbsoluteFill>
  )
}

// ---------- монтаж ----------
// 30 к/с: 0–2.7 с зацепка, 2.7–6.5 главная, 6.5–13 шопсы, 13–17 чат, 17–21 витрина, 21–24.5 финал
export const Promo: React.FC = () => {
  const f = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()
  const phoneIn = spring({ frame: f - 80, fps: 30, config: { damping: 15 } })
  const phoneOut = interpolate(f, [622, 636], [0, 1], clamp)
  const showPhone = f >= 80 && f < 636
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence durationInFrames={82}><Hook /></Sequence>
      {showPhone && (
        <AbsoluteFill>
          <Backdrop dark={f >= 195 && f < 390} />
          <Sequence from={80} durationInFrames={115}><Caption text="Объявления в Сербии | на русском" sub="и на английском, и на сербском" /></Sequence>
          <Sequence from={195} durationInFrames={195}><Caption dark text="Шопсы — видео с вещами" sub="двойной тап — лайк, карточка — сразу купить" /></Sequence>
          <Sequence from={390} durationInFrames={120}><Caption text="Пишете продавцу | прямо из видео" /></Sequence>
          <Sequence from={510} durationInFrames={126}><Caption text="Витрина продавца | по одной ссылке" sub="подписка на новые вещи" /></Sequence>
          <div style={{ position: 'absolute', inset: 0, transform: `translateY(${(1 - phoneIn) * 900 + phoneOut * 1200}px)` }}>
            <Phone dark={f >= 195 && f < 390}>
              <Sequence from={80} durationInFrames={140}><Home /></Sequence>
              <Sequence from={195} durationInFrames={210}><ShopsTab /></Sequence>
              <Sequence from={390} durationInFrames={135}><Chat /></Sequence>
              <Sequence from={510} durationInFrames={126}><Store /></Sequence>
            </Phone>
          </div>
        </AbsoluteFill>
      )}
      <Sequence from={630} durationInFrames={durationInFrames - 630}><Final /></Sequence>
    </AbsoluteFill>
  )
}
