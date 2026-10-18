# Video Short

Turn a raw talking-head recording into a polished video Short, complete with B-roll, motion graphics, captions, music, and more, with your favorite AI agent.

<!-- Demo video: drag assets/before-after.mp4 into this README on GitHub and put the user-attachments link here. -->

## Problem

Every social platform is hungry for video Shorts. But creating a polished 30 to 60 second Short still takes hours. You have to cut filler words and retakes, hunt for compelling B-roll, add motion graphics and captions, and find the right music.

With Video Short, you can turn a raw recording into a polished Short directly in Claude Code, Codex, or your favorite AI agent. It comes with a review interface that lets you give feedback on any frame and iterate until the draft feels right.

## How to install Video Short

The easiest way to install the skill is to paste this into Claude Code, Codex, or your favorite coding agent:

```text
Install the /video-short skill globally from https://github.com/petergyang/video-short
```

You can also install it with `npx`:

```sh
npx skills add petergyang/video-short --skill video-short --global --yes
```

Video Short runs on your computer and needs:

- **ffmpeg** to cut and encode video.
- **yt-dlp** to pull B-roll from YouTube, X, and other sites.
- **Python 3.10 or newer** for transcription, which runs on your computer with a local speech model (about 600 MB).
- **Node.js 22 or newer** for [HyperFrames](https://github.com/heygen-com/hyperframes), the free, open-source renderer that turns the edit into video.
- **Optional: A Gemini API key** with billing enabled, to generate images with Nano Banana, video clips with Veo, and music with Lyria. Get a key at [Google AI Studio](https://aistudio.google.com/apikey) and set `GEMINI_API_KEY`.

The first time you use the skill, it checks for these, offers to install anything missing, and sets up HyperFrames for you.

## How to use Video Short

Record yourself talking, then hand the file to your agent:

```text
/video-short edit ~/Videos/raw.mp4 into a Short
```

1. **Cut.** The agent transcribes the recording, reads every line, and cuts retakes, false starts, and dead air.
2. **Plan.** It researches the topic, finds B-roll from your footage and the web, and shows you the plan in chat: every scene, what's on screen, and what it wants to generate. Reply "go" or ask for changes.
3. **Review.** It renders a draft and opens a review page. Pause on any frame, press C, type what should change, and click Send.
4. **Iterate.** The agent applies your notes and renders the next draft, and the page reloads. Repeat until you click Approve and render final.

The agent checks loudness, sync, and every cut before it hands back the final video. Each render saves a new version, so you can compare `v1` and `v2`.

## What goes on screen

Every Short cuts between four layouts on spoken words:

1. **A-roll:** You, full screen.
2. **Punch:** A tighter shot of you for emphasis.
3. **Split:** A visual on top, you below.
4. **B-roll:** A visual full screen while you keep talking.

Every visual moves:

- **Clips** from your footage, the web, or Veo.
- **List cards** that add a row as you say each item.
- **Numbers** that count up to the stat you mention.
- **Custom graphics** the agent writes in HTML, like a flow or a before and after.

Captions show a few words at a time on a quiet band, with an occasional highlighted key term. Add music from your own library or have Lyria write a track.

## Make it yours

Fonts, colors, and caption style come from a small `style.json`. Save yours at `~/.config/video-short/style.json` and every Short uses it. The keys are in [`reference.md`](skills/video-short/reference.md).

## What's inside

- [`SKILL.md`](skills/video-short/SKILL.md) contains the editing rules and workflow.
- [`reference.md`](skills/video-short/reference.md) contains the commands, the `edit.md` format, graphics, and style options.
- [`eval.md`](skills/video-short/eval.md) contains the checks the skill runs before handing back a video.
- [`scripts/`](skills/video-short/scripts) contains the scripts for setup, transcription, cutting, generation, rendering, the review page, and QA.

## Want more great AI skills?

Check out [Behind the Craft](https://behindthecraft.com), my personal AI system with over a dozen other quality skills and courses.

Subscribe to my [YouTube channel](https://www.youtube.com/@PeterYangYT?sub_confirmation=1) and [newsletter](https://creatoreconomy.so) for practical AI tutorials and interviews.

## License

MIT. The bundled Inter font is under the [SIL Open Font License](skills/video-short/fonts/OFL.txt).
