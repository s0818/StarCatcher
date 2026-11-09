# Synthesizes a soft, upbeat background track (no external samples).
import sys, wave
import numpy as np

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 92.0
BPM = 100
beat = 60 / BPM
n = int(SR * DUR)
t = np.arange(n) / SR
L = np.zeros(n); R = np.zeros(n)

def note(f): return 440 * 2 ** ((f - 69) / 12)

# Cmaj7 - Am7 - Fmaj7 - G(add9), one chord per bar (4 beats)
prog = [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 55, 62]]
bar = beat * 4

def env(length, a, r):
    e = np.ones(length)
    ai = min(length, int(a * SR)); ri = min(length, int(r * SR))
    e[:ai] = np.linspace(0, 1, ai)
    e[-ri:] *= np.linspace(1, 0, ri)
    return e

i = 0
tb = 0.0
while tb < DUR:
    chord = prog[i % 4]
    s = int(tb * SR); e = min(n, int((tb + bar) * SR)); ln = e - s
    if ln <= 0: break
    tt = np.arange(ln) / SR
    # Pad
    pad = sum(np.sin(2 * np.pi * note(m) * tt) + 0.3 * np.sin(2 * np.pi * note(m) * 2.003 * tt) for m in chord)
    pad *= env(ln, 0.6, 0.6) * 0.035
    L[s:e] += pad; R[s:e] += pad
    # Bass on beats 1 and 3
    for b in (0, 2):
        bs = s + int(b * beat * SR); be = min(n, bs + int(beat * 1.6 * SR))
        if bs >= n: continue
        bt = np.arange(be - bs) / SR
        bass = np.sin(2 * np.pi * note(chord[0] - 12) * bt) * np.exp(-bt * 2.5) * 0.12
        L[bs:be] += bass; R[bs:be] += bass
    # Arpeggio (8th notes) after the intro
    if tb >= bar * 2:
        arp = [chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[2] + 24]
        for k in range(8):
            as_ = s + int(k * beat / 2 * SR); ae = min(n, as_ + int(0.4 * SR))
            if as_ >= n: continue
            at = np.arange(ae - as_) / SR
            m = arp[k % 4]
            pl = (np.sin(2 * np.pi * note(m) * at) + 0.25 * np.sin(4 * np.pi * note(m) * at)) * np.exp(-at * 9) * 0.05
            pan = 0.3 if k % 2 else -0.3
            L[as_:ae] += pl * (1 - pan); R[as_:ae] += pl * (1 + pan)
    # Soft kick + hat from bar 4
    if tb >= bar * 4:
        for b in range(4):
            ks = s + int(b * beat * SR); ke = min(n, ks + int(0.25 * SR))
            if ks >= n: continue
            kt = np.arange(ke - ks) / SR
            kick = np.sin(2 * np.pi * (50 + 80 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 12) * 0.18
            L[ks:ke] += kick; R[ks:ke] += kick
            hs = s + int((b + 0.5) * beat * SR); he = min(n, hs + int(0.05 * SR))
            if hs >= n: continue
            hat = np.random.RandomState(b).randn(he - hs) * np.exp(-np.arange(he - hs) / SR * 80) * 0.02
            L[hs:he] += hat; R[hs:he] += hat
    tb += bar; i += 1

# Simple stereo delay for space
d = int(beat * 0.75 * SR)
L[d:] += R[:-d] * 0.18; R[d:] += L[:-d] * 0.18

# Fade in/out
fi = int(1.5 * SR); fo = int(3.0 * SR)
for ch in (L, R):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)

mx = max(np.abs(L).max(), np.abs(R).max())
st = np.stack([L, R], axis=1) / mx * 0.8
data = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
print('bgm ok', DUR)
