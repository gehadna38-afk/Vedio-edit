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
num() { python3 -c "print('%.2f' % ($1))"; }

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
LOGO_EARLY=$(cfg logo.small_before_brand --default true)

VEIL_UNTIL=$(cfg video.veil.until --default 0)
VEIL_COLOUR=$(cfg video.veil.colour --default "#7E8A9E")
VEIL_ALPHA=$(cfg video.veil.alpha --default 0.30)
VEIL_FADE=$(cfg video.veil.fade --default 1.2)

VOICE_REL=$(cfg voiceover.file --default "")
VOICE=""
[ -n "$VOICE_REL" ] && [ -f "$ROOT/$VOICE_REL" ] && VOICE="$ROOT/$VOICE_REL"

mkdir -p "$BUILD" "$(dirname "$OUT")"

if [ ! -f "$LOGO" ]; then
  echo "logo not found: $LOGO" >&2
  exit 1
fi

TOTAL=$(python3 "$ROOT/scripts/gen_cards.py" "$PROJECT" --duration)
MUSIC_DUR=$(num "$TOTAL + 0.2")
FADE_AT=$(num "$TOTAL - 2.4")
# The backdrop is rendered 10% oversize so it can drift slowly behind the cards;
# a dead-still background reads as a slideshow rather than a video.
PAN_TO=192

echo ">> project $PROJECT (card reel, ${TOTAL}s)"

echo ">> drawing backdrop"
python3 "$ROOT/scripts/make_backdrop.py" "$PROJECT" "$BUILD/backdrop.png"

echo ">> generating music"
python3 "$ROOT/scripts/make_music.py" "$PROJECT" "$BUILD/music.wav" "$MUSIC_DUR"

echo ">> generating scenes"
python3 "$ROOT/scripts/gen_cards.py" "$PROJECT" "$BUILD"

# ---------------------------------------------------------------------------
# Audio bed. With a voice-over the music has to get out of the way, so it is
# ducked by the voice through a sidechain compressor and the two are mixed down
# to one track before the loudness pass - measuring the music alone would leave
# the finished mix off target.
# ---------------------------------------------------------------------------
BED="$BUILD/music.wav"
if [ -n "$VOICE" ]; then
  VOICE_GAIN=$(cfg voiceover.gain --default 1.0)
  MUSIC_UNDER=$(cfg voiceover.music_gain --default 0.70)
  echo ">> mixing voice-over (music ducked under it)"
  ffmpeg -v error -y -i "$BUILD/music.wav" -i "$VOICE" \
    -filter_complex "
      [0:a]aresample=44100,atrim=0:${TOTAL},asetpts=PTS-STARTPTS,
           volume=${MUSIC_UNDER}[mus];
      [1:a]aresample=44100,aformat=channel_layouts=stereo,
           volume=${VOICE_GAIN},
           loudnorm=I=-16:TP=-2:LRA=9,
           apad,atrim=0:${TOTAL},asetpts=PTS-STARTPTS[vo];
      [vo]asplit=2[vo_out][vo_key];
      [mus][vo_key]sidechaincompress=threshold=0.05:ratio=5:attack=20:release=350[duck];
      [duck][vo_out]amix=inputs=2:duration=first:normalize=0[mix]
    " -map "[mix]" -c:a pcm_s16le "$BUILD/bed.wav"
  BED="$BUILD/bed.wav"
fi

# Two-pass loudness: single-pass loudnorm only approximates the target, and
# undershoots on percussive material. Measure first, then apply linear gain.
echo ">> measuring loudness"
MEASURED=$(ffmpeg -hide_banner -nostats -i "$BED" \
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

# ---------------------------------------------------------------------------
# Video graph. The veil is a cool wash over the backdrop that lifts at the turn
# of the story, so the opening reads grey and the resolution reads bright. It
# sits under the logo and the text, which stay in full brand colour throughout.
# ---------------------------------------------------------------------------
if python3 -c "import sys; sys.exit(0 if float('$VEIL_UNTIL') > 0 else 1)"; then
  VEIL_SRC="color=c=${VEIL_COLOUR/#\#/0x}:s=1080x1920:r=${FPS}:d=${TOTAL},format=rgba,
            colorchannelmixer=aa=${VEIL_ALPHA},
            fade=t=out:st=${VEIL_UNTIL}:d=${VEIL_FADE}:alpha=1[veil];"
  VEIL_APPLY="[bg0][veil]overlay=shortest=1[bg];"
else
  VEIL_SRC=""
  VEIL_APPLY="[bg0]null[bg];"
fi

# fade=t=in leaves every frame before its start fully transparent, so a single
# stream cannot fade out and back in later - the second fade-in would erase the
# first stint. The small logo therefore rides one stream per stint.
if [ "$LOGO_EARLY" = "True" ] || [ "$LOGO_EARLY" = "true" ]; then
  SMALL_OUT=$(num "$LOGO_IN - 0.35")
  EARLY_SRC="[l1]scale=${LOGO_SW}:-1:flags=lanczos,format=rgba,
             fade=t=in:st=0:d=0.7:alpha=1,
             fade=t=out:st=${SMALL_OUT}:d=0.35:alpha=1[ls1];"
  EARLY_APPLY="[bg][ls1]overlay=x='(W-w)/2':y=${LOGO_SY}[s1];"
else
  EARLY_SRC="[l1]nullsink;"
  EARLY_APPLY="[bg]null[s1];"
fi

echo ">> encoding reel"
ffmpeg -v warning -stats -y \
  -loop 1 -framerate $FPS -t "$TOTAL" -i "$BUILD/backdrop.png" \
  -loop 1 -framerate $FPS -t "$TOTAL" -i "$LOGO" \
  -i "$BED" \
  -filter_complex "
    ${VEIL_SRC}
    [0:v]scale=1188:2112:flags=lanczos,
         crop=1080:1920:x='(iw-1080)/2':y='${PAN_TO}*t/${TOTAL}',
         format=rgba[bg0];
    ${VEIL_APPLY}
    [1:v]split=3[l1][l2][l3];
    ${EARLY_SRC}
    [l2]scale=${LOGO_SW}:-1:flags=lanczos,format=rgba,
        fade=t=in:st=${LOGO_OUT}:d=0.35:alpha=1[ls2];
    [l3]scale=${LOGO_BW}:-1:flags=lanczos,format=rgba,
        fade=t=in:st=${LOGO_IN}:d=0.5:alpha=1,
        fade=t=out:st=$(num "$LOGO_OUT - 0.5"):d=0.5:alpha=1[lb];
    ${EARLY_APPLY}
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
