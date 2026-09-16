#!/usr/bin/env python3
"""Generate the burned-in Arabic caption tracks for the shape-board reel.

Shares the ASS drawing and timing helpers with gen_subs.py; see that file for
the libass Spacing constraint, which applies to the styles here too.

Everything sits in the top fifth of the frame. The board and the two pairs of
hands occupy the middle and lower thirds for the whole clip, and a caption over
them hides the very thing the reel is meant to show.

Usage: python3 gen_subs2.py MAIN_DURATION_SECONDS OUTRO_DURATION_SECONDS OUTDIR
"""

import os
import sys

from gen_subs import AMBER, OUTLINE, WHITE, ev, rrect, shape

W, H = 1080, 1920
FONT = "Lemonada"

# Caption bar, pinned to the top so the action below stays clear.
BAR_X, BAR_W = 80, 920
BAR_TOP, BAR_H = 140, 172
BAR_CY = BAR_TOP + BAR_H // 2
BADGE_CX, BADGE_R = 930, 32
TEXT_CX = (BAR_X + BADGE_CX - BADGE_R) // 2

PROG_Y, PROG_H = 336, 7

PLATE_FILL = "&H3A160F0C"
CHIP_FILL = "&H3C1D1712"
TRACK = "&H8AFFFFFF"

# Step colours cycle through the toy's own palette.
STEP_COLOURS = ("&H002D2DDC", "&H00DC782D", "&H004BB43C",
                "&H003CC8F5", "&H002D2DDC", "&H00DC782D")
DIGITS = ("١", "٢", "٣", "٤", "٥", "٦")

TITLE_W, TITLE_H = 780, 200
TITLE_X = (W - TITLE_W) // 2
TITLE_TOP = 150
TITLE_CY = TITLE_TOP + TITLE_H // 2

CHIP_W, CHIP_H = 700, 76
CHIP_X = (W - CHIP_W) // 2
CHIP_YS = (272, 360, 448)
DOT_COLOURS = ("&H00DC782D", "&H002D2DDC", "&H004BB43C")

GOALS = ("تمييز سمعي بصري", "تمييز الألوان", "تقوية العضلات الدقيقة")
GOALS_HEADER = "هدف الجلسة"
GOALS_IN, GOALS_OUT = 4.5, 11.0

TITLE_MAIN = "جلسة تنمية مهارات"
TITLE_SUB = "لوحة الأشكال والألوان"

# (start, end, line1, line2)
CAPTIONS = [
    (11.6, 17.8, "الأخصائية بتطلب", "والطفل بيسمع وينفّذ"),
    (18.1, 24.3, "بيختار اللون الصح", "من وسط كل الألوان"),
    (24.6, 30.8, "ويطابق الشكل بمكانه", "مربع.. مثلث.. دايرة"),
    (31.1, 37.3, "وكل قطعة بيركّبها", "بتقوّي عضلات أصابعه"),
    (37.6, 43.4, "بيركّز ويكمّل لآخر اللوحة", "من غير ما يتشتّت"),
    (43.7, 49.3, "واللوحة اكتملت", "نحتفل بكل خطوة صغيرة"),
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
Style: Cap,{font},48,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,3.0,2.2,5,20,20,20,1
Style: Big,{font},72,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,3.6,2.6,5,40,40,40,1
Style: Sub,{font},40,{amber},{amber},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.6,1.8,5,40,40,40,1
Style: Chip,{font},42,{white},{white},{outline},&H64000000,-1,0,0,0,100,100,0,0,1,2.4,1.6,5,40,40,40,1
Style: Step,{font},40,&H00FFFFFF,&H00FFFFFF,&H00201008,&H64000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
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
    t0, t1 = 0.3, 4.2
    out.append(shape(1, t0, t1, PLATE_FILL,
                     rrect(TITLE_X, TITLE_TOP, TITLE_W, TITLE_H, 30),
                     "\\fad(260,300)"))
    out.append(ev(2, t0, t1, "Big",
                  "{\\an5\\pos(%d,%d)\\fad(260,300)\\fscx90\\fscy90"
                  "\\t(0,300,\\fscx100\\fscy100)}%s"
                  % (W // 2, TITLE_CY - 32, TITLE_MAIN)))
    out.append(ev(2, t0 + 0.18, t1, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(300,300)}%s"
                  % (W // 2, TITLE_CY + 44, TITLE_SUB)))
    out.append(shape(2, t0 + 0.1, t1, AMBER,
                     rrect(W // 2 - 60, TITLE_CY + 4, 120, 5, 2.5),
                     "\\fad(300,300)"))

    # --- Session goals: staggered reveal, then out of the way ------------
    out.append(ev(2, GOALS_IN, GOALS_OUT, "Sub",
                  "{\\an5\\pos(%d,%d)\\fad(280,360)\\fs52\\c%s}%s"
                  % (W // 2, 196, WHITE, GOALS_HEADER)))
    out.append(shape(2, GOALS_IN + 0.08, GOALS_OUT, AMBER,
                     rrect(W // 2 - 56, 228, 112, 5, 2.5), "\\fad(280,360)"))

    for i, (text, y, dot) in enumerate(zip(GOALS, CHIP_YS, DOT_COLOURS)):
        start = GOALS_IN + 0.3 + i * 0.45
        cy = y + CHIP_H // 2
        dot_x = CHIP_X + CHIP_W - 62
        # Drawings anchor with \an7 and absolute coordinates; \an5 would let
        # libass re-centre a path that is already centred on its own origin.
        plate_move = "\\move(%d,%d,%d,%d,0,300)" % (CHIP_X + 70, y, CHIP_X, y)
        dot_move = "\\move(%d,%d,%d,%d,0,300)" % (dot_x + 70, cy, dot_x, cy)
        # Centre the label in the space left of the dot, not the whole chip,
        # or the dot pulls the line visually off centre.
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

    # --- Captions: numbered steps in a top bar that wipes in -------------
    bar_path = rrect(BAR_X, BAR_TOP, BAR_W, BAR_H, 34)
    for i, (start, end, l1, l2) in enumerate(CAPTIONS):
        colour = STEP_COLOURS[i % len(STEP_COLOURS)]
        dur = int((end - start) * 1000)
        # Right-to-left reveal: animate the clip window's left edge inwards,
        # matching the reading direction.
        wipe = ("\\clip(%d,%d,%d,%d)\\t(0,300,\\clip(%d,%d,%d,%d))"
                % (BAR_X + BAR_W, BAR_TOP, BAR_X + BAR_W, BAR_TOP + BAR_H,
                   BAR_X, BAR_TOP, BAR_X + BAR_W, BAR_TOP + BAR_H))

        out.append(ev(1, start, end, "Shape",
                      "{\\an7\\pos(0,0)\\c%s\\fad(180,200)%s\\p1}%s"
                      % (PLATE_FILL, wipe, bar_path)))
        out.append(ev(2, start + 0.12, end, "Cap",
                      "{\\an5\\pos(%d,%d)\\fad(200,200)}%s\\N%s"
                      % (TEXT_CX, BAR_CY, l1, l2)))
        # Numbered badge: a coloured disc that pops in with the step number.
        out.append(ev(2, start + 0.18, end, "Shape",
                      "{\\an7\\pos(%d,%d)\\c%s\\fad(200,200)"
                      "\\fscx40\\fscy40\\t(0,240,\\fscx100\\fscy100)\\p1}%s"
                      % (BADGE_CX, BAR_CY, colour, circle(0, 0, BADGE_R))))
        out.append(ev(3, start + 0.26, end, "Step",
                      "{\\an5\\pos(%d,%d)\\fad(220,200)}%s"
                      % (BADGE_CX, BAR_CY, DIGITS[i % len(DIGITS)])))
        # A thin colour tick under the bar, sized to this step's share.
        seg_w = BAR_W / float(len(CAPTIONS))
        # Finished steps stay filled, so the bar reads as progress instead of
        # a dash sliding along.
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

    # --- Progress track: only once the goal chips have cleared, or it cuts
    # --- a line straight through them.
    out.append(shape(0, GOALS_OUT, duration, TRACK,
                     rrect(BAR_X, PROG_Y, BAR_W, PROG_H, PROG_H / 2.0),
                     "\\alpha&HC0&\\fad(400,300)"))
    return "".join(out)


BRAND = "سوبر نينو"
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
    with open(os.path.join(outdir, "main2.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_main(main_dur))
    with open(os.path.join(outdir, "outro2.ass"), "w", encoding="utf-8") as fh:
        fh.write(build_outro(outro_dur))
    print("wrote main2.ass (%.2fs) and outro2.ass (%.2fs)" % (main_dur, outro_dur))
