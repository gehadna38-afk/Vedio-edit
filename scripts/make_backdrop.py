#!/usr/bin/env python3
"""Render the branded still backdrop a card reel is built on.

A card reel has no footage, so the background is drawn here: a near-white
gradient with soft out-of-focus blobs in the brand colours, echoing the corner
blobs on the clinic's own posters. It stays pale on purpose - every caption in
the reel sits on top of it, and anything busier would fight the text.

Usage: python3 make_backdrop.py PROJECT OUT.png
"""

import sys

from PIL import Image, ImageDraw, ImageFilter

import project as project_mod

W, H = 1080, 1920


def hexrgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def gradient(top, bottom):
    base = Image.new("RGB", (1, H))
    px = base.load()
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = tuple(int(round(a + (b - a) * t)) for a, b in zip(top, bottom))
    return base.resize((W, H), Image.BILINEAR)


def blobs(img, specs):
    """specs: (cx, cy, radius, #rrggbb, alpha 0-1) in frame coordinates."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for cx, cy, r, colour, alpha in specs:
        rgb = hexrgb(colour)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=rgb + (int(round(alpha * 255)),))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=90))
    img.paste(layer, (0, 0), layer)
    return img


def build(cfg):
    bd = cfg["backdrop"]
    img = gradient(hexrgb(bd["top"]), hexrgb(bd["bottom"])).convert("RGBA")
    img = blobs(img, [tuple(s) for s in bd["blobs"]])
    return img.convert("RGB")


if __name__ == "__main__":
    cfg = project_mod.load(sys.argv[1])
    out = sys.argv[2]
    build(cfg).save(out)
    print("wrote %s (%dx%d)" % (out, W, H))
