#!/usr/bin/env bash
# Build the publish-ready Facebook Reel from the raw session footage.
#
#   ./scripts/build_reel.sh [SOURCE] [OUTPUT]
#
# Output: 1080x1920, 30fps, H.264 High + AAC, faststart, ~-14 LUFS.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/build/source.mov}"
OUT="${2:-$ROOT/output/reel_facebook.mp4}"
BUILD="$ROOT/build"

# Gentle speed-up: tightens the pacing for a feed without reading as sped up.
SPEED=1.15
OUTRO=5.0
XFADE=0.6
FPS=30

mkdir -p "$BUILD" "$(dirname "$OUT")"

SRC_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
MAIN_DUR=$(python3 -c "print('%.4f' % ($SRC_DUR / $SPEED))")
TOTAL=$(python3 -c "print('%.4f' % ($MAIN_DUR + $OUTRO - $XFADE))")
XFADE_AT=$(python3 -c "print('%.4f' % ($MAIN_DUR - $XFADE))")
MUSIC_DUR=$(python3 -c "print('%.2f' % ($TOTAL + 0.2))")
FADE_AT=$(python3 -c "print('%.2f' % ($TOTAL - 2.2))")

echo ">> source ${SRC_DUR}s -> main ${MAIN_DUR}s + outro ${OUTRO}s = ${TOTAL}s"

echo ">> generating music"
python3 "$ROOT/scripts/make_music.py" "$BUILD/music.wav" "$MUSIC_DUR"

echo ">> generating captions"
python3 "$ROOT/scripts/gen_subs.py" "$MAIN_DUR" "$OUTRO" "$BUILD"

# Grade applied to the footage. The source is a dim indoor 576x1024 phone clip
# upscaled 1.875x, so it needs a little contrast, saturation and sharpening.
GRADE="eq=contrast=1.08:saturation=1.18:brightness=0.02:gamma=1.02"

# Two-pass loudness: single-pass loudnorm only approximates the target, and
# undershoots on percussive material. Measure first, then apply linear gain.
echo ">> measuring loudness"
MEASURED=$(ffmpeg -hide_banner -nostats -i "$BUILD/music.wav" \
  -af "atrim=0:${TOTAL},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" \
  -f null - 2>&1 | python3 -c '
import json, re, sys
m = re.search(r"\{[^{}]*input_i[^{}]*\}", sys.stdin.read(), re.S)
if not m:
    sys.exit(1)
d = json.loads(m.group(0))
print("measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s"
      ":offset=%s:linear=true" % (d["input_i"], d["input_tp"], d["input_lra"],
                                  d["input_thresh"], d["target_offset"]))
' || echo "")

if [ -n "$MEASURED" ]; then
  LOUDNORM="loudnorm=I=-14:TP=-1.5:LRA=11:${MEASURED}"
  echo "   $MEASURED"
else
  echo "   measurement failed; falling back to single-pass"
  LOUDNORM="loudnorm=I=-14:TP=-1.5:LRA=11"
fi

echo ">> capturing closing frame"
ffmpeg -v error -y -sseof -0.4 -i "$SRC" \
  -vf "scale=1080:1920:flags=lanczos,${GRADE}" \
  -frames:v 1 "$BUILD/lastframe.png"

echo ">> encoding reel"
ffmpeg -v warning -stats -y \
  -i "$SRC" \
  -loop 1 -framerate $FPS -t "$OUTRO" -i "$BUILD/lastframe.png" \
  -i "$BUILD/music.wav" \
  -filter_complex "
    [0:v]setpts=PTS/${SPEED},fps=${FPS},
         hqdn3d=1.2:1.0:5:5,
         scale=1080:1920:flags=lanczos,
         ${GRADE},
         unsharp=5:5:0.55:5:5:0.0,
         vignette=PI/5,
         ass=${BUILD}/main.ass,
         format=yuv420p,setsar=1[v0];
    [1:v]scale=1080:1920,gblur=sigma=22,
         eq=brightness=-0.20:saturation=0.82:contrast=1.02,
         zoompan=z='min(1.0+0.0007*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=${FPS},
         ass=${BUILD}/outro.ass,
         format=yuv420p,setsar=1[v1];
    [v0][v1]xfade=transition=fade:duration=${XFADE}:offset=${XFADE_AT}[v];
    [2:a]atrim=0:${TOTAL},asetpts=PTS-STARTPTS,
         ${LOUDNORM},
         afade=t=out:st=${FADE_AT}:d=2.2,
         aresample=44100[a]
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset slower -crf 17 -profile:v high -level:v 4.1 \
  -pix_fmt yuv420p -r $FPS -g 60 -keyint_min 30 -sc_threshold 0 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 192k -ar 44100 -ac 2 \
  -movflags +faststart \
  -t "$TOTAL" \
  "$OUT"

echo ">> done: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of default=nw=1 "$OUT"
