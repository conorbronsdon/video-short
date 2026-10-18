# Video Short reference

Set `S` to this skill's `scripts` folder and `P` to the project folder. Run every script through `$S/py`, which creates a venv at `~/.cache/video-short/venv` on first run and installs numpy, Pillow, and onnx-asr. The first transcription downloads the Parakeet model (about 600 MB) from Hugging Face.

```bash
S=/path/to/video-short/scripts
P=~/Videos/my-short
mkdir -p "$P/broll"
```

## Commands

```bash
# 1. Transcribe the raw recording -> work/transcript_raw.md and .json
$S/py $S/transcribe.py "$P/raw.mp4" "$P/work/transcript_raw"

# Framing stills with a 0.1 grid, and a side-by-side grade preview
$S/py $S/frames.py "$P/raw.mp4" "$P/work/frames" --count 3
$S/py $S/frames.py "$P/raw.mp4" "$P/work/frames" --times 12 --grade "eq=contrast=1.06:saturation=1.1"

# Apply Cuts and Grade -> work/clean.mp4, work/transcript_clean.md and .json
$S/py $S/cut.py "$P"

# 3. Draft, then review: run review.py in the background and wait for it to print the notes
$S/py $S/render.py "$P" --draft
$S/py $S/review.py "$P"            # later rounds: --no-open, the open page reloads itself

# Optional: scrub the timeline in HyperFrames Studio
$S/py $S/build.py "$P"
npx -y hyperframes@0.8.169 preview "$P/hf"

# 4. Render the final, then check it
$S/py $S/render.py "$P"
$S/py $S/qa.py "$P"
```

`render.py --draft` renders faster at lower quality. `review.py` reviews the newest render unless you pass a video, saves the notes to `work/feedback.md`, and uses port 8791 (or any free port). All scripts accept `--style FILE` where relevant. A 45-second Short renders in about 1.5 minutes on an M-series Mac.

Optional music (needs `GEMINI_API_KEY`, free at https://aistudio.google.com/apikey). Lyria streams in real time, so 40 seconds takes about 40 seconds:

```bash
$S/py $S/music.py "$P/music.wav" --seconds 45 --bpm 90 \
  --prompt "warm lo-fi jazz, Rhodes piano, upright bass, soft brushed drums"
```

## edit.md

Settings come first, then sections. Times are seconds. Cuts use raw-recording time; scenes use the cut (clean) timeline.

```markdown
# edit.md: gemini-short

Source: raw.mp4
Grade: eq=contrast=1.06:saturation=1.1:brightness=0.01
Framing: 0.47, 0.36
Music: music.wav
Music level: -18
Sound effects: off

## Cuts
- 3.40-11.20  (lead-in silence removed)
- 12.05-42.80  (dropped the false start at 11.2)

## Scenes
| id  | start | end   | layout | visual                                       | note                    |
|-----|-------|-------|--------|----------------------------------------------|-------------------------|
| s01 | 0.00  | 3.80  | a-roll |                                              | hook                    |
| s02 | 3.80  | 5.30  | split  | broll/3d_castle.mp4 @0.5                     | on "3D models"          |
| s03 | 5.30  | 6.80  | b-roll | broll/benchmarks.mp4 fit                     | source: blog.google     |
| s04 | 6.80  | 11.00 | punch  |                                              | the turn                |
| s05 | 11.00 | 13.90 | split  | card: Gemini did the edit ; Image            | one row per spoken item |
| s06 | 13.90 | 16.00 | split  | card: Gemini did the edit ; Image ; Video    | only the new row animates |
| s07 | 16.00 | 19.50 | split  | number: 3 ; prompts from raw cut to Short    | counts up               |
| s08 | 19.50 | 23.00 | b-roll | graphic: broll/flow.html                     | your own motion graphic |

## Caption fixes
- Anti Gravity -> Antigravity

## Emphasis
- Gemini 4
```

- `Source`: the raw recording, relative to the project or absolute.
- `Grade`: any ffmpeg video filter chain, or `none`. Leave it out to use the style's `grade`. Useful pieces: `eq=contrast=:saturation=:brightness=:gamma=`, `colortemperature=temperature=5600`, `lut3d=file.cube`.
- `Framing`: face center as fractions of the source frame width and height.
- `Sound effects`: `off` (default) or `subtle`: quiet taps when a card, row, or number enters and a soft whoosh on B-roll cuts, synthesized locally.
- `Music`: an audio file or `none`. `Music level`: dB relative to the voice (default -18). The mix normalizes to -14 LUFS with a -1.5 dBTP soft ceiling.
- Scenes must be contiguous: each start equals the previous end, the first starts at 0, and the last ends at the clean video's end.
- `visual` for a clip: `path [@start] [fit|fill]`. `@start` is the second in the clip to begin from. `fill` crops to cover the panel; `fit` shows the whole clip over a blurred copy. The default picks `fill` when the shapes are close and `fit` otherwise. Clips shorter than their scene loop.
- `visual` for a card: `card: Title ; row ; row`. Separate parts with `;`, because `|` ends a table cell. Rows slide in one by one. When the next scene repeats the same title and rows, only its new rows animate, so a list builds across scenes.
- `visual` for a number: `number: 3x ; label`. The number counts up from zero, keeping any prefix or suffix such as `$`, `%`, or `x`, and the label fades in below.
- `visual` for a graphic: `graphic: path.html`, a HyperFrames sub-composition you write. See below.
- `split` and `b-roll` need a visual. `a-roll` and `punch` leave it empty.
- `## Caption fixes` rows replace words in captions only, matching whole words without case.
- `## Emphasis` rows are phrases that get a solid box behind them in the caption (the style's `caption.emphasis` color), matching whole words without case. A style without `emphasis` ignores them.

The parser stops with the line number on any malformed row.

## Graphics

A `graphic:` file is a self-contained HyperFrames sub-composition: inline CSS and SVG, no external files. Size it to the panel it fills, 1080x880 for `split` or 1080x1920 for `b-roll`, and give it the scene's duration. Register its GSAP timeline under its composition id. The style's fonts are loaded as `Ftitle`, `Fbody`, `Fnum`, and `Fcap`, and its colors are in `style.json`. The build copies it into the project, and Studio shows it on its own track.

```html
<template id="flow-template">
  <div data-composition-id="flow" data-width="1080" data-height="1920" data-duration="3.5">
    <style>
      .g { position: absolute; inset: 0; background: #0B0B0D; display: flex; flex-direction: column;
           align-items: center; justify-content: center; gap: 48px; font: 72px Ftitle, sans-serif; color: #fff; }
      .box { padding: 40px 60px; border-radius: 28px; background: #17171B; }
      .arrow { color: #3B82F6; font-size: 96px; }
    </style>
    <div class="g"><div class="box b1">Raw recording</div><div class="arrow">↓</div><div class="box b2">Finished Short</div></div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.from(".b1", { autoAlpha: 0, y: -40, duration: .4 }, .1)
        .from(".arrow", { autoAlpha: 0, scale: .6, duration: .3 }, .5)
        .from(".b2", { autoAlpha: 0, y: 40, duration: .4 }, .8);
      window.__timelines["flow"] = tl;
    </script>
  </div>
</template>
```

Keep motion purposeful: one entrance per element, eased, then hold. Check it in the draft before the final render.

## Layout geometry

- `a-roll`: the camera covers 1080x1920 with the face centered horizontally and 36% down.
- `punch`: the same, zoomed by `punch_zoom` (default 1.1).
- `split`: the visual fills y 0 to 880. The speaker fills y 880 to 1920 at 1.2x, face 42% down the panel.
- Captions sit at y 1400 on speaker shots, on the 880 seam for splits, and at y 1560 on B-roll. Override with `caption_y` in the style.

## Getting B-roll

```bash
# YouTube, X, and most video sites (the player client flag avoids YouTube's throttled formats)
yt-dlp --extractor-args "youtube:player_client=tv,mweb" -f "bv*[height<=1080]+ba/b" -o "$P/broll/raw_%(id)s.%(ext)s" URL

# Media embedded in a blog post: list candidate files, then download the one you need
curl -sL -A "Mozilla/5.0" "PAGE_URL" | grep -oE 'https?://[^"'"'"' ]+\.(mp4|webm|gif|m3u8)' | sort -u
curl -sL -o "$P/broll/clip.gif" "MEDIA_URL"

# Trim to the useful seconds and convert anything (gif, webm, mov) to H.264
ffmpeg -ss 12.0 -t 4 -i in.webm -an -c:v libx264 -crf 18 -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" "$P/broll/clip.mp4"

# Crop to the part that reads on a phone (w:h:x:y in source pixels)
ffmpeg -i in.mp4 -an -vf "crop=1200:900:300:120" -c:v libx264 -crf 18 "$P/broll/clip_crop.mp4"
```

Inspect a clip before using it: `$S/py $S/frames.py clip.mp4 /tmp/look --count 4`.

## style.json

`sound_effects` is the default for the `Sound effects:` line. Every key is optional; missing keys fall back to `styles/default.json`. `pad` is the band's horizontal and vertical padding; `max_words` and `max_chars` cap each caption, which also splits at punctuation and pauses; `border` with zero alpha draws no outline. Font paths are relative to the style file; weights pick a weight from a variable font. The default is Inter for everything. Colors are `#RRGGBB` or `#RRGGBBAA`. `projects_dir` is where new projects go when the user doesn't say. `grade` is the default ffmpeg grade, used when `edit.md` has no `Grade:` line.

```json
{
  "projects_dir": "~/Videos/shorts",
  "grade": "colortemperature=temperature=6200,eq=contrast=1.04:saturation=1.05",
  "punch_zoom": 1.1,
  "caption_y": {"a-roll": 1400, "punch": 1400, "split": 880, "b-roll": 1560},
  "caption": {"font": "fonts/MyFont.woff2", "weight": 500, "size": 64, "color": "#FFFFFF", "box": "#000000E0",
              "border": "#FFFFFF30", "radius": 18, "pad": [36, 20], "uppercase": true,
              "max_words": 3, "max_chars": 18, "emphasis": "#F59E0B"},
  "card": {"background": "#0B0B0D", "panel": "#17171B", "border": "#FFFFFF24", "text": "#FFFFFF",
           "accent": "#3B82F6", "title_font": "fonts/Title.woff2", "title_weight": 800, "body_font": "fonts/Body.woff2",
           "body_weight": 600, "number_font": "fonts/Mono.woff2", "number_weight": 800},
  "sound_effects": "off"
}
```
