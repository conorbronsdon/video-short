"""Apply the Cuts and Grade from edit.md (or the style's default grade) in one ffmpeg pass, then re-transcribe the cut video.
usage: cut.py PROJECT
reads edit.md (Source, Grade, ## Cuts); writes work/clean.mp4 and work/transcript_clean.md/.json.
One pass keeps audio and video in sync across every join. Cut edges snap to the quietest 10ms
nearby and to the 30fps frame grid so no join lands on a waveform peak."""
import os, sys, tempfile

import numpy as np
from common import FPS, die, energy_db, load_style, parse_edit, probe, project_paths, read_wav_mono, run, setting
from transcribe import extract_wav, transcribe


def snap(cuts, db, duration, hop=0.01):
    out = []
    for a, b in cuts:
        ka, kb = int(a / hop), int(b / hop)
        lo, hi = max(0, ka - 4), min(len(db) - 1, ka + 2)
        a = (lo + int(np.argmin(db[lo:hi + 1]))) * hop if hi > lo else a
        lo, hi = max(0, kb - 2), min(len(db) - 1, kb + 5)
        b = (lo + int(np.argmin(db[lo:hi + 1]))) * hop if hi > lo else b
        a, b = round(a * FPS) / FPS, min(duration, round(b * FPS) / FPS)
        if b - a >= 1.0 / FPS:
            out.append((a, b))
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    paths = project_paths(sys.argv[1])
    edit = parse_edit(paths["edit"])
    src = setting(edit, "source")
    if not src:
        die("edit.md needs a 'Source: raw.mp4' line")
    src = src if os.path.isabs(src) else os.path.join(paths["root"], src)
    if not edit["cuts"]:
        die("edit.md has no ranges under '## Cuts'")
    _, _, duration = probe(src)

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "raw.wav")
        extract_wav(src, wav)
        pcm, sr = read_wav_mono(wav)
        cuts = snap(sorted(edit["cuts"]), energy_db(pcm, sr), duration)

        parts, joins = [], ""
        fade = 0.012  # tiny audio fades stop clicks at each join
        for i, (a, b) in enumerate(cuts):
            parts.append(f"[0:v]trim=start={a:.6f}:end={b:.6f},setpts=PTS-STARTPTS,fps={FPS}[v{i}]")
            parts.append(f"[0:a]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,"
                         f"afade=t=in:d={fade},afade=t=out:st={max(0, b - a - fade):.6f}:d={fade}[a{i}]")
            joins += f"[v{i}][a{i}]"
        grade = setting(edit, "grade") or load_style(paths["root"]).get("grade", "")
        grade_chain = f",{grade}" if grade and grade.lower() != "none" else ""
        parts.append(f"{joins}concat=n={len(cuts)}:v=1:a=1[vc][ac]")
        parts.append(f"[vc]setsar=1{grade_chain},format=yuv420p[vout]")
        script = os.path.join(tmp, "cut.txt")
        open(script, "w").write(";\n".join(parts))
        os.makedirs(paths["work"], exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex_script", script,
             "-map", "[vout]", "-map", "[ac]", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
             "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", paths["clean"]])

    _, _, clean_dur = probe(paths["clean"])
    words, _ = transcribe(paths["clean"], os.path.join(paths["work"], "transcript_clean"))
    kept = sum(b - a for a, b in cuts)
    print(f"Cut {len(cuts)} ranges ({kept:.2f}s of {duration:.2f}s) -> work/clean.mp4 ({clean_dur:.2f}s, {len(words)} words). "
          f"Read work/transcript_clean.md next.")


if __name__ == "__main__":
    main()
