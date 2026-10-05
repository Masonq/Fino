"""Звуковое оформление ролика PromoReal: свисты на склейках, «поп» ценников, тапы, звук отправки, финальный аккорд.
Синтез (без чужих сэмплов), события — по кадрам монтажа (30 к/с)."""
import numpy as np, wave
SR, DUR = 48000, 760 / 30
out = np.zeros(int(SR * DUR) + SR)
rng = np.random.default_rng(7)
t_ = lambda d: np.arange(int(SR * d)) / SR

def env(n, a=0.005, r=0.1):
    t = np.arange(n) / SR; e = np.minimum(1, t / a) * np.exp(-t / r); return e

def whoosh(d=0.32, lo=300, hi=3500, up=True):
    n = int(SR * d); x = rng.standard_normal(n)
    # полосовой «свист»: огибающая по частоте через простую рекурсию резонатора
    y = np.zeros(n); f = np.linspace(lo, hi, n) if up else np.linspace(hi, lo, n)
    a1 = a2 = 0.0
    for i in range(n):
        w = 2 * np.pi * f[i] / SR; r = 0.97
        yi = x[i] * (1 - r) + 2 * r * np.cos(w) * a1 - r * r * a2
        a2, a1 = a1, yi; y[i] = yi
    sh = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    y = y * sh; return y / (np.abs(y).max() + 1e-9)

def pop(f0=900, f1=420, d=0.12):
    t = t_(d); f = np.linspace(f0, f1, len(t)); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(len(t), 0.002, 0.035)

def tap(d=0.05):
    t = t_(d); return (np.sin(2 * np.pi * 2400 * t) * 0.6 + rng.standard_normal(len(t)) * 0.4) * env(len(t), 0.0005, 0.008)

def chime():
    t = t_(1.6); y = np.zeros(len(t))
    for k, (fr, dl) in enumerate([(659.25, 0), (987.77, 0.09), (1318.5, 0.18)]):
        s = int(SR * dl); tt = t[: len(t) - s]
        y[s:] += (np.sin(2 * np.pi * fr * tt) + 0.3 * np.sin(4 * np.pi * fr * tt)) * env(len(tt), 0.004, 0.5) * 0.5
    return y

def add(sig, frame, gain):
    s = int(frame / 30 * SR); out[s:s + len(sig)] += sig[: len(out) - s] * gain

W_UP, W_DN, W_SH = whoosh(), whoosh(up=False), whoosh(0.22, 800, 5000)
add(pop(700, 350, 0.16), 0, 0.5); add(pop(), 9, 0.45)
for i in range(3): add(W_SH, 4 + i * 4, 0.12)
for i in range(6):
    st = 60 + i * 27
    add(W_UP if i % 2 == 0 else W_DN, st - 4, 0.22)
    add(pop(1100, 520), st + 6, 0.42)
add(whoosh(0.45, 200, 2500), 226, 0.25)                                  # телефон въезжает
P = 231
add(pop(), P + 22, 0.3); add(tap(), P + 52, 0.5); add(tap(), P + 58, 0.5); add(pop(1300, 600, 0.18), P + 58, 0.45)
add(W_UP, P + 102, 0.25); add(pop(), P + 128, 0.3); add(tap(), P + 186, 0.5)
C = 443; add(W_SH, C - 2, 0.2)
for k in range(14, 44, 3): add(tap(0.02), C + k, 0.12)                   # печать
add(tap(), C + 46, 0.45); add(whoosh(0.25, 1500, 6000), C + 52, 0.2); add(pop(800, 1200, 0.14), C + 70, 0.4)
S = 547; add(W_SH, S - 2, 0.2)
for i in range(4): add(pop(1000 + i * 80, 600), S + 14 + i * 4, 0.18)
add(tap(), S + 64, 0.45); add(pop(900, 1300, 0.12), S + 70, 0.35)
add(whoosh(0.4, 2500, 200), 650, 0.22); add(chime(), 660, 0.55)
for i in range(5): add(pop(1200, 700, 0.08), 668 + i * 3, 0.15)
add(pop(600, 300, 0.2), 676, 0.4)
out = out / max(1.0, np.abs(out).max() / 0.7)
st = np.stack([out, out], 1)[: int(SR * DUR)]
with wave.open('out/sfx.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok', round(np.abs(out).max(), 2))
