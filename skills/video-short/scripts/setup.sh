#!/bin/bash
# Check what Video Short needs and prepare it. Prints each missing tool with its install command and exits 1,
# so the agent can ask the user before installing. When everything is present, it installs numpy and fetches
# HyperFrames with its headless Chrome and the Parakeet speech model (about 1 GB in all), so nothing stalls later.
DIR="$(cd "$(dirname "$0")" && pwd)"
missing=0
need() { command -v "$1" >/dev/null || { echo "missing: $1  (Mac: brew install $2)"; missing=1; }; }
need ffmpeg ffmpeg
need yt-dlp yt-dlp
need python3 python
need node node
if command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 22 ]; then
  echo "too old: node $(node -v), needs 22 or newer  (Mac: brew upgrade node)"; missing=1
fi
[ "$missing" = 1 ] && exit 1
"$DIR/py" -c "import numpy" || exit 1
HF=hyperframes@0.8.169
LOG="$(mktemp)"
quiet() { "$@" >"$LOG" 2>&1 || { tail -c 1500 "$LOG"; return 1; }; }   # progress spinners stay out of the agent's context
quiet npx -y $HF browser ensure || { echo "HyperFrames could not download its Chrome"; exit 1; }
quiet npx -y $HF models install parakeet || { echo "HyperFrames could not download the Parakeet speech model"; exit 1; }
echo "ready: ffmpeg, yt-dlp, Python, Node $(node -v), HyperFrames with Chrome and Parakeet"
