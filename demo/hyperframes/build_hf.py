"""Usage: python3 build_hf.py <project dir>   (the HyperFrames project made by `npx hyperframes init`; writes public/index.html and public/cards/)
Generate the HyperFrames talking-head-recut project for the demo: cards, caption track and the single master GSAP timeline.
Cards follow the skill's contract (scoped <style>, no <script>, no external URLs); the composition script is assembled here."""
import json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
PUB = ROOT / "public"
TIM = json.load(open(Path(__file__).resolve().parent / "timing.json"))
FPS, W, H = 30, 1080, 1920
DUR = 35.3667
q = lambda x: round(x * FPS) / FPS

BEAT = {b["id"]: b for b in TIM["beats"]}
def ws(b, i): return BEAT[b]["words"][i]["s"]
def we(b, i): return BEAT[b]["words"][i]["e"]

BG, INK = "#0E1116", "#F4F1EA"
A = ["#FFD166", "#FF5D73", "#3DDBB0", "#7FDBFF", "#A78BFA"]      # yellow, coral, mint, cyan, lilac

cards, tl = [], []

def sc(cid): return f'.card[data-card-id="{cid}"]'
def S(cid, eid): return f'{sc(cid)} #{eid}'
def css(cid, body): return body.replace("&", sc(cid))

def chars(text):
    out = []
    for w in text.split(" "):
        out.append('<span class="wd">' + "".join(f'<span class="char">{c}</span>' for c in w) + "</span>")
    return " ".join(out)

# ---- GSAP statement helpers (absolute seconds) ----
def T(x): return f"{q(x):.4f}"
def fi(sel, t, d=0.4, y=0, x=0, ease="power3.out"): tl.append(f"tl.fromTo('{sel}',{{opacity:0,y:{y},x:{x}}},{{opacity:1,y:0,x:0,duration:{d},ease:'{ease}'}},{T(t)});")
def fo(sel, t, d=0.3): tl.append(f"tl.to('{sel}',{{opacity:0,duration:{d},ease:'power2.in'}},{T(t)});")
def pop(sel, t, d=0.5): tl.append(f"tl.fromTo('{sel}',{{opacity:0,scale:0.55}},{{opacity:1,scale:1,duration:{d},ease:'back.out(1.8)'}},{T(t)});")
def grow(sel, t, w, d=0.5): tl.append(f"tl.fromTo('{sel}',{{width:0}},{{width:{w},duration:{d},ease:'power2.out'}},{T(t)});")
def chars_in(sel, t, st=0.035, d=0.35): tl.append(f"tl.from('{sel} .char',{{opacity:0,y:18,scale:0.8,duration:{d},ease:'power2.out',stagger:{st}}},{T(t)});")
def count(sel, t, a, b, d=0.8, f=0):
    tl.append(f"(function(){{var o={{v:{a}}};tl.to(o,{{v:{b},duration:{d},ease:'power2.out',onUpdate:function(){{var e=document.querySelector('{sel}');if(e)e.textContent=o.v.toFixed({f});}}}},{T(t)});}})();")
def show(host, t0, t1, fade=0.3):
    sel = f"{host} .card"
    tl.append(f"tl.fromTo('{sel}',{{opacity:0}},{{opacity:1,duration:{fade},ease:'power2.out'}},{T(t0)});")
    tl.append(f"tl.to('{sel}',{{opacity:0,duration:{fade},ease:'power2.in'}},{T(t1 - fade)});")

BASE = """
& .root{position:absolute;left:0;top:0;width:1080px;height:1920px;font-family:'Inter',ui-sans-serif,system-ui,sans-serif;color:#F4F1EA;}
& .mono{font-family:ui-monospace,'SF Mono',Menlo,monospace;}
& .char{display:inline-block}
& .wd{display:inline-block;white-space:nowrap}
& .abs{position:absolute}
"""
PIP_BG = """
& .bgfx{position:absolute;left:0;top:0;width:1080px;height:1920px;background:radial-gradient(circle at 18% 14%,rgba(255,209,102,.16),rgba(255,209,102,0) 42%),radial-gradient(circle at 92% 62%,rgba(61,219,176,.10),rgba(61,219,176,0) 46%),linear-gradient(180deg,#0E1116 0%,#131925 100%);}
& .dots{position:absolute;left:0;top:0;width:1080px;height:1920px;opacity:.5;background-image:radial-gradient(rgba(244,241,234,.07) 2px,transparent 2px);background-size:54px 54px;}
& .kick{position:absolute;left:400px;top:318px;width:560px;font-size:34px;font-weight:700;letter-spacing:5px;color:#FFD166;text-transform:uppercase}
"""

def card(cid, t0, t1, mode, body_html, body_css, track=2):
    html = f'<div class="card" data-card-id="{cid}"><style>{css(cid, BASE + (PIP_BG if mode == "pip" else "") + body_css)}</style>{body_html}</div>'
    (PUB / "cards" / f"{cid}.html").write_text(html, encoding="utf-8")
    cards.append(dict(id=cid, t0=t0, t1=t1, mode=mode, html=html, track=track))

# ============ card-01: hook (overlay) ============
c = "card-01"
body = f'''<div class="root">
 <div id="c1-t1" class="abs tag" style="left:120px;top:872px">NUMBERS</div>
 <div id="c1-t2" class="abs tag" style="left:670px;top:872px">VOICE</div>
 <div id="c1-t3" class="abs tag" style="left:120px;top:984px">FOOTAGE</div>
 <div id="c1-t4" class="abs tag" style="left:670px;top:984px">CAPTIONS</div>
 <div id="c1-pl" class="abs plaque" style="left:434px;top:872px"><span>ONE</span><span>TOOL</span></div>
 <div id="c1-st" class="abs strike" style="left:108px;top:858px"></div>
</div>'''
bcss = """
& .tag{width:290px;height:78px;line-height:78px;text-align:center;font-size:40px;font-weight:700;letter-spacing:1px;background:rgba(14,17,22,.9);border:4px solid #7FDBFF;border-radius:20px;color:#F4F1EA}
& .plaque{width:212px;height:190px;border-radius:24px;background:rgba(14,17,22,.94);border:5px solid #FFD166;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:56px;line-height:1.05;font-weight:700;color:#FFD166}
& .strike{width:800px;height:14px;border-radius:7px;background:#FF5D73;transform-origin:0 50%;transform:rotate(14deg);box-shadow:0 0 24px rgba(255,93,115,.7)}
"""
card(c, 0.1, 3.75, "overlay", body, bcss)
show(f"#h-{c}", 0.1, 3.75, 0.25)
for i, (eid, t) in enumerate([("c1-t1", ws(1, 2)), ("c1-t2", ws(1, 3)), ("c1-t3", ws(1, 5)), ("c1-t4", ws(1, 6))]):
    fi(S(c, eid), t, 0.4, y=20)
pop(S(c, "c1-pl"), ws(1, 4), 0.5)
tl.append(f"tl.to('{S(c,'c1-pl')}',{{x:'+=6',duration:0.05,repeat:9,yoyo:true,ease:'none'}},{T(ws(1,9)-0.1)});")
tl.append(f"tl.fromTo('{S(c,'c1-st')}',{{width:0,opacity:1}},{{width:800,duration:0.28,ease:'power3.in'}},{T(ws(1,10))});")
tl.append(f"tl.to('{sc(c)} .tag, {sc(c)} .plaque',{{opacity:0.45,duration:0.3}},{T(ws(1,10)+0.15)});")

# ============ card-02: four layers (pip) ============
c = "card-02"
bars = [("HOST", "HUMAN", 5, A[4]), ("REAL", "PROOF", 4, A[3]), ("AI", "ATMOSPHERE", 3, A[1]), ("CODE", "EXACT", 2, A[2])]
bhtml = "".join(f'<div id="c2-b{i}" class="abs bar" style="top:{650+i*122}px;border-color:{col}"><span class="bn" style="color:{col}">{n}</span><span class="bd">{d}</span></div>' for i, (n, d, _, col) in enumerate(bars))
body = f'''<div class="root"><div class="bgfx"></div><div class="dots"></div>
 <div class="abs kick">THE FRAME HAS</div>
 <div id="c2-n" class="abs big" style="left:400px;top:352px">0</div><div id="c2-l" class="abs lab" style="left:560px;top:420px">LAYERS</div>
 {bhtml}
 
</div>'''
bcss = """
& .big{font-size:230px;line-height:1;font-weight:700;color:#FFD166}
& .lab{font-size:78px;font-weight:700;letter-spacing:2px;color:#F4F1EA}
& .bar{left:120px;width:768px;height:104px;border:5px solid;border-radius:22px;background:rgba(20,26,38,.92);display:flex;align-items:center;justify-content:space-between;padding:0 32px;box-sizing:border-box}
& .bn{font-size:56px;font-weight:700}
& .bd{font-size:38px;font-weight:700;letter-spacing:2px;color:#A9B4C6}
& .dim{left:928px;top:650px;width:8px;height:0;background:#FFD166;border-radius:4px}
"""
card(c, 3.8, 9.5, "pip", body, bcss)
show(f"#h-{c}", 3.8, 9.5, 0.25)
fi(S(c, "c2-n"), ws(2, 3) - 0.1, 0.3); fi(S(c, "c2-l"), ws(2, 3) + 0.1, 0.3, x=30)
count(S(c, "c2-n"), ws(2, 3), 0, 4, 0.55)
for (n, d, wi, col), eid, t in zip(bars[::-1], ["c2-b3", "c2-b2", "c2-b1", "c2-b0"], [ws(2, 5), ws(2, 6), ws(2, 7), ws(2, 11)]):
    fi(S(c, eid), t - 0.15, 0.45, x=-80)

# ============ card-03: labels never drift (pip) ============
c = "card-03"
body = f'''<div class="root"><div class="bgfx"></div><div class="dots"></div>
 <div class="abs kick">LABELS</div><div id="c3-h" class="abs hh" style="left:400px;top:350px">NEVER DRIFT</div>
 <div id="c3-r1" class="abs row" style="top:660px"><div class="code mono">number(15)</div><div class="arr">&#8594;</div><div id="c3-v1" class="out num">0</div><div class="ok">&#10003;</div></div>
 <div id="c3-r2" class="abs row" style="top:828px"><div class="code mono">label("REEL")</div><div class="arr">&#8594;</div><div class="out chip">REEL</div><div class="ok">&#10003;</div></div>
 <div id="c3-r3" class="abs row" style="top:996px"><div class="code mono">axis(0, 35)</div><div class="arr">&#8594;</div><div class="out axis"><i></i><b>0</b><b style="right:0">35s</b></div><div class="ok">&#10003;</div></div>
</div>'''
bcss = """
& .hh{font-size:84px;font-weight:700;line-height:1.04;color:#F4F1EA;width:600px}
& .row{left:120px;width:768px;height:132px;display:flex;align-items:center;gap:20px}
& .code{width:330px;height:132px;line-height:132px;font-size:40px;color:#A9B4C6;background:rgba(20,26,38,.95);border:4px solid #2A3345;border-radius:20px;text-align:center;box-sizing:border-box}
& .arr{font-size:52px;color:#7FDBFF;width:44px;text-align:center}
& .out{width:290px;height:132px;display:flex;align-items:center;justify-content:center;position:relative}
& .num{font-size:112px;font-weight:700;color:#FFD166}
& .chip{font-size:60px;font-weight:700;color:#7FDBFF;background:rgba(127,219,255,.12);border:4px solid #7FDBFF;border-radius:20px;height:112px;box-sizing:border-box}
& .axis i{position:absolute;left:0;right:0;top:56px;height:6px;background:#7FDBFF;border-radius:3px}
& .axis b{position:absolute;top:78px;font-size:40px;color:#A9B4C6;font-weight:700}
& .ok{font-size:58px;color:#3DDBB0;font-weight:700;width:60px}
"""
card(c, 9.6, 13.4, "pip", body, bcss)
show(f"#h-{c}", 9.6, 13.4, 0.25)
fi(S(c, "c3-h"), 9.75, 0.4, x=30)
for eid, t in [("c3-r1", ws(3, 3)), ("c3-r2", ws(3, 5)), ("c3-r3", ws(3, 6) + 0.1)]:
    fi(S(c, eid), t - 0.2, 0.45, x=-60)
count(S(c, "c3-v1"), ws(3, 3) + 0.2, 0, 15, 0.8)

# ============ card-04: director, 15 formats, the plan (pip) ============
c = "card-04"
names = ["DATA STORY", "MANIM MATHS", "KINETIC TYPE", "DIAGRAM", "SCREEN DEMO", "CHAT", "VOX COLLAGE", "MAP", "ARCHIVAL DOC", "FLAT VECTOR", "HOST + B-ROLL", "TALKING HEAD", "NEWS BRIEF", "COMEDY SKETCH", "CARTOON"]
chip = "".join(f'<div id="c4-f{i}" class="abs fc{" me" if n == "HOST + B-ROLL" else ""}" style="left:{120+(i%3)*262}px;top:{790+(i//3)*84}px">{n}</div>' for i, n in enumerate(names))
plan = "".join(f'<div id="c4-p{i}" class="abs pl" style="left:{130+(i%2)*390}px;top:{720+(i//2)*118}px"><b>{i+1:02d}</b> {n}</div>' for i, n in enumerate(["HOOK", "CONTEXT", "BUILD", "BUILD", "BUILD", "TURN", "REVEAL", "PAYOFF"]))
body = f'''<div class="root"><div class="bgfx"></div><div class="dots"></div>
 <div id="c4-dir" class="abs dirw" style="left:400px;top:330px">THE DIRECTOR</div>
 <div id="c4-n" class="abs big4" style="left:400px;top:352px">0</div><div id="c4-l" class="abs lab4" style="left:660px;top:452px">FORMATS</div>
 {chip}
 <div id="c4-me" class="abs me2" style="left:120px;top:1218px;width:0">THIS VIDEO &#8593;</div>
 <div id="c4-pt" class="abs pt" style="left:400px;top:344px">THE PLAN</div>
 {plan}
</div>'''
bcss = """
& .dirw{font-size:88px;font-weight:700;color:#FFD166;line-height:1}
& .big4{font-size:210px;line-height:1;font-weight:700;color:#FFD166}
& .lab4{font-size:60px;font-weight:700;color:#F4F1EA;letter-spacing:2px}
& .fc{width:246px;height:66px;line-height:66px;text-align:center;font-size:25px;font-weight:700;letter-spacing:0;white-space:nowrap;color:#C5CEDD;background:rgba(20,26,38,.95);border:3px solid #2A3345;border-radius:16px}
& .fc.me{color:#0E1116;background:#FFD166;border-color:#FFD166}
& .me2{font-size:38px;font-weight:700;color:#FFD166;white-space:nowrap;overflow:hidden;letter-spacing:2px}
& .pt{font-size:84px;font-weight:700;color:#FFD166}
& .pl{width:370px;height:92px;line-height:92px;font-size:40px;white-space:nowrap;font-weight:700;color:#F4F1EA;background:rgba(20,26,38,.95);border-left:10px solid #3DDBB0;border-radius:14px;padding-left:22px;box-sizing:border-box}
& .pl b{color:#3DDBB0;margin-right:12px}
"""
card(c, 13.4, 19.0, "pip", body, bcss)
show(f"#h-{c}", 13.4, 19.0, 0.25)
fi(S(c, "c4-dir"), ws(4, 4), 0.4, x=30)
t15 = ws(4, 7)
tl.append(f"tl.to('{S(c,'c4-dir')}',{{opacity:0,duration:0.25}},{T(t15-0.1)});")
fi(S(c, "c4-n"), t15 - 0.05, 0.25); fi(S(c, "c4-l"), t15 + 0.1, 0.3, x=30)
count(S(c, "c4-n"), ws(4, 9) - 0.9, 0, 15, 0.9)
for i in range(15): fi(S(c, f"c4-f{i}"), ws(4, 7) + 0.05 * i, 0.3, y=14)
tl.append(f"tl.fromTo('{S(c,'c4-me')}',{{width:0}},{{width:330,duration:0.5,ease:'power2.out'}},{T(ws(4,10))});")
tp = ws(4, 12)
tl.append(f"tl.to('{sc(c)} .fc, {S(c,'c4-n')}, {S(c,'c4-l')}, {S(c,'c4-me')}',{{opacity:0,duration:0.3}},{T(tp-0.05)});")
fi(S(c, "c4-pt"), tp + 0.1, 0.35, x=30)
for i in range(8): fi(S(c, f"c4-p{i}"), tp + 0.2 + 0.06 * i, 0.3, x=-40)

# ============ card-05: you approve first (pip) ============
c = "card-05"
lock_c = '<svg viewBox="0 0 48 48" width="56" height="56"><rect x="11" y="22" width="26" height="19" rx="4" fill="#FFD166"/><path d="M17 22v-6a7 7 0 0 1 14 0v6" fill="none" stroke="#FFD166" stroke-width="5" stroke-linecap="round"/></svg>'
lock_o = '<svg viewBox="0 0 48 48" width="56" height="56"><rect x="11" y="22" width="26" height="19" rx="4" fill="#3DDBB0"/><path d="M17 22v-6a7 7 0 0 1 14 0" fill="none" stroke="#3DDBB0" stroke-width="5" stroke-linecap="round"/></svg>'
rows = ["PLAN", "AI IMAGES", "AI CLIPS", "HOST"]
rh = "".join(f'<div id="c5-r{i}" class="abs lrow" style="top:{640+i*118}px"><span class="lk"><u class="lc">{lock_c}</u><u class="lo">{lock_o}</u></span><span class="ln">{n}</span><span class="pr" id="c5-p{i}">PRICED</span><span class="st"><u class="sl">LOCKED</u><u class="so">OPEN</u></span></div>' for i, n in enumerate(rows))
body = f'''<div class="root"><div class="bgfx"></div><div class="dots"></div>
 <div class="abs kick">BEFORE ANY SPEND</div><div id="c5-h" class="abs hh5" style="left:400px;top:350px">YOU APPROVE FIRST</div>
 {rh}
 <div id="c5-btn" class="abs btn" style="left:200px;top:1140px"><span>YOU APPROVE</span></div>
</div>'''
bcss = """
& .hh5{font-size:72px;font-weight:700;line-height:1.05;width:560px}
& .lrow{left:120px;width:768px;height:100px;border:4px solid #2A3345;border-radius:20px;background:rgba(20,26,38,.95);display:flex;align-items:center;box-sizing:border-box;padding:0 26px;gap:18px}
& .lk{position:relative;width:56px;height:56px}
& .lk u,& .st u{position:absolute;left:0;top:0;text-decoration:none}
& .lo{opacity:0}
& .ln{font-size:44px;font-weight:700;width:250px}
& .pr{font-size:34px;font-weight:700;color:#A9B4C6;border:3px solid #3A465C;border-radius:30px;padding:6px 20px;opacity:0}
& .st{position:relative;margin-left:auto;width:170px;height:48px;font-size:36px;font-weight:700;text-align:right}
& .st u{right:0;left:auto;width:170px}
& .sl{color:#FF5D73}
& .so{color:#3DDBB0;opacity:0}
& .btn{width:620px;height:112px;border-radius:26px;border:5px solid #FFD166;display:flex;align-items:center;justify-content:center;font-size:54px;font-weight:700;color:#FFD166;opacity:0;background:rgba(20,26,38,.95)}
"""
card(c, 19.0, 23.1, "pip", body, bcss)
show(f"#h-{c}", 19.0, 23.1, 0.3)
fi(S(c, "c5-h"), 19.1, 0.4, x=30)
for i in range(4):
    fi(S(c, f"c5-r{i}"), ws(5, 0) + 0.1 * i, 0.4, x=-50)
    fi(S(c, f"c5-p{i}"), ws(5, 1) + 0.18 * i, 0.35, y=8)
fi(S(c, "c5-btn"), ws(5, 4), 0.45, y=26)
press = ws(5, 7)
tl.append(f"tl.to('{S(c,'c5-btn')}',{{backgroundColor:'#FFD166',color:'#0E1116',scale:0.96,duration:0.15,yoyo:true,repeat:1}},{T(press)});")
for i in range(4):
    tl.append(f"tl.to('{S(c,f'c5-r{i}')} .lc, {S(c,f'c5-r{i}')} .sl',{{opacity:0,duration:0.2}},{T(press+0.25+0.18*i)});")
    tl.append(f"tl.to('{S(c,f'c5-r{i}')} .lo, {S(c,f'c5-r{i}')} .so',{{opacity:1,duration:0.2}},{T(press+0.25+0.18*i)});")

# ============ card-06: how do you use it (overlay) ============
c = "card-06"
body = f'''<div class="root">
 <div id="c6-a" class="abs k1" style="left:90px;top:868px">{chars("HOW DO YOU")}</div>
 <div id="c6-b" class="abs k1" style="left:90px;top:996px">{chars("USE IT?")}</div>
</div>'''
bcss = """
& .k1{width:900px;text-align:center;font-size:116px;line-height:1;font-weight:700;color:#F4F1EA;text-shadow:0 6px 30px rgba(0,0,0,.85),0 0 4px rgba(0,0,0,.9)}
& #c6-b{color:#FFD166}
"""
card(c, 23.0, 24.0, "overlay", body, bcss)
show(f"#h-{c}", 23.0, 24.0, 0.2)
chars_in(S(c, "c6-a"), ws(6, 1) - 0.05, 0.03, 0.3)
chars_in(S(c, "c6-b"), ws(6, 4) - 0.05, 0.04, 0.3)

# ============ card-07: terminal (overlay) ============
c = "card-07"
def typed(eid, text): return f'<div id="{eid}" class="abs tl mono">{chars(text).replace("&nbsp;", " ")}</div>'
body = f'''<div class="root">
 <div id="c7-w" class="abs win" style="left:120px;top:850px"><div class="hd"><i style="background:#FF5D73"></i><i style="background:#FFD166"></i><i style="background:#3DDBB0"></i><span class="mono">agent</span></div></div>
 {typed("c7-l1", "github.com/").replace('class="abs tl mono"', 'class="abs tl mono" style="left:150px;top:944px"')}
 {typed("c7-l2", "muhammad-ahmed-ghani/").replace('class="abs tl mono"', 'class="abs tl mono" style="left:150px;top:996px"')}
 {typed("c7-l3", "hybrid-social-video-skill").replace('class="abs tl mono"', 'class="abs tl mono y" style="left:150px;top:1048px"')}
 <div id="c7-h" class="abs tl mono dm" style="left:150px;top:948px"># tell your agent</div>
 {typed("c7-cm", "> use hybrid-social-video").replace('class="abs tl mono"', 'class="abs tl mono y big" style="left:150px;top:1010px"')}
</div>'''
bcss = """
& .win{width:768px;height:262px;border-radius:24px;background:rgba(10,13,18,.95);border:4px solid #3DDBB0;box-shadow:0 12px 60px rgba(0,0,0,.6)}
& .hd{height:60px;border-bottom:3px solid #1E2736;position:relative}
& .hd i{position:absolute;top:21px;width:18px;height:18px;border-radius:9px}
& .hd i:nth-child(1){left:26px}& .hd i:nth-child(2){left:56px}& .hd i:nth-child(3){left:86px}
& .hd span{position:absolute;right:26px;top:12px;font-size:36px;color:#6B778C}
& .tl{font-size:42px;color:#F4F1EA;white-space:nowrap;line-height:1.1}
& .tl.y{color:#FFD166}
& .tl.big{font-size:44px}
& .dm{color:#7B879C;font-size:38px}
"""
card(c, 24.0, 30.3, "overlay", body, bcss)
show(f"#h-{c}", 24.0, 30.3, 0.25)
t0, t1 = ws(7, 0), we(7, 7)
d = t1 - t0
tl.append(f"tl.from('{S(c,'c7-w')}',{{opacity:0,y:30,duration:0.4,ease:'power3.out'}},{T(t0-0.1)});")
chars_in(S(c, "c7-l1"), t0, 0.04, 0.02); chars_in(S(c, "c7-l2"), t0 + d * 0.28, 0.04, 0.02); chars_in(S(c, "c7-l3"), t0 + d * 0.62, 0.035, 0.02)
tsw = ws(7, 8) + 0.1
tl.append(f"tl.to('{sc(c)} #c7-l1, {sc(c)} #c7-l2, {sc(c)} #c7-l3',{{opacity:0,duration:0.2}},{T(tsw)});")
fi(S(c, "c7-h"), tsw + 0.1, 0.3)
chars_in(S(c, "c7-cm"), ws(7, 10), 0.052, 0.02)
tl.append(f"tl.fromTo('{S(c,'c7-cm')}',{{opacity:0}},{{opacity:1,duration:0.01}},{T(ws(7,10)-0.02)});")

# ============ card-08: three steps + repo + Slate (overlay) ============
c = "card-08"
steps = [("1", "DESCRIBE THE REEL"), ("2", "APPROVE THE PLAN"), ("3", "GET THE VIDEO")]
sh = "".join(f'<div id="c8-s{i}" class="abs stp" style="top:{850+i*88}px"><b>{n}</b><span>{t}</span></div>' for i, (n, t) in enumerate(steps))
body = f'''<div class="root">
 {sh}
 <img id="c8-mc" class="abs" src="img/slate.png" style="left:836px;top:896px;width:220px;height:220px"/>
 <div id="c8-repo" class="abs repo"><div class="r1">hybrid-social-video-skill</div><div class="r2">github.com/muhammad-ahmed-ghani</div></div>
</div>'''
bcss = """
& .stp{left:120px;width:700px;height:78px;border-radius:20px;background:rgba(14,17,22,.92);border:4px solid #7FDBFF;display:flex;align-items:center;box-sizing:border-box;padding-left:18px;gap:22px;font-size:44px;font-weight:700}
& .stp b{width:50px;height:50px;border-radius:25px;background:#FFD166;color:#0E1116;display:flex;align-items:center;justify-content:center;font-size:34px}
& .repo{left:120px;top:1136px;width:768px;height:144px;border-radius:22px;background:rgba(14,17,22,.95);border:4px solid #FFD166;text-align:center;opacity:0}
& .r1{font-size:46px;font-weight:700;color:#FFD166;margin-top:18px}
& .r2{font-size:34px;font-weight:700;color:#A9B4C6;margin-top:8px}
"""
card(c, 30.4, 35.3, "overlay", body, bcss)
show(f"#h-{c}", 30.4, 35.3, 0.25)
for i, wi in enumerate([0, 3, 6]):
    fi(S(c, f"c8-s{i}"), ws(8, wi) - 0.05, 0.45, x=-90)
tl.append(f"tl.fromTo('{S(c,'c8-mc')}',{{opacity:0,scale:0.3,rotation:-14,transformOrigin:'50% 90%'}},{{opacity:1,scale:1,rotation:0,duration:0.7,ease:'back.out(1.9)'}},{T(ws(8,6))});")
tl.append(f"tl.to('{S(c,'c8-mc')}',{{y:-14,duration:0.6,yoyo:true,repeat:3,ease:'sine.inOut'}},{T(ws(8,6)+0.8)});")
tr = we(8, 8) + 0.05
fi(S(c, "c8-repo"), tr, 0.4, y=20)

# ============ captions: the host's own words, word-highlighted ============
def chunks(words):
    out, cur, ln = [], [], 0
    for w in words:
        if cur and (len(cur) >= 4 or ln + len(w["word"]) + 1 > 22):
            out.append(cur); cur, ln = [], 0
        cur.append(w); ln += len(w["word"]) + 1
        if re.search(r"[.?!]$", w["word"]) or (re.search(r"[,:;]$", w["word"]) and len(cur) >= 2):
            out.append(cur); cur, ln = [], 0
    if cur: out.append(cur)
    return out
allw = [w for b in TIM["beats"] for w in b["words"]]
ch = chunks(allw)
cap_html, cap_tl = [], []
for k, cu in enumerate(ch):
    t0c = cu[0]["s"] - 0.02
    t1c = (ch[k + 1][0]["s"] - 0.02) if k + 1 < len(ch) else cu[-1]["e"] + 0.35
    if cu[-1]["word"].endswith("video.") and k == len(ch) - 1: t1c = cu[-1]["e"] + 0.05
    spans = "".join(f'<span class="cw" id="cap{k}w{j}">{w["word"]}</span> ' for j, w in enumerate(cu))
    cap_html.append(f'<div id="cap{k}" class="cap"><span class="pill">{spans}</span></div>')
    cap_tl.append(f"tl.set('#cap{k}',{{visibility:'visible'}},{T(t0c)});tl.set('#cap{k}',{{visibility:'hidden'}},{T(t1c)});")
    for j, w in enumerate(cu):
        cap_tl.append(f"tl.set('#cap{k}w{j}',{{color:'#FFD166'}},{T(w['s'])});")
(PUB / "captions.html").write_text("\n".join(cap_html), encoding="utf-8")

# ============ video framing: overlay <-> pip, a slow push in overlay moments ============
FX, FY = 540, 480          # the host's face centre, in video-wrap pixels
PX, PY, PR = 206, 442, 150  # pill centre and radius on the canvas
SC = 0.55
CIRC = lambda r: f"circle({r}px at {FX}px {FY}px)"
vtl = [
    f"tl.set('#video-wrap',{{zIndex:1,transformOrigin:'{FX}px {FY}px',clipPath:'{CIRC(1700)}'}},0);",
    f"tl.fromTo('#bg-video',{{scale:1.0,transformOrigin:'50% 30%'}},{{scale:1.07,duration:3.5,ease:'none'}},0);",
    f"tl.set('#video-wrap',{{zIndex:20}},{T(3.55)});",
    f"tl.to('#video-wrap',{{x:{PX-FX},y:{PY-FY},scale:{SC},clipPath:'{CIRC(round(PR/SC))}',duration:0.65,ease:'power3.inOut'}},{T(3.55)});",
    f"tl.to('#bg-video',{{scale:1.0,duration:0.65,ease:'power3.inOut'}},{T(3.55)});",
    f"tl.fromTo('#pip-ring',{{opacity:0,scale:0.9}},{{opacity:1,scale:1,duration:0.5,ease:'power3.out'}},{T(4.0)});",
    f"tl.to('#pip-ring',{{opacity:0,duration:0.25}},{T(22.4)});",
    f"tl.to('#video-wrap',{{x:0,y:0,scale:1,clipPath:'{CIRC(1700)}',duration:0.6,ease:'power3.inOut'}},{T(22.55)});",
    f"tl.set('#video-wrap',{{zIndex:1}},{T(23.2)});",
    f"tl.fromTo('#bg-video',{{scale:1.0}},{{scale:1.06,duration:12.5,ease:'none'}},{T(23.2)});",
]

# ============ assemble index.html ============
fonts = """@font-face{font-family:'Inter';src:url('fonts/Inter-400-latin.woff2') format('woff2');font-weight:400;font-display:block}
@font-face{font-family:'Inter';src:url('fonts/Inter-700-latin.woff2') format('woff2');font-weight:700;font-display:block}"""
hosts = "\n".join(
    f'<div id="h-{cd["id"]}" class="card-host clip" data-card-id="{cd["id"]}" data-start="{T(cd["t0"])}" data-duration="{T(cd["t1"]-cd["t0"])}" data-track-index="{cd["track"]}" style="left:0;top:0;width:1080px;height:1920px;z-index:10">{cd["html"]}</div>'
    for cd in cards)
caps = (PUB / "captions.html").read_text()
index = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><style>
{fonts}
:root{{--bg:{BG};--text:{INK};--accent-0:{A[0]};--accent-1:{A[1]};--accent-2:{A[2]};--accent-3:{A[3]};--accent-4:{A[4]}}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#000;font-family:'Inter',ui-sans-serif,system-ui,sans-serif}}
#stage{{position:relative;width:100%;height:100%;overflow:hidden}}
.video-wrapper{{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:hidden;border-radius:0}}
.video-wrapper video{{width:100%;height:100%;object-fit:cover;display:block}}
#pip-ring{{position:absolute;left:{PX-PR-8}px;top:{PY-PR-8}px;width:{2*PR+16}px;height:{2*PR+16}px;border-radius:50%;border:7px solid #FFD166;box-shadow:0 0 0 7px rgba(255,209,102,.22),0 18px 50px rgba(0,0,0,.55);z-index:21;opacity:0;pointer-events:none}}
.card-host{{position:absolute;pointer-events:none;overflow:hidden}}
.card-host .card{{position:relative;width:100%;height:100%;overflow:hidden}}
#caps{{position:absolute;left:156px;top:1330px;width:768px;z-index:40;pointer-events:none}}
.cap{{position:absolute;left:0;top:0;width:768px;display:flex;justify-content:center;visibility:hidden}}
.pill{{background:rgba(10,13,18,.9);border:3px solid rgba(169,180,198,.5);border-radius:14px;padding:12px 20px;font-weight:700;font-size:48px;line-height:1.15;white-space:nowrap;color:#F4F1EA;text-align:center}}
</style></head><body>
<div id="stage" data-composition-id="talking-head-recut" data-start="0" data-duration="{DUR:.4f}" data-fps="30" data-width="1080" data-height="1920">
<div class="video-wrapper" id="video-wrap"><video id="bg-video" src="input-video.mp4" playsinline data-has-audio="true" data-start="0" data-duration="{DUR:.4f}" data-track-index="1"></video></div>
{hosts}
<div id="pip-ring"></div>
<div id="caps" class="clip" data-start="0" data-duration="{DUR:.4f}" data-track-index="3">{caps}</div>
<script src="vendor/gsap.min.js"></script>
<script>
(function(){{
var tl=window.gsap.timeline({{paused:true}});
{chr(10).join(vtl)}
{chr(10).join(tl)}
{chr(10).join(cap_tl)}
window.__timelines=window.__timelines||{{}};window.__timelines["talking-head-recut"]=tl;
}})();
</script></div></body></html>'''
(PUB / "index.html").write_text(index, encoding="utf-8")
json.dump({"schemaVersion": 3, "composition": {"fps": 30, "width": 1080, "height": 1920, "durationSeconds": DUR, "layout": "portrait", "themeId": "custom", "seed": 7},
           "videoTrack": {"sourcePath": "input-video.mp4", "startSec": 0, "endSec": DUR}, "subtitles": {"enabled": False},
           "cards": [{"id": cd["id"], "startSec": cd["t0"], "endSec": cd["t1"], "layout": cd["mode"]} for cd in cards]}, open(ROOT / "storyboard.json", "w"), indent=1)
print("cards:", len(cards), "| captions:", len(ch), "| index.html", round(len(index) / 1024), "KB")
