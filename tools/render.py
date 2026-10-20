"""Vitelize Health social visual renderer, v2: photography on every visual, rotating layouts and brand themes.

Usage: python3 render.py specs.json out_dir

specs.json is a list of objects:
  id         file stem; starts with the post date, e.g. "2026-10-21" or "2026-11-05_pm"
  program    "peptide" | "glp1" | "both" (selects the disclosure footer)
  eyebrow    short uppercase label
  headline   main line; wrap the accent phrase in [[ ]]
  body       one or two sentences (optional)
  tag        top-right pill text (optional, default "PARTNER PROGRAM")
  Content block, at most one (optional):
    tiles    up to 4 short labels
    stat     {"value": "13M+", "label": "...", "source": "..."}
    columns  [{"title": "...", "items": [...], "mark": "check"|"cross"}, ...] up to 2, plus optional "note"
    people   [{"photo": "team-craig.jpg", "name", "role", "points": [...]} ] 1 person, or 3 people with "line"
  Design controls (all optional; chosen automatically when omitted):
    layout   "fullbleed" | "splittop" | "splitside" | "framed"
    theme    "light" | "grey" | "ink" | "teal"     (fullbleed always uses ink or teal)
    band     "dark" | "orange" | "tone"            (footer call-to-action band)
    photo    a file from tools/photos/photos.json
    photo_tags  list of tags to choose the photo from
Output: <out_dir>/<id>.png at 1080 x 1350. Prints the layout, theme and photo used for each image.
Photo usage is logged in tools/photos/used.json so the same picture is not repeated in nearby posts.
"""
import json, sys, html, re, pathlib, hashlib, datetime
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PHOTOS = HERE / "photos"
LIB = json.load(open(PHOTOS / "photos.json"))
USED_PATH = PHOTOS / "used.json"

DISCLOSURE = {
    "peptide": "Prescribed by licensed clinicians only where clinically appropriate. Compounded medications are not FDA-approved. Available in eligible U.S. states. Partner earnings are not guaranteed.",
    "glp1": "All therapy is prescribed by licensed clinicians only where clinically appropriate. Available in eligible U.S. states. Partner earnings are not guaranteed.",
    "both": "All therapy is prescribed by licensed clinicians only where clinically appropriate. Compounded medications are not FDA-approved. Available in eligible U.S. states.",
}

# Brand palette: teal #36ACA0, orange #F16422, black #131313, grey #E6EBEA, white; secondary sky #AEE6F8, sage #B6E6AD.
THEMES = {
    "light": dict(bg="#FFFFFF", fg="#131313", sub="#3A4140", card="#E6EBEA", cardfg="#131313", line="#CDD5D3", accent="#F16422",
                  eyebrow="#1E6E66", tick="#2B8C82", pill="#36ACA0", logo="logo.png", xcard="#FBEFE8", xtitle="#B4441A", xmark="#D9531A", dark=False),
    "grey":  dict(bg="#E6EBEA", fg="#131313", sub="#3A4140", card="#FFFFFF", cardfg="#131313", line="#D5DCDB", accent="#F16422",
                  eyebrow="#1E6E66", tick="#2B8C82", pill="#36ACA0", logo="logo.png", xcard="#FFFFFF", xtitle="#B4441A", xmark="#D9531A", dark=False),
    "ink":   dict(bg="#131313", fg="#FFFFFF", sub="#C4CDCC", card="rgba(255,255,255,0.09)", cardfg="#FFFFFF", line="rgba(255,255,255,0.14)", accent="#F16422",
                  eyebrow="#5CC7BB", tick="#5CC7BB", pill="#5CC7BB", logo="logo-white.png", xcard="rgba(241,100,34,0.16)", xtitle="#F79A6E", xmark="#F79A6E", dark=True),
    "teal":  dict(bg="#0C3A36", fg="#FFFFFF", sub="#D2E6E3", card="rgba(255,255,255,0.10)", cardfg="#FFFFFF", line="rgba(255,255,255,0.16)", accent="#F16422",
                  eyebrow="#B6E6AD", tick="#B6E6AD", pill="#B6E6AD", logo="logo-white.png", xcard="rgba(241,100,34,0.18)", xtitle="#F8A57E", xmark="#F8A57E", dark=True),
}
BANDS = {
    "dark":   dict(bg="#131313", t1="#FFFFFF", t2="#FFFFFF", acc="#F16422", mail="#5CC7BB", disc="#B9C3C2", rule="#3A4140"),
    "orange": dict(bg="#F16422", t1="#131313", t2="#131313", acc="#FFFFFF", mail="#131313", disc="#3B1704", rule="rgba(19,19,19,0.25)"),
    "tone_ink":  dict(bg="#1E2122", t1="#FFFFFF", t2="#FFFFFF", acc="#F16422", mail="#5CC7BB", disc="#AEB8B7", rule="rgba(255,255,255,0.12)"),
    "tone_teal": dict(bg="#082A27", t1="#FFFFFF", t2="#FFFFFF", acc="#F16422", mail="#B6E6AD", disc="#B7CDCA", rule="rgba(255,255,255,0.12)"),
}
LAYOUTS = ["fullbleed", "splittop", "framed", "splitside"]
THEME_CYCLE = ["light", "teal", "grey", "ink", "light", "teal", "grey"]
CLINICIAN_OK = {"clinician-29.jpg"}  # clinician faces only; no identifiable patient
SENSITIVE = re.compile(r"glp-?1|semaglutide|tirzepatide|medication|peptide|prescri|weight|therap|compound|patient|dose", re.I)

def tick_svg(color, size):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M7.5 12.5l3 3 6-6.5"/></svg>'

def cross_svg(color, size):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.6" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8.5 8.5l7 7M15.5 8.5l-7 7"/></svg>'

def font_face(name, file, weight):
    return f"@font-face{{font-family:'{name}';src:url('{(HERE/'fonts'/file).as_uri()}') format('woff2');font-weight:{weight};}}"

FONTS = "".join([
    font_face("Montserrat", "montserrat-latin-600-normal.woff2", 600),
    font_face("Montserrat", "montserrat-latin-700-normal.woff2", 700),
    font_face("Montserrat", "montserrat-latin-800-normal.woff2", 800),
    font_face("Noto Sans", "noto-sans-latin-400-normal.woff2", 400),
    font_face("Noto Sans", "noto-sans-latin-500-normal.woff2", 500),
])
esc = html.escape

def headline_html(text, accent):
    return re.sub(r"\[\[(.+?)\]\]", lambda m: f'<span style="color:{accent}">{m.group(1)}</span>', esc(text))

def headline_size(text, layout, has_block, delta=0):
    n = len(re.sub(r"\[\[|\]\]", "", text))
    base = 96 if n <= 40 else 86 if n <= 60 else 74 if n <= 85 else 64
    cap = {"fullbleed": 88, "splittop": 78, "framed": 80, "splitside": 62}[layout]
    s = min(base, cap) - (6 if has_block else 0) - delta
    return max(s, 44)

# ---------- content blocks ----------
def block_html(spec, T, narrow=False):
    tiles, stat = spec.get("tiles") or [], spec.get("stat")
    if stat:
        return f'''<div style="background:{T['card']};border-radius:16px;padding:28px 32px;display:flex;align-items:center;gap:30px">
          <div style="font-family:Montserrat;font-weight:800;font-size:{84 if narrow else 100}px;line-height:1;color:{T['accent']};white-space:nowrap">{esc(stat["value"])}</div>
          <div style="display:flex;flex-direction:column;gap:8px;min-width:0">
            <div style="font-family:Montserrat;font-weight:700;font-size:{22 if narrow else 26}px;line-height:1.3;color:{T['cardfg']}">{esc(stat["label"])}</div>
            <div style="font-size:15px;line-height:1.4;color:{T['sub']}">{esc(stat.get("source",""))}</div></div></div>'''
    if spec.get("people"):
        return people_html(spec["people"], T)
    if spec.get("columns"):
        cols = []
        for c in spec["columns"][:2]:
            x = c.get("mark") == "cross"
            mark = cross_svg(T["xmark"], 28) if x else tick_svg(T["tick"], 28)
            rows = "".join(f'<div style="display:flex;align-items:center;gap:12px;padding:9px 0;border-top:1px solid {T["line"]}">{mark}<div style="font-family:Montserrat;font-weight:700;font-size:23px;color:{T["cardfg"]};line-height:1.2">{esc(i)}</div></div>' for i in c["items"])
            cols.append(f'<div style="background:{T["xcard"] if x else T["card"]};border-radius:16px;padding:20px 22px 12px;min-width:0"><div style="font-family:Montserrat;font-weight:700;font-size:17px;letter-spacing:3px;color:{T["xtitle"] if x else T["eyebrow"]};margin-bottom:6px">{esc(c["title"])}</div>{rows}</div>')
        note = f'<div style="font-size:17px;line-height:1.45;color:{T["sub"]};margin-top:12px">{esc(spec["note"])}</div>' if spec.get("note") else ""
        return f'<div><div style="display:grid;grid-template-columns:repeat({len(cols)},minmax(0,1fr));gap:14px">{"".join(cols)}</div>{note}</div>'
    if tiles:
        cols = 1 if narrow else 2
        cells = "".join(f'<div style="background:{T["card"]};border-radius:14px;padding:18px 22px;display:flex;align-items:center;gap:14px">{tick_svg(T["tick"], 30)}<div style="font-family:Montserrat;font-weight:700;font-size:24px;color:{T["cardfg"]};line-height:1.2">{esc(t)}</div></div>' for t in tiles[:4])
        return f'<div style="display:grid;grid-template-columns:repeat({cols},minmax(0,1fr));gap:12px">{cells}</div>'
    return ""

def people_html(ppl, T):
    if len(ppl) == 1:
        pp = ppl[0]
        pts = "".join(f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-top:1px solid {T["line"]}">{tick_svg(T["tick"], 24)}<div style="font-family:Montserrat;font-weight:700;font-size:22px;line-height:1.25;color:{T["cardfg"]}">{esc(t)}</div></div>' for t in pp.get("points", []))
        return (f'<div style="background:{T["card"]};border-radius:16px;padding:22px;display:flex;gap:24px;align-items:center">'
                f'<img src="{(HERE/"people"/pp["photo"]).as_uri()}" style="width:230px;height:230px;object-fit:cover;border-radius:12px;flex:0 0 auto">'
                f'<div style="min-width:0;flex:1"><div style="font-family:Montserrat;font-weight:800;font-size:32px;line-height:1.1;color:{T["cardfg"]}">{esc(pp["name"])}</div>'
                f'<div style="font-family:Montserrat;font-weight:700;font-size:18px;letter-spacing:2px;color:{T["eyebrow"]};margin:8px 0 8px">{esc(pp["role"].upper())}</div>{pts}</div></div>')
    cards = "".join(
        f'<div style="background:{T["card"]};border-radius:16px;padding:16px;min-width:0">'
        f'<img src="{(HERE/"people"/pp["photo"]).as_uri()}" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px;display:block">'
        f'<div style="font-family:Montserrat;font-weight:800;font-size:23px;line-height:1.15;margin-top:12px;color:{T["cardfg"]}">{esc(pp["name"])}</div>'
        f'<div style="font-family:Montserrat;font-weight:700;font-size:14px;letter-spacing:1.5px;color:{T["eyebrow"]};margin-top:6px">{esc(pp["role"].upper())}</div>'
        f'<div style="font-size:16px;line-height:1.4;color:{T["sub"]};margin-top:6px">{esc(pp.get("line",""))}</div></div>' for pp in ppl[:3])
    return f'<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px">{cards}</div>'

# ---------- shared pieces ----------
def header_html(spec, T, logo=None, pill=None):
    logo = logo or T["logo"]; pill = pill or T["pill"]
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;position:relative;z-index:2">'
            f'<img src="{(HERE/logo).as_uri()}" style="width:280px;display:block">'
            f'<div style="font-family:Montserrat;font-weight:700;font-size:17px;letter-spacing:3px;color:{pill};border:2px solid {pill};border-radius:40px;padding:9px 20px">{esc(spec.get("tag","PARTNER PROGRAM"))}</div></div>')

def text_html(spec, T, layout, has_block, delta, narrow=False):
    hs = headline_size(spec["headline"], layout, has_block, delta)
    body = f'<p style="margin:0;font-size:{25 if narrow else 28}px;line-height:1.45;color:{T["sub"]}">{esc(spec["body"])}</p>' if spec.get("body") else ""
    return (f'<div style="font-family:Montserrat;font-weight:700;font-size:20px;letter-spacing:4px;color:{T["eyebrow"]}">{esc(spec.get("eyebrow",""))}</div>'
            f'<h1 style="margin:0;font-family:Montserrat;font-weight:800;font-size:{hs}px;line-height:1.04;letter-spacing:-1.5px;color:{T["fg"]};text-wrap:balance">{headline_html(spec["headline"], T["accent"])}</h1>{body}')

def footer_html(program, B):
    return f'''<div style="background:{B['bg']};padding:32px 64px 30px;display:flex;flex-direction:column;gap:16px;flex:0 0 auto">
      <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:20px">
        <div style="display:flex;flex-direction:column;gap:8px">
          <div style="font-family:Montserrat;font-weight:700;font-size:16px;letter-spacing:3px;color:{B['t1']};white-space:nowrap">YOU KEEP THE FLOOR. <span style="color:{B['acc']}">WE CARRY THE MEDICINE.</span></div>
          <div style="font-family:Montserrat;font-weight:800;font-size:40px;color:{B['t2']};letter-spacing:-0.5px;white-space:nowrap">Book a 15-minute partner call</div></div>
        <div style="font-family:Montserrat;font-weight:700;font-size:23px;color:{B['mail']};white-space:nowrap;padding-bottom:6px">info@vitelizehealth.com</div></div>
      <div style="height:1px;background:{B['rule']}"></div>
      <div style="font-size:15px;line-height:1.5;color:{B['disc']}">{DISCLOSURE[program]}</div></div>'''

def img(photo, style):
    return f'<img src="{(PHOTOS/photo).as_uri()}" style="{style};object-fit:cover;filter:contrast(1.06) saturate(0.88) brightness(0.96)">'

def rgba(hex_, a):
    h = hex_.lstrip("#"); return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"

# ---------- layouts ----------
def build(spec, layout, theme, band, photo, delta=0):
    T = THEMES[theme]; B = BANDS[band]
    program = spec.get("program", "both")
    blk = block_html(spec, T, narrow=(layout == "splitside"))
    has_block = bool(blk)
    if layout == "fullbleed":
        bg = T["bg"]
        main = f'''<div class="main" style="position:relative;flex:1;overflow:hidden">
          {img(photo, "position:absolute;inset:0;width:100%;height:100%")}
          <div style="position:absolute;inset:0;background:linear-gradient(180deg,{rgba(bg,0.55)} 0%,{rgba(bg,0.10)} 22%,{rgba(bg,0.25)} 42%,{rgba(bg,0.88)} 64%,{bg} 80%)"></div>
          <div class="content" style="position:absolute;inset:0;padding:54px 64px 44px;display:flex;flex-direction:column;gap:20px">
            {header_html(spec, T)}<div style="flex:1"></div>{text_html(spec, T, layout, has_block, delta)}{blk}</div></div>'''
    elif layout == "splittop":
        ph = 470 if has_block else 560
        main = f'''<div class="main" style="flex:1;display:flex;flex-direction:column;overflow:hidden;background:{T['bg']}">
          <div style="position:relative;height:{ph}px;flex:0 0 auto">{img(photo, "position:absolute;inset:0;width:100%;height:100%")}
            <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(19,19,19,0.78) 0%,rgba(19,19,19,0.35) 22%,rgba(19,19,19,0) 42%)"></div>
            <div style="position:absolute;left:64px;right:64px;top:48px">{header_html(spec, T, logo="logo-white.png", pill="#FFFFFF")}</div>
            <div style="position:absolute;left:0;bottom:0;width:200px;height:10px;background:{T['accent']}"></div></div>
          <div class="content" style="flex:1;padding:40px 64px 40px;display:flex;flex-direction:column;gap:18px;justify-content:center">
            {text_html(spec, T, layout, has_block, delta)}{blk}</div></div>'''
    elif layout == "splitside":
        main = f'''<div class="main" style="flex:1;display:flex;overflow:hidden;background:{T['bg']}">
          <div style="position:relative;width:420px;flex:0 0 auto">{img(photo, "position:absolute;inset:0;width:100%;height:100%")}
            <div style="position:absolute;top:0;right:0;width:10px;height:220px;background:{T['accent']}"></div></div>
          <div class="content" style="flex:1;min-width:0;padding:52px 52px 40px;display:flex;flex-direction:column;gap:18px">
            <img src="{(HERE/T['logo']).as_uri()}" style="width:250px;display:block">
            <div style="font-family:Montserrat;font-weight:700;font-size:15px;letter-spacing:3px;color:{T['pill']};border:2px solid {T['pill']};border-radius:40px;padding:8px 16px;align-self:flex-start">{esc(spec.get("tag","PARTNER PROGRAM"))}</div>
            <div style="flex:1"></div>{text_html(spec, T, layout, has_block, delta, narrow=True)}{blk}</div></div>'''
    else:  # framed
        main = f'''<div class="main" style="flex:1;overflow:hidden;background:{T['bg']}">
          <div class="content" style="height:100%;padding:52px 64px 40px;display:flex;flex-direction:column;gap:18px">
            {header_html(spec, T)}
            <div style="position:relative;flex:1 1 auto;min-height:{240 if has_block else 360}px;border-radius:18px;overflow:hidden;margin:6px 0 8px">{img(photo, "position:absolute;inset:0;width:100%;height:100%")}
              <div style="position:absolute;left:0;top:0;bottom:0;width:10px;background:{T['accent']}"></div></div>
            {text_html(spec, T, layout, has_block, delta)}{blk}</div></div>'''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{FONTS}
body{{margin:0;width:1080px;height:1350px}}*{{box-sizing:border-box}}</style></head><body>
<div style="width:1080px;height:1350px;display:flex;flex-direction:column;font-family:'Noto Sans';overflow:hidden;background:{T['bg']}">
{main}{footer_html(program, B)}</div></body></html>'''

# ---------- automatic choices ----------
def day_index(spec_id):
    try:
        return datetime.date.fromisoformat(spec_id[:10]).toordinal()
    except ValueError:
        return int(hashlib.md5(spec_id.encode()).hexdigest(), 16) % 1000

def choose_design(spec):
    d = day_index(spec["id"]) + (3 if spec["id"].endswith("_pm") else 0)
    layout = spec.get("layout") or LAYOUTS[d % 4]
    theme = spec.get("theme") or THEME_CYCLE[d % 7]
    if layout == "fullbleed" and not THEMES[theme]["dark"]:
        theme = "teal" if d % 2 else "ink"
    if spec.get("people") and layout == "splitside":
        layout = "framed"
    band = spec.get("band") or (("tone_" + theme) if THEMES[theme]["dark"] else ("orange" if d % 2 == 0 else "dark"))
    return layout, theme, band

def photo_tags(spec):
    if spec.get("photo_tags"):
        return spec["photo_tags"]
    t = " ".join(str(spec.get(k, "")) for k in ("headline", "body", "eyebrow", "tag")).lower()
    if re.search(r"physician|clinician|doctor|medical|prescri|clinic\b|md\b", t): return ["clinician", "telehealth"]
    if re.search(r"physio|rehab|recovery", t): return ["physio"]
    if re.search(r"studio|pilates|yoga|barre", t): return ["studio"]
    if re.search(r"trainer|coach|staff|team|operator|owner|member", t): return ["coaching", "gym"]
    if re.search(r"muscle|strength|train|lift|glp", t): return ["strength", "training"]
    return ["gym", "equipment", "strength", "energy"]

def choose_photo(spec, used):
    if spec.get("photo"):
        return spec["photo"]
    tags = photo_tags(spec)
    text = " ".join(str(spec.get(k, "")) for k in ("headline", "body", "eyebrow"))
    sensitive = bool(SENSITIVE.search(text)) or spec.get("program") in ("peptide", "glp1")
    pool = [p for p in LIB if p["tag"] in tags and (not sensitive or not p["face"] or p["file"] in CLINICIAN_OK)]
    if not pool:
        pool = [p for p in LIB if not p["face"]]
    counts = {}
    for f in used.values():
        counts[f] = counts.get(f, 0) + 1
    recent = set(v for k, v in sorted(used.items())[-10:])
    h = int(hashlib.md5(spec["id"].encode()).hexdigest(), 16)
    pool.sort(key=lambda p: (p["file"] in recent, counts.get(p["file"], 0), int(hashlib.md5((spec["id"] + p["file"]).encode()).hexdigest(), 16) % 997))
    return pool[0]["file"]

def main(spec_path, out_dir):
    specs = json.load(open(spec_path))
    out = pathlib.Path(out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    used = json.load(open(USED_PATH)) if USED_PATH.exists() else {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for s in specs:
            layout, theme, band = choose_design(s)
            photo = choose_photo(s, {k: v for k, v in used.items() if k != s["id"]})
            tried, ok, delta = [], False, 0
            order = [layout] + [l for l in ["framed", "splitside", "fullbleed", "splittop"] if l != layout and not (s.get("people") and l == "splitside")]
            for lay in order:
                th = theme if (lay != "fullbleed" or THEMES[theme]["dark"]) else "teal"
                bd = band if (THEMES[th]["dark"] == THEMES[theme]["dark"]) else ("tone_" + th if THEMES[th]["dark"] else "dark")
                for delta in (0, 8, 16):
                    f = out / "_tmp.html"; f.write_text(build(s, lay, th, bd, photo, delta))
                    pg.goto(f.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
                    over = pg.evaluate("""() => { const c = document.querySelector('.content'); const m = document.querySelector('.main');
                        return c.scrollHeight > c.clientHeight + 1 || m.scrollHeight > m.clientHeight + 1 || document.body.scrollHeight > 1350; }""")
                    if not over:
                        ok = True; break
                tried.append(lay)
                if ok:
                    layout, theme, band = lay, th, bd; break
            pg.screenshot(path=str(out / f"{s['id']}.png"), clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            used[s["id"]] = photo
            print(s["id"], "ok" if ok else "OVERFLOW", layout, theme, band, photo)
        b.close()
        (out / "_tmp.html").unlink(missing_ok=True)
    json.dump(dict(sorted(used.items())), open(USED_PATH, "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
