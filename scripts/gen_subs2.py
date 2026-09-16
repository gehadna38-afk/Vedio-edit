#!/usr/bin/env python3
"""Generate the burned-in Arabic caption tracks for the shape-board reel.

Shares the ASS drawing and timing helpers with gen_subs.py; see that file for
the libass Spacing constraint, which applies to the styles here too.

Layout differs from the first reel: the three session goals get their own
staggered reveal in the opening seconds, so a viewer knows what the session is
training before the captions start narrating it.

Usage: python3 gen_subs2.py MAIN_DURATION_SECONDS OUTRO_DURATION_SECONDS OUTDIR
"""

import os
import sys

from gen_subs import (AMBER, BAR_H, BAR_W, BAR_Y, OUTLINE, PLATE_CY, PLATE_FILL,
                      PLATE_H, PLATE_W, PLATE_X, PLATE_Y, TITLE_CY, TITLE_FILL,
                      TITLE_H, TITLE_W, TITLE_X, TITLE_Y, WHITE, ev, rrect, shape)

W, H = 1080, 1920
FONT = "Lemonada"

BAR_TRACK = "&H8AFFFFFF"

# Goal chips, shown during the opening reveal.
CHIP_W, CHIP_H = 700, 78
CHIP_X = (W - CHIP_W) // 2
CHIP_YS = (412, 502, 592)
CHIP_FILL = "&H3C1D1712"

# Dot colours echo the toy: blue, red, green.
DOT_COLOURS = ("&H00D98B3A", "&H003A3ADF", "&H0055B84C")

GOALS = ("تمييز سمعي بصري", "تمييز الألوان", "تقوية العضلات الدقيقة")
GOALS_HEADER = "هدف الجلسة"

TITLE_MAIN = "جلسة تنمية مهارات"
TITLE_SUB = "لوحة الأشكال والألوان"

# (start, end, line1, line2)
CAPTIONS = [
    (13.8, 20.5, "الأخصائية بتطلب", "والطفل بيسمع وينفّذ"),
    (21.0, 27.7, "بيختار اللون الصح", "من وسط كل الألوان"),
    (28.2, 34.9, "ويطابق الشكل بمكانه", "مربع.. مثلث.. دايرة"),
    (35.4, 42.1, "وكل قطعة بيركّبها", "بتقوّي عضلات أصابعه"),
    (42.6, 49.3, "بيركّز ويكمّل لآخر اللوحة", "من غير ما يتشتّت"),
    (49.8, 56.5, "واللوحة اكتملت", "نحتفل بكل خطوة صغيرة"),
]

GOALS_IN, GOALS_OUT = 5.0, 13.2

HEADER = """[Script Info]
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
Style: Sub,{font},40,{amber},{amber},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.6,1.8,5,40,40,40,1
Style: Chip,{font},42,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.4,1.6,5,40,40,40,1
Style: Shape,{font},40,{white},{white},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(w=W, h=H, font=FONT, white=WHITE, amber=AMBER, outline=OUTLINE)


def circle(cx, cy, r):
    """Circle as an ASS drawing path, with proper bezier handles."""
    k = r * 0.5523
    def n(v):
        return ("%.1f" % v).rstrip("0").rstrip(".")
    return ("m {l} {cy} b {l} {uk} {lk} {u} {cx} {u} "
            "b {rk} {u} {rr} {uk} {rr} {cy} "
            "b {rr} {dk} {rk} {d} {cx} {d} "
            "b {lk} {d} {l} {dk} {l} {cy}").format(
        l=n(cx - r), rr=n(cx + r), u=n(cy - r), d=n(cy + r), cx=n(cx), cy=n(cy),
        lk=n(cx - k), rk=n(cx + k), uk=n(cy - k), dk=n(cy + k))


def build_main(duration):
    out = [HEADER]

    # --- Opening title over live footage --------------------------------
    t0, t1 = 0.3, 4.6
    out.append(shape(1, t0, t1, TITLE_FILL,
                     rrect(TITLE_X, TITLE_Y, TITLE_W, TITLE_H, 30),
                     "\\fad(280,320)"))
    out.append(ev(2, t0, t1, "Big",
                  "{\\an5\\pos(%d,%d)\\fad(280,320)\\fscx90\\fscy90"
                  "\\t(0,300,\\fscx100\\fscy100)}%s"
                  % (W // 2, TITLE_CY - 34, TITLE_MAIN)))
    out.append(ev(2, t0 + 0.18, t1, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(320,320)}%s"
                  % (W // 2, TITLE_CY + 44, TITLE_SUB)))
    out.append(shape(2, t0 + 0.1, t1, AMBER,
                     rrect(W // 2 - 60, TITLE_CY + 6, 120, 5, 2.5),
                     "\\fad(320,320)"))

    # --- Session goals: staggered reveal, then out of the way ------------
    out.append(ev(2, GOALS_IN, GOALS_OUT, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(300,400)\\fs54\\c%s}%s"
                  % (W // 2, 326, WHITE, GOALS_HEADER)))
    out.append(shape(2, GOALS_IN + 0.08, GOALS_OUT, AMBER,
                     rrect(W // 2 - 56, 362, 112, 5, 2.5), "\\fad(300,400)"))

    for i, (text, y, dot) in enumerate(zip(GOALS, CHIP_YS, DOT_COLOURS)):
        start = GOALS_IN + 0.35 + i * 0.55
        cy = y + CHIP_H // 2
        dot_x = CHIP_X + CHIP_W - 66
        # Drawings anchor with \an7 and absolute coordinates; \an5 would let
        # libass re-centre a path that is already centred on its own origin.
        # Each chip slides in from the right, the reading-start side.
        plate_move = "\\move(%d,%d,%d,%d,0,320)" % (CHIP_X + 70, y, CHIP_X, y)
        dot_move = "\\move(%d,%d,%d,%d,0,320)" % (
            dot_x + 70, cy, dot_x, cy)
        # Centre the label in the space left of the dot, not the whole
        # chip, or the dot pulls the line visually off centre.
        text_cx = (CHIP_X + dot_x) // 2

        out.append(ev(1, start, GOALS_OUT, "Shape",
                      "{\\an7%s\\c%s\\fad(260,400)\\p1}%s"
                      % (plate_move, CHIP_FILL,
                         rrect(0, 0, CHIP_W, CHIP_H, 26))))
        out.append(ev(2, start, GOALS_OUT, "Chip",
                      "{\\an5%s\\fad(260,400)}%s"
                      % ("\\move(%d,%d,%d,%d,0,320)"
                         % (text_cx + 70, cy, text_cx, cy), text)))
        out.append(ev(2, start + 0.12, GOALS_OUT, "Shape",
                      "{\\an7%s\\c%s\\fad(300,400)\\p1}%s"
                      % (dot_move, dot, circle(0, 0, 11))))

    # --- Captions -------------------------------------------------------
    plate_path = rrect(PLATE_X, PLATE_Y, PLATE_W, PLATE_H, 34)
    for start, end, l1, l2 in CAPTIONS:
        out.append(shape(1, start, end, PLATE_FILL, plate_path,
                         "\\fad(220,220)"))
        out.append(ev(2, start, end, "Cap",
                      "{\\an5\\move(%d,%d,%d,%d,0,260)\\fad(220,220)}%s\\N%s"
                      % (W // 2, PLATE_CY + 14, W // 2, PLATE_CY, l1, l2)))

    # --- Progress bar ---------------------------------------------------
    out.append(shape(1, 0.0, duration, BAR_TRACK,
                     rrect(PLATE_X, BAR_Y, BAR_W, BAR_H, BAR_H / 2.0),
                     "\\alpha&HB0&\\fad(400,300)"))
    out.append(ev(2, 0.0, duration, "Shape",
                  "{\\an7\\pos(%d,%d)\\c%s\\fscx0\\t(0,%d,\\fscx100)"
                  "\\fad(400,300)\\p1}%s"
                  % (PLATE_X, BAR_Y, AMBER, int(duration * 1000),
                     rrect(0, 0, BAR_W, BAR_H, BAR_H / 2.0))))
    return "".join(out)


BRAND = "سوبر نينو"
OUTRO_CTA = "احجزي جلسة تقييم لطفلك"
OUTRO_PHONE = "01031907588"
OUTRO_ADDR = "بنها — أمام مستشفى الجامعة"


def build_outro(duration):
    out = [HEADER]
    cy = H // 2
    out.append(ev(2, 0.1, duration, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(400,400)\\fs50}%s"
                  % (W // 2, cy - 250, BRAND)))
    out.append(ev(2, 0.3, duration, "Big",
                  "{\\an5\\move(%d,%d,%d,%d,0,420)\\fad(420,400)}%s"
                  % (W // 2, cy - 100, W // 2, cy - 122, OUTRO_CTA)))
    out.append(shape(1, 0.5, duration, AMBER,
                     rrect(W // 2 - 70, cy - 40, 140, 6, 3), "\\fad(500,400)"))
    out.append(ev(2, 0.9, duration, "Big",
                  "{\\an5\\pos(%d,%d)\\fad(420,400)\\c%s}%s"
                  % (W // 2, cy + 50, AMBER, OUTRO_PHONE)))
    out.append(ev(2, 1.2, duration, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(420,400)\\fs42\\c%s}%s"
                  % (W // 2, cy + 160, WHITE, OUTRO_ADDR)))
    return "".join(out)


if __name__ == "__main__":
    main_dur = float(sys.argv[1])
    outro_dur = float(sys.argv[2])
    outdir = sys.argv[3]
    with open(os.path.join(outdir, "main2.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_main(main_dur))
    with open(os.path.join(outdir, "outro2.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_outro(outro_dur))
    print("wrote main2.ass (%.2fs) and outro2.ass (%.2fs)" % (main_dur, outro_dur))
