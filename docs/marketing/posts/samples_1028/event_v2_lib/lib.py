"""事件貼文 v2 共用版型（法說／總經／ETF）。規範：docs/marketing/social_unit/post_design_system.md「事件貼文 v2」。
封面＝AI 寫實背景（無字、無 logo）＋ HTML 疊字；內頁＝柔和底色＋分區色塊。字全部由 Playwright 渲染，不讓 AI 生字。"""
import io, os, sys, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "scripts" / "social_theme.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
from social_theme import logo_uri  # noqa: E402

INK, INK2, INK3 = "#0F2233", "#33485B", "#566B7D"
RISE, FALL = "#C4142F", "#07784E"          # 紅漲綠跌（台股慣例，不動）
YEL = "#FFD23F"
# 類別：(標籤色, 頁底色, 強調深色)
KIND = {"台股": ("#D63A22", "#F3F0EA", "#A82C18"), "總經": ("#5145C8", "#F0EEFA", "#3F35A8"), "ETF": ("#0A7F77", "#EAF5F3", "#0A6F68")}
# 色塊（中性，不得與紅綠混淆）
TINT = dict(blue="#E2ECFA", amber="#FFF0D1", lilac="#ECE8FA", teal="#DDF1EE", white="#FFFFFF")
FONT = "'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"

ICON = {  # 24x24 線條圖示（stroke 由外層指定）
 "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
 "coin": '<circle cx="12" cy="12" r="9"/><path d="M9 9.5c0-1 1.3-1.8 3-1.8s3 .8 3 1.8-1.3 1.6-3 2-3 .9-3 2 1.3 1.8 3 1.8 3-.8 3-1.8M12 6v1.7M12 16.3V18"/>',
 "pct": '<path d="M19 5L5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
 "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
 "chip": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
 "factory": '<path d="M3 21V10l6 4V10l6 4V6h6v15z"/>',
 "quote": '<path d="M4 5h16v11H9l-5 4z"/>',
 "cal": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
 "down": '<path d="M3 5l7 8 4-4 7 9"/><path d="M15 18h6v-6"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 "flag": '<path d="M5 21V4h12l-2 4 2 4H5"/>',
}
def icon(name, color, size=56, bg=None):
    s = f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{ICON[name]}</svg>'
    return s

def b64(path, mx=None, fmt="PNG"):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
def bibi(name, h, cls="bibi"):
    return f'<img class="{cls}" style="height:{h}px" src="{b64(ROOT/"docs"/"anim"/"bibi_library"/name/"key.png")}">'
def bg_uri(name):
    return "data:image/jpeg;base64," + base64.b64encode((HERE / "bg" / f"{name}.jpg").read_bytes()).decode()

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;font-family:{FONT};color:{INK};position:relative;overflow:hidden}}
.num{{font-family:Inter,'DejaVu Sans',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
/* ---- 內頁 ---- */
body.in{{padding:48px 56px 0;display:flex;flex-direction:column;gap:28px}}
.hd{{display:flex;align-items:center;gap:16px;height:72px;flex:none}}
.hd img.lg{{width:64px;height:64px;border-radius:16px}}
.tagp{{color:#fff;font-weight:800;font-size:30px;padding:6px 20px;border-radius:999px}}
.hname{{font-size:34px;font-weight:700;color:{INK2}}}
.hdate{{margin-left:auto;font-size:30px;font-weight:700;color:{INK3}}}
.head{{font-size:64px;font-weight:800;line-height:1.28;flex:none}}
.y{{background:{YEL};padding:0 12px;border-radius:10px}}
.main{{flex:1;display:flex;flex-direction:column;gap:22px;min-height:0;justify-content:center}}
.ft{{height:128px;flex:none;display:flex;align-items:center;gap:16px;border-top:2px solid rgba(15,34,51,.12);margin:0 -0px}}
.ft .d{{font-size:28px;font-weight:600;color:{INK3}}}
.ft .pg{{margin-left:auto;font-size:28px;font-weight:700;color:{INK3}}}
.bibi{{object-fit:contain;flex:none}}
.blk{{border-radius:28px;padding:24px 34px;display:flex;flex-direction:column;gap:6px}}
.row{{display:flex;align-items:center;gap:28px}}
.ic{{width:88px;height:88px;border-radius:28px;background:#fff;display:flex;align-items:center;justify-content:center;flex:none;box-shadow:0 2px 0 rgba(15,34,51,.06)}}
.lab{{font-size:36px;font-weight:700;color:{INK2}}}
.kv{{font-size:100px;font-weight:800;line-height:1.1}}
.kv small{{font-size:42px;font-weight:700;color:{INK2};margin-left:10px;font-family:{FONT}}}
.chip{{display:inline-block;font-size:34px;font-weight:800;padding:4px 18px;border-radius:999px;background:#fff;align-self:flex-start}}
.up{{color:{RISE}}} .dn{{color:{FALL}}}
.chip.up{{background:#FDE9EC}} .chip.dn{{background:#DDF3E8}} .chip.nt{{background:#fff;color:{INK2}}}
.note{{font-size:34px;font-weight:600;color:{INK2};line-height:1.5}}
.unit{{font-size:30px;font-weight:600;color:{INK3};line-height:1.5}}
.main>.blk{{flex:1 1 auto;justify-content:center}} .main>.blk.s{{flex:none}} .two{{display:flex;gap:22px;flex:0 1 auto}} .two .blk{{flex:1 1 0;min-width:0;justify-content:center;padding:96px 34px;gap:16px}} .two .kv{{font-size:108px}} .two .lab{{font-size:40px}}
.track{{flex:1;height:44px;background:rgba(255,255,255,.8);border-radius:999px;position:relative}}
.bar{{position:absolute;left:0;top:0;height:100%;border-radius:999px}}
.val{{font-size:52px;font-weight:800;width:250px;text-align:right}}
.lb{{font-size:38px;font-weight:700;width:170px;color:{INK2}}}
.li{{display:flex;gap:26px;align-items:center}}
.li .t{{font-size:42px;font-weight:700;line-height:1.4}}
.nb{{width:64px;height:64px;border-radius:999px;color:#fff;font-weight:800;font-size:36px;display:flex;align-items:center;justify-content:center;flex:none}}
table{{width:100%;border-collapse:separate;border-spacing:0 14px}}
th{{font-size:30px;font-weight:700;color:{INK3};text-align:left;padding:0 24px}}
td{{background:#fff;font-size:40px;font-weight:700;padding:26px 24px;white-space:nowrap}}
td:first-child{{border-radius:20px 0 0 20px}} td:last-child{{border-radius:0 20px 20px 0}}
td.n{{font-size:46px;font-weight:800}}
/* ---- 封面 ---- */
body.cv{{background:#0B1626;color:#fff}}
.bgimg{{position:absolute;left:0;width:1080px;height:1620px}}
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,16,30,.50) 0%,rgba(8,16,30,.04) 18%,rgba(8,16,30,.22) 40%,rgba(8,16,30,.86) 60%,rgba(8,16,30,.96) 74%,rgba(8,16,30,.98) 100%)}}
.cvtop{{position:absolute;left:56px;top:52px;right:56px;display:flex;align-items:center;gap:18px}}
.cvtop img{{width:84px;height:84px;border-radius:20px}}
.brand{{font-size:38px;font-weight:800;text-shadow:0 2px 8px rgba(0,0,0,.5)}}
.cvtag{{font-size:34px;font-weight:800;padding:8px 26px;border-radius:12px;color:#fff}}
.cvdate{{margin-left:auto;font-size:32px;font-weight:700;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,.6)}}
.cvbody{{position:absolute;left:56px;right:56px;bottom:64px;display:flex;flex-direction:column;gap:26px}}
.cvt{{font-size:118px;font-weight:900;line-height:1.16;text-shadow:0 4px 18px rgba(0,0,0,.45)}}
.cvt .yy{{color:{YEL}}}
.hook{{font-size:56px;font-weight:700;line-height:1.35;color:#fff}}
.cvsub{{font-size:32px;font-weight:600;color:#C9D6E6;border-top:2px solid rgba(255,255,255,.28);padding-top:20px}}
"""

def logo(): return f'<img class="lg" src="{logo_uri()}">'
def page_in(kind, name, date, headline, body, idx, total, asof, bib=None, bh=100):
    c, bgc, _ = KIND[kind]
    f = f'<div class="ft"><span class="d">{asof}</span><span class="pg num">{idx} / {total}</span>{bibi(bib, bh) if bib else ""}</div>'
    return (f'<body class="in" style="background:{bgc}"><div class="hd">{logo()}<span class="tagp" style="background:{c}">{kind}</span>'
            f'<span class="hname">{name}</span><span class="hdate num">{date}</span></div><div class="head">{headline}</div><div class="main">{body}</div>{f}</body>')
def page_cover(kind, bg, title, hook, sub, date, top=0):
    c = KIND[kind][0]
    return (f'<body class="cv"><img class="bgimg" data-bg="1" style="top:{top}px" src="{bg_uri(bg)}"><div class="shade"></div>'
            f'<div class="cvtop"><img src="{logo_uri()}"><span class="brand">哩股哩股</span><span class="cvtag" style="background:{c}">{kind}</span><span class="cvdate num">{date}</span></div>'
            f'<div class="cvbody"><div class="cvt">{title}</div><div class="hook">{hook}</div><div class="cvsub">{sub}</div></div></body>')

CHECK = """() => {
 const els=[...document.body.querySelectorAll('*')].filter(e=>{
   if(e.dataset.bg||e.classList.contains('shade')||e.tagName==='path'||e.tagName==='svg'&&false)return false;
   const t=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
   return t||e.tagName==='IMG'||e.classList.contains('bar')||e.classList.contains('track')||false;});
 const R=els.map(e=>({e,r:e.getBoundingClientRect()}));let bad=[];
 const nm=e=>(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)+e.tagName;
 for(let i=0;i<R.length;i++){const a=R[i];
  if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+nm(a.e));
  if(a.e.scrollWidth>a.e.clientWidth+1&&a.e.clientWidth>0&&a.e.tagName!=='svg')bad.push('溢出:'+nm(a.e));
  const fs=parseFloat(getComputedStyle(a.e).fontSize); if(a.e.childNodes.length&&[...a.e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&fs<26)bad.push('字太小:'+nm(a.e)+fs);
  for(let j=i+1;j<R.length;j++){const b=R[j];
   if(a.e.contains(b.e)||b.e.contains(a.e))continue;
   const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
   if(w>1&&h>1)bad.push('重疊:'+nm(a.e)+'/'+nm(b.e));}}
 const m=document.querySelector('.main');if(m&&m.scrollHeight>m.clientHeight+1)bad.push('main 溢出 '+m.scrollHeight+'>'+m.clientHeight);
 const bt=document.querySelector('.cvbody');if(bt&&bt.getBoundingClientRect().top<420)bad.push('封面文字區過高 '+bt.getBoundingClientRect().top);
 return bad;}"""

def render(pages, out, names=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); tot = 0
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, html in enumerate(pages, 1):
            pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head>{html}</html>")
            pg.wait_for_timeout(250); bad = pg.evaluate(CHECK); tot += len(bad); print(i, bad)
            nm = (names[i-1] if names else f"{i}.jpg")
            Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}))).convert("RGB").save(out / nm, quality=92)
        b.close()
    print(f"重疊檢查：程式 {len(pages)} 張 {tot} 筆"); return tot

def sheet(dirp, files, dest, cols, w=360):
    ims = [Image.open(Path(dirp) / f).convert("RGB") for f in files]
    h = int(w * 1350 / 1080); rows = -(-len(ims) // cols)
    s = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * h + (rows + 1) * 12), "#DDDDDD")
    for k, im in enumerate(ims): s.paste(im.resize((w, h), Image.LANCZOS), (12 + (k % cols) * (w + 12), 12 + (k // cols) * (h + 12)))
    s.save(dest, quality=90)
