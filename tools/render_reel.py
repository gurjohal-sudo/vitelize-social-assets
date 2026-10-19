"""Vitelize Health Reel renderer: 1080 x 1920 MP4, 30 fps, captions on screen, silent audio track.

Usage: python3 render_reel.py reel_specs.json out_dir
Each spec:
  id        file stem, e.g. "2026-10-26"
  program   "peptide" | "glp1" | "both"   (selects the disclosure on the closing card)
  scenes    list, played in order. A closing CTA scene is appended if none is given.
    {"type":"hook", "eyebrow":"...", "headline":"text with [[accent phrase]]", "hold":3.5}
    {"type":"list", "title":"...", "items":["...", "..."], "mark":"check"|"cross", "hold":4.5}
    {"type":"stat", "value":"13M+", "label":"...", "source":"...", "hold":4.5}
    {"type":"cta",  "hold":4.5}
Content stays inside the Reels safe area (x 72 to 950, y 300 to 1500).
"""
import json, sys, html, re, pathlib, subprocess
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FPS = 30
W, H = 1080, 1920
DISCLOSURE = {
    "peptide": "Prescribed by licensed clinicians only where clinically appropriate. Compounded medications are not FDA-approved. Available in eligible U.S. states. Partner earnings are not guaranteed.",
    "glp1": "All therapy is prescribed by licensed clinicians only where clinically appropriate. Available in eligible U.S. states. Partner earnings are not guaranteed.",
    "both": "All therapy is prescribed by licensed clinicians only where clinically appropriate. Compounded medications are not FDA-approved. Available in eligible U.S. states.",
}
ORANGE, TEAL, TEAL_TXT, INK = "#F16422", "#36ACA0", "#2B8C82", "#131313"
CHECK = f'<svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="{TEAL_TXT}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M7.5 12.5l3 3 6-6.5"/></svg>'
CROSS = f'<svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="{ORANGE}" stroke-width="2.6" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7"/></svg>'

def ff(name, file, w):
    return f"@font-face{{font-family:'{name}';src:url('{(HERE/'fonts'/file).as_uri()}') format('woff2');font-weight:{w};}}"
FONTS = "".join([ff("Montserrat","montserrat-latin-600-normal.woff2",600), ff("Montserrat","montserrat-latin-700-normal.woff2",700),
                 ff("Montserrat","montserrat-latin-800-normal.woff2",800), ff("Noto Sans","noto-sans-latin-400-normal.woff2",400),
                 ff("Noto Sans","noto-sans-latin-500-normal.woff2",500)])

def accent(text):
    return re.sub(r"\[\[(.+?)\]\]", lambda m: f'<span style="color:{ORANGE}">{m.group(1)}</span>', html.escape(text))

def el(inner, t0, t1, style=""):
    return f'<div class="a" data-t0="{t0:.2f}" data-t1="{t1:.2f}" style="{style}">{inner}</div>'

def build(spec):
    scenes = list(spec["scenes"])
    if not any(s["type"] == "cta" for s in scenes):
        scenes.append({"type": "cta", "hold": 4.5})
    t = 0.0; parts = []
    for s in scenes:
        hold = float(s.get("hold", 4.0)); a, b = t, t + hold
        body = []
        if s["type"] == "hook":
            n = len(re.sub(r"\[\[|\]\]", "", s["headline"]))
            size = 108 if n < 45 else 96 if n < 70 else 84
            body.append(el(html.escape(s.get("eyebrow", "")), a + 0.1, b, f"font-family:Montserrat;font-weight:700;font-size:30px;letter-spacing:5px;color:{TEAL_TXT}"))
            body.append(el(accent(s["headline"]), a + 0.35, b, f"font-family:Montserrat;font-weight:800;font-size:{size}px;line-height:1.05;letter-spacing:-2px;color:{INK}"))
        elif s["type"] == "list":
            body.append(el(html.escape(s["title"]), a + 0.1, b, f"font-family:Montserrat;font-weight:800;font-size:64px;line-height:1.1;letter-spacing:-1px;color:{INK}"))
            icon = CROSS if s.get("mark") == "cross" else CHECK
            for i, item in enumerate(s["items"][:5]):
                body.append(el(f'{icon}<div>{html.escape(item)}</div>', a + 0.6 + 0.55 * i, b,
                               "display:flex;align-items:center;gap:26px;background:#E6EBEA;border-radius:20px;padding:30px 34px;font-family:Montserrat;font-weight:700;font-size:44px;line-height:1.2;color:#131313"))
        elif s["type"] == "stat":
            body.append(el(html.escape(s["value"]), a + 0.1, b, f"font-family:Montserrat;font-weight:800;font-size:260px;line-height:1;letter-spacing:-6px;color:{ORANGE}"))
            body.append(el(html.escape(s["label"]), a + 0.6, b, f"font-family:Montserrat;font-weight:700;font-size:52px;line-height:1.2;color:{INK}"))
            body.append(el(html.escape(s.get("source", "")), a + 1.0, b, "font-family:'Noto Sans';font-size:26px;line-height:1.4;color:#4A5352"))
        elif s["type"] == "cta":
            body.append(el(f'YOU KEEP THE FLOOR.<br><span style="color:{ORANGE}">WE CARRY THE MEDICINE.</span>', a + 0.1, b + 99,
                           "font-family:Montserrat;font-weight:700;font-size:34px;letter-spacing:5px;line-height:1.5;color:#FFFFFF"))
            body.append(el("Book a 15-minute partner call", a + 0.45, b + 99, "font-family:Montserrat;font-weight:800;font-size:84px;line-height:1.05;letter-spacing:-1px;color:#FFFFFF"))
            body.append(el("info@vitelizehealth.com", a + 0.8, b + 99, "font-family:Montserrat;font-weight:600;font-size:50px;color:#5CC7BB"))
            body.append(el(DISCLOSURE[spec.get("program", "both")], a + 1.1, b + 99, "font-family:'Noto Sans';font-size:26px;line-height:1.5;color:#B9C3C2;border-top:1px solid #3A4140;padding-top:28px"))
        bg = "#131313" if s["type"] == "cta" else "transparent"
        parts.append(f'<div class="scene" data-a="{a:.2f}" data-b="{b:.2f}" data-cta="{1 if s["type"]=="cta" else 0}" style="background:{bg}">'
                     f'<div style="position:absolute;left:72px;right:130px;top:330px;bottom:420px;display:flex;flex-direction:column;justify-content:center;gap:34px">{"".join(body)}</div></div>')
        t = b
    total = t
    doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}
*{{box-sizing:border-box}}body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#FFFFFF;font-family:'Noto Sans'}}
.scene{{position:absolute;inset:0;opacity:0}} .a{{opacity:0;will-change:transform,opacity}}</style></head><body>
<div style="position:absolute;left:0;right:0;top:0;height:16px;background:{ORANGE};z-index:5"></div>
<img id="logo" src="{(HERE/'logo.png').as_uri()}" style="position:absolute;left:72px;top:210px;width:330px;z-index:4">
<div id="bar" style="position:absolute;left:72px;top:290px;height:6px;width:0;background:{TEAL};border-radius:3px;z-index:4"></div>
{"".join(parts)}
<script>
const TOTAL={total:.3f};
function ease(x){{x=Math.min(1,Math.max(0,x));return 1-Math.pow(1-x,3);}}
function setTime(t){{
  document.querySelectorAll('.scene').forEach(s=>{{
    const a=+s.dataset.a,b=+s.dataset.b,cta=s.dataset.cta==='1';
    const fin=ease((t-a)/0.25), fout=cta?1:1-ease((t-(b-0.25))/0.25);
    s.style.opacity=(t>=a&&(cta||t<b))?Math.min(fin,fout):0;
  }});
  document.querySelectorAll('.a').forEach(e=>{{
    const p=ease((t-(+e.dataset.t0))/0.45);
    e.style.opacity=p; e.style.transform='translateY('+(48*(1-p))+'px)';
  }});
  document.getElementById('bar').style.width=(Math.min(1,t/TOTAL)*936)+'px';
  const onCta=[...document.querySelectorAll('.scene')].some(s=>s.dataset.cta==='1'&&t>=+s.dataset.a);
  document.getElementById('logo').style.filter=onCta?'brightness(0) invert(1)':'none';
}}
</script></body></html>'''
    return doc, total

def main(spec_path, out_dir):
    out = pathlib.Path(out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": W, "height": H})
        for spec in json.load(open(spec_path)):
            doc, total = build(spec)
            f = out / "_reel.html"; f.write_text(doc)
            pg.goto(f.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
            mp4 = out / f"{spec['id']}.mp4"
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                   "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                   "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(mp4)]
            ff_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            frames = int(round(total * FPS))
            for i in range(frames):
                pg.evaluate(f"setTime({i / FPS})")
                ff_proc.stdin.write(pg.screenshot(type="png"))
            ff_proc.stdin.close(); ff_proc.wait()
            pg.evaluate("setTime(2.8)"); pg.screenshot(path=str(out / f"{spec['id']}_cover.jpg"), type="jpeg", quality=90)
            print(spec["id"], f"{total:.1f}s", "ok" if ff_proc.returncode == 0 else "FFMPEG ERROR")
        br.close(); (out / "_reel.html").unlink(missing_ok=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
