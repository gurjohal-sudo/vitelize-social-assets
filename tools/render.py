"""Vitelize Health social visual renderer.

Usage: python3 render.py specs.json out_dir
specs.json is a list of objects:
  id         file stem, e.g. "2026-10-21"
  program    "peptide" | "glp1" | "both"
  eyebrow    short uppercase label, e.g. "PEPTIDE PARTNER PROGRAM"
  headline   main line; wrap the accent phrase in [[ ]], e.g. "They're already buying it. [[Just not from you.]]"
  body       one or two sentences (optional)
  tiles      up to 4 short labels (optional)
  stat       {"value": "13M+", "label": "...", "source": "..."} (optional, replaces tiles)
  columns    [{"title": "ON OUR MENU", "items": [...], "mark": "check"|"cross"}, ...] up to 2 (optional, replaces tiles)
  note       one short line under the columns (optional)
  tag        top-right pill text (optional, default "PARTNER PROGRAM")
  accent     hex (optional, default orange #F16422)
Output: <out_dir>/<id>.png at 1080 x 1350.
"""
import json, sys, html, re, pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
DISCLOSURE = {
    "peptide": "Prescribed by licensed clinicians only where clinically appropriate. Compounded medications are not FDA-approved. Available in eligible U.S. states. Partner earnings are not guaranteed.",
    "glp1": "All therapy is prescribed by licensed clinicians only where clinically appropriate. Available in eligible U.S. states. Partner earnings are not guaranteed.",
    "both": "All therapy is prescribed by licensed clinicians only where clinically appropriate. Compounded medications are not FDA-approved. Available in eligible U.S. states.",
}
CROSS = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#D9531A" stroke-width="2.6" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7"/></svg>'
CHECK = '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#2B8C82" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M7.5 12.5l3 3 6-6.5"/></svg>'

def font_face(name, file, weight):
    return f"@font-face{{font-family:'{name}';src:url('{(HERE/'fonts'/file).as_uri()}') format('woff2');font-weight:{weight};}}"

FONTS = "".join([
    font_face("Montserrat", "montserrat-latin-600-normal.woff2", 600),
    font_face("Montserrat", "montserrat-latin-700-normal.woff2", 700),
    font_face("Montserrat", "montserrat-latin-800-normal.woff2", 800),
    font_face("Noto Sans", "noto-sans-latin-400-normal.woff2", 400),
    font_face("Noto Sans", "noto-sans-latin-500-normal.woff2", 500),
])

def headline_html(text, accent):
    esc = html.escape(text)
    return re.sub(r"\[\[(.+?)\]\]", lambda m: f'<span style="color:{accent}">{m.group(1)}</span>', esc)

def headline_size(text, has_block):
    n = len(re.sub(r"\[\[|\]\]", "", text))
    if n <= 40: s = 100
    elif n <= 60: s = 92
    elif n <= 85: s = 80
    else: s = 68
    return s - (6 if has_block else 0)

def build(spec):
    accent = spec.get("accent", "#F16422")
    program = spec.get("program", "both")
    tiles = spec.get("tiles") or []
    stat = spec.get("stat")
    block = ""
    if stat:
        block = f'''<div style="background:#E6EBEA;border-radius:16px;padding:32px 36px;display:flex;align-items:center;gap:36px">
          <div style="font-family:Montserrat;font-weight:800;font-size:110px;line-height:1;color:{accent};white-space:nowrap">{html.escape(stat["value"])}</div>
          <div style="display:flex;flex-direction:column;gap:10px">
            <div style="font-family:Montserrat;font-weight:700;font-size:28px;line-height:1.3;color:#131313">{html.escape(stat["label"])}</div>
            <div style="font-size:17px;line-height:1.4;color:#4A5352">{html.escape(stat.get("source",""))}</div>
          </div></div>'''
    elif spec.get("columns"):
        cols = []
        for c in spec["columns"][:2]:
            mark = CROSS if c.get("mark") == "cross" else CHECK.replace('width="34" height="34"', 'width="30" height="30"')
            dark = c.get("mark") == "cross"
            rows = "".join(f'<div style="display:flex;align-items:center;gap:14px;padding:11px 0;border-top:1px solid {"#DCC9BF" if dark else "#CDD5D3"}">{mark}<div style="font-family:Montserrat;font-weight:700;font-size:25px;color:#131313;line-height:1.2">{html.escape(i)}</div></div>' for i in c["items"])
            cols.append(f'<div style="background:{"#FBEFE8" if dark else "#E6EBEA"};border-radius:16px;padding:24px 26px 14px;min-width:0"><div style="font-family:Montserrat;font-weight:700;font-size:19px;letter-spacing:3px;color:{"#B4441A" if dark else "#1E6E66"};margin-bottom:8px">{html.escape(c["title"])}</div>{rows}</div>')
        note = f'<div style="font-size:19px;line-height:1.45;color:#4A5352;margin-top:14px">{html.escape(spec["note"])}</div>' if spec.get("note") else ""
        block = f'<div><div style="display:grid;grid-template-columns:repeat({len(cols)},minmax(0,1fr));gap:16px">{"".join(cols)}</div>{note}</div>'
    elif tiles:
        cells = "".join(f'<div style="background:#E6EBEA;border-radius:14px;padding:24px 28px;display:flex;align-items:center;gap:18px">{CHECK}<div style="font-family:Montserrat;font-weight:700;font-size:28px;color:#131313">{html.escape(t)}</div></div>' for t in tiles[:4])
        block = f'<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px">{cells}</div>'
    body = f'<p style="margin:0;font-size:30px;line-height:1.45;color:#2E3433">{html.escape(spec["body"])}</p>' if spec.get("body") else ""
    hs = headline_size(spec["headline"], bool(block))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{FONTS}
body{{margin:0;width:1080px;height:1350px}}*{{box-sizing:border-box}}</style></head><body>
<div style="width:1080px;height:1350px;background:#FFFFFF;display:flex;flex-direction:column;font-family:'Noto Sans';color:#131313;overflow:hidden">
  <div style="height:14px;background:{accent}"></div>
  <div style="flex:1;padding:64px 72px 48px;display:flex;flex-direction:column;gap:40px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <img src="{(HERE/'logo.png').as_uri()}" style="width:300px;display:block">
      <div style="font-family:Montserrat;font-weight:700;font-size:18px;letter-spacing:3px;color:#2B8C82;border:2px solid #36ACA0;border-radius:40px;padding:10px 22px">{html.escape(spec.get("tag","PARTNER PROGRAM"))}</div>
    </div>
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:22px">
      <div style="font-family:Montserrat;font-weight:700;font-size:22px;letter-spacing:4px;color:#2B8C82">{html.escape(spec.get("eyebrow",""))}</div>
      <h1 style="margin:0;font-family:Montserrat;font-weight:800;font-size:{hs}px;line-height:1.04;letter-spacing:-2px">{headline_html(spec["headline"], accent)}</h1>
      {body}
    </div>
    {block}
  </div>
  <div style="background:#131313;padding:44px 72px 40px;display:flex;flex-direction:column;gap:22px">
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="font-family:Montserrat;font-weight:700;font-size:18px;letter-spacing:3px;color:#FFFFFF;white-space:nowrap">YOU KEEP THE FLOOR.  <span style="color:{accent}">WE CARRY THE MEDICINE.</span></div>
      <div style="font-family:Montserrat;font-weight:800;font-size:46px;color:#FFFFFF;letter-spacing:-0.5px;white-space:nowrap">Book a 15-minute partner call</div>
      <div style="font-family:Montserrat;font-weight:600;font-size:30px;color:#5CC7BB">info@vitelizehealth.com</div>
    </div>
    <div style="height:1px;background:#3A4140"></div>
    <div style="font-size:17px;line-height:1.5;color:#B9C3C2">{DISCLOSURE[program]}</div>
  </div>
</div></body></html>'''

def main(spec_path, out_dir):
    specs = json.load(open(spec_path))
    out = pathlib.Path(out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for s in specs:
            f = out / "_tmp.html"; f.write_text(build(s))
            pg.goto(f.as_uri()); pg.wait_for_load_state("networkidle")
            pg.evaluate("document.fonts.ready")
            overflow = pg.evaluate("document.body.scrollHeight > 1350")
            pg.screenshot(path=str(out / f"{s['id']}.png"), clip={"x":0,"y":0,"width":1080,"height":1350})
            print(s["id"], "OVERFLOW" if overflow else "ok")
        b.close()
        (out / "_tmp.html").unlink(missing_ok=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
