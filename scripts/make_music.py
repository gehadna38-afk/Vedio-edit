#!/usr/bin/env python3
"""Synthesise the calm, child-friendly background track for the reel.

Everything is generated from scratch with the standard library, so the result is
original audio: no licensing questions and nothing for Facebook's Rights Manager
to match against.

Musical design: C major pentatonic (no semitone clashes, so every combination
stays consonant), 72 BPM, music-box lead over a slow pad and a soft sine bass.

Usage: python3 make_music.py OUT.wav [duration_seconds]
"""

import array
import math
import struct
import sys
import wave

SR = 44100
BPM = 72.0
BEAT = 60.0 / BPM

# Pentatonic pitches, in Hz.
NOTE = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "G3": 196.00, "A3": 220.00,
    "F3": 174.61,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00,
    "A4": 440.00,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99, "A5": 880.00,
    "C6": 1046.50, "D6": 1174.66, "E6": 1318.51,
}


def blank(n):
    return array.array("d", bytes(8 * n))


def add_bell(buf, start, freq, dur, amp):
    """Music-box / celesta tone: a few quickly-decaying partials."""
    i0 = int(start * SR)
    n = int(dur * SR)
    if i0 >= len(buf):
        return
    n = min(n, len(buf) - i0)
    partials = ((1.0, 1.00, 3.0), (2.0, 0.42, 4.4), (3.0, 0.18, 6.0),
                (4.19, 0.09, 8.0))
    attack = int(0.004 * SR)
    for k in range(n):
        t = k / SR
        env = 1.0 if k >= attack else k / attack
        s = 0.0
        for mult, pamp, decay in partials:
            s += pamp * math.exp(-t * decay) * math.sin(
                2.0 * math.pi * freq * mult * t)
        buf[i0 + k] += amp * env * s


def add_pad(buf, start, freqs, dur, amp):
    """Soft sustained chord bed with a slow attack and release."""
    i0 = int(start * SR)
    n = int(dur * SR)
    if i0 >= len(buf):
        return
    n = min(n, len(buf) - i0)
    atk = max(1, int(0.9 * SR))
    rel = max(1, int(1.4 * SR))
    for k in range(n):
        t = k / SR
        if k < atk:
            env = k / atk
        elif k > n - rel:
            env = max(0.0, (n - k) / rel)
        else:
            env = 1.0
        env *= env  # gentler curve
        s = 0.0
        for f in freqs:
            # Two slightly detuned oscillators per voice for warmth.
            s += math.sin(2.0 * math.pi * f * t)
            s += 0.7 * math.sin(2.0 * math.pi * f * 1.0016 * t)
            s += 0.25 * math.sin(2.0 * math.pi * f * 2.0 * t)
        buf[i0 + k] += amp * env * s / (len(freqs) * 2.0)


def add_bass(buf, start, freq, dur, amp):
    i0 = int(start * SR)
    n = int(dur * SR)
    if i0 >= len(buf):
        return
    n = min(n, len(buf) - i0)
    atk = max(1, int(0.12 * SR))
    rel = max(1, int(0.5 * SR))
    for k in range(n):
        t = k / SR
        if k < atk:
            env = k / atk
        elif k > n - rel:
            env = max(0.0, (n - k) / rel)
        else:
            env = 1.0
        buf[i0 + k] += amp * env * (
            math.sin(2.0 * math.pi * freq * t)
            + 0.12 * math.sin(4.0 * math.pi * freq * t))


def reverb(buf, mix=0.28):
    """Schroeder reverb: four parallel combs into two allpass sections."""
    n = len(buf)
    combs = ((1557, 0.76), (1617, 0.74), (1491, 0.78), (1422, 0.72))
    wet = blank(n)
    for delay, fb in combs:
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
            bufout = state[pos]
            inp = wet[i]
            state[pos] = inp + bufout * g
            wet[i] = bufout - inp * g
            pos += 1
            if pos == delay:
                pos = 0

    for i in range(n):
        buf[i] = buf[i] * (1.0 - mix) + wet[i] * mix
    return buf


def build(duration):
    n = int(duration * SR)
    buf = blank(n)

    # --- Pad: C - Am - F - G, two bars each, looping. -------------------
    chords = [
        ("C", (NOTE["C4"], NOTE["E4"], NOTE["G4"])),
        ("Am", (NOTE["A3"], NOTE["C4"], NOTE["E4"])),
        ("F", (NOTE["F3"], NOTE["A4"], NOTE["C5"])),
        ("G", (NOTE["G3"], NOTE["D4"], NOTE["G4"])),
    ]
    bass_roots = [NOTE["C3"], NOTE["A3"] / 2, NOTE["F3"], NOTE["G3"]]

    bar = 0
    while bar * 4 * BEAT < duration:
        idx = (bar // 2) % 4
        if bar % 2 == 0:
            t = bar * 4 * BEAT
            add_pad(buf, t, chords[idx][1], 8 * BEAT + 0.6, 0.30)
            add_bass(buf, t, bass_roots[idx], 4 * BEAT, 0.16)
            add_bass(buf, t + 4 * BEAT, bass_roots[idx], 4 * BEAT, 0.13)
        bar += 1

    # --- Lead: an eight-bar music-box phrase, repeated with variation. --
    # (beat offset within the phrase, note, length in beats)
    phrase = [
        (0, "E5", 2), (2, "G5", 1), (3, "E5", 1),
        (4, "D5", 2), (6, "C5", 2),
        (8, "D5", 1), (9, "E5", 1), (10, "G5", 2),
        (12, "A5", 2), (14, "G5", 2),
        (16, "E5", 2), (18, "D5", 1), (19, "C5", 1),
        (20, "D5", 2), (22, "E5", 2),
        (24, "C5", 1), (25, "D5", 1), (26, "E5", 1), (27, "G5", 1),
        (28, "C5", 4),
    ]
    phrase_beats = 32

    rep = 0
    while rep * phrase_beats * BEAT < duration:
        base = rep * phrase_beats * BEAT
        # Let the melody enter only after the pad has established itself.
        for off, name, length in phrase:
            t = base + off * BEAT
            if t < 3.0 or t >= duration:
                continue
            amp = 0.24
            if rep >= 1:
                amp = 0.20
            add_bell(buf, t, NOTE[name], min(length * BEAT + 1.2, 3.0), amp)
            # Octave-up sparkle on the repeat, very quiet.
            if rep >= 1 and length >= 2:
                add_bell(buf, t + 0.5 * BEAT, NOTE[name] * 2.0, 1.0, 0.045)
        rep += 1

    # --- Gentle arpeggio sparkle in the second half. --------------------
    arp = ["C5", "E5", "G5", "E5", "D5", "G5", "A5", "G5"]
    t = duration * 0.42
    i = 0
    while t < duration - 2.0:
        add_bell(buf, t, NOTE[arp[i % len(arp)]] * 2.0, 0.9, 0.030)
        t += BEAT / 2.0
        i += 1

    reverb(buf, mix=0.30)

    # --- Normalise, then fade in/out. -----------------------------------
    peak = max(abs(v) for v in buf) or 1.0
    gain = 0.72 / peak
    fade_in = int(2.2 * SR)
    fade_out = int(3.0 * SR)
    for i in range(n):
        g = gain
        if i < fade_in:
            g *= (i / fade_in) ** 2
        if i > n - fade_out:
            g *= max(0.0, (n - i) / fade_out) ** 1.5
        buf[i] *= g
    return buf


def write_wav(path, buf):
    n = len(buf)
    frames = array.array("h", bytes(4 * n))
    # Tiny inter-channel delay widens the stereo image without phase problems.
    off = int(0.008 * SR)
    for i in range(n):
        left = buf[i]
        right = buf[i - off] if i >= off else 0.0
        right = right * 0.55 + left * 0.45
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
