#!/usr/bin/env bash
# Build the publish-ready Facebook Reel from the shape-sorter session footage.
#
#   ./scripts/build_reel3.sh [SOURCE] [OUTPUT]
#
# This source is landscape (848x478) and 127s long, and carries no audio track
# at all. So: only the stretches where the child is placing a shape are kept,
# the footage is letterboxed into a band with a blurred fill behind it, and the
# reel ships silent. A silent audio stream is muxed in anyway, since a file with
# no audio stream at all trips up some players.
#
# Output: 1080x1920, 30fps, H.264 High + silent AAC, faststart.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/build/source3.mov}"
OUT="${2:-$ROOT/output/reel3_facebook.mp4}"
BUILD="$ROOT/build"

# Segments where the CHILD is placing a shape, as start:end in source seconds.
# The stretches in between are the therapist explaining or handing him a piece,
# which is not what the reel is selling.
SEGMENTS=(
  "4.0:8.5"       # pushes the yellow block into the top
  "10.0:14.5"     # presses the next piece home
  "36.0:44.5"     # the long run: orange in, hand into the side opening
  "46.0:50.5"     # keeps going on the top face
  "85.0:89.5"     # yellow seated, then the filled face
  "92.5:95.5"     # both hands working the top
  "110.5:116.5"   # blue block into the side, then the result
)

SPEED=1.1
OUTRO=4.5
XFADE=0.6
FPS=30
SR=48000

# Footage band; must stay in step with VIDEO_TOP/VIDEO_H in gen_subs3.py.
VIDEO_TOP=560

mkdir -p "$BUILD" "$(dirname "$OUT")"

TRIMS=""
CONCAT_IN=""
KEPT=0
i=0
for seg in "${SEGMENTS[@]}"; do
  seg_in="${seg%%:*}"
  seg_out="${seg##*:}"
  TRIMS+="[0:v]trim=${seg_in}:${seg_out},setpts=PTS-STARTPTS[s${i}];"
  CONCAT_IN+="[s${i}]"
  KEPT=$(python3 -c "print('%.4f' % ($KEPT + $seg_out - $seg_in))")
  i=$((i + 1))
done
NSEG=$i

MAIN_DUR=$(python3 -c "print('%.4f' % ($KEPT / $SPEED))")
TOTAL=$(python3 -c "print('%.4f' % ($MAIN_DUR + $OUTRO - $XFADE))")
XFADE_AT=$(python3 -c "print('%.4f' % ($MAIN_DUR - $XFADE))")

echo ">> kept ${KEPT}s across ${NSEG} segments -> main ${MAIN_DUR}s + outro ${OUTRO}s = ${TOTAL}s"

echo ">> generating captions"
python3 "$ROOT/scripts/gen_subs3.py" "$MAIN_DUR" "$OUTRO" "$BUILD"

GRADE="eq=contrast=1.08:saturation=1.18:brightness=0.02:gamma=1.03"

echo ">> capturing closing frame"
ffmpeg -v error -y -sseof -0.4 -i "$SRC" \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,${GRADE}" \
  -frames:v 1 "$BUILD/lastframe3.png"

echo ">> encoding reel"
ffmpeg -v warning -stats -y \
  -i "$SRC" \
  -loop 1 -framerate $FPS -t "$OUTRO" -i "$BUILD/lastframe3.png" \
  -f lavfi -t "$TOTAL" -i "anullsrc=channel_layout=stereo:sample_rate=${SR}" \
  -filter_complex "
    ${TRIMS}
    ${CONCAT_IN}concat=n=${NSEG}:v=1:a=0,
         setpts=PTS/${SPEED},fps=${FPS},
         hqdn3d=1.4:1.1:6:6,
         split=2[fg][bg];
    [bg]scale=1080:1920:force_original_aspect_ratio=increase,
        crop=1080:1920,
        gblur=sigma=34,
        eq=brightness=-0.18:saturation=0.62:contrast=0.98[bgblur];
    [fg]scale=1080:-2:flags=lanczos,
        ${GRADE},
        unsharp=5:5:0.65:5:5:0.0[fgs];
    [bgblur][fgs]overlay=(W-w)/2:${VIDEO_TOP}:shortest=1,
        ass=${BUILD}/main3.ass,
        format=yuv420p,setsar=1[v0];
    [1:v]scale=1080:1920,gblur=sigma=24,
         eq=brightness=-0.24:saturation=0.78:contrast=1.02,
         zoompan=z='min(1.0+0.0007*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=${FPS},
         ass=${BUILD}/outro3.ass,
         format=yuv420p,setsar=1[v1];
    [v0][v1]xfade=transition=fade:duration=${XFADE}:offset=${XFADE_AT}[v]
  " \
  -map "[v]" -map 2:a \
  -c:v libx264 -preset slower -crf 22 -profile:v high -level:v 4.1 \
  -pix_fmt yuv420p -r $FPS -g 60 -keyint_min 30 -sc_threshold 0 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 96k -ar $SR -ac 2 \
  -movflags +faststart \
  -t "$TOTAL" \
  "$OUT"

echo ">> done: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of default=nw=1 "$OUT"
