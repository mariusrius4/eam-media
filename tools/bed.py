#!/usr/bin/env python3
"""
Generator de pat muzical pentru clipurile Electric Auto Market.

Muzica e compusa aici, de la zero, prin sinteza. Nu vine din nicio biblioteca,
deci nu exista nicio amprenta Content ID cu care sa se potriveasca si nimeni
altcineva nu are ce sa revendice. Fisierul asta e dovada de autorship -
se pastreaza in proiect.

Sapte „mood”-uri, cate unul pe pilon editorial, fiecare cu alta tonalitate,
alt tempo, alt desen ritmic si alte instrumente — ca sa NU sune toate la fel.
In plus, `--seed` (de regula derivat din numele clipului) schimba fraza,
asezarea acordurilor si ordinea clopoteilor, deci doua clipuri din acelasi
pilon nu sunt identice.

Uz:  python3 bed.py --cuts 0,4.6,10.8,16.2,22.2 --end 27.2 --mood bateria --seed 1234 --out bed.wav
     (sau --name 2026-10-27-anvelope  → seed-ul se calculeaza din nume)
"""
import argparse, wave, zlib
import numpy as np
from scipy.signal import fftconvolve

SR = 48000

# rapoarte de frecventa fata de fundamentala
M2, m3, M3, P4, TT, P5, M6, m7, M7, O8, M9 = (
    1.1225, 1.1892, 1.2599, 1.3348, 1.4142, 1.4983, 1.6818, 1.7818, 1.8877, 2.0, 2.2449)

# Fiecare pilon editorial are semnatura lui sonora.
#  root   - fundamentala (Hz)            bpm    - tempo
#  chords - doua-trei asezari de acord (se alege prin seed si se schimba la 56% din clip)
#  pat    - desenul plucks pe optimi: multiplicator de frecventa sau None (pauza); 2 variante
#  pluck  - timbrul: (decay s, armonici)   bass  - puls de bas pe patrimi (0 = fara)
#  arp    - arpegiu continuu pe 16-imi (0/1)   accent - ce se aude pe taieturi: impact / riser / click
#  bell   - cat de prezente sunt clopoteii    shim/wet/bright - aer, reverb, stralucire
MOODS = {
    # Bateria — adanc, calm, pad dominant, putine plucks, clopotei lungi
    'bateria':   dict(root=73.42, bpm=80, bright=1.00, shim=0.12, wet=0.28, bell=1.0, bass=0.0, arp=0,
                      accent='impact', pluck=(0.085, (1.0, .32, .12)), plk=2.2,
                      chords=[[1, m3, P5, O8], [1, P5, m7, M9], [1, m3, P5, m7]],
                      pat=[[4, None, None, 6, None, None, 4.76, None, 6, None, None, 4, None, None, None, None],
                           [4, None, None, None, 6, None, None, None, 4.76, None, None, 6, None, None, None, None]]),
    # Incarcare — rapid, major, arpegiu continuu, luminos
    'incarcare': dict(root=98.0, bpm=108, bright=1.18, shim=0.14, wet=0.17, bell=0.7, bass=0.0, arp=1,
                      accent='impact', pluck=(0.070, (1.0, .40, .15)), plk=2.4,
                      chords=[[1, M3, P5, M9], [1, M3, M6, O8], [1, P5, M9, 2*M3]],
                      pat=[[4, 5.04, 6, 8, 6, 5.04, 4, 6, 4, 5.04, 6, 8, 6, 5.04, 4, 6],
                           [4, 6, 5.04, 8, 4, 6, 5.04, 8, 4, 6, 5.04, 8, 4, 6, 5.04, 8]]),
    # Range real — larg, deschis, lidian, riser pe taieturi, fraza de 3 optimi peste 4
    'range':     dict(root=87.31, bpm=90, bright=1.05, shim=0.16, wet=0.32, bell=0.6, bass=0.0, arp=0,
                      accent='riser', pluck=(0.110, (1.0, .25, .08)), plk=2.0,
                      chords=[[1, TT, P5, O8], [1, M3, M7, O8], [1, P5, M7, M9]],
                      pat=[[4, None, None, 6, None, None, 5.66, None, None, 4, None, None, 8, None, None, None],
                           [4, None, None, 5.66, None, None, 6, None, None, 8, None, None, 4, None, None, None]]),
    # Costuri reale — precis, minor, puls de bas pe patrimi, plucks staccato, fara clopotei
    'costuri':   dict(root=82.41, bpm=96, bright=1.10, shim=0.08, wet=0.15, bell=0.0, bass=0.9, arp=0,
                      accent='click', pluck=(0.045, (1.0, .50, .22)), plk=2.6,
                      chords=[[1, m3, P5, m7], [1, P4, P5, O8], [1, m3, P5, O8]],
                      pat=[[4, 4, None, 4, 4.76, None, 4, 4, None, 4, 6, None, 4, 4, None, 4.76],
                           [4, None, 4, 4, None, 4.76, 4, None, 4, 4, None, 6, 4, None, 4, 4]]),
    # Cum cumperi corect — prietenos, major in registru inalt, marimba, saltaret
    'cumperi':   dict(root=65.41, bpm=86, bright=1.12, shim=0.10, wet=0.21, bell=0.5, bass=0.35, arp=0,
                      accent='impact', pluck=(0.060, (1.0, .10, .35, .12)), plk=2.8,
                      chords=[[O8, 2*M3, 2*P5, 4], [O8, 2*P4, 2*M6, 4], [O8, 2*M3, 2*M6, 2*M9]],
                      pat=[[8, None, 10.08, 8, None, 12, None, 8, 10.08, None, 8, None, 12, None, 16, None],
                           [8, None, 12, None, 10.08, None, 8, 12, None, 8, None, 16, None, 12, None, None]]),
    # Piata RO — reflexiv, dorian, pluck de bas o octava mai jos, reverb mare
    'piata':     dict(root=110.0, bpm=76, bright=0.92, shim=0.10, wet=0.30, bell=0.8, bass=0.0, arp=0,
                      accent='impact', pluck=(0.120, (1.0, .30, .10)), plk=2.0, lowpluck=1,
                      chords=[[1, m3, P5, M6], [1, P4, m7, O8], [1, m3, M6, O8]],
                      pat=[[2, None, None, None, 3, None, None, None, 2.38, None, None, None, 3, None, None, None],
                           [2, None, None, None, 2.38, None, None, None, 3, None, None, None, 3.36, None, None, None]]),
    # Transparenta dealer — clar, sus2/sus4, clopotei metalici, uscat
    'dealer':    dict(root=123.47, bpm=100, bright=1.15, shim=0.07, wet=0.13, bell=1.3, bass=0.0, arp=0,
                      accent='impact', pluck=(0.075, (1.0, .20, .45, .18)), plk=2.3,
                      chords=[[1, M2, P5, O8], [1, P4, P5, O8], [1, M2, P5, M9]],
                      pat=[[2, None, 2.245, None, 3, None, None, 2, None, 2.67, None, 3, None, None, 4, None],
                           [2, None, 3, None, 2.245, None, 4, None, 2, None, 3, None, 2.67, None, None, None]]),
}
# denumiri alternative (pilonul din Notion, cu sau fara diacritice)
ALIASES = {
    'bateria': 'bateria', 'baterie': 'bateria',
    'incarcare': 'incarcare', 'încărcare': 'incarcare',
    'range': 'range', 'range real': 'range', 'autonomie': 'range',
    'costuri': 'costuri', 'costuri reale': 'costuri',
    'cumperi': 'cumperi', 'cum cumperi corect': 'cumperi', 'cumparare': 'cumperi',
    'piata': 'piata', 'piata ro': 'piata', 'piața ro': 'piata', 'piață ro': 'piata',
    'dealer': 'dealer', 'transparenta dealer': 'dealer', 'transparența dealer': 'dealer',
}


def resolve_mood(s):
    key = (s or '').strip().lower()
    return ALIASES.get(key) or ('bateria' if key not in MOODS else key)


def seed_from(name):
    return zlib.crc32((name or 'eam').encode('utf-8')) & 0xFFFF


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
        env *= 0.80 + 0.20 * np.sin(2 * np.pi * 0.055 * tt + rng.uniform(0, 6.28))
        return out * env

    dec, harm = M['pluck']

    def pluck(freq, length=None):
        length = length or min(0.5, dec * 4.5)
        m = int(length * SR); tt = np.arange(m) / SR
        s = np.zeros(m)
        for k, a in enumerate(harm, start=1):
            s += a * np.sin(2 * np.pi * freq * k * tt) * np.exp(-tt / (dec / k ** 0.5))
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

    def riser(length=1.6):
        # fasie de zgomot care urca si se rupe pe taietura
        m = int(length * SR); tt = np.arange(m) / SR
        x = rng.normal(0, 1, m)
        x = np.diff(np.concatenate(([0.0], x)))          # mai aerat
        env = (tt / length) ** 2.2
        env[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
        return x * env / (np.abs(x).max() + 1e-9)

    def click(length=0.09):
        m = int(length * SR); tt = np.arange(m) / SR
        s = np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt / 0.012) + 0.5 * rng.normal(0, 1, m) * np.exp(-tt / 0.006)
        return s / (np.abs(s).max() + 1e-9)

    def thump(freq, length=0.32):
        m = int(length * SR); tt = np.arange(m) / SR
        f = freq * (1 + 1.8 * np.exp(-tt / 0.03))
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.11)
        s[:48] *= np.linspace(0, 1, 48)
        return s

    def shimmer(length, sd):
        m = int(length * SR); r = np.random.default_rng(sd)
        x = np.diff(np.concatenate(([0.0], r.normal(0, 1, m))))
        tt = np.arange(m) / SR
        env = np.minimum(tt / 1.8, 1.0) * np.exp(-np.maximum(tt - length + 2.4, 0) / 0.9)
        env *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.08 * tt + 1.1)
        return x * env / (np.abs(x).max() + 1e-9)

    root = M['root']
    half = end * 0.56                      # unde se schimba asezarea acordului

    # --- acorduri: doua asezari alese prin seed ---
    ch_idx = rng.permutation(len(M['chords']))[:2]
    CH1, CH2 = M['chords'][ch_idx[0]], M['chords'][ch_idx[1]]
    GA1, GA2 = [0.55, 0.34, 0.22, 0.17], [0.50, 0.30, 0.24, 0.14]

    # --- pad-uri, jos si sus ---
    for ratios, gains, t0, ln in ((CH1, GA1, 0.0, half + 2.0), (CH2, GA2, half, end - half + 1.2)):
        for r_, g in zip(ratios, gains):
            add(L, t0, pad(root * r_, ln, 0.0017, (1.0, .5, .28, .14, .07)), g)
            add(R, t0, pad(root * r_, ln, 0.0022, (1.0, .5, .28, .14, .07)), g)
        for r_, g in zip(ratios[:3], (.10, .075, .055)):   # corp in medii, pentru difuzor de telefon
            add(L, t0, pad(root * r_ * 4, ln, 0.0028, (1.0, .30, .12)), g * M['bright'])
            add(R, t0, pad(root * r_ * 4, ln, 0.0019, (1.0, .30, .12)), g * M['bright'])

    # --- plucks pe optimi (sau arpegiu pe 16-imi) ---
    pat = list(M['pat'][rng.integers(len(M['pat']))])
    rot = int(rng.integers(len(pat)))
    pat = pat[rot:] + pat[:rot]
    step = 60.0 / M['bpm'] / (4 if M['arp'] else 2)
    t, k = 1.4, 0
    while t < end - 1.0:
        mult = pat[k % len(pat)]
        if M['arp']:
            # arpegiu: notele acordului curent, in bucla, cu accent pe prima
            chord = CH1 if t < half else CH2
            mult = chord[k % len(chord)] * (2 if chord[k % len(chord)] < 1.5 else 1)
        if mult is not None:
            arc = np.interp(t, [1.4, end * .22, end * .40, end * .80, end * .92, end - 1.0],
                            [0.0, .30, .46, .46, .16, 0.0])
            if M['arp'] and k % len(CH1) != 0:
                arc *= 0.7
            pan = 0.5 + 0.18 * np.sin(0.7 * t + rng.uniform(0, 1))
            p = pluck(root * mult)
            add(L, t, p, arc * (1 - pan) * M['plk'])
            add(R, t, p, arc * pan * M['plk'])
            if M.get('lowpluck'):
                q = pluck(root * mult / 2, 0.6)
                add(L, t, q, arc * 0.9); add(R, t, q, arc * 0.9)
        t += step; k += 1

    # --- puls de bas pe patrimi ---
    if M['bass'] > 0:
        beat = 60.0 / M['bpm']
        t = 1.4; j = 0
        while t < end - 1.2:
            arc = np.interp(t, [1.4, end * .25, end * .85, end - 1.2], [0.0, 1.0, 1.0, 0.0])
            g = M['bass'] * arc * (1.0 if j % 2 == 0 else 0.55)
            th = thump(root / 2 if root > 90 else root)
            add(L, t, th, g); add(R, t, th, g)
            t += beat; j += 1

    # --- accent pe fiecare taietura de scena ---
    bell_order = rng.permutation([8.0, 12.0, 9.512, 12.0, 8.0, 10.08]).tolist()
    for j, c in enumerate(cuts):
        if M['accent'] == 'impact':
            add(L, max(0, c - 0.05), impact(), 0.42 if c > 0 else 0.30)
            add(R, max(0, c - 0.05), impact(), 0.40 if c > 0 else 0.29)
        elif M['accent'] == 'riser' and c > 0:
            add(L, max(0, c - 1.6), riser(), 0.26)
            add(R, max(0, c - 1.6), riser(), 0.24)
            add(L, c - 0.02, impact(0.8), 0.22); add(R, c - 0.02, impact(0.8), 0.21)
        elif M['accent'] == 'click':
            add(L, c, click(), 0.30); add(R, c + 0.004, click(), 0.28)
            add(L, max(0, c - 0.03), impact(0.9), 0.34); add(R, max(0, c - 0.03), impact(0.9), 0.32)
        if M['bell'] > 0:
            bf = root * bell_order[j % len(bell_order)]
            g = (0.13 if 0 < j < len(cuts) - 1 else 0.09) * M['bell']
            add(L, c + 0.16, bell(bf), g * 0.85 * M['bright'])
            add(R, c + 0.16, bell(bf), g * M['bright'])

    add(L, 0.5, shimmer(end - 1.0, seed + 11), M['shim'])
    add(R, 0.5, shimmer(end - 1.0, seed + 29), M['shim'])

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
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--name', default=None, help='numele clipului; da seed-ul daca --seed lipseste')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    cuts = [float(x) for x in a.cuts.split(',')]
    mood = resolve_mood(a.mood)
    seed = a.seed if a.seed is not None else seed_from(a.name)
    mix = build(cuts, a.end, mood, seed)
    with wave.open(a.out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    print(f'{a.out}  mood={mood}  seed={seed}  {len(mix)/SR:.1f}s')
