"""LinkedIn carousel PDF renderer (1080x1350). Usage: python3 tools/li_carousel.py <repo_root> out.html spec.json, then print out.html to PDF with Playwright (see RUNBOOK_LINKEDIN.md).
Slide types: cover, point, person, bullets, recap, cta. Wrap the accent phrase in [[ ]]."""
import base64, pathlib, sys
R = pathlib.Path(sys.argv[1]); T = R/'tools'
def b64(p): return base64.b64encode(p.read_bytes()).decode()
fonts = "".join(f"@font-face{{font-family:'{n}';font-weight:{w};src:url(data:font/woff2;base64,{b64(T/'fonts'/f)}) format('woff2');}}" for n,w,f in [
 ('Mont',600,'montserrat-latin-600-normal.woff2'),('Mont',700,'montserrat-latin-700-normal.woff2'),('Mont',800,'montserrat-latin-800-normal.woff2'),
 ('Noto',400,'noto-sans-latin-400-normal.woff2'),('Noto',500,'noto-sans-latin-500-normal.woff2')])
logo = b64(T/'logo-white.png'); cover = b64(T/'photos'/'strength-44.jpg')
craig = b64(T/'people'/'team-craig.jpg'); gray = b64(T/'people'/'team-gray.jpg')
N=0
def frame(i, inner, bg='#0E3B37'):
    return f"""<section style="background:{bg}"><img class="logo" src="data:image/png;base64,{logo}"><div class="num">{i}/{len(spec)}</div>{inner}<div class="foot">Vitelize Health &nbsp;·&nbsp; vitelizehealth.com</div></section>"""
def std(i, head, body, src=None, bg='#0E3B37'):
    s = f'<div class="src">{src}</div>' if src else ''
    return frame(i, f'<div class="mid"><h2>{head}</h2><p>{body}</p>{s}</div>', bg)
def person(i, label, name, role, pts, img):
    li = ''.join(f'<li>{p}</li>' for p in pts)
    return frame(i, f'<div class="mid"><div class="eye">{label}</div><img class="face" src="data:image/jpeg;base64,{img}"><h2 style="font-size:64px">{name}</h2><p class="role">{role}</p><ul>{li}</ul></div>')
import json
spec=json.load(open(sys.argv[3])); N=len(spec)
def hl(t): return t.replace('[[','<span>').replace(']]','</span>')
slides=[]
for i,sl in enumerate(spec,1):
    k=sl['type']
    if k=='cover':
        ph=b64(T/'photos'/sl.get('photo','strength-44.jpg'))
        slides.append(frame(i, f'<div class="coverimg" style="background-image:url(data:image/jpeg;base64,{ph})"></div><div class="cov"><div class="eye">{sl.get("eyebrow","CLINICAL BRIEFING FOR GYM OPERATORS")}</div><h1>{hl(sl["headline"])}</h1><p>{sl.get("body","")}</p></div>','#131313'))
    elif k=='point':
        slides.append(std(i, hl(sl['headline']), sl.get('body',''), sl.get('source')))
    elif k=='person':
        img=b64(T/'people'/sl['photo'])
        slides.append(person(i, sl['eyebrow'], sl['name'], sl['role'], sl.get('points',[]), img))
    elif k=='bullets':
        li=''.join(f'<li>{x}</li>' for x in sl['items'])
        slides.append(frame(i, f'<div class="mid"><h2>{hl(sl["headline"])}</h2><ul class="big">{li}</ul></div>'))
    elif k=='recap':
        li=''.join(f'<li>{x}</li>' for x in sl['items'])
        slides.append(frame(i, f'<div class="mid"><div class="eye">{sl.get("eyebrow","THE EVIDENCE, IN ONE LIST")}</div><ol>{li}</ol></div>','#131313'))
    elif k=='cta':
        slides.append(frame(i, f'<div class="mid"><h2>{hl(sl["headline"])}</h2><p>{sl.get("body","")}</p><p class="small">{sl.get("note","")}</p><div class="refs">{sl.get("sources","")}</div></div>'))
css = fonts + """
@page{size:1080px 1350px;margin:0}*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px}
section{width:1080px;height:1350px;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;break-inside:avoid;break-after:page;color:#fff;font-family:'Noto';page-break-after:always;padding:0 90px}
.logo{position:absolute;top:70px;left:90px;height:56px}
.num{position:absolute;top:80px;right:90px;font:600 30px 'Mont';color:#9FD9D2;letter-spacing:2px}
.foot{position:absolute;bottom:60px;left:90px;font:500 28px 'Noto';color:#9FD9D2}
.mid{position:relative}
h1{font:800 104px/1.04 'Mont';letter-spacing:-2px} h2{font:800 84px/1.08 'Mont';letter-spacing:-1.5px;margin-bottom:44px}
span{color:#F16422} p{font:400 42px/1.4 'Noto';color:#E6EBEA}
.src{margin-top:48px;font:500 30px 'Noto';color:#9FD9D2;border-left:6px solid #F16422;padding-left:22px}
.eye{font:700 30px 'Mont';letter-spacing:4px;color:#9FD9D2;margin-bottom:36px}
.coverimg{position:absolute;inset:0;background-size:cover;background-position:center;opacity:.45}
.cov{position:absolute;left:90px;right:90px;bottom:200px}.cov p{margin-top:36px}
.face{width:260px;height:260px;border-radius:50%;object-fit:cover;border:8px solid #F16422;margin-bottom:40px}
.role{font-size:36px;margin-top:-28px;margin-bottom:36px;color:#9FD9D2}
ul{list-style:none} ul li{break-inside:avoid;font:500 38px/1.35 'Noto';padding:14px 0 14px 46px;position:relative}
ul li:before{content:'';position:absolute;left:0;top:32px;width:22px;height:22px;background:#F16422;border-radius:4px}
ul.big li{font-size:40px}
ol{counter-reset:n;list-style:none} ol li{break-inside:avoid;counter-increment:n;font:600 44px/1.3 'Mont';padding:20px 0 20px 90px;position:relative;border-bottom:2px solid #2A5652}
ol li:before{content:counter(n);position:absolute;left:0;top:18px;width:62px;height:62px;border-radius:50%;background:#F16422;color:#131313;font:800 34px/62px 'Mont';text-align:center}
.small{font-size:34px;margin-top:30px;color:#9FD9D2}
.refs{margin-top:60px;font:400 24px/1.45 'Noto';color:#9FD9D2}
"""
html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(slides)}</body></html>"
pathlib.Path(sys.argv[2]).write_text(html)
