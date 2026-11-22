#!/usr/bin/env bash
# Usage: ELEVENLABS_API_KEY=... pipeline/make_reel.sh episodes/YYYY-MM-DD.json videos/YYYY-MM-DD.mp4
set -euo pipefail
EP="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
export EPISODE="$EP" WORK="${WORK:-/tmp/reelwork-$(basename "$EP" .json)}"
mkdir -p "$WORK" "$(dirname "$OUT")"
python3 "$HERE/render.py" "$WORK/raw.mp4"
ffmpeg -y -hide_banner -loglevel error -i "$WORK/raw.mp4" -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11 \
  -c:a aac -b:a 160k -ar 44100 -movflags +faststart "$WORK/final.mp4"
mv "$WORK/final.mp4" "$OUT"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
