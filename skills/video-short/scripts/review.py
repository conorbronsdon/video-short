"""Build the storyboard from edit.md, open it in the browser, and wait for the user's feedback.
usage: review.py PROJECT [--style STYLE_JSON] [--no-open] [--build-only] [--timeout 7200]
Each scene gets a preview frame and its own comment box. Submit saves work/feedback.md and exits,
printing the feedback. The page also has Copy feedback for pasting into chat if this script is not running."""
import argparse, html, json, os, re, subprocess, sys, threading, time, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from common import parse_edit, probe, project_paths, validate_scenes

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Storyboard: __TITLE__</title>
<style>
:root{--bg:#0e0e10;--panel:#18181b;--line:#2a2a2e;--text:#f4f4f5;--muted:#a1a1aa;--accent:#3b82f6;--ok:#22c55e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;display:grid;grid-template-columns:340px 1fr;min-height:100vh}
aside{position:sticky;top:0;height:100vh;padding:20px;border-right:1px solid var(--line);display:flex;flex-direction:column;gap:12px}
aside h1{font-size:18px;margin:0}aside p{color:var(--muted);margin:0;font-size:13px}
video{width:100%;aspect-ratio:16/9;background:#000;border-radius:10px}
main{padding:24px;display:flex;flex-direction:column;gap:14px;max-width:980px}
.scene{display:grid;grid-template-columns:150px 1fr;gap:18px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.scene img{width:150px;aspect-ratio:9/16;object-fit:cover;border-radius:8px;cursor:pointer;display:block}
.head{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.id{background:var(--accent);color:#fff;font:600 12px ui-monospace,monospace;padding:2px 8px;border-radius:5px}
.meta{color:var(--muted);font:13px ui-monospace,monospace}.row{margin:6px 0}.row b{color:var(--muted);font-weight:500;margin-right:6px}
.spoken{font-style:italic}button{background:var(--accent);color:#fff;border:0;border-radius:7px;padding:7px 12px;font-weight:600;cursor:pointer}
button.ghost{background:transparent;border:1px solid var(--line);color:var(--text)}
textarea{width:100%;min-height:52px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit;resize:vertical}
textarea:focus{outline:2px solid var(--accent);border-color:transparent}
.submit{position:sticky;bottom:0;background:var(--bg);padding:14px 0;display:flex;flex-direction:column;gap:10px;border-top:1px solid var(--line)}
.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}#status{color:var(--muted);font-size:13px}#status.ok{color:var(--ok)}
#copybox{display:none;min-height:140px}
@media (max-width:800px){body{grid-template-columns:1fr}aside{position:static;height:auto}.scene{grid-template-columns:110px 1fr}.scene img{width:110px}}
</style></head><body>
<aside><h1>__TITLE__</h1><p>__SUMMARY__</p><video id="player" src="__VIDEO__" controls playsinline></video>
<p>Click a frame or Play to hear that scene. Write notes in any scene, then Submit.</p></aside>
<main>__SCENES__
<div class="submit"><label for="overall"><b>Overall notes</b></label><textarea id="overall" placeholder="Pacing, music, anything that spans scenes"></textarea>
<div class="actions"><button id="send">Submit to agent</button><button class="ghost" id="copy">Copy feedback</button><span id="status"></span></div>
<textarea id="copybox" readonly></textarea></div></main>
<script>
const KEY="storyboard:"+location.pathname, v=document.getElementById("player"); let stopAt=null;
v.addEventListener("timeupdate",()=>{if(stopAt!==null&&v.currentTime>=stopAt){v.pause();stopAt=null}});
function play(a,b){stopAt=b;v.currentTime=a;v.play()}
const boxes=[...document.querySelectorAll("textarea[data-scene]"),document.getElementById("overall")];
try{const saved=JSON.parse(localStorage.getItem(KEY)||"{}");boxes.forEach(b=>{const k=b.dataset.scene||"overall";if(saved[k])b.value=saved[k]})}catch(e){}
boxes.forEach(b=>b.addEventListener("input",()=>{try{const s={};boxes.forEach(x=>{if(x.value.trim())s[x.dataset.scene||"overall"]=x.value});localStorage.setItem(KEY,JSON.stringify(s))}catch(e){}}));
function collect(){const scenes={};document.querySelectorAll("textarea[data-scene]").forEach(t=>{if(t.value.trim())scenes[t.dataset.scene]=t.value.trim()});return{overall:document.getElementById("overall").value.trim(),scenes}}
function asMarkdown(f){let out="# Storyboard feedback\\n";if(f.overall)out+="\\n## Overall\\n"+f.overall+"\\n";for(const[k,val]of Object.entries(f.scenes))out+="\\n## "+k+"\\n"+val+"\\n";return out}
const status=document.getElementById("status");function say(t,ok){status.textContent=t;status.className=ok?"ok":""}
document.getElementById("send").onclick=async()=>{const f=collect();if(!f.overall&&!Object.keys(f.scenes).length&&!confirm("No notes written. Approve the storyboard as is?"))return;
try{const r=await fetch("/feedback",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(f)});if(!r.ok)throw 0;
say("Sent. Your agent has the notes. You can close this tab.",true);try{localStorage.removeItem(KEY)}catch(e){}}
catch(e){say("The review script isn't running, so Submit can't reach your agent. Use Copy feedback and paste it into chat.")}};
document.getElementById("copy").onclick=async()=>{const md=asMarkdown(collect()),box=document.getElementById("copybox");box.value=md;
try{await navigator.clipboard.writeText(md);say("Copied. Paste it into chat.",true);return}catch(e){}
box.style.display="block";box.focus();box.select();let ok=false;try{ok=document.execCommand("copy")}catch(e){}
say(ok?"Copied. Paste it into chat.":"Select all in the box below and copy it.",ok)};
</script></body></html>"""


def words_between(words, a, b):
    return " ".join(w["text"] for w in words if w["end"] > a + 0.04 and w["start"] < b - 0.04)


def describe(vis):
    if not vis:
        return "Camera"
    if vis["type"] == "card":
        return "Card: " + vis["title"] + (" / " + " / ".join(vis["rows"]) if vis["rows"] else "")
    return f"Clip: {vis['src']}" + (f" from {vis['start']:g}s" if vis["start"] else "")


def build(paths, style):
    edit = parse_edit(paths["edit"])
    _, _, duration = probe(paths["clean"])
    scenes = validate_scenes(edit, paths["root"], duration)
    stills = os.path.join(paths["work"], "storyboard")
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "render.py"), paths["root"], "--stills", stills]
    if style:
        cmd += ["--style", style]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr or r.stdout)
    words = json.load(open(os.path.join(paths["work"], "transcript_clean.json")))
    bust = int(time.time())
    cards = []
    for sc in scenes:
        a, b = sc["start"], sc["end"]
        esc = html.escape
        cards.append(f"""
<section class="scene"><img src="{sc['id']}.jpg?v={bust}" alt="{esc(sc['id'])} preview" onclick="play({a},{b})">
<div><div class="head"><span class="id">{esc(sc['id'])}</span><span class="meta">{a:.2f}-{b:.2f}s ({b - a:.1f}s) · {esc(sc['layout'])}</span>
<button class="ghost" onclick="play({a},{b})">Play</button></div>
<div class="row"><b>Visual</b>{esc(describe(sc['visual']))}</div>
<div class="row spoken"><b>Says</b>“{esc(words_between(words, a, b))}”</div>
{f'<div class="row"><b>Note</b>{esc(sc["note"])}</div>' if sc["note"] else ''}
<textarea data-scene="{esc(sc['id'])}" placeholder="Notes for {esc(sc['id'])}"></textarea></div></section>""")
    name = os.path.basename(paths["root"])
    page = (PAGE.replace("__TITLE__", html.escape(name))
            .replace("__SUMMARY__", f"{len(scenes)} scenes, {duration:.1f}s")
            .replace("__VIDEO__", f"../clean.mp4?v={bust}")
            .replace("__SCENES__", "".join(cards)))
    out = os.path.join(stills, "index.html")
    open(out, "w").write(page)
    return out


class Handler(SimpleHTTPRequestHandler):
    """Serves the project folder (with byte ranges so the video can seek) and receives feedback."""
    done = None
    feedback_path = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/feedback":
            self.send_error(404)
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        lines = ["# Storyboard feedback", ""]
        if data.get("overall"):
            lines += ["## Overall", data["overall"], ""]
        for sid, note in data.get("scenes", {}).items():
            lines += [f"## {sid}", note, ""]
        if len(lines) == 2:
            lines.append("Approved with no notes.")
        open(self.feedback_path, "w").write("\n".join(lines).strip() + "\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
        Handler.done.set()

    def do_GET(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path.split("?")[0])
        if not rng or not os.path.isfile(path):
            return super().do_GET()
        size = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        start = int(m.group(1)) if m and m.group(1) else 0
        end = min(int(m.group(2)) if m and m.group(2) else size - 1, size - 1)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--style")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--timeout", type=int, default=7200)
    a = ap.parse_args()
    paths = project_paths(a.project)
    page = build(paths, a.style)
    if a.build_only:
        print(f"Storyboard -> {page}")
        return
    Handler.done = threading.Event()
    Handler.feedback_path = os.path.join(paths["work"], "feedback.md")
    if os.path.exists(Handler.feedback_path):
        os.remove(Handler.feedback_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *x, **k: Handler(*x, directory=paths["work"], **k))
    url = f"http://127.0.0.1:{server.server_port}/storyboard/index.html"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Storyboard open at {url}\nWaiting for Submit (saves work/feedback.md)...", flush=True)
    if not a.no_open:
        webbrowser.open(url)
    got = Handler.done.wait(a.timeout)
    time.sleep(0.3)
    server.shutdown()
    if not got:
        sys.exit("No feedback before the timeout. Ask the user to paste notes from Copy feedback instead.")
    print(open(Handler.feedback_path).read())


if __name__ == "__main__":
    main()
