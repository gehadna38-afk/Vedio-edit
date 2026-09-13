#!/usr/bin/env python3
"""Render a card reel's scenes to one burned-in ASS track.

A card reel has no footage: the whole video is drawn. Scenes come from the
project's `scenes` list, each with a type, a start and an end. Four types cover
the clinic's poster language:

  hook   Two large lines and a supporting line on a white card. The opener.
  brand  Name and tagline under the logo (the logo itself is overlaid by
         ffmpeg, so this scene leaves the upper frame empty for it).
  list   A heading and a stack of pills, each with a coloured dot, appearing
         one after another. Set "numbered" to put 1..n in the dots instead.
  cta    The closing ask: headline, a navy phone bar and an address line.

Colours are named in the project's `theme.palette` and referenced by name from
the scenes, so recolouring the reel is one edit.

Usage:
  python3 gen_cards.py PROJECT OUTDIR      # writes cards.ass
  python3 gen_cards.py PROJECT --duration  # prints the reel length in seconds
"""

import os
import random
import sys

import project as project_mod
from assbase import ass_colour, circle, ev, rrect, shape, star

W, H = 1080, 1920

CARD_X, CARD_W, CARD_R = 80, 920, 46
PILL_X, PILL_W, PILL_H, PILL_GAP, PILL_R = 110, 860, 152, 26, 48

BAR_X, BAR_W, BAR_H, BAR_Y = 150, 780, 10, 1450

# Layers, low to high.
L_STAR, L_SHADOW, L_CARD, L_ACCENT, L_TEXT, L_BAR = 0, 1, 2, 3, 4, 5

# Every style must keep Spacing at 0 - see assbase for why. Outline is 0 here:
# the text sits on white cards, so an outline would only muddy the letterforms.
HEADER_TMPL = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: H1,{font},80,{ink},{ink},&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1
Style: H2,{font},58,{ink},{ink},&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1
Style: Body,{font},44,{ink},{ink},&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1
Style: Pill,{font},46,{ink},{ink},&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,6,40,40,40,1
Style: Dot,{font},40,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Icon,DejaVu Sans,44,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Phone,{font},58,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Shape,{font},40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def nl(text):
    """'a|b' -> an ASS hard line break, so project files stay readable."""
    return text.replace("|", "\\N")


class Palette(dict):
    def ass(self, name, fallback="ink"):
        return ass_colour(self.get(name) or self[fallback])


def card(t0, t1, x, y, w, h, r=CARD_R, fill="&H00FFFFFF", fade="\\fad(300,240)"):
    """A white panel with a soft drop shadow, the clinic's poster building block."""
    return [
        shape(L_SHADOW, t0, t1, ass_colour("#0B2C63"), rrect(x + 4, y + 12, w, h, r),
              "\\alpha&HDE&\\blur18" + fade),
        shape(L_CARD, t0, t1, fill, rrect(x, y, w, h, r), fade),
    ]


def scene_hook(sc, pal, out):
    t0, t1 = sc["start"], sc["end"]
    y, h = sc.get("y", 610), sc.get("h", 600)
    out += card(t0, t1, CARD_X, y, CARD_W, h)

    cy = y + 150
    for i, line in enumerate(sc["lines"]):
        text, colour = (line if isinstance(line, list) else [line, "ink"])
        out.append(ev(L_TEXT, t0 + 0.10 + i * 0.16, t1, "H1",
                      "{\\an5\\move(%d,%d,%d,%d,0,300)\\fad(280,240)\\c%s}%s"
                      % (W // 2, cy + i * 120 + 26, W // 2, cy + i * 120,
                         pal.ass(colour), nl(text))))

    bar_y = y + 150 + len(sc["lines"]) * 120 - 40
    out.append(shape(L_ACCENT, t0 + 0.24, t1, pal.ass(sc.get("rule", "amber")),
                     rrect(W // 2 - 64, bar_y, 128, 7, 3.5), "\\fad(320,240)"))

    if sc.get("sub"):
        out.append(ev(L_TEXT, t0 + 0.34, t1, "Body",
                      "{\\an5\\pos(%d,%d)\\fad(320,240)\\c%s}%s"
                      % (W // 2, bar_y + 76, pal.ass(sc.get("sub_colour", "teal_ink")),
                         nl(sc["sub"]))))


def scene_brand(sc, pal, out):
    """Name and tagline; the logo above them is an ffmpeg overlay, not ASS."""
    t0, t1 = sc["start"], sc["end"]
    cy = sc.get("y", 1180)
    out.append(ev(L_TEXT, t0 + 0.30, t1, "H1",
                  "{\\an5\\move(%d,%d,%d,%d,0,340)\\fad(340,260)\\c%s}%s"
                  % (W // 2, cy + 24, W // 2, cy, pal.ass("navy"), nl(sc["title"]))))
    out.append(shape(L_ACCENT, t0 + 0.42, t1, pal.ass("amber"),
                     rrect(W // 2 - 64, cy + 58, 128, 7, 3.5), "\\fad(360,260)"))
    if sc.get("sub"):
        out.append(ev(L_TEXT, t0 + 0.50, t1, "Body",
                      "{\\an5\\pos(%d,%d)\\fad(360,260)\\c%s}%s"
                      % (W // 2, cy + 124, pal.ass("teal_ink"), nl(sc["sub"]))))


def scene_list(sc, pal, out):
    t0, t1 = sc["start"], sc["end"]
    head_y = sc.get("heading_y", 500)
    out.append(ev(L_TEXT, t0, t1, "H2",
                  "{\\an5\\move(%d,%d,%d,%d,0,300)\\fad(280,240)\\c%s}%s"
                  % (W // 2, head_y + 22, W // 2, head_y, pal.ass("navy"),
                     nl(sc["heading"]))))
    out.append(shape(L_ACCENT, t0 + 0.12, t1, pal.ass("amber"),
                     rrect(W // 2 - 56, head_y + 52, 112, 7, 3.5), "\\fad(300,240)"))

    numbered = bool(sc.get("numbered"))
    # Numbered rows carry a counter on the right, as on the clinic's own journey
    # poster, so they need the full width. A plain list has no counter, so it
    # reads better as a narrower pill with the label in the clinic's colour.
    pill_w = sc.get("pill_w", PILL_W if numbered else 580)
    pill_x = (W - pill_w) // 2
    top = sc.get("y", 620)

    for i, item in enumerate(sc["items"]):
        text, colour = (item if isinstance(item, list) else [item, "navy"])
        y = top + i * (PILL_H + PILL_GAP)
        cy = y + PILL_H // 2
        at = t0 + 0.30 + i * 0.30
        out += card(at, t1, pill_x, y, pill_w, PILL_H, PILL_R,
                    fade="\\fad(260,240)")

        if numbered:
            # Counter on the right: Arabic reads right to left, so that is
            # where the eye starts each row.
            dot_cx = pill_x + pill_w - 86
            out.append(shape(L_ACCENT, at, t1, pal.ass(colour),
                             circle(dot_cx, cy, 34), "\\fad(260,240)"))
            out.append(ev(L_TEXT, at, t1, "Dot",
                          "{\\an5\\pos(%d,%d)\\fad(260,240)}%d"
                          % (dot_cx, cy, i + 1)))
            text_cx = (pill_x + dot_cx - 34) // 2
            text_colour = pal.ass("navy")
        else:
            text_cx = W // 2
            text_colour = pal.ass(colour)

        out.append(ev(L_TEXT, at + 0.06, t1, "Pill",
                      "{\\an5\\move(%d,%d,%d,%d,0,260)\\fad(280,240)\\c%s}%s"
                      % (text_cx, cy + 14, text_cx, cy, text_colour, nl(text))))


def scene_cta(sc, pal, out):
    t0, t1 = sc["start"], sc["end"]
    y, h = sc.get("y", 620), sc.get("h", 700)
    out += card(t0, t1, CARD_X, y, CARD_W, h)

    out.append(ev(L_TEXT, t0 + 0.12, t1, "H1",
                  "{\\an5\\move(%d,%d,%d,%d,0,320)\\fad(300,260)\\c%s}%s"
                  % (W // 2, y + 168, W // 2, y + 144, pal.ass("navy"),
                     nl(sc["title"]))))
    if sc.get("sub"):
        out.append(ev(L_TEXT, t0 + 0.28, t1, "Body",
                      "{\\an5\\pos(%d,%d)\\fad(320,260)\\c%s}%s"
                      % (W // 2, y + 268, pal.ass("teal_ink"), nl(sc["sub"]))))

    # Phone bar, styled after the navy footer strip on the clinic's posters.
    bar_y = y + 340
    out.append(shape(L_ACCENT, t0 + 0.42, t1, pal.ass("navy"),
                     rrect(CARD_X + 70, bar_y, CARD_W - 140, 126, 40),
                     "\\fad(340,260)"))
    out.append(shape(L_TEXT, t0 + 0.42, t1, pal.ass("red"),
                     circle(CARD_X + CARD_W - 150, bar_y + 63, 30),
                     "\\fad(340,260)"))
    out.append(ev(L_TEXT, t0 + 0.42, t1, "Icon",
                  "{\\an5\\pos(%d,%d)\\fad(340,260)}\u260e"
                  % (CARD_X + CARD_W - 150, bar_y + 66)))
    out.append(ev(L_TEXT, t0 + 0.48, t1, "Phone",
                  "{\\an5\\pos(%d,%d)\\fad(340,260)}%s"
                  % (W // 2 - 26, bar_y + 65, sc["phone"])))
    if sc.get("address"):
        out.append(ev(L_TEXT, t0 + 0.60, t1, "Body",
                      "{\\an5\\pos(%d,%d)\\fad(360,260)\\fs38\\c%s}%s"
                      % (W // 2, bar_y + 206, pal.ass("navy"), nl(sc["address"]))))


SCENES = {"hook": scene_hook, "brand": scene_brand, "list": scene_list,
          "cta": scene_cta}


def stars(cfg, pal, duration, out):
    """Slow drifting confetti in the side margins, well clear of the cards."""
    spec = cfg.get("stars") or []
    if not spec:
        return
    rng = random.Random(11)
    for i in range(int(spec[0])):
        colour = pal.ass(spec[1:][i % len(spec[1:])] if len(spec) > 1 else "amber")
        left = i % 2 == 0
        x = rng.randint(44, 124) if left else rng.randint(W - 124, W - 44)
        # Keep clear of the progress bar and of Facebook's bottom UI strip.
        y0 = rng.randint(330, BAR_Y - 120)
        rise = rng.randint(90, 200)
        size = rng.randint(13, 23)
        t0 = rng.uniform(0.0, 2.5)
        out.append(ev(L_STAR, t0, duration, "Shape",
                      "{\\an7\\move(%d,%d,%d,%d,0,%d)\\alpha&H86&\\fad(900,600)"
                      "\\c%s\\p1}%s"
                      % (0, 0, 0, -rise, int((duration - t0) * 1000), colour,
                         star(x, y0, size))))


def progress(cfg, pal, duration, out):
    out.append(shape(L_BAR, 0.0, duration, ass_colour("#C9D7EC"),
                     rrect(BAR_X, BAR_Y, BAR_W, BAR_H, BAR_H / 2.0),
                     "\\alpha&H70&\\fad(500,300)"))
    out.append(ev(L_BAR, 0.0, duration, "Shape",
                  "{\\an7\\pos(%d,%d)\\c%s\\fscx0\\t(0,%d,\\fscx100)"
                  "\\fad(500,300)\\p1}%s"
                  % (BAR_X, BAR_Y, pal.ass("amber"), int(duration * 1000),
                     rrect(0, 0, BAR_W, BAR_H, BAR_H / 2.0))))


def duration_of(cfg):
    return max(float(s["end"]) for s in cfg["scenes"])


def build(cfg):
    pal = Palette(cfg["theme"]["palette"])
    total = duration_of(cfg)
    out = [HEADER_TMPL.format(w=W, h=H, font=cfg["theme"]["font"],
                              ink=pal.ass("navy"))]
    stars(cfg, pal, total, out)
    for sc in cfg["scenes"]:
        try:
            SCENES[sc["type"]](sc, pal, out)
        except KeyError:
            raise SystemExit("unknown scene type: %r (have: %s)"
                             % (sc.get("type"), ", ".join(sorted(SCENES))))
    progress(cfg, pal, total, out)
    return "".join(out)


if __name__ == "__main__":
    cfg = project_mod.load(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "--duration":
        print("%.2f" % duration_of(cfg))
        raise SystemExit(0)
    outdir = sys.argv[2]
    path = os.path.join(outdir, "cards.ass")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build(cfg))
    print("wrote cards.ass (%.2fs, %d scenes)"
          % (duration_of(cfg), len(cfg["scenes"])))
