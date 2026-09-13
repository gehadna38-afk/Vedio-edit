#!/usr/bin/env bash
# Build a publish-ready Facebook Reel that has no source footage.
#
#   ./scripts/build_card_reel.sh [PROJECT] [OUTPUT]
#
# Everything on screen is drawn: a branded backdrop, the logo, and the scenes
# from the project's `scenes` list burned in with libass. Use build_reel.sh
# instead when there is real footage to cut.
#
# Output: 1080x1920, 30fps, H.264 High + AAC, faststart, ~-14 LUFS.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="${1:-superni-speech}"
BUILD="$ROOT/build"

cfg() { python3 "$ROOT/scripts/project.py" "$PROJECT" get "$@"; }

OUT="${2:-$ROOT/$(cfg output)}"
FPS=$(cfg video.fps)
CRF=$(cfg video.crf)
PRESET=$(cfg video.preset)
LUFS=$(cfg video.loudness)

LOGO="$ROOT/$(cfg logo.file)"
LOGO_SW=$(cfg logo.small_w)
LOGO_SY=$(cfg logo.small_y)
LOGO_BW=$(cfg logo.big_w)
LOGO_BY=$(cfg logo.big_y)
LOGO_IN=$(cfg logo.big_from)
LOGO_OUT=$(cfg logo.big_to)

mkdir -p "$BUILD" "$(dirname "$OUT")"

if [ ! -f "$LOGO" ]; then
  echo "logo not found: $LOGO" >&2
  exit 1
fi

TOTAL=$(python3 "$ROOT/scripts/gen_cards.py" "$PROJECT" --duration)
MUSIC_DUR=$(python3 -c "print('%.2f' % ($TOTAL + 0.2))")
FADE_AT=$(python3 -c "print('%.2f' % ($TOTAL - 2.4))")
# The backdrop is rendered 10% oversize so it can drift slowly behind the cards;
# a dead-still background reads as a slideshow rather than a video.
PAN_TO=$(python3 -c "print(int(2112 - 1920))")
SMALL_OUT=$(python3 -c "print('%.2f' % ($LOGO_IN - 0.35))")

echo ">> project $PROJECT (card reel, ${TOTAL}s)"

echo ">> drawing backdrop"
python3 "$ROOT/scripts/make_backdrop.py" "$PROJECT" "$BUILD/backdrop.png"

echo ">> generating music"
python3 "$ROOT/scripts/make_music.py" "$PROJECT" "$BUILD/music.wav" "$MUSIC_DUR"

echo ">> generating scenes"
python3 "$ROOT/scripts/gen_cards.py" "$PROJECT" "$BUILD"

# Two-pass loudness: single-pass loudnorm only approximates the target, and
# undershoots on percussive material. Measure first, then apply linear gain.
echo ">> measuring loudness"
MEASURED=$(ffmpeg -hide_banner -nostats -i "$BUILD/music.wav" \
  -af "atrim=0:${TOTAL},loudnorm=I=${LUFS}:TP=-1.5:LRA=11:print_format=json" \
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
  LOUDNORM="loudnorm=I=${LUFS}:TP=-1.5:LRA=11:${MEASURED}"
  echo "   $MEASURED"
else
  echo "   measurement failed; falling back to single-pass"
  LOUDNORM="loudnorm=I=${LUFS}:TP=-1.5:LRA=11"
fi

echo ">> encoding reel"
ffmpeg -v warning -stats -y \
  -loop 1 -framerate $FPS -t "$TOTAL" -i "$BUILD/backdrop.png" \
  -loop 1 -framerate $FPS -t "$TOTAL" -i "$LOGO" \
  -i "$BUILD/music.wav" \
  -filter_complex "
    [0:v]scale=1188:2112:flags=lanczos,
         crop=1080:1920:x='(iw-1080)/2':y='${PAN_TO}*t/${TOTAL}',
         format=rgba[bg];
    [1:v]split=3[l1][l2][l3];
    [l1]scale=${LOGO_SW}:-1:flags=lanczos,format=rgba,
        fade=t=in:st=0:d=0.7:alpha=1,
        fade=t=out:st=${SMALL_OUT}:d=0.35:alpha=1[ls1];
    [l2]scale=${LOGO_SW}:-1:flags=lanczos,format=rgba,
        fade=t=in:st=${LOGO_OUT}:d=0.35:alpha=1[ls2];
    [l3]scale=${LOGO_BW}:-1:flags=lanczos,format=rgba,
        fade=t=in:st=${LOGO_IN}:d=0.5:alpha=1,
        fade=t=out:st=$(python3 -c "print('%.2f' % ($LOGO_OUT - 0.5))"):d=0.5:alpha=1[lb];
    [bg][ls1]overlay=x='(W-w)/2':y=${LOGO_SY}[s1];
    [s1][ls2]overlay=x='(W-w)/2':y=${LOGO_SY}[s2];
    [s2][lb]overlay=x='(W-w)/2':y='${LOGO_BY}-h/2+12*sin(2*PI*(t-${LOGO_IN})/5)':eval=frame[s3];
    [s3]ass=${BUILD}/cards.ass,format=yuv420p,setsar=1[v];
    [2:a]atrim=0:${TOTAL},asetpts=PTS-STARTPTS,
         ${LOUDNORM},
         afade=t=out:st=${FADE_AT}:d=2.4,
         aresample=44100[a]
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset "$PRESET" -crf "$CRF" -profile:v high -level:v 4.1 \
  -pix_fmt yuv420p -r $FPS -g 60 -keyint_min 30 -sc_threshold 0 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 192k -ar 44100 -ac 2 \
  -movflags +faststart \
  -t "$TOTAL" \
  "$OUT"

echo ">> done: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of default=nw=1 "$OUT"
