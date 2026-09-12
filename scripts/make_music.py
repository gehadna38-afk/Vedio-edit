#!/usr/bin/env python3
"""Synthesise the children's background track for the reel.

Everything is generated from scratch with the standard library, so the result is
original audio: no licensing questions and nothing for Facebook's Rights Manager
to match against. Commercial nursery tracks (Baby Shark and friends) are
fingerprinted and enforced on Meta, and using one gets a reel muted or
throttled, which is the whole reason this exists.

Musical design: a cheerful eight-bar nursery-style tune in C major at 104 BPM.
Glockenspiel lead over a bouncing marimba bass, soft kick and shaker, and a
quiet pad for warmth - playful and clearly "kids music", but soft enough to sit
under captions.

Usage: python3 make_music.py OUT.wav [duration_seconds]
"""

import array
import math
import random
import sys
import wave

SR = 44100
BPM = 104.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT

# MIDI note numbers.
C5, D5, E5, G5, A5 = 72, 74, 76, 79, 81


def hz(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def blank(n):
    return array.array("d", bytes(8 * n))


def _span(buf, start, dur):
    i0 = int(start * SR)
    n = int(dur * SR)
    if i0 < 0 or i0 >= len(buf):
        return None, 0
    return i0, min(n, len(buf) - i0)


def tone(buf, start, midi, dur, amp, partials, attack=0.003):
    """Struck-percussion voice: partials with independent decay rates."""
    i0, n = _span(buf, start, dur)
    if not n:
        return
    freq = hz(midi)
    atk = max(1, int(attack * SR))
    for k in range(n):
        t = k / SR
        env = 1.0 if k >= atk else k / atk
        s = 0.0
        for mult, pamp, decay in partials:
            s += pamp * math.exp(-t * decay) * math.sin(
                2.0 * math.pi * freq * mult * t)
        buf[i0 + k] += amp * env * s


# Bright, bell-like: the melody instrument.
GLOCK = ((1.0, 1.00, 4.2), (3.0, 0.34, 7.0), (5.4, 0.16, 9.5),
         (8.9, 0.05, 13.0))
# Wooden and short: the bass instrument.
MARIMBA = ((1.0, 1.00, 6.5), (4.0, 0.22, 11.0), (10.0, 0.06, 16.0))


def glock(buf, start, midi, dur, amp):
    tone(buf, start, midi, min(dur + 0.9, 2.4), amp, GLOCK)


def marimba(buf, start, midi, dur, amp):
    tone(buf, start, midi, min(dur + 0.4, 1.2), amp, MARIMBA)


def kick(buf, start, amp):
    """Soft round kick: a pitch-dropping sine plus a small mid click so it
    still reads on phone speakers, which roll off below ~150 Hz."""
    i0, n = _span(buf, start, 0.22)
    if not n:
        return
    phase = 0.0
    for k in range(n):
        t = k / SR
        f = 45.0 + 55.0 * math.exp(-t * 32.0)
        phase += 2.0 * math.pi * f / SR
        env = math.exp(-t * 11.0)
        click = 0.22 * math.exp(-t * 90.0) * math.sin(2.0 * math.pi * 210.0 * t)
        buf[i0 + k] += amp * (env * math.sin(phase) + click)


def shaker(buf, start, amp, rng):
    """Filtered noise burst. Differentiating the noise tilts it bright, which
    is what separates a shaker from a thud."""
    i0, n = _span(buf, start, 0.09)
    if not n:
        return
    prev = 0.0
    smooth = 0.0
    for k in range(n):
        t = k / SR
        w = rng.uniform(-1.0, 1.0)
        # Tilt bright, then roll the very top back off so it reads as a shaker
        # rather than hiss on phone speakers.
        hp = 0.7 * (w - prev) + 0.3 * w
        prev = w
        smooth = 0.6 * smooth + 0.4 * hp
        buf[i0 + k] += amp * math.exp(-t * 42.0) * smooth


def pad(buf, start, midis, dur, amp):
    i0, n = _span(buf, start, dur)
    if not n:
        return
    freqs = [hz(m) for m in midis]
    atk = max(1, int(0.5 * SR))
    rel = max(1, int(0.7 * SR))
    for k in range(n):
        t = k / SR
        if k < atk:
            env = k / atk
        elif k > n - rel:
            env = max(0.0, (n - k) / rel)
        else:
            env = 1.0
        env *= env
        s = 0.0
        for f in freqs:
            s += math.sin(2.0 * math.pi * f * t)
            s += 0.6 * math.sin(2.0 * math.pi * f * 1.0016 * t)
        buf[i0 + k] += amp * env * s / (len(freqs) * 2.0)


def reverb(buf, mix=0.16):
    """Schroeder reverb. Kept restrained: a long tail would smear the bounce."""
    n = len(buf)
    wet = blank(n)
    for delay, fb in ((1557, 0.74), (1617, 0.72), (1491, 0.76), (1422, 0.70)):
        state = blank(delay)
        pos = 0
        for i in range(n):
            y = state[pos]
            wet[i] += y
            state[pos] = buf[i] + y * fb
            pos += 1
            if pos == delay:
                pos = 0
    for i in range(n):
        wet[i] *= 0.25
    for delay, g in ((225, 0.5), (556, 0.5)):
        state = blank(delay)
        pos = 0
        for i in range(n):
            out = state[pos]
            inp = wet[i]
            state[pos] = inp + out * g
            wet[i] = out - inp * g
            pos += 1
            if pos == delay:
                pos = 0
    for i in range(n):
        buf[i] = buf[i] * (1.0 - mix) + wet[i] * mix


# Eight-bar tune. Per bar: (beat offset in bar, note, length in beats).
MELODY = [
    [(0, E5, 1), (1, G5, 1), (2, E5, 1), (3, C5, 1)],
    [(0, D5, 1), (1, E5, 1), (2, D5, 2)],
    [(0, C5, 1), (1, D5, 1), (2, E5, 1), (3, G5, 1)],
    [(0, A5, 2), (2, G5, 2)],
    [(0, G5, 1), (1, E5, 1), (2, G5, 1), (3, A5, 1)],
    [(0, G5, 1), (1, E5, 1), (2, C5, 2)],
    [(0, D5, 1), (1, E5, 1), (2, D5, 1), (3, C5, 1)],
    [(0, C5, 4)],
]
# Chord bed and bass root per bar: C - G - C - F - C - Am - G - C
CHORDS = [(60, 64, 67), (55, 59, 62), (60, 64, 67), (53, 57, 60),
          (60, 64, 67), (57, 60, 64), (55, 59, 62), (60, 64, 67)]
ROOTS = [36, 43, 36, 41, 36, 45, 43, 36]


def build(duration):
    n = int(duration * SR)
    buf = blank(n)
    rng = random.Random(7)

    n_bars = int(math.ceil(duration / BAR))
    last_bars = n_bars - 2  # wind down at the end

    for b in range(n_bars):
        t0 = b * BAR
        if t0 >= duration:
            break
        p = b % 8
        # Bar 0 is an intro: melody and shaker only, so the tune arrives first.
        full = b >= 1
        winding_down = b >= last_bars

        pad(buf, t0, CHORDS[p], BAR + 0.3, 0.16)

        for off, midi, length in MELODY[p]:
            glock(buf, t0 + off * BEAT, midi, length * BEAT, 0.34)
            # Octave-up doubling from the second phrase on, for sparkle.
            if b >= 8 and length >= 2:
                glock(buf, t0 + off * BEAT, midi + 12, length * BEAT, 0.05)

        if full:
            # Bouncing bass: root on 1 and 3, fifth on the "and" of 2.
            marimba(buf, t0, ROOTS[p], BEAT, 0.26)
            marimba(buf, t0 + 1.5 * BEAT, ROOTS[p] + 7, BEAT * 0.5, 0.13)
            marimba(buf, t0 + 2 * BEAT, ROOTS[p], BEAT, 0.22)

        if full and not winding_down:
            kick(buf, t0, 0.34)
            kick(buf, t0 + 2 * BEAT, 0.30)

        for e in range(8):
            if not winding_down or e % 2 == 0:
                amp = 0.085 if e % 2 == 0 else 0.048
                shaker(buf, t0 + e * BEAT * 0.5, amp, rng)

    reverb(buf, mix=0.16)

    peak = max(abs(v) for v in buf) or 1.0
    gain = 0.85 / peak
    # Short fade in: a long one reads as "the video has no music".
    fade_in = int(0.8 * SR)
    fade_out = int(2.6 * SR)
    for i in range(n):
        g = gain
        if i < fade_in:
            g *= i / fade_in
        if i > n - fade_out:
            g *= max(0.0, (n - i) / fade_out) ** 1.4
        buf[i] *= g
    return buf


def write_wav(path, buf):
    n = len(buf)
    frames = array.array("h", bytes(4 * n))
    off = int(0.007 * SR)
    for i in range(n):
        left = buf[i]
        right = buf[i - off] if i >= off else 0.0
        right = right * 0.5 + left * 0.5
        frames[2 * i] = max(-32768, min(32767, int(left * 32767)))
        frames[2 * i + 1] = max(-32768, min(32767, int(right * 32767)))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames.tobytes())


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "music.wav"
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0
    write_wav(out, build(dur))
    print("wrote %s (%.1fs)" % (out, dur))
