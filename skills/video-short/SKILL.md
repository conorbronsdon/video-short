---
name: video-short
description: "Turn a raw talking-head recording into a finished 1080x1920 Short, Reel, or TikTok with B-roll, motion graphics, captions, and music. Shows the plan in chat, then iterates on drafts the user comments on frame by frame. Use when someone wants to edit a raw recording into a vertical video or add captions, B-roll, or motion graphics to one."
---

# Video Short

Input: a raw talking-head recording. Output: `renders/<project>-vN.mp4` at 1080x1920 and 30 fps, plus the `edit.md` that produced it.

You make every editorial call; the scripts measure, render, and serve the review page. Commands, the `edit.md` format, graphics, and style keys live in [reference.md](reference.md).

On first use, run `setup.sh`. If it lists missing tools, tell the user Video Short needs them and offer to install them with the commands it prints. A `GEMINI_API_KEY` with billing enabled is optional, for generated images, video, and music.

## 1. Cut

Make one folder per Short, named with a short slug, where the user asks, else `projects_dir` from the style file, else the current folder. Leave the recording untouched and point `Source:` at it.

Run `transcribe.py` and read every line of `work/transcript_raw.md`. The transcript keeps ums, stutters, and restarts, so retakes show in the text. Write `## Cuts` in `edit.md`:

- Keep the last complete take of any repeated line. Drop false starts, stray fillers, and dead air.
- Cut between words, never inside one; use the word times in the `.json` for a restart mid-sentence.
- Start about 0.1s before the first word and end about 0.1s after the last. Leave a natural breath after commas and list items. Never speed up the voice.

Run `cut.py --look` and read the gridded stills for `Framing: x, y`, the face center. Add `--grade` to compare a subtle ffmpeg grade side by side, or use `Grade: none` when the footage already looks good.

Run `cut.py`, then read `work/transcript_clean.md`. Fix any clipped word or surviving retake and run it again. All scene times use this cut timeline.

## 2. Plan

Research what the Short needs, then write `## Scenes` in `edit.md`, one row per shot, with start and end on spoken words.

- **Hook in the first 3 seconds.** Open on the hook line with the speaker or the strongest visual. Close on the speaker.
- **Layouts:** `a-roll` (full-screen speaker), `punch` (tighter speaker for emphasis), `split` (visual on top, speaker below), `b-roll` (visual full screen).
- **Keep the speaker present** for at least half the Short, and end each full-screen B-roll shot within about 3.5 seconds, because viewers connect with a face.
- **Visuals show what the words don't:** the product doing the thing, the result, the proof. Captions already carry the words.
- **Everything off-camera moves.** Real footage first. Otherwise a list card that adds a row per spoken item, a `number:` that counts up to a stat the speaker says, or a `graphic:` you write for anything else, such as a flow or a before and after. A still image needs motion on it.
- **Pace:** Change the shot every few seconds, since a phone viewer swipes away from a static frame. Give each spoken list item its own beat. Use each clip once.

Find B-roll in this order: the user's own footage, then official demos and the media in posts or launch pages about the topic. Trim each clip to its useful seconds and crop until it reads on a phone. Use footage the user has the right to use.

When the user has a Gemini key and a shot has no good footage, propose generating it: a Nano Banana image, a Veo clip, or a Lyria music bed. Generate only what the user approves, because each call costs money.

Add `## Caption fixes` for misspelled names, and `## Emphasis` for the rare term that earns a box in the caption, such as a product name or the main number, so captions stay quiet. For music, use the user's track, a Lyria bed they approve, or none. Leave sound effects off unless the user asks.

Show the plan in chat and wait for a go:

- One line per scene: time, layout, what's on screen, and the words spoken.
- The B-roll sources you found, with links.
- What you propose to generate, if anything, and the music.

## 3. Draft and review

Run `render.py --draft`, then `review.py` in the background. The review page plays the draft on a timeline split into scenes. The user pauses on any frame, presses C to comment, and clicks Send. The script exits and prints each note with its time, scene, and spoken words.

Apply every note to `edit.md`, render the next draft, and run `review.py --no-open`; the open page reloads itself. Repeat until the user clicks Approve and render final.

## 4. Final

Run `render.py`, then `qa.py`, and fix any failed check. Look at `opening.jpg`, `contact.jpg`, and `cuts/*.jpg` in `work/qa/`:

- Captions never cover the mouth or chin.
- Every cut lands on the right word, with no blank, frozen, or stretched frames.
- Text and clip details are readable at phone size.

You can't hear the mix, so ask the user to listen for music level and clipped words. Run [eval.md](eval.md), then share the video path, duration, and loudness.

## Style

Fonts and colors come from a style file: `--style`, then `style.json` in the project, then `~/.config/video-short/style.json`, then the bundled default. When the user gives a note about the look, offer to save it to their style file so every Short gets it.
