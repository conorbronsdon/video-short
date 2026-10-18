"""Transcribe a video with Parakeet (local, via onnx-asr) into word timestamps and a readable transcript.
usage: transcribe.py VIDEO OUT_PREFIX
writes OUT_PREFIX.json [{text,start,end}] and OUT_PREFIX.md (phrases with times and pauses).
Parakeet keeps um, uh, stutters, and restarts, which the retake cut needs."""
import json, os, sys, tempfile

import numpy as np
from common import energy_db, read_wav_mono, run, silence_threshold

MODEL = "nemo-parakeet-tdt-0.6b-v3"
CHUNK_MAX = 20.0  # seconds per recognition pass; Parakeet drops words on some longer inputs


def extract_wav(video, wav):
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav])


def chunks(db, total_s, hop=0.01):
    """Split at the middle of pauses so no chunk exceeds CHUNK_MAX, and skip chunks with no speech."""
    thr = silence_threshold(db)
    quiet = db < thr
    pauses, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - k) * hop >= 0.25:
                pauses.append((k + j) / 2 * hop)
            k = j
        else:
            k += 1
    bounds, start = [0.0], 0.0
    while total_s - start > CHUNK_MAX:
        fits = [p for p in pauses if start + 5 < p <= start + CHUNK_MAX]
        if fits:
            cut = fits[-1]
        else:
            lo, hi = int((start + CHUNK_MAX * 0.75) / hop), int((start + CHUNK_MAX) / hop)
            cut = (lo + int(np.argmin(db[lo:hi]))) * hop
        bounds.append(cut)
        start = cut
    bounds.append(total_s)
    return [(a, b) for a, b in zip(bounds, bounds[1:]) if np.any(db[int(a / hop):int(b / hop)] >= thr)]


def tokens_to_words(tokens, stamps):
    words = []
    for tok, ts in zip(tokens, stamps):
        if tok.startswith(" ") or not words:
            words.append({"text": tok.strip(), "start": ts, "last": ts})
        else:
            words[-1]["text"] += tok
            if any(ch.isalnum() for ch in tok):  # punctuation tokens can be stamped long after the word
                words[-1]["last"] = ts
    return [w for w in words if w["text"]]


def refine_ends(words, db, hop=0.01):
    """Parakeet gives token start times only. Estimate each word end from the energy envelope."""
    thr = silence_threshold(db)
    n = len(db)
    for i, w in enumerate(words):
        nxt = words[i + 1]["start"] if i + 1 < len(words) else n * hop
        cand = min(nxt, w["last"] + 0.45)
        k = min(n - 1, int(cand / hop))
        floor_k = int((w["last"] + 0.06) / hop)
        while k > floor_k and db[k] < thr:
            k -= 1
        w["end"] = round(min(nxt, max(w["last"] + 0.08, k * hop + 0.05)), 3)
        w["start"] = round(w["start"], 3)
        del w["last"]
    return words


def recognize(wav):
    import onnx_asr
    model = onnx_asr.load_model(MODEL, quantization="int8").with_timestamps()
    pcm, sr = read_wav_mono(wav)
    db = energy_db(pcm, sr)
    total = len(pcm) / sr
    words = []
    for a, b in chunks(db, total):
        res = model.recognize(pcm[int(a * sr):int(b * sr)], sample_rate=sr)
        for w in tokens_to_words(res.tokens, [t + a for t in res.timestamps]):
            words.append(w)
    return refine_ends(words, db), total


def phrases(words, gap=0.3):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or nxt["start"] - w["end"] >= gap or w["text"][-1] in ".?!":
            out.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["text"] for x in cur),
                        "pause_after": round(nxt["start"] - w["end"], 2) if nxt else None})
            cur = []
    return out


def write_markdown(words, total, path, title):
    lines = [f"# {title}", "", f"Duration: {total:.2f}s. Times are seconds. Word-level times are in the matching .json file.", ""]
    if words and words[0]["start"] > 0.5:
        lines.append(f"(silence 0.00-{words[0]['start']:.2f})")
    for p in phrases(words):
        lines.append(f"[{p['start']:.2f}-{p['end']:.2f}] {p['text']}")
        if p["pause_after"] and p["pause_after"] >= 0.5:
            lines.append(f"(pause {p['pause_after']:.2f}s)")
    open(path, "w").write("\n".join(lines) + "\n")


def transcribe(video, out_prefix):
    os.makedirs(os.path.dirname(os.path.abspath(out_prefix)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "voice.wav")
        extract_wav(video, wav)
        words, total = recognize(wav)
    if not words:
        sys.exit("error: no speech found")
    json.dump(words, open(out_prefix + ".json", "w"), indent=1)
    write_markdown(words, total, out_prefix + ".md", os.path.basename(out_prefix))
    return words, total


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    words, total = transcribe(sys.argv[1], sys.argv[2])
    print(f"{len(words)} words, {total:.2f}s -> {sys.argv[2]}.md and .json")


if __name__ == "__main__":
    main()
