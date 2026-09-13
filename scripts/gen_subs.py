#!/usr/bin/env python3
"""Generate the burned-in Arabic caption tracks (ASS) for a reel.

libass is built here with HarfBuzz and FriBidi, so Arabic text is shaped and
bidi-reordered correctly; the text in the project file is written in plain
logical order.

Layout targets Facebook Reels safe zones: captions sit around 58-70% of the
frame height, clear of the bottom description strip and the right-hand action
rail, and clear of the subject, which stays near the vertical middle.

All text, colours and timings come from the project JSON; this file holds only
the layout and animation, which is the same for every reel.

Usage: python3 gen_subs.py PROJECT MAIN_DURATION OUTRO_DURATION OUTDIR
"""

import os
import sys

import project as project_mod

W, H = 1080, 1920

# Caption plate geometry.
PLATE_W, PLATE_H = 830, 216
PLATE_X = (W - PLATE_W) // 2
PLATE_CY = 1230
PLATE_Y = PLATE_CY - PLATE_H // 2

BAR_Y = PLATE_Y + PLATE_H + 24
BAR_W, BAR_H = PLATE_W, 8

# Title card geometry.
TITLE_W, TITLE_H = 780, 208
TITLE_X = (W - TITLE_W) // 2
TITLE_CY = 356
TITLE_Y = TITLE_CY - TITLE_H // 2


def ts(seconds):
    """Seconds -> ASS timestamp H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return "%d:%02d:%02d.%02d" % (h, m, s, cs)


def rrect(x, y, w, h, r):
    """Rounded rectangle as an ASS drawing path."""
    r = min(r, w / 2.0, h / 2.0)
    x2, y2 = x + w, y + h
    return (
        "m {xr} {y} l {x2r} {y} b {x2} {y} {x2} {y} {x2} {yr} "
        "l {x2} {y2r} b {x2} {y2} {x2} {y2} {x2r} {y2} "
        "l {xr} {y2} b {x} {y2} {x} {y2} {x} {y2r} "
        "l {x} {yr} b {x} {y} {x} {y} {xr} {y}"
    ).format(x=f(x), y=f(y), x2=f(x2), y2=f(y2), xr=f(x + r), yr=f(y + r),
             x2r=f(x2 - r), y2r=f(y2 - r))


def f(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


# Every style must keep Spacing at 0: a non-zero value makes libass position
# glyphs individually, which disables Arabic shaping and bidi reordering and
# renders the text backwards in disconnected letterforms.
HEADER_TMPL = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},54,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,3.2,2.4,5,40,40,40,1
Style: Big,{font},74,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,3.6,2.6,5,40,40,40,1
Style: Sub,{font},40,{accent},{accent},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.6,1.8,5,40,40,40,1
Style: Shape,{font},40,{white},{white},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def header(theme):
    return HEADER_TMPL.format(w=W, h=H, font=theme["font"],
                              white=theme["white"], accent=theme["accent"],
                              outline=theme["outline"])


def ev(layer, start, end, style, text):
    return "Dialogue: %d,%s,%s,%s,,0,0,0,,%s\n" % (
        layer, ts(start), ts(end), style, text)


def shape(layer, start, end, colour, path, extra=""):
    return ev(layer, start, end, "Shape",
              "{\\an7\\pos(0,0)\\c%s%s\\p1}%s" % (colour, extra, path))


def build_main(cfg, duration):
    """The reel body: opening title over live footage, then timed captions.

    Every caption must describe something visible in the frame. Footage with no
    audio track cannot support any claim about what was said on camera.
    """
    theme = cfg["theme"]
    title = cfg["title"]
    accent = theme["accent"]

    out = [header(theme)]
    plate_path = rrect(PLATE_X, PLATE_Y, PLATE_W, PLATE_H, 34)

    # --- Opening title, overlaid on live footage so the reel never opens on
    # --- a static card (which costs retention in the first second).
    t0, t1 = float(title["start"]), float(title["end"])
    out.append(shape(1, t0, t1, theme["title_fill"],
                     rrect(TITLE_X, TITLE_Y, TITLE_W, TITLE_H, 30),
                     "\\fad(280,320)"))
    out.append(ev(2, t0, t1, "Big",
                  "{\\an5\\pos(%d,%d)\\fad(280,320)\\fscx90\\fscy90"
                  "\\t(0,300,\\fscx100\\fscy100)}%s"
                  % (W // 2, TITLE_CY - 34, title["main"])))
    out.append(ev(2, t0 + 0.18, t1, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(320,320)}%s"
                  % (W // 2, TITLE_CY + 44, title["sub"])))
    # Small accent underline between the two title lines.
    out.append(shape(2, t0 + 0.1, t1, accent,
                     rrect(W // 2 - 60, TITLE_CY + 6, 120, 5, 2.5),
                     "\\fad(320,320)"))

    # --- Captions -------------------------------------------------------
    for start, end, l1, l2 in cfg["captions"]:
        out.append(shape(1, start, end, theme["plate_fill"], plate_path,
                         "\\fad(220,220)"))
        out.append(ev(2, start, end, "Cap",
                      "{\\an5\\move(%d,%d,%d,%d,0,260)\\fad(220,220)}%s\\N%s"
                      % (W // 2, PLATE_CY + 14, W // 2, PLATE_CY, l1, l2)))

    # --- Progress bar: a quiet "how much is left" cue that lifts watch time.
    out.append(shape(1, 0.0, duration, theme["bar_track"],
                     rrect(PLATE_X, BAR_Y, BAR_W, BAR_H, BAR_H / 2.0),
                     "\\alpha&HB0&\\fad(400,300)"))
    out.append(ev(2, 0.0, duration, "Shape",
                  "{\\an7\\pos(%d,%d)\\c%s\\fscx0\\t(0,%d,\\fscx100)"
                  "\\fad(400,300)\\p1}%s"
                  % (PLATE_X, BAR_Y, accent, int(duration * 1000),
                     rrect(0, 0, BAR_W, BAR_H, BAR_H / 2.0))))
    return "".join(out)


def build_outro(cfg, duration):
    theme = cfg["theme"]
    outro = cfg["outro"]
    out = [header(theme)]
    cy = H // 2
    out.append(shape(1, 0.0, duration, theme["accent"],
                     rrect(W // 2 - 70, cy + 60, 140, 6, 3),
                     "\\fad(500,400)"))
    for i, (style, text, dy) in enumerate(outro["lines"]):
        out.append(ev(2, 0.15 + i * 0.35, duration, style,
                      "{\\an5\\move(%d,%d,%d,%d,0,420)\\fad(420,400)}%s"
                      % (W // 2, cy + dy + 22, W // 2, cy + dy, text)))
    out.append(ev(2, 1.1, duration, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(420,400)\\fs46}%s"
                  % (W // 2, cy + 150, outro["cta"])))
    return "".join(out)


if __name__ == "__main__":
    cfg = project_mod.load(sys.argv[1])
    main_dur = float(sys.argv[2])
    outro_dur = float(sys.argv[3])
    outdir = sys.argv[4]
    with open(os.path.join(outdir, "main.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_main(cfg, main_dur))
    with open(os.path.join(outdir, "outro.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_outro(cfg, outro_dur))
    print("wrote main.ass (%.2fs) and outro.ass (%.2fs)" % (main_dur, outro_dur))
