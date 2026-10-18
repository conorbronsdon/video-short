"""Optional: generate an instrumental music bed with Google Lyria RealTime. Needs GEMINI_API_KEY.
usage: music.py OUT_WAV --seconds 45 --prompt "warm lo-fi, Rhodes, soft brushed drums" [--bpm 90]
Writes 48 kHz stereo WAV. Set 'Music: <file>' in edit.md to use it."""
import argparse, asyncio, os, subprocess, sys, wave


def ensure_genai():
    """Install google-genai into this venv on first use, then restart so the import sees it."""
    try:
        import google.genai  # noqa: F401
        return
    except ImportError:
        pass
    pip = [sys.executable, "-m", "pip", "install", "-q", "google-genai"]
    if subprocess.run(pip, capture_output=True).returncode:
        subprocess.run(["uv", "pip", "install", "-q", "-p", sys.executable, "google-genai"], check=True)
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def stream(key, prompt, seconds, bpm, out):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key, http_options={"api_version": "v1alpha"})
    sr, ch, width = 48000, 2, 2
    need = int(seconds * sr) * ch * width
    buf = bytearray()
    async with client.aio.live.music.connect(model="models/lyria-realtime-exp") as session:
        await session.set_weighted_prompts(prompts=[types.WeightedPrompt(text=prompt, weight=1.0)])
        await session.set_music_generation_config(config=types.LiveMusicGenerationConfig(bpm=bpm, temperature=1.0))
        await session.play()
        async for msg in session.receive():
            sc = msg.server_content
            if sc and sc.audio_chunks:
                for chunk in sc.audio_chunks:
                    buf.extend(chunk.data)
            if len(buf) >= need:
                break
    with wave.open(out, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(width)
        wf.setframerate(sr)
        wf.writeframes(bytes(buf[:need]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--bpm", type=int, default=90)
    a = ap.parse_args()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("error: set GEMINI_API_KEY (free key at https://aistudio.google.com/apikey), or use your own music file")
    ensure_genai()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    asyncio.run(stream(key, a.prompt + ", instrumental, no vocals", a.seconds + 1, a.bpm, a.out))
    print(f"Music -> {a.out}")


if __name__ == "__main__":
    main()
