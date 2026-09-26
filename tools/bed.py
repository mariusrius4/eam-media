#!/usr/bin/env python3
"""
Generator de pat muzical pentru clipurile Electric Auto Market.

Muzica e compusa aici, de la zero, prin sinteza. Nu vine din nicio biblioteca,
deci nu exista nicio amprenta Content ID cu care sa se potriveasca si nimeni
altcineva nu are ce sa revendice. Fisierul asta e dovada de autorship -
se pastreaza in proiect.

Uz:  python3 bed.py --cuts 0,4.6,10.8,16.2,22.2 --end 27.2 --mood bateria --out bed.wav
"""
import argparse, wave
import numpy as np
from scipy.signal import fftconvolve

SR = 48000

# Fiecare pilon editorial are semnatura lui sonora, ca sa nu sune toate la fel.
MOODS = {
    'bateria':   dict(root=73.42,  bpm=84,  pluck=2.6, shim=0.115, wet=0.26, bright=1.00),
    'costuri':   dict(root=82.41,  bpm=92,  pluck=2.9, shim=0.100, wet=0.22, bright=1.10),
    'incarcare': dict(root=97.999, bpm=100, pluck=3.1, shim=0.135, wet=0.20, bright=1.18),
    'piata':     dict(root=65.41,  bpm=76,  pluck=2.2, shim=0.095, wet=0.30, bright=0.92),
}

CH1 = [1.0, 1.498, 2.0,   2.378]        # fundamentala, cvinta, octava, terta minora
CH2 = [1.0, 1.498, 2.245, 2.378]        # a doua asezare, cu nona
GA1 = [0.55, 0.34, 0.22, 0.17]
GA2 = [0.50, 0.30, 0.24, 0.14]
PLK = [4.0, None, 6.0, None, 4.756, None, 6.0, None,
       4.0, None, 6.0, 4.49, 4.756, None, 6.0, None]


def build(cuts, end, mood, seed=7):
    M = MOODS[mood]
    rng = np.random.default_rng(seed)
    dur = end + 1.4
    n = int(dur * SR)
    L, R = np.zeros(n), np.zeros(n)

    def add(buf, start, sig, g=1.0):
        i = int(start * SR)
        if i >= len(buf) or g == 0:
            return
        k = min(len(sig), len(buf) - i)
        buf[i:i + k] += sig[:k] * g

    def pad(freq, length, detune, harm):
        m = int(length * SR); tt = np.arange(m) / SR
        out = np.zeros(m)
        for d in (-detune, 0.0, detune):
            ph = 2 * np.pi * freq * (1 + d) * tt + rng.uniform(0, 6.28)
            for k, a in enumerate(harm, start=1):
                out += a * np.sin(k * ph + 0.3 * np.sin(0.11 * tt + k)) / k ** 0.6
        out /= 3
        atk, rel = int(min(2.2, length * .25) * SR), int(min(3.0, length * .35) * SR)
        env = np.ones(m)
        env[:atk] = np.linspace(0, 1, atk) ** 2
        env[-rel:] = np.linspace(1, 0, rel) ** 2
        env *= 0.80 + 0.20 * np.sin(2 * np.pi * 0.055 * tt)
        return out * env

    def pluck(freq, length=0.34):
        m = int(length * SR); tt = np.arange(m) / SR
        s = (np.sin(2 * np.pi * freq * tt)
             + 0.32 * np.sin(4 * np.pi * freq * tt)
             + 0.12 * np.sin(6 * np.pi * freq * tt)) * np.exp(-tt / 0.085)
        s[:96] *= np.linspace(0, 1, 96)
        return s

    def bell(freq, length=2.0):
        m = int(length * SR); tt = np.arange(m) / SR
        s = (np.sin(2 * np.pi * freq * tt) * np.exp(-tt / 0.55)
             + 0.42 * np.sin(2 * np.pi * freq * 2.76 * tt) * np.exp(-tt / 0.22)
             + 0.18 * np.sin(2 * np.pi * freq * 5.4 * tt) * np.exp(-tt / 0.11))
        s[:128] *= np.linspace(0, 1, 128)
        return s

    def impact(length=1.25):
        m = int(length * SR); tt = np.arange(m) / SR
        f = 92 * np.exp(-tt / 0.28) + 41
        sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.30)
        air = np.cumsum(rng.normal(0, 1, m) * np.exp(-tt / 0.045))
        air -= air.mean(); air /= (np.abs(air).max() + 1e-9)
        return sub * 0.85 + air * 0.10

    def shimmer(length, sd):
        m = int(length * SR); r = np.random.default_rng(sd)
        x = np.diff(np.concatenate(([0.0], r.normal(0, 1, m))))
        tt = np.arange(m) / SR
        env = np.minimum(tt / 1.8, 1.0) * np.exp(-np.maximum(tt - length + 2.4, 0) / 0.9)
        env *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.08 * tt + 1.1)
        return x * env / (np.abs(x).max() + 1e-9)

    root = M['root']
    half = end * 0.56                      # unde se schimba asezarea acordului

    # --- pad-uri, jos si sus ---
    for ratios, gains, t0, ln in ((CH1, GA1, 0.0, half + 2.0), (CH2, GA2, half, end - half + 1.2)):
        for r_, g in zip(ratios, gains):
            add(L, t0, pad(root * r_, ln, 0.0017, (1.0, .5, .28, .14, .07)), g)
            add(R, t0, pad(root * r_, ln, 0.0022, (1.0, .5, .28, .14, .07)), g)
        for r_, g in zip(ratios[:3], (.10, .075, .055)):   # corp in medii, pentru difuzor de telefon
            add(L, t0, pad(root * r_ * 4, ln, 0.0028, (1.0, .30, .12)), g * M['bright'])
            add(R, t0, pad(root * r_ * 4, ln, 0.0019, (1.0, .30, .12)), g * M['bright'])

    # --- puls, optimi ---
    step = 60.0 / M['bpm'] / 2
    t, k = 1.4, 0
    while t < end - 1.0:
        mult = PLK[k % len(PLK)]
        if mult is not None:
            arc = np.interp(t, [1.4, end * .22, end * .40, end * .80, end * .92, end - 1.0],
                            [0.0, .30, .46, .46, .16, 0.0])
            pan = 0.5 + 0.18 * np.sin(0.7 * t)
            p = pluck(root * mult)
            add(L, t, p, arc * (1 - pan) * M['pluck'])
            add(R, t, p, arc * pan * M['pluck'])
        t += step; k += 1

    # --- impact + clopotel pe fiecare taietura de scena ---
    for j, c in enumerate(cuts):
        add(L, max(0, c - 0.05), impact(), 0.42 if c > 0 else 0.30)
        add(R, max(0, c - 0.05), impact(), 0.40 if c > 0 else 0.29)
        bf = root * [8.0, 12.0, 9.512, 12.0, 8.0][j % 5]
        g = 0.13 if 0 < j < len(cuts) - 1 else 0.09
        add(L, c + 0.16, bell(bf), g * 0.85 * M['bright'])
        add(R, c + 0.16, bell(bf), g * M['bright'])

    add(L, 0.5, shimmer(end - 1.0, 11), M['shim'])
    add(R, 0.5, shimmer(end - 1.0, 29), M['shim'])

    # --- reverb ---
    def ir(sd):
        m = int(1.7 * SR); r = np.random.default_rng(sd)
        h = r.normal(0, 1, m) * np.exp(-np.arange(m) / SR / 0.42)
        h[:int(0.012 * SR)] = 0
        return h / (np.sqrt((h ** 2).sum()) + 1e-9)

    w = M['wet']
    L = (1 - w) * L + w * fftconvolve(L, ir(3))[:n]
    R = (1 - w) * R + w * fftconvolve(R, ir(8))[:n]

    mix = np.stack([L, R], axis=1)
    mix *= 0.92 / (np.abs(mix).max() + 1e-9)
    fi = int(0.25 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    return mix


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cuts', required=True)
    ap.add_argument('--end', type=float, required=True)
    ap.add_argument('--mood', default='bateria')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    cuts = [float(x) for x in a.cuts.split(',')]
    mood = a.mood if a.mood in MOODS else 'bateria'
    mix = build(cuts, a.end, mood)
    with wave.open(a.out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    print(f'{a.out}  mood={mood}  {len(mix)/SR:.1f}s')
