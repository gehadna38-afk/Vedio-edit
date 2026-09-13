#!/usr/bin/env python3
"""Load a reel project definition.

A project is one JSON file under projects/ holding everything that differs
between reels: the footage path, the on-screen text, the colours, the pacing
and grade, the music mood, and the Facebook post copy. The build scripts hold
only the parts that are the same for every reel.

Usage as a CLI (used by build_reel.sh to read single values in shell):

    python3 project.py PROJECT get video.speed
    python3 project.py PROJECT get output --default out.mp4
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "source": "build/source.mov",
    "output": "output/reel.mp4",
    "video": {
        "speed": 1.15,
        "outro": 5.0,
        "xfade": 0.6,
        "fps": 30,
        "grade": "eq=contrast=1.08:saturation=1.18:brightness=0.02:gamma=1.02",
        "denoise": "hqdn3d=1.2:1.0:5:5",
        "unsharp": "unsharp=5:5:0.55:5:5:0.0",
        "vignette": "vignette=PI/5",
        "crf": 17,
        "preset": "slower",
        "loudness": -14,
    },
    "theme": {
        "font": "Lemonada",
        "white": "&H00FFFFFF",
        "accent": "&H0055C8F7",
        "outline": "&H00241A12",
        "plate_fill": "&H4A1D1712",
        "title_fill": "&H3A1D1712",
        "bar_track": "&H8AFFFFFF",
    },
    "title": {"main": "", "sub": "", "start": 0.25, "end": 4.75},
    "captions": [],
    "outro": {"lines": [], "cta": ""},
    "music": {"mood": "kids", "bpm": 104, "transpose": 0},
    "post": {"caption": "", "alt": ""},
}


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def resolve(name):
    """Project name, bare filename or path -> path to the JSON file."""
    if os.path.sep in name or name.endswith(".json"):
        cand = name if os.path.isabs(name) else os.path.join(ROOT, name)
        if os.path.exists(cand):
            return cand
    cand = os.path.join(ROOT, "projects", name + ".json")
    if os.path.exists(cand):
        return cand
    raise SystemExit("no such project: %s (looked in %s/projects)" % (name, ROOT))


def load(name):
    with open(resolve(name), encoding="utf-8") as fh:
        return _merge(DEFAULTS, json.load(fh))


def get(cfg, path, default=None):
    """Read a dotted key, e.g. get(cfg, 'video.speed')."""
    cur = cfg
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] != "get":
        raise SystemExit(__doc__)
    cfg = load(sys.argv[1])
    default = None
    args = sys.argv[3:]
    if "--default" in args:
        i = args.index("--default")
        default = args[i + 1]
        args = args[:i]
    value = get(cfg, args[0], default)
    if value is None:
        raise SystemExit("project has no key: %s" % args[0])
    print(value)
