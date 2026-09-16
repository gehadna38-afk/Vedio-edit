#!/usr/bin/env python3
"""Generate the burned-in Arabic caption tracks for the shape-sorter reel.

This source is landscape, so the footage is letterboxed into a band across the
middle of the 9:16 frame and everything else is designed around it: title and
goals above, captions below. Nothing overlaps the footage at all.

Shares the ASS drawing helpers with gen_subs.py and gen_subs2.py; see gen_subs.py
for the libass Spacing constraint, which applies to these styles too.

Usage: python3 gen_subs3.py MAIN_DURATION_SECONDS OUTRO_DURATION_SECONDS OUTDIR
"""

import os
import sys

from gen_subs import AMBER, OUTLINE, WHITE, ev, rrect, shape
from gen_subs2 import circle

W, H = 1080, 1920

# The letterboxed footage band. build_reel3.sh overlays the video here, so these
# must stay in step with VIDEO_TOP/VIDEO_H in that script.
VIDEO_TOP, VIDEO_H = 560, 608
VIDEO_BOTTOM = VIDEO_TOP + VIDEO_H

# Caption bar, in the clear band below the footage.
BAR_X, BAR_W = 80, 920
BAR_TOP, BAR_H = 1246, 172
BAR_CY = BAR_TOP + BAR_H // 2
BADGE_CX, BADGE_R = 930, 32
TEXT_CX = (BAR_X + BADGE_CX - BADGE_R) // 2

PROG_Y, PROG_H = 1446, 7

PLATE_FILL = "&H3A160F0C"
CHIP_FILL = "&H3C1D1712"
TRACK = "&H8AFFFFFF"

STEP_COLOURS = ("&H002D2DDC", "&H00DC782D", "&H004BB43C",
                "&H003CC8F5", "&H002D2DDC", "&H004BB43C")
DIGITS = ("١", "٢", "٣", "٤", "٥", "٦")

TITLE_W, TITLE_H = 780, 196
TITLE_X = (W - TITLE_W) // 2
TITLE_TOP = 150
TITLE_CY = TITLE_TOP + TITLE_H // 2

CHIP_W, CHIP_H = 660, 76
CHIP_X = (W - CHIP_W) // 2
CHIP_YS = (286, 378)
DOT_COLOURS = ("&H003CC8F5", "&H004BB43C")

GOALS = ("التطابق", "التدريب على حل المشكلات")
GOALS_HEADER = "هدف الجلسة"
GOALS_IN, GOALS_OUT = 4.3, 10.0

BRAND = "سوبر نينو"
TITLE_MAIN = "جلسة تنمية مهارات"
TITLE_SUB = "صندوق الأشكال"

# (start, end, line1, line2)
CAPTIONS = [
    (10.6, 17.4, "الطفل بيشوف الشكل", "ويدوّر على مكانه المطابق"),
    (17.7, 24.5, "مش أول مرة بيظبط", "بيجرّب ويلفّ القطعة"),
    (24.8, 31.6, "ودي بالظبط حل المشكلات", "يحاول.. يعدّل.. ينجح"),
    (31.9, 38.7, "كل شكل له مكان واحد بس", "مثلث.. دايرة.. مربع"),
    (39.0, 45.8, "بيقارن بعينه قبل ما يحط", "تآزر بصري حركي"),
    (46.1, 52.4, "وخطوة بخطوة الصندوق بيمتلي", "نحتفل بكل قطعة بتدخل"),
]

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Lemonada,48,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,3.0,2.2,5,20,20,20,1
Style: Big,Lemonada,72,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,3.6,2.6,5,40,40,40,1
Style: Sub,Lemonada,40,{amber},{amber},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.6,1.8,5,40,40,40,1
Style: Chip,Lemonada,42,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.4,1.6,5,40,40,40,1
Style: Step,Lemonada,40,&H00FFFFFF,&H00FFFFFF,&H00201008,&H64000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Shape,Lemonada,40,{white},{white},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(w=W, h=H, white=WHITE, amber=AMBER, outline=OUTLINE)


def build_main(duration):
    out = [HEADER]

    # --- Thin rules framing the footage band, so the letterbox reads as a
    # --- deliberate frame rather than a video that failed to fill the screen.
    for y in (VIDEO_TOP - 5, VIDEO_BOTTOM + 1):
        out.append(shape(0, 0.0, duration, AMBER,
                         rrect(BAR_X, y, BAR_W, 4, 2),
                         "\\alpha&H60&\\fad(500,400)"))

    # --- Opening title ---------------------------------------------------
    t0, t1 = 0.3, 4.0
    out.append(shape(1, t0, t1, PLATE_FILL,
                     rrect(TITLE_X, TITLE_TOP, TITLE_W, TITLE_H, 30),
                     "\\fad(260,300)"))
    out.append(ev(2, t0, t1, "Big",
                  "{\\an5\\pos(%d,%d)\\fad(260,300)\\fscx90\\fscy90"
                  "\\t(0,300,\\fscx100\\fscy100)}%s"
                  % (W // 2, TITLE_CY - 30, TITLE_MAIN)))
    out.append(ev(2, t0 + 0.18, t1, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(300,300)}%s"
                  % (W // 2, TITLE_CY + 44, TITLE_SUB)))
    out.append(shape(2, t0 + 0.1, t1, AMBER,
                     rrect(W // 2 - 60, TITLE_CY + 4, 120, 5, 2.5),
                     "\\fad(300,300)"))

    # --- Session goals ---------------------------------------------------
    out.append(ev(2, GOALS_IN, GOALS_OUT, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(280,360)\\fs52\\c%s}%s"
                  % (W // 2, 210, WHITE, GOALS_HEADER)))
    out.append(shape(2, GOALS_IN + 0.08, GOALS_OUT, AMBER,
                     rrect(W // 2 - 56, 242, 112, 5, 2.5), "\\fad(280,360)"))

    for i, (text, y, dot) in enumerate(zip(GOALS, CHIP_YS, DOT_COLOURS)):
        start = GOALS_IN + 0.3 + i * 0.5
        cy = y + CHIP_H // 2
        dot_x = CHIP_X + CHIP_W - 62
        # Drawings anchor with \an7 and absolute coordinates; \an5 would let
        # libass re-centre a path already centred on its own origin.
        plate_move = "\\move(%d,%d,%d,%d,0,300)" % (CHIP_X + 70, y, CHIP_X, y)
        dot_move = "\\move(%d,%d,%d,%d,0,300)" % (dot_x + 70, cy, dot_x, cy)
        text_cx = (CHIP_X + dot_x) // 2
        text_move = "\\move(%d,%d,%d,%d,0,300)" % (
            text_cx + 70, cy, text_cx, cy)

        out.append(ev(1, start, GOALS_OUT, "Shape",
                      "{\\an7%s\\c%s\\fad(240,360)\\p1}%s"
                      % (plate_move, CHIP_FILL,
                         rrect(0, 0, CHIP_W, CHIP_H, 26))))
        out.append(ev(2, start, GOALS_OUT, "Chip",
                      "{\\an5%s\\fad(240,360)}%s" % (text_move, text)))
        out.append(ev(2, start + 0.1, GOALS_OUT, "Shape",
                      "{\\an7%s\\c%s\\fad(280,360)\\p1}%s"
                      % (dot_move, dot, circle(0, 0, 11))))

    # --- Brand tag: the band above the footage is otherwise empty for the
    # --- rest of the reel once the goal chips clear.
    tag_w, tag_h, tag_y = 300, 68, 268
    out.append(shape(1, GOALS_OUT + 0.3, duration, CHIP_FILL,
                     rrect((W - tag_w) // 2, tag_y, tag_w, tag_h, 24),
                     "\\fad(400,300)"))
    out.append(ev(2, GOALS_OUT + 0.3, duration, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(400,300)\\fs44}%s"
                  % (W // 2, tag_y + tag_h // 2, BRAND)))

    # --- Captions: numbered steps, below the footage ---------------------
    bar_path = rrect(BAR_X, BAR_TOP, BAR_W, BAR_H, 34)
    seg_w = BAR_W / float(len(CAPTIONS))
    for i, (start, end, l1, l2) in enumerate(CAPTIONS):
        colour = STEP_COLOURS[i % len(STEP_COLOURS)]
        dur = int((end - start) * 1000)
        # Right-to-left reveal, matching the reading direction.
        wipe = ("\\clip(%d,%d,%d,%d)\\t(0,300,\\clip(%d,%d,%d,%d))"
                % (BAR_X + BAR_W, BAR_TOP, BAR_X + BAR_W, BAR_TOP + BAR_H,
                   BAR_X, BAR_TOP, BAR_X + BAR_W, BAR_TOP + BAR_H))

        out.append(ev(1, start, end, "Shape",
                      "{\\an7\\pos(0,0)\\c%s\\fad(180,200)%s\\p1}%s"
                      % (PLATE_FILL, wipe, bar_path)))
        out.append(ev(2, start + 0.12, end, "Cap",
                      "{\\an5\\pos(%d,%d)\\fad(200,200)}%s\\N%s"
                      % (TEXT_CX, BAR_CY, l1, l2)))
        out.append(ev(2, start + 0.18, end, "Shape",
                      "{\\an7\\pos(%d,%d)\\c%s\\fad(200,200)"
                      "\\fscx40\\fscy40\\t(0,240,\\fscx100\\fscy100)\\p1}%s"
                      % (BADGE_CX, BAR_CY, colour, circle(0, 0, BADGE_R))))
        out.append(ev(3, start + 0.26, end, "Step",
                      "{\\an5\\pos(%d,%d)\\fad(220,200)}%s"
                      % (BADGE_CX, BAR_CY, DIGITS[i % len(DIGITS)])))
        # Finished steps stay filled, so the bar reads as progress.
        if i:
            out.append(ev(1, start, end, "Shape",
                          "{\\an7\\pos(%d,%d)\\c%s\\alpha&H78&"
                          "\\fad(180,200)\\p1}%s"
                          % (BAR_X, PROG_Y, AMBER,
                             rrect(0, 0, i * seg_w, PROG_H, PROG_H / 2.0))))
        out.append(ev(2, start, end, "Shape",
                      "{\\an7\\pos(%d,%d)\\c%s\\fscx0\\t(0,%d,\\fscx100)"
                      "\\fad(180,200)\\p1}%s"
                      % (BAR_X + i * seg_w, PROG_Y, colour, dur,
                         rrect(0, 0, seg_w, PROG_H, PROG_H / 2.0))))

    out.append(shape(0, GOALS_OUT, duration, TRACK,
                     rrect(BAR_X, PROG_Y, BAR_W, PROG_H, PROG_H / 2.0),
                     "\\alpha&HC0&\\fad(400,300)"))
    return "".join(out)


OUTRO_CTA = "احجزي جلسة تقييم لطفلك"
OUTRO_PHONE = "01031907588"
OUTRO_ADDR = "بنها — أمام مستشفى الجامعة"


def build_outro(duration):
    out = [HEADER]
    cy = H // 2
    out.append(ev(2, 0.1, duration, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(360,360)\\fs50}%s"
                  % (W // 2, cy - 250, BRAND)))
    out.append(ev(2, 0.25, duration, "Big",
                  "{\\an5\\move(%d,%d,%d,%d,0,380)\\fad(380,360)}%s"
                  % (W // 2, cy - 100, W // 2, cy - 122, OUTRO_CTA)))
    out.append(shape(1, 0.4, duration, AMBER,
                     rrect(W // 2 - 70, cy - 40, 140, 6, 3), "\\fad(420,360)"))
    out.append(ev(2, 0.7, duration, "Big",
                  "{\\an5\\pos(%d,%d)\\fad(380,360)\\c%s}%s"
                  % (W // 2, cy + 50, AMBER, OUTRO_PHONE)))
    out.append(ev(2, 0.95, duration, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(380,360)\\fs42\\c%s}%s"
                  % (W // 2, cy + 160, WHITE, OUTRO_ADDR)))
    return "".join(out)


if __name__ == "__main__":
    main_dur = float(sys.argv[1])
    outro_dur = float(sys.argv[2])
    outdir = sys.argv[3]
    with open(os.path.join(outdir, "main3.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_main(main_dur))
    with open(os.path.join(outdir, "outro3.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_outro(outro_dur))
    print("wrote main3.ass (%.2fs) and outro3.ass (%.2fs)" % (main_dur, outro_dur))
