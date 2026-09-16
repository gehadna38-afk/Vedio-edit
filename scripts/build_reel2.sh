#!/usr/bin/env bash
# Build the publish-ready Facebook Reel from the shape-board session footage.
#
#   ./scripts/build_reel2.sh [SOURCE] [OUTPUT]
#
# Unlike the first reel, this source carries the therapist's voice. The voice is
# the evidence for the auditory-discrimination goal, so it is kept, cleaned, and
# the music is side-chained to duck underneath it.
#
# Output: 1080x1920, 30fps, H.264 High + AAC, faststart, ~-14 LUFS.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/build/source2.mov}"
OUT="${2:-$ROOT/output/reel2_facebook.mp4}"
BUILD="$ROOT/build"

SPEED=1.3          # atempo keeps the voice at its original pitch
OUTRO=5.0
XFADE=0.6
FPS=30
SR=48000

mkdir -p "$BUILD" "$(dirname "$OUT")"

SRC_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
MAIN_DUR=$(python3 -c "print('%.4f' % ($SRC_DUR / $SPEED))")
TOTAL=$(python3 -c "print('%.4f' % ($MAIN_DUR + $OUTRO - $XFADE))")
XFADE_AT=$(python3 -c "print('%.4f' % ($MAIN_DUR - $XFADE))")
MUSIC_DUR=$(python3 -c "print('%.2f' % ($TOTAL + 0.3))")
FADE_AT=$(python3 -c "print('%.2f' % ($TOTAL - 2.2))")

echo ">> source ${SRC_DUR}s -> main ${MAIN_DUR}s + outro ${OUTRO}s = ${TOTAL}s"

echo ">> generating music"
python3 "$ROOT/scripts/make_music.py" "$BUILD/music2.wav" "$MUSIC_DUR"

echo ">> generating captions"
python3 "$ROOT/scripts/gen_subs2.py" "$MAIN_DUR" "$OUTRO" "$BUILD"

# The voice is recorded in a hard room and clips at 0 dBFS, so it needs a
# high-pass for rumble, gentle broadband denoise, and a limiter before it can
# sit under music. apad carries silence across the end card.
echo ">> mixing audio (voice + ducked music)"
ffmpeg -v error -y -i "$SRC" -i "$BUILD/music2.wav" -filter_complex "
  [0:a]atempo=${SPEED},aresample=${SR},
       highpass=f=85,
       afftdn=nr=12:nf=-30,
       acompressor=threshold=0.089:ratio=3:attack=20:release=250:makeup=1.8,
       alimiter=limit=0.88:level=false,
       apad=whole_dur=${TOTAL},atrim=0:${TOTAL},asetpts=PTS-STARTPTS,
       asplit=2[vmix][vkey];
  [1:a]aresample=${SR},atrim=0:${TOTAL},asetpts=PTS-STARTPTS,volume=0.34[m0];
  [m0][vkey]sidechaincompress=threshold=0.035:ratio=7:attack=12:release=380[mduck];
  [vmix][mduck]amix=inputs=2:normalize=0,
       alimiter=limit=0.90:level=false,
       afade=t=out:st=${FADE_AT}:d=2.2[a]
" -map "[a]" -c:a pcm_s16le "$BUILD/mix2.wav"

echo ">> measuring loudness"
MEASURED=$(ffmpeg -hide_banner -nostats -i "$BUILD/mix2.wav" \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" \
  -f null - 2>&1 | python3 -c '
import json, re, sys
m = re.search(r"\{[^{}]*input_i[^{}]*\}", sys.stdin.read(), re.S)
if not m:
    sys.exit(1)
d = json.loads(m.group(0))
print("measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s"
      ":offset=%s" % (d["input_i"], d["input_tp"], d["input_lra"],
                                  d["input_thresh"], d["target_offset"]))
' || echo "")

if [ -n "$MEASURED" ]; then
  LOUDNORM="loudnorm=I=-14:TP=-1.5:LRA=11:${MEASURED}"
  echo "   $MEASURED"
else
  echo "   measurement failed; falling back to single-pass"
  LOUDNORM="loudnorm=I=-14:TP=-1.5:LRA=11"
fi

GRADE="eq=contrast=1.09:saturation=1.20:brightness=0.02:gamma=1.03"

echo ">> capturing closing frame"
ffmpeg -v error -y -sseof -0.4 -i "$SRC" \
  -vf "scale=1080:1920:flags=lanczos,${GRADE}" \
  -frames:v 1 "$BUILD/lastframe2.png"

# zoompan sits before the ass filter so the slow push-in moves the footage
# without dragging the captions with it.
echo ">> encoding reel"
ffmpeg -v warning -stats -y \
  -i "$SRC" \
  -loop 1 -framerate $FPS -t "$OUTRO" -i "$BUILD/lastframe2.png" \
  -i "$BUILD/mix2.wav" \
  -filter_complex "
    [0:v]setpts=PTS/${SPEED},fps=${FPS},
         hqdn3d=1.5:1.2:6:6,
         scale=1080:1920:flags=lanczos,
         ${GRADE},
         unsharp=5:5:0.70:5:5:0.0,
         zoompan=z='min(1.0+0.00035*on,1.07)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=${FPS},
         vignette=PI/5,
         ass=${BUILD}/main2.ass,
         format=yuv420p,setsar=1[v0];
    [1:v]scale=1080:1920,gblur=sigma=22,
         eq=brightness=-0.22:saturation=0.80:contrast=1.02,
         zoompan=z='min(1.0+0.0007*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=${FPS},
         ass=${BUILD}/outro2.ass,
         format=yuv420p,setsar=1[v1];
    [v0][v1]xfade=transition=fade:duration=${XFADE}:offset=${XFADE_AT}[v];
    [2:a]${LOUDNORM},alimiter=limit=0.79:level=false,aresample=${SR}[a]
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset slower -crf 22 -profile:v high -level:v 4.1 \
  -pix_fmt yuv420p -r $FPS -g 60 -keyint_min 30 -sc_threshold 0 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 192k -ar $SR -ac 2 \
  -movflags +faststart \
  -t "$TOTAL" \
  "$OUT"

echo ">> done: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of default=nw=1 "$OUT"
