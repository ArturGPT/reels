"""Generate an original soft electronic bed: pad chords + kick + hats, 100 bpm. Writes wav."""
import sys, wave
import numpy as np

SR = 44100
dur = float(sys.argv[2]); out = sys.argv[1]
n = int(dur * SR); t = np.arange(n) / SR
bpm = 100; beat = 60 / bpm; bar = beat * 4

# chord progression (Am - F - C - G), frequencies of triads an octave low
CH = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [130.81, 164.81, 196.0], [196.0, 246.94, 293.66]]
pad = np.zeros(n)
for i in range(int(dur / bar) + 1):
    s0, s1 = int(i * bar * SR), min(n, int((i + 1) * bar * SR))
    if s0 >= n: break
    seg = t[s0:s1] - i * bar
    env = np.minimum(1, seg / 0.6) * np.minimum(1, (bar - seg) / 0.4)
    for f in CH[i % 4]:
        for det in (-0.6, 0.6):  # detuned saw-ish via few harmonics
            ph = 2 * np.pi * (f + det) * t[s0:s1]
            pad[s0:s1] += env * (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph))
pad /= np.abs(pad).max() + 1e-9
# simple low-pass smoothing of pad
k = np.ones(40) / 40; pad = np.convolve(pad, k, mode="same")

kick = np.zeros(n); hat = np.zeros(n)
rng = np.random.default_rng(7)
for b in range(int(dur / beat) + 1):
    s = int(b * beat * SR)
    if s >= n: break
    L = min(int(0.25 * SR), n - s); tt = np.arange(L) / SR
    kick[s:s + L] += np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
    h = int((b + 0.5) * beat * SR)
    if h < n:
        L2 = min(int(0.05 * SR), n - h)
        hat[h:h + L2] += rng.normal(0, 1, L2) * np.exp(-np.arange(L2) / SR * 80)
hat = np.diff(hat, prepend=0)  # crude high-pass
mixv = 0.55 * pad + 0.6 * kick + 0.12 * hat
fade = np.minimum(1, t / 1.0) * np.minimum(1, (dur - t) / 1.5)
mixv = mixv * fade
mixv = mixv / (np.abs(mixv).max() + 1e-9) * 0.9
data = (np.stack([mixv, mixv], 1) * 32767).astype("<i2")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
