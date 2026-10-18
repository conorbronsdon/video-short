---
name: video-short
description: "Turn a raw talking-head recording into a finished 1080x1920 YouTube Short, Reel, or TikTok. The agent cuts retakes and dead air from a local transcript, plans layouts, B-roll, and motion graphics in a readable edit.md, opens it in HyperFrames Studio for review, then renders captions, clips, and music. Use when someone wants to edit a raw recording into a vertical Short, cut retakes from talking-head footage, or add captions, B-roll, or motion graphics to a Short."
---

# Video Short

Input: a raw talking-head recording, landscape or vertical. Output: `renders/<project>-vN.mp4` at 1080x1920 and 30 fps, plus the `edit.md` that produced it.

You make every editorial call: what to cut, how to frame, which layout, which visual. The scripts only measure, build, and render. Commands, the `edit.md` format, and style keys live in [reference.md](reference.md).

Needs ffmpeg, Python 3.10+, and Node.js 22+ for [HyperFrames](https://github.com/heygen-com/hyperframes), which renders the video in headless Chrome. The scripts install their own Python packages, and `npx` fetches HyperFrames on first run. Optional: yt-dlp for web clips, and `GEMINI_API_KEY` for generated music.

## Set up the project

Make one folder per Short, named with a short slug, where the user asks. Otherwise use `projects_dir` from the style file, or the current folder. Leave the original recording untouched; point `Source:` at it or copy it in. Put clips and graphics in `broll/`.

## 1. Cut

Run `transcribe.py` and read every line of `work/transcript_raw.md`. Parakeet keeps ums, stutters, and restarts, so retakes are visible in the text.

Write `## Cuts` in `edit.md`:

- Keep the last complete take of any repeated line. Drop false starts, stray fillers, and dead air.
- Cut between words, never inside one. For a restart mid-sentence, use the word times in the `.json`.
- Start about 0.1s before the first word and end about 0.1s after the last. Keep gaps between kept phrases short, but leave a natural breath after commas and list items. Never speed up the voice.

Pick the grade and framing by looking, not guessing. `frames.py` exports gridded stills: read the face center as `Framing: x, y`. Preview a subtle ffmpeg grade side by side with `--grade`, or use `Grade: none` when the footage already looks good. When the style file sets a `grade`, leave the line out to use it.

Run `cut.py`, then read `work/transcript_clean.md`. If a word got clipped or a retake survived, fix the cuts and run it again. All scene times use this cut timeline.

## 2. Plan the scenes

Write `## Scenes` in `edit.md`, one row per shot, with start and end on spoken words.

- **The first 3 seconds decide whether someone keeps watching.** Open on the hook line with the speaker or the strongest visual. Close on the speaker.
- **Layouts:** `a-roll` (full-screen speaker), `punch` (tighter speaker for emphasis), `split` (visual on top, speaker below), `b-roll` (visual full screen).
- **Keep the speaker present.** The speaker is on screen for at least half the Short, and a full-screen B-roll shot ends within about 3.5 seconds, because viewers connect with a face.
- **Visuals show what the words don't:** the product doing the thing, the result, the proof. Captions already carry the words, so a visual that repeats the sentence wastes the shot.
- **Prefer motion.** Real footage first. Without footage, use a motion graphic: a list card that adds one row per spoken item, a `number:` that counts up to a stat the speaker says, or a `graphic:` you write in HyperFrames for anything else, such as a flow or a before and after. Use a still image only with something moving on it.
- **Pace:** Most shots run 1.5 to 4 seconds. Give each item in a spoken list its own beat.
- **Use each clip once.** The build warns on a repeat.

Find B-roll in this order: the user's own footage, then official demos and the media in the post or launch page they mention. yt-dlp handles YouTube, X, and most video sites. For a blog post, read the page and download the media it embeds (mp4, webm, gif, images). If a video only loads by script, open the page in a browser to find the file. Trim each clip to its useful seconds, fit the whole action in frame, then crop until it reads on a phone. Use footage the user has the right to use, and list sources in the scene notes.

Add `## Caption fixes` for names the transcript misspells. Add `## Emphasis` for the rare term that earns a box in the caption: a product name, a number, or the main claim, about once every 10-15 seconds at most, so captions stay quiet.

For music, ask whether the user has a track (from Suno, a library, anywhere) or wants one generated with `music.py`. With neither, leave music out. Leave sound effects off unless the user asks. `Sound effects: subtle` adds quiet taps on cards and numbers and a soft whoosh on B-roll cuts.

## 3. Review in Studio

Run `build.py`, then open the project with `npx hyperframes preview` in the background. HyperFrames Studio plays the whole Short with every scene, caption, and graphic on its own track, so the user can scrub to any moment. Ask for notes in chat.

Apply every note to `edit.md` and build again; Studio reloads. Each build rewrites `hf/` from `edit.md`, so if the user drags a clip or caption in Studio, read the new times from `hf/index.html` and carry them into `edit.md` first.

If Studio won't open, or the user wants to write notes scene by scene, run `review.py` in the background instead. It opens a storyboard with a frame and a notes box per scene, then exits with the notes when the user clicks Submit. A submit with no notes approves the plan.

## 4. Render and check

Run `render.py`, then `qa.py`, and fix any failed check. Look at `opening.jpg`, `contact.jpg`, and `cuts/*.jpg` in `work/qa/`:

- Captions never cover the mouth or chin.
- Every cut lands on the right word, with no blank, frozen, or stretched frames.
- Text and clip details are readable at phone size.

You can't hear the mix, so ask the user to listen for music level and clipped words. Each render saves the next version and keeps earlier ones.

Run [eval.md](eval.md), then share the video path, duration, loudness, and the scene table.

## Style

Caption, card, and color choices come from a style file: the `--style` flag, then `style.json` in the project, then `~/.config/video-short/style.json`, then the bundled default. Keys are in [reference.md](reference.md). When the user gives a note about the look, offer to save it to their style file so every Short gets it.
