#!/usr/bin/env bash
# Build the publish-ready Facebook Reel from the shape-sorter session footage.
#
#   ./scripts/build_reel3.sh [SOURCE] [OUTPUT]
#
# This source is landscape (848x478) and 127s long, and carries no audio track
# at all. So: three representative segments are picked out rather than played
# end to end, the footage is letterboxed into a band with a blurred fill behind
# it, and the reel ships silent. A silent audio stream is muxed in anyway, since
# a file with no audio stream at all trips up some players.
#
# Output: 1080x1920, 30fps, H.264 High + silent AAC, faststart.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/build/source3.mov}"
OUT="${2:-$ROOT/output/reel3_facebook.mp4}"
BUILD="$ROOT/build"

# The activity repeats, so a representative selection loses no story and keeps
# the reel inside a length people will actually watch.
SEG1_IN=2;   SEG1_OUT=32
SEG2_IN=56;  SEG2_OUT=82
SEG3_IN=104; SEG3_OUT=127.1

SPEED=1.5
OUTRO=4.5
XFADE=0.6
FPS=30
SR=48000

# Footage band; must stay in step with VIDEO_TOP/VIDEO_H in gen_subs3.py.
VIDEO_TOP=560

mkdir -p "$BUILD" "$(dirname "$OUT")"

KEPT=$(python3 -c "print('%.4f' % (($SEG1_OUT-$SEG1_IN)+($SEG2_OUT-$SEG2_IN)+($SEG3_OUT-$SEG3_IN)))")
MAIN_DUR=$(python3 -c "print('%.4f' % ($KEPT / $SPEED))")
TOTAL=$(python3 -c "print('%.4f' % ($MAIN_DUR + $OUTRO - $XFADE))")
XFADE_AT=$(python3 -c "print('%.4f' % ($MAIN_DUR - $XFADE))")

echo ">> kept ${KEPT}s of source -> main ${MAIN_DUR}s + outro ${OUTRO}s = ${TOTAL}s"

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
    [0:v]trim=${SEG1_IN}:${SEG1_OUT},setpts=PTS-STARTPTS[s1];
    [0:v]trim=${SEG2_IN}:${SEG2_OUT},setpts=PTS-STARTPTS[s2];
    [0:v]trim=${SEG3_IN}:${SEG3_OUT},setpts=PTS-STARTPTS[s3];
    [s1][s2][s3]concat=n=3:v=1:a=0,
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
