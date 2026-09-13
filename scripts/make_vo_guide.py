#!/usr/bin/env python3
"""Lay the project's narration lines onto a timing guide track.

This is a SCRATCH track, not a publishable voice-over: it is espeak-ng, which
is robotic. Its job is to prove the timing - to show whether each line actually
fits the scene it belongs to before anyone records the real thing - and to
exercise the mixing path the real recording will travel.

Every line is checked against the start of the next one, and any overrun is
reported, because a line that runs past its scene is the one thing a script
cannot show on paper.

Usage: python3 make_vo_guide.py PROJECT OUT.wav TOTAL_SECONDS [words_per_min]
"""

import array
import os
import subprocess
import sys
import tempfile
import wave

import project as project_mod

SR = 44100


def synth(text, wpm, path):
    subprocess.run(["espeak-ng", "-v", "ar", "-s", str(wpm), "-w", path, text],
                   check=True, capture_output=True)
    with wave.open(path, "rb") as w:
        frames = w.readframes(w.getnframes())
        src_rate, channels = w.getframerate(), w.getnchannels()
    samples = array.array("h")
    samples.frombytes(frames)
    if channels == 2:
        samples = array.array("h", samples[0::2])
    # espeak writes 22050 Hz; the rest of the pipeline is 44100. The ratio is a
    # whole number, so plain sample repetition is exact enough for a guide.
    step = SR // src_rate
    if step > 1:
        out = array.array("h", bytes(2 * len(samples) * step))
        for i, v in enumerate(samples):
            for k in range(step):
                out[i * step + k] = v
        samples = out
    return samples


def build(cfg, total, wpm):
    n = int(total * SR)
    bed = array.array("i", bytes(4 * n))
    lines = cfg["voiceover"]["script"]
    report = []

    with tempfile.TemporaryDirectory() as tmp:
        for i, (at, text) in enumerate(lines):
            clip = synth(text, wpm, os.path.join(tmp, "l%d.wav" % i))
            start = int(float(at) * SR)
            dur = len(clip) / SR
            nxt = float(lines[i + 1][0]) if i + 1 < len(lines) else total
            report.append((float(at), dur, nxt - float(at), text))
            for k, v in enumerate(clip):
                j = start + k
                if 0 <= j < n:
                    bed[j] += v

    peak = max((abs(v) for v in bed), default=1) or 1
    gain = min(1.0, 26000.0 / peak)
    out = array.array("h", bytes(4 * n))
    for i in range(n):
        v = int(bed[i] * gain)
        v = max(-32768, min(32767, v))
        out[2 * i] = v
        out[2 * i + 1] = v
    return out, report


if __name__ == "__main__":
    cfg = project_mod.load(sys.argv[1])
    out_path = sys.argv[2]
    total = float(sys.argv[3])
    wpm = int(sys.argv[4]) if len(sys.argv) > 4 else 150

    samples, report = build(cfg, total, wpm)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(samples.tobytes())

    print("wrote %s (%.1fs)" % (out_path, total))
    print("%-7s %-7s %-7s  %s" % ("at", "spoken", "slot", "line"))
    for at, dur, slot, text in report:
        flag = "  <-- OVERRUNS by %.1fs" % (dur - slot) if dur > slot else ""
        print("%-7.1f %-7.1f %-7.1f  %s%s" % (at, dur, slot, text[:44], flag))
