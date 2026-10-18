"""Export stills so the agent can judge framing and color by looking at them.
usage: frames.py VIDEO OUT_DIR [--count 3] [--times 1.0 5.5] [--grade "eq=contrast=1.05"]
Each still gets a labeled 0.1 grid, so the face center can be read as x, y fractions.
With --grade, each still is a side-by-side: original on the left, graded on the right."""
import argparse, os, tempfile

from PIL import Image, ImageDraw
from common import probe, run


def grab(video, t, out, vf=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1"]
    if vf:
        cmd += ["-vf", vf]
    run(cmd + [out])
    return Image.open(out).convert("RGB")


def draw_grid(im):
    im = im.copy()
    d = ImageDraw.Draw(im)
    w, h = im.size
    for i in range(1, 10):
        x, y = int(w * i / 10), int(h * i / 10)
        d.line([(x, 0), (x, h)], fill=(255, 255, 0), width=1)
        d.line([(0, y), (w, y)], fill=(255, 255, 0), width=1)
        d.text((x + 3, 3), f".{i}", fill=(255, 255, 0))
        d.text((3, y + 3), f".{i}", fill=(255, 255, 0))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out_dir")
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--times", type=float, nargs="*")
    ap.add_argument("--grade")
    a = ap.parse_args()
    _, _, dur = probe(a.video)
    times = a.times or [dur * (i + 1) / (a.count + 1) for i in range(a.count)]
    os.makedirs(a.out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for t in times:
            raw = grab(a.video, t, os.path.join(tmp, "a.png"))
            if a.grade:
                graded = grab(a.video, t, os.path.join(tmp, "b.png"), a.grade)
                im = Image.new("RGB", (raw.width * 2, raw.height))
                im.paste(raw, (0, 0))
                im.paste(graded, (raw.width, 0))
                name = f"grade_{t:06.2f}.jpg"
            else:
                im = draw_grid(raw)
                name = f"frame_{t:06.2f}.jpg"
            im.thumbnail((1600, 1600))
            im.save(os.path.join(a.out_dir, name), quality=88)
            print(os.path.join(a.out_dir, name))


if __name__ == "__main__":
    main()
