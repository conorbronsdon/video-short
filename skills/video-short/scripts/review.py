"""Open the draft render for review: one 9:16 player with a scene-band timeline, where the user pauses on any frame,
comments on it, and clicks Send. Send saves work/feedback.md and this script prints it and exits.
usage: review.py PROJECT [VIDEO] [--no-open] [--port 8791] [--timeout 7200]
VIDEO defaults to the newest renders/*.mp4. Pass --no-open after the first round: the open page reloads itself
when the next draft is ready."""
import argparse, glob, html, json, os, re, sys, threading, time, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from common import parse_edit, probe, project_paths, validate_scenes

CSS = """
:root, :root[data-theme="dark"] {
  --canvas: #171614; --rail: #1f1e1b; --card: #262420; --card-border: #34322d; --hair: #2f2d29;
  --strong-border: #403d37; --txt: #eae7e0; --strong-txt: #f4f1ea; --mute: #9c968a; --faint: #6e6961;
  --soft: #2c2a26; --chip: #2e2c27; --input-bg: #1c1b18; --focus: #4d4941; --danger: #d9705f;
  --btn-bg: #f0ede6; --btn-fg: #1b1a16; --band: #2a2825; --band-alt: #24221f; --band-cur: #3a3631; --pin: #e0a800;
}
:root[data-theme="light"] {
  --canvas: #eceae4; --rail: #fbfaf7; --card: #ffffff; --card-border: #e9e7e0; --hair: #e4e2db;
  --strong-border: #d9d5c9; --txt: #26241e; --strong-txt: #1b1a16; --mute: #8b877d; --faint: #b6b2a8;
  --soft: #f2f0ea; --chip: #f4f2ec; --input-bg: #fdfcfa; --focus: #c2beb4; --danger: #b23b2e;
  --btn-bg: #1b1a16; --btn-fg: #fbfaf7; --band: #dfdcd4; --band-alt: #e6e3dc; --band-cur: #cfcbc1; --pin: #c99500;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
button, textarea { font: inherit; color: inherit; }
html, body { height: 100%; overflow: hidden; }
body { background: var(--canvas); color: var(--txt); font: 13px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, sans-serif; -webkit-font-smoothing: antialiased; display: flex; }
.stage { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 20px 28px; }
video { height: calc(100vh - 140px); aspect-ratio: 9 / 16; background: #000; border-radius: 10px; cursor: pointer; display: block; }
.controls { width: min(100%, 860px); display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; align-items: center; gap: 10px; }
.play { width: 30px; height: 30px; border-radius: 50%; border: 1px solid var(--strong-border); background: var(--card); display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 11px; }
.play:hover { border-color: var(--focus); }
.tc { font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--strong-txt); }
.tc span { color: var(--faint); }
.chip { padding: 2px 8px; border-radius: 999px; background: var(--chip); color: var(--mute); font-size: 11px; font-weight: 600; }
#bar { position: relative; height: 28px; border-radius: 6px; overflow: hidden; background: var(--band); cursor: pointer; user-select: none; }
.band { position: absolute; top: 0; bottom: 0; background: var(--band); border-right: 1px solid var(--canvas); font: 10px ui-monospace, monospace; color: var(--faint); padding: 7px 0 0 5px; overflow: hidden; white-space: nowrap; }
.band:nth-child(even) { background: var(--band-alt); }
.band.cur { background: var(--band-cur); color: var(--strong-txt); }
.band.nolabel { color: transparent; }
.pin { position: absolute; top: 2px; width: 8px; height: 8px; margin-left: -4px; border-radius: 50%; background: var(--pin); z-index: 2; pointer-events: none; }
#head { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: var(--strong-txt); pointer-events: none; z-index: 3; }
.rail { flex: none; width: 352px; display: flex; flex-direction: column; border-left: 1px solid var(--hair); background: var(--rail); }
.rail-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 12px 12px; }
.rail-head { display: flex; align-items: center; gap: 7px; padding: 0 4px 10px; }
.section { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--mute); }
.dim { color: var(--faint); font-size: 11px; }
.icon-btn { width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--hair); border-radius: 7px; background: var(--soft); font-size: 12.5px; line-height: 1; cursor: pointer; }
.icon-btn:hover { border-color: var(--strong-border); color: var(--strong-txt); }
.push { margin-left: auto; }
.speed { min-width: 46px; padding: 3px 9px; border: 1px solid var(--strong-border); border-radius: 999px; background: var(--card); font: 600 11.5px ui-monospace, monospace; color: var(--strong-txt); cursor: pointer; }
.speed:hover { border-color: var(--focus); }
.controls { position: relative; }
.keys { position: absolute; right: 0; bottom: 74px; z-index: 10; width: 250px; padding: 10px 12px; border: 1px solid var(--strong-border); border-radius: 8px; background: var(--card); box-shadow: 0 8px 24px -10px rgba(0, 0, 0, 0.45); color: var(--mute); font-size: 12px; }
.keys div { display: flex; justify-content: space-between; gap: 12px; padding: 3px 0; }
kbd { font: 10.5px ui-monospace, monospace; padding: 1px 5px; border: 1px solid var(--hair); border-radius: 4px; background: var(--soft); color: var(--txt); }
.compose { margin-bottom: 12px; padding: 13px 14px; border: 1px solid var(--strong-border); border-radius: 8px; background: var(--card); box-shadow: 0 4px 14px -8px rgba(27, 26, 22, 0.3); }
.compose-head { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; }
textarea { width: 100%; padding: 8px 10px; border: 1px solid var(--hair); border-radius: 6px; background: var(--input-bg); font-size: 13px; line-height: 1.5; resize: none; outline: none; }
textarea:focus { border-color: var(--focus); background: var(--card); }
#note { min-height: 72px; }
.compose-foot { display: flex; align-items: center; gap: 8px; margin-top: 9px; }
.btn { padding: 6px 12px; border: 1px solid var(--btn-bg); border-radius: 6px; background: var(--btn-bg); color: var(--btn-fg); font-size: 12px; font-weight: 500; cursor: pointer; }
.btn:disabled { border-color: var(--hair); background: var(--soft); color: var(--faint); cursor: default; }
.cards { display: flex; flex-direction: column; gap: 8px; }
.empty { padding: 8px 4px; color: var(--faint); font-size: 12px; }
.comment { padding: 11px 12px; border: 1px solid var(--card-border); border-radius: 8px; background: var(--card); cursor: pointer; }
.comment:hover { border-color: var(--strong-border); }
.comment-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.comment p { font-size: 13px; line-height: 1.5; white-space: pre-wrap; }
.del { margin-left: auto; border: 0; background: none; color: var(--faint); font-size: 11px; cursor: pointer; }
.del:hover { color: var(--danger); }
.rail-foot { flex: none; padding: 12px; border-top: 1px solid var(--hair); }
.send { width: 100%; padding: 10px 12px; border: 1px solid var(--btn-bg); border-radius: 6px; background: var(--btn-bg); color: var(--btn-fg); font-size: 12.5px; font-weight: 500; cursor: pointer; }
#status { margin-top: 8px; min-height: 16px; color: var(--mute); font-size: 11.5px; text-align: center; }
@media (max-aspect-ratio: 4/5) {   /* phone or portrait window: video and timeline on top, comments below */
  body { flex-direction: column; }
  .stage { flex: none; padding: 12px 14px 6px; gap: 8px; }
  video { height: 46vh; }
  .rail { width: 100%; flex: 1; min-height: 0; border-left: 0; border-top: 1px solid var(--hair); }
}
"""

JS = r"""
const $ = (id) => document.getElementById(id);
const v = $("v"), bar = $("bar"), note = $("note");
const fmt = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(2).padStart(5, "0")}`;
const sceneAt = (t) => SCENES.find((s) => t >= s.start && t < s.end) || SCENES[SCENES.length - 1];
const store = (k, val) => { try { if (val === undefined) return localStorage.getItem(k); localStorage.setItem(k, val); } catch {} };
const KEY = "review:" + location.pathname;
let state; try { state = JSON.parse(store(KEY)) || { comments: [] }; } catch { state = { comments: [] }; }
const save = () => store(KEY, JSON.stringify(state));

// Theme: dark by default, remembered per browser.
const setTheme = (t) => { document.documentElement.dataset.theme = t; $("theme").textContent = t === "dark" ? "☀" : "☾"; store("review:theme", t); };
setTheme(store("review:theme") || "dark");
$("theme").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
$("keysbtn").onclick = (e) => { e.stopPropagation(); $("keys").hidden = !$("keys").hidden; };
addEventListener("click", (e) => { if (!$("keys").contains(e.target)) $("keys").hidden = true; });
addEventListener("keydown", (e) => { if (e.key === "Escape") $("keys").hidden = true; });

SCENES.forEach((s) => {
  const b = document.createElement("div");
  b.className = "band"; b.dataset.id = s.id; b.textContent = s.id;
  b.style.left = (s.start / DUR) * 100 + "%"; b.style.width = ((s.end - s.start) / DUR) * 100 + "%";
  b.title = `${s.id} · ${s.layout} · ${s.visual}\n“${s.spoken}”`;
  bar.appendChild(b);
});
const fitLabels = () => document.querySelectorAll(".band").forEach((b) => b.classList.toggle("nolabel", b.offsetWidth < 34));
window.addEventListener("resize", fitLabels); fitLabels();

const seek = (t) => { v.currentTime = Math.max(0, Math.min(DUR - 0.001, t)); };
function tick() {
  const t = v.currentTime, s = sceneAt(t);
  $("tc").innerHTML = `${fmt(t)} <span>/ ${fmt(DUR)}</span>`;
  $("scene").textContent = `${s.id} · ${s.layout}`;
  $("at").textContent = `${fmt(t)} · ${s.id}`;
  $("head").style.left = (t / DUR) * 100 + "%";
  document.querySelectorAll(".band").forEach((b) => b.classList.toggle("cur", b.dataset.id === s.id));
  $("play").textContent = v.paused ? "▶" : "❚❚";
}
["timeupdate", "seeked", "play", "pause"].forEach((e) => v.addEventListener(e, tick));
(function loop() { if (!v.paused) tick(); requestAnimationFrame(loop); })();
const toggle = () => (v.paused ? v.play() : v.pause());
// Playback speed: click to cycle, or < and > to step; remembered per browser.
const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
const setSpeed = (r) => { v.playbackRate = r; $("speed").textContent = r + "×"; store("review:speed", String(r)); };
setSpeed(Number(store("review:speed")) || 1);
const stepSpeed = (d) => { const i = SPEEDS.indexOf(v.playbackRate); setSpeed(SPEEDS[Math.max(0, Math.min(SPEEDS.length - 1, (i < 0 ? 2 : i) + d))]); };
$("speed").onclick = () => setSpeed(SPEEDS[(SPEEDS.indexOf(v.playbackRate) + 1) % SPEEDS.length]);
v.onclick = toggle; $("play").onclick = toggle;
let drag = false;
const scrub = (e) => { const r = bar.getBoundingClientRect(); seek(((e.clientX - r.left) / r.width) * DUR); };
bar.addEventListener("mousedown", (e) => { drag = true; v.pause(); scrub(e); });
addEventListener("mousemove", (e) => drag && scrub(e));
addEventListener("mouseup", () => (drag = false));

function render() {
  document.querySelectorAll(".pin").forEach((p) => p.remove());
  state.comments.sort((a, b) => a.t - b.t);
  $("count").textContent = state.comments.length || "";
  const list = $("list");
  list.innerHTML = state.comments.length ? "" : '<div class="empty">Pause on a frame and type what should change.</div>';
  state.comments.forEach((c, i) => {
    const pin = document.createElement("div");
    pin.className = "pin"; pin.style.left = (c.t / DUR) * 100 + "%"; bar.appendChild(pin);
    const el = document.createElement("div");
    el.className = "comment";
    el.innerHTML = `<div class="comment-head"><span class="chip">${fmt(c.t)} · ${c.scene}</span><button class="del">Delete</button></div><p></p>`;
    el.querySelector("p").textContent = c.note;
    el.onclick = () => { v.pause(); seek(c.t); };
    el.querySelector(".del").onclick = (e) => { e.stopPropagation(); state.comments.splice(i, 1); save(); render(); };
    list.appendChild(el);
  });
  $("send").textContent = state.comments.length ? "Send notes" : "Approve and render final";
}
function add() {
  const text = note.value.trim();
  if (!text) return;
  const t = +v.currentTime.toFixed(3), s = sceneAt(t);
  state.comments.push({ t, scene: s.id, scene_start: s.start, scene_end: s.end, note: text });
  note.value = ""; $("add").disabled = true; save(); render(); note.blur();
}
note.onfocus = () => v.pause();
note.oninput = () => ($("add").disabled = !note.value.trim());
note.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); add(); } if (e.key === "Escape") note.blur(); };
$("add").onclick = add;

addEventListener("keydown", (e) => {
  if (e.target.tagName === "TEXTAREA") return;
  const step = e.shiftKey ? 1 : 1 / FPS;
  if (e.code === "Space") { e.preventDefault(); toggle(); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); v.pause(); seek(v.currentTime - step); }
  else if (e.key === "ArrowRight") { e.preventDefault(); v.pause(); seek(v.currentTime + step); }
  else if (e.key === "c") { e.preventDefault(); note.focus(); }
  else if (e.key === "<" || e.key === ",") { e.preventDefault(); stepSpeed(-1); }
  else if (e.key === ">" || e.key === ".") { e.preventDefault(); stepSpeed(1); }
});

$("send").onclick = async () => {
  $("send").disabled = true; $("status").textContent = "Sending…";
  try {
    const r = await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video: v.getAttribute("src").split("?")[0], comments: state.comments }) });
    if (!r.ok) throw new Error(r.status);
    state = { comments: [] }; save(); render();
    $("status").textContent = "Sent. This page reloads when the next draft is ready.";
  } catch { $("status").textContent = "Couldn't reach your agent. Ask it to run review.py again; your notes are saved here."; render(); }
};

// Reload when the page is rebuilt, unless unsent comments are waiting.
let version = null;
setInterval(async () => {
  try {
    const { version: now } = await (await fetch("/api/version")).json();
    if (version === null) version = now;
    else if (now !== version && !state.comments.length && !note.value.trim()) location.reload();
  } catch {}
}, 3000);
render(); tick();
"""


def words_between(words, a, b):
    return " ".join(w["text"] for w in words if w["end"] > a + 0.04 and w["start"] < b - 0.04)


def describe(vis):
    if not vis:
        return "camera"
    if vis["type"] == "card":
        return "card: " + " / ".join([vis["title"], *vis["rows"]])
    if vis["type"] == "number":
        return f"number: {vis['value']}"
    return f"{vis['type']}: {vis['src']}"


def fmt(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def build(paths, video):
    edit = parse_edit(paths["edit"])
    dur = probe(video)[2]
    words = json.load(open(os.path.join(paths["work"], "transcript_clean.json")))
    scenes = [{"id": sc["id"], "start": sc["start"], "end": sc["end"], "layout": sc["layout"], "visual": describe(sc["visual"]),
               "spoken": words_between(words, sc["start"], sc["end"])}
              for sc in validate_scenes(edit, paths["root"], probe(paths["clean"])[2])]
    src = "/" + os.path.relpath(video, paths["root"]) + f"?v={int(os.path.getmtime(video))}"
    out = os.path.join(paths["work"], "review")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "index.html"), "w").write(PAGE.format(css=CSS, js=JS, src=html.escape(src), scenes=json.dumps(scenes), dur=dur))
    return scenes


def notes_markdown(data, scenes, video):
    by_id = {s["id"]: s for s in scenes}
    lines = [f"# Review notes: {os.path.basename(video)}", ""]
    for c in data.get("comments", []):
        s = by_id.get(c["scene"], {})
        lines += [f"## {fmt(c['t'])} · {c['scene']} ({s.get('layout', '')}, {s.get('visual', '')})",
                  f"Says: “{s.get('spoken', '')}”", "", c["note"], ""]
    if data.get("overall"):
        lines += ["## Overall", data["overall"], ""]
    if len(lines) == 2:
        lines.append("Approved with no notes. Render the final.")
    return "\n".join(lines).strip() + "\n"


def serve(paths, scenes, video, port, open_browser, timeout):
    done, feedback = threading.Event(), os.path.join(paths["work"], "feedback.md")
    page = os.path.join(paths["work"], "review", "index.html")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=paths["root"], **k)

        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def reply(self, obj):
            body = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/api/feedback":
                return self.send_error(404)
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            open(feedback, "w").write(notes_markdown(data, scenes, video))
            self.reply({"ok": True})
            done.set()

        def do_GET(self):   # byte ranges, so the video can seek
            path = self.path.split("?")[0]
            if path == "/api/version":
                return self.reply({"version": os.path.getmtime(page)})
            file, rng = self.translate_path(path), self.headers.get("Range")
            if not rng or not os.path.isfile(file):
                return super().do_GET()
            size = os.path.getsize(file)
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            start = int(m.group(1)) if m and m.group(1) else 0
            end = min(int(m.group(2)) if m and m.group(2) else size - 1, size - 1)
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(file))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            with open(file, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    left -= len(chunk)

    if os.path.exists(feedback):
        os.remove(feedback)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:   # port busy: use any free one, and open the page since the old tab can't find it
        server, open_browser = ThreadingHTTPServer(("127.0.0.1", 0), Handler), True
    url = f"http://127.0.0.1:{server.server_port}/work/review/index.html"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Review page: {url}\nWaiting for Send (saves work/feedback.md)...", flush=True)
    if open_browser:
        webbrowser.open(url)
    got = done.wait(timeout)
    time.sleep(0.3)
    server.shutdown()
    if not got:
        sys.exit("No notes before the timeout. Run review.py again; the page keeps unsent notes.")
    print(open(feedback).read())


PAGE = """<!DOCTYPE html>
<html data-theme="dark"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Review</title>
<style>{css}</style></head>
<body>
  <main class="stage">
    <video id="v" src="{src}" playsinline preload="auto"></video>
    <div class="controls">
      <div class="row"><button id="play" class="play" type="button" aria-label="Play or pause">▶</button><span id="tc" class="tc"></span><span id="scene" class="chip"></span><button id="speed" class="speed" type="button" aria-label="Playback speed">1×</button><button id="keysbtn" class="icon-btn push" type="button" aria-label="Keyboard shortcuts">?</button></div>
      <div id="keys" class="keys" hidden>
        <div><span>Play or pause</span><kbd>Space</kbd></div>
        <div><span>One frame</span><span><kbd>←</kbd> <kbd>→</kbd></span></div>
        <div><span>One second</span><span><kbd>Shift</kbd> + arrows</span></div>
        <div><span>Playback speed</span><span><kbd>&lt;</kbd> <kbd>&gt;</kbd></span></div>
        <div><span>Comment on this frame</span><kbd>C</kbd></div>
        <div><span>Add comment</span><kbd>Enter</kbd></div>
        <div><span>Back to the video</span><kbd>Esc</kbd></div>
      </div>
      <div id="bar"><div id="head"></div></div>
    </div>
  </main>
  <aside class="rail">
    <div class="rail-scroll">
      <div class="rail-head"><span class="section">Review</span><span id="count" class="dim"></span>
        <button id="theme" class="icon-btn push" type="button" aria-label="Toggle light or dark mode">☀</button></div>
      <div class="compose">
        <div class="compose-head"><span class="chip" id="at">0:00.00</span><span class="dim">Press C to comment on this frame</span></div>
        <textarea id="note" placeholder="What should change here?"></textarea>
        <div class="compose-foot"><button id="add" class="btn push" type="button" disabled>Add comment</button></div>
      </div>
      <div id="list" class="cards"></div>
    </div>
    <div class="rail-foot">
      <button id="send" class="send" type="button">Send notes</button>
      <div id="status"></div>
    </div>
  </aside>
  <script>
    const SCENES = {scenes};
    const DUR = {dur}, FPS = 30;
    {js}
  </script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("video", nargs="?")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--timeout", type=int, default=7200)
    a = ap.parse_args()
    paths = project_paths(a.project)
    renders = glob.glob(os.path.join(paths["renders"], "*.mp4"))
    if not a.video and not renders:
        sys.exit("No render to review. Run render.py --draft first.")
    video = os.path.abspath(a.video or max(renders, key=os.path.getmtime))
    scenes = build(paths, video)
    serve(paths, scenes, video, a.port, not a.no_open, a.timeout)


if __name__ == "__main__":
    main()
