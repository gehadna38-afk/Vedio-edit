#!/usr/bin/env python3
"""Shared ASS subtitle primitives: timestamps, drawings and event lines.

Both reel builders burn their text in with libass, which is built here against
HarfBuzz and FriBidi, so Arabic is shaped and bidi-reordered from plain logical
order. One rule applies to every style either builder writes: keep `Spacing` at
0. A non-zero value makes libass position glyphs individually, which silently
disables shaping and bidi and renders Arabic backwards in disconnected forms.
"""

import math


def ts(seconds):
    """Seconds -> ASS timestamp H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return "%d:%02d:%02d.%02d" % (h, m, s, cs)


def f(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


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


def circle(cx, cy, r):
    """Circle as an ASS drawing path, via four Bezier quadrants."""
    k = r * 0.5523
    return (
        "m {l} {cy} b {l} {cyk} {cxk} {t} {cx} {t} "
        "b {cxk2} {t} {rt} {cyk} {rt} {cy} "
        "b {rt} {cyk2} {cxk2} {b} {cx} {b} "
        "b {cxk} {b} {l} {cyk2} {l} {cy}"
    ).format(l=f(cx - r), rt=f(cx + r), t=f(cy - r), b=f(cy + r),
             cx=f(cx), cy=f(cy), cxk=f(cx - k), cxk2=f(cx + k),
             cyk=f(cy - k), cyk2=f(cy + k))


def star(cx, cy, r, points=5, inner=0.45):
    """Five-pointed star as an ASS drawing path, first point straight up."""
    pts = []
    for i in range(points * 2):
        rad = r if i % 2 == 0 else r * inner
        a = -math.pi / 2 + i * math.pi / points
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    head = "m %s %s" % (f(pts[0][0]), f(pts[0][1]))
    tail = " ".join("l %s %s" % (f(x), f(y)) for x, y in pts[1:])
    return head + " " + tail


def ev(layer, start, end, style, text):
    return "Dialogue: %d,%s,%s,%s,,0,0,0,,%s\n" % (
        layer, ts(start), ts(end), style, text)


def shape(layer, start, end, colour, path, extra="", style="Shape"):
    return ev(layer, start, end, style,
              "{\\an7\\pos(0,0)\\c%s%s\\p1}%s" % (colour, extra, path))


def ass_colour(value):
    """#RRGGBB (or an existing &H.. literal) -> ASS &HAABBGGRR, opaque."""
    if value.startswith("&H"):
        return value
    s = value.lstrip("#")
    r, g, b = (int(s[i:i + 2], 16) for i in (0, 2, 4))
    return "&H00%02X%02X%02X" % (b, g, r)
