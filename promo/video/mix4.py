"""
Звук ролика PromoV4 (16 с, без голоса). Основа — как у PromoReal (24 с, 30 к/с): ламповый lo-fi саундтрек 90 BPM (такт = 80 кадров — склейки
ролика стоят на долях), голос (Piper, по умолчанию женский sova200 — Apache-2.0; VOICE=… для другого), звуки интерфейса. Всё синтезировано
или сгенерировано локально — чужих треков и сэмплов нет. Музыка приглушается под голосом.
"""
import os
import wave

import numpy as np

SR, FPS, DUR = 48000, 30, 16.0
N = int(SR * DUR)
rng = np.random.default_rng(11)
BEAT = 60 / 90  # 0,667 с = 20 кадров


def fr(frame):
    return int(frame / FPS * SR)


def env(n, a=0.005, r=0.1):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x); z = 0.0
    for i, v in enumerate(x):
        z = (1 - a) * v + a * z; y[i] = z
    return y


def place(buf, sig, at, gain=1.0):
    if at >= len(buf):
        return
    e = min(len(buf), at + len(sig)); buf[at:e] += sig[: e - at] * gain


# ---------- музыка ----------
def note(m):
    return 440 * 2 ** ((m - 69) / 12)


def rhodes(freq, d):
    t = np.arange(int(SR * d)) / SR
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 6)
         + 0.12 * np.sin(2 * np.pi * 3.01 * freq * t) * np.exp(-t * 9))
    return s * trem * env(len(t), 0.01, 1.4)


def kick():
    t = np.arange(int(SR * 0.4)) / SR
    f = 45 + 80 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.001, 0.16)


def snare():
    n = int(SR * 0.25); t = np.arange(n) / SR
    noise = lowpass(rng.standard_normal(n), 5000) * env(n, 0.001, 0.07)
    return noise * 0.8 + np.sin(2 * np.pi * 185 * t) * env(n, 0.001, 0.05) * 0.5


def hat():
    n = int(SR * 0.06); x = rng.standard_normal(n)
    x = x - lowpass(x, 6000)
    return x * env(n, 0.0005, 0.015)


def bass(freq, d):
    t = np.arange(int(SR * d)) / SR
    return (np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)) * env(len(t), 0.005, 0.5)


music = np.zeros(N + SR)
CH = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]  # Fmaj7 Em7 Dm7 Cmaj7
ROOT = [41, 40, 38, 36]
bar = 4 * BEAT
for b in range(int(DUR / bar) + 1):
    t0 = b * bar; c = CH[b % 4]
    for k, m in enumerate(c):                              # аккорд с лёгким «стрампом»
        place(music, rhodes(note(m), bar * 1.05), int((t0 + k * 0.018) * SR), 0.16)
    drums = True                                           # v4: барабаны с первой доли — зацепка с ударом
    if drums:
        for q in range(4):
            tb = t0 + q * BEAT
            if q in (0, 2):
                place(music, kick(), int(tb * SR), 0.9)
            if q in (1, 3):
                place(music, snare(), int(tb * SR), 0.35)
            for h in (0, 1):                               # восьмые со свингом
                place(music, hat(), int((tb + h * BEAT * 0.58) * SR), 0.18 if h else 0.12)
        place(music, bass(note(ROOT[b % 4]), BEAT * 1.6), int(t0 * SR), 0.45)
        place(music, bass(note(ROOT[b % 4]), BEAT * 0.9), int((t0 + 2.5 * BEAT) * SR), 0.35)
music = lowpass(music, 7000)                               # «тёплый» верх, как с плёнки
crackle = np.zeros(N + SR)
for _ in range(int(DUR * 14)):
    i = rng.integers(0, N); place(crackle, rng.standard_normal(40) * env(40, 0.0001, 0.0006), i, rng.uniform(0.05, 0.25))
music += crackle * 0.5 + lowpass(rng.standard_normal(N + SR), 3000) * 0.006
# раскачка под бочку (sidechain) — характерное «дыхание» lo-fi
pump = np.ones(N + SR)
for b in range(0, 6):
    for q in (0, 2):
        s = int((b * bar + q * BEAT) * SR); n = int(SR * 0.3)
        pump[s:s + n] *= 1 - 0.35 * np.exp(-np.arange(n) / SR / 0.09)
music *= pump
# мягкий вход и уход
music[: int(SR * 0.3)] *= np.linspace(0, 1, int(SR * 0.3))
fade = int(SR * 1.2); music[N - fade:N] *= np.linspace(1, 0, fade)

# ---------- звуки интерфейса ----------
def whoosh(d=0.3, lo=300, hi=3500):
    n = int(SR * d); x = rng.standard_normal(n); f = np.linspace(lo, hi, n)
    y = np.zeros(n); a1 = a2 = 0.0
    for i in range(n):
        w_ = 2 * np.pi * f[i] / SR; r = 0.97
        yi = x[i] * (1 - r) + 2 * r * np.cos(w_) * a1 - r * r * a2; a2, a1 = a1, yi; y[i] = yi
    y *= np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return y / (np.abs(y).max() + 1e-9)


def pop(f0=900, f1=420, d=0.12):
    t = np.arange(int(SR * d)) / SR; f = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.035)


def tap(d=0.05):
    t = np.arange(int(SR * d)) / SR
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + rng.standard_normal(len(t)) * 0.4) * env(len(t), 0.0005, 0.008)


def chime():
    t = np.arange(int(SR * 1.8)) / SR; y = np.zeros(len(t))
    for fr_, dl in [(659.25, 0), (987.77, 0.09), (1318.5, 0.18)]:
        s = int(SR * dl); tt = t[: len(t) - s]
        y[s:] += (np.sin(2 * np.pi * fr_ * tt) + 0.3 * np.sin(4 * np.pi * fr_ * tt)) * env(len(tt), 0.004, 0.6) * 0.5
    return y



def impact():
    n = int(SR * 0.6); t = np.arange(n) / SR
    k = np.sin(2 * np.pi * np.cumsum(40 + 110 * np.exp(-t * 20)) / SR) * env(n, 0.001, 0.25)
    nz = lowpass(rng.standard_normal(n), 3000) * env(n, 0.001, 0.12)
    return k + nz * 0.5


sfx = np.zeros(N + SR)
W1, W2 = whoosh(), whoosh(0.22, 800, 5000)
place(sfx, impact(), fr(0), 0.7); place(sfx, impact(), fr(10), 0.55); place(sfx, pop(1300, 500, 0.15), fr(10), 0.3)
for k in range(1, 8):
    place(sfx, tap(0.03), fr(k * 5), 0.12)
place(sfx, W1, fr(36), 0.22); place(sfx, whoosh(0.7, 3000, 300), fr(56), 0.18); place(sfx, pop(), fr(74), 0.35)
place(sfx, W2, fr(97), 0.2); place(sfx, tap(), fr(112), 0.4); place(sfx, tap(), fr(118), 0.4); place(sfx, pop(1300, 600, 0.18), fr(118), 0.4)
place(sfx, W1, fr(138), 0.22); place(sfx, pop(), fr(156), 0.28); place(sfx, whoosh(0.45, 400, 2500), fr(170), 0.2)
place(sfx, tap(), fr(196), 0.45); place(sfx, whoosh(0.4, 2500, 400), fr(206), 0.16)
place(sfx, W2, fr(217), 0.2)
for at in (224, 240, 256):
    place(sfx, pop(800, 1200, 0.12), fr(at), 0.32)
place(sfx, W1, fr(277), 0.2)
for i in range(6):
    place(sfx, pop(1000 + i * 70, 600, 0.1), fr(280 + i * 7), 0.2)
for at in (280, 290, 300, 310):
    place(sfx, impact(), fr(at), 0.25)
place(sfx, impact(), fr(332), 0.45)
place(sfx, impact(), fr(380), 0.6); place(sfx, chime(), fr(384), 0.5); place(sfx, pop(600, 300, 0.2), fr(392), 0.4)

mix = music * 0.75 + sfx * 0.6
mix = mix[:N]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix = mix / np.abs(mix).max() * 0.89
st = np.stack([mix, mix], 1)
with wave.open("out/mix4.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())
print("ok")
