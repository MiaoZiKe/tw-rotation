"""薪資續集 IG 輪播 8 張（1080×1350）：亮色 HUD，色票取自 scripts/social_theme.py。
用法：python render_carousel.py <輸出資料夾> [--no-xinhua]
  --no-xinhua：發文前查證信驊 561.7 仍只有單一來源時，用它重產（第 5 張改只放聯發科）。
輸出 JPEG（IG 只收 JPEG）並逐張跑重疊檢查，最後印「重疊檢查：程式 N 張 0 筆」。
"""
import sys, io
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from social_theme import logo_uri, TOKENS as T  # noqa: E402

XIN = "--no-xinhua" not in sys.argv
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;font-family:'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{T['ink']};
background:{T['bg']};background-image:linear-gradient(rgba(10,106,134,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(10,106,134,.05) 1px,transparent 1px);background-size:32px 32px;padding:36px 40px 40px;display:flex;flex-direction:column;gap:16px}}
.num{{font-family:Inter,sans-serif;font-variant-numeric:tabular-nums}}
.hd{{height:88px;display:flex;align-items:center;gap:18px;border-bottom:2px solid {T['accent']};flex:none}}
.hd img{{width:72px;height:72px;border-radius:17px}}
.pill{{background:#F5B73B;color:{T['ink']};font-weight:800;font-size:28px;padding:6px 18px;border-radius:12px}}
.ht{{font-size:52px;font-weight:800}}
.hdate{{margin-left:auto;font-size:34px;font-weight:600;color:{T['ink2']}}}
.card{{flex:1;background:{T['panel']};border:1.5px solid {T['line']};border-radius:10px;padding:48px 44px;display:flex;flex-direction:column;justify-content:center;gap:28px;position:relative;box-shadow:inset 0 1px 0 rgba(255,255,255,.9)}}
.big{{font-size:92px;font-weight:800;line-height:1.25}}
.mid{{font-size:60px;font-weight:800;line-height:1.3}}
.sub{{font-size:36px;font-weight:600;color:{T['ink2']};line-height:1.5}}
.acc{{color:{T['accent']}}}
.row{{display:flex;align-items:center;gap:20px;height:120px}}
.rk{{font-size:60px;font-weight:800;width:70px;color:{T['accent']}}}
.nm{{font-size:44px;font-weight:800;width:190px}}
.track{{flex:1;height:44px;background:{T['panel2']};border:1.5px solid {T['line']};border-radius:6px}}
.bar{{height:100%;background:{T['accent']};border-radius:5px}}
.bar.b2{{background:#7BB3C6}}
.val{{font-size:48px;font-weight:800;width:150px;text-align:right}}
.unit{{font-size:30px;font-weight:600;color:{T['ink3']}}}
.cmp{{display:flex;flex-direction:column;gap:12px}}
.cmp .t{{font-size:44px;font-weight:800}}
.line{{display:flex;align-items:center;gap:16px;height:72px}}
.line .l{{font-size:32px;font-weight:700;width:130px;color:{T['ink2']}}}
.line .track{{height:40px}}
.line .val{{font-size:44px;width:130px}}
.tag{{font-size:32px;font-weight:800;background:{T['accent']};color:#fff;padding:6px 20px;border-radius:12px;align-self:flex-start}}
.disc{{font-size:30px;font-weight:600;color:{T['ink3']};line-height:1.5}}
"""

def hd():
    return f'<div class="hd"><img src="{logo_uri()}"><div class="pill">薪資</div><div class="ht">薪水榜</div><div class="hdate num">114 年度</div></div>'

def row(i, name, v, mx, cls=""):
    return (f'<div class="row"><div class="rk num">{i}</div><div class="nm">{name}</div>'
            f'<div class="track"><div class="bar {cls}" style="width:{v/mx*100:.1f}%"></div></div>'
            f'<div class="val num">{v}</div></div>')

def cmpblock(name, avg, med, mx):
    return (f'<div class="cmp"><div class="t">{name}</div>'
            f'<div class="line"><div class="l">平均數</div><div class="track"><div class="bar" style="width:{avg/mx*100:.1f}%"></div></div><div class="val num">{avg}</div></div>'
            f'<div class="line"><div class="l">中位數</div><div class="track"><div class="bar b2" style="width:{med/mx*100:.1f}%"></div></div><div class="val num">{med}</div></div></div>')

s5 = cmpblock("聯發科", 446.5, 355.2, 600) + (cmpblock("信驊（上櫃）", 561.7, 453.7, 600) if XIN else "")
slides = [
 ('<div class="mid acc">114 年度非主管全時員工</div><div class="big">去年薪水最高的<br>公司，這次換誰？</div><div class="sub">證交所、櫃買中心 6/30 公布</div>'),
 ('<div class="mid">上市平均前三</div>' + row(1,"聯發科",446.5,500) + row(2,"祥碩",428.1,500) + row(3,"台積電",407.2,500) + '<div class="unit">單位：萬元</div>'),
 ('<div class="big">平均數，<br>不等於你的同事</div><div class="sub">平均數會被少數高薪拉高</div>'),
 ('<div class="mid">中位數看中間那位</div>' + row(1,"聯發科",355.2,400,"b2") + row(2,"祥碩",337.4,400,"b2") + row(3,"瑞昱",319.3,400,"b2") + row(4,"台積電",316.2,400,"b2") + '<div class="unit">單位：萬元</div>'),
 ('<div class="mid">同一家公司，兩個數字</div>' + s5 + '<div class="unit">單位：萬元</div>'),
 ('<div class="big">前十名全是半導體業</div><div class="sub">上市中位數前十名同一個產業</div>'),
 ('<div class="tag">轉折</div><div class="big">資金有沒有<br>流進這個族群？</div><div class="sub">薪水高 ≠ 股價漲，兩件事分開看</div>'),
 ('<div class="big">看完整資料：<br>點個人簡介的連結</div><div class="sub">族群資金流向</div><div class="disc">本內容為公開資料整理，不構成任何投資建議；投資有風險，請自行判斷。</div>'),
]

CHECK = """() => {
 const els=[...document.body.querySelectorAll('*')].filter(e=>{
   const t=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
   return t||e.classList.contains('bar')||e.tagName==='IMG'||e.classList.contains('track');});
 const R=els.map(e=>({e,r:e.getBoundingClientRect()}));
 let bad=[];
 for(let i=0;i<R.length;i++){const a=R[i];
  if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+a.e.className);
  if(a.e.scrollWidth>a.e.clientWidth+1&&a.e.clientWidth>0)bad.push('溢出:'+a.e.className);
  for(let j=i+1;j<R.length;j++){const b=R[j];
   if(a.e.contains(b.e)||b.e.contains(a.e))continue;
   const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
   if(w>1&&h>1)bad.push('重疊:'+a.e.className+'/'+b.e.className);}}
 return bad;}"""

total = 0
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=__import__("os").environ.get("CHROMIUM") or None)
    pg = b.new_page(viewport={"width": 1080, "height": 1350})
    for i, body in enumerate(slides, 1):
        pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{hd()}<div class='card'>{body}</div></body></html>")
        pg.wait_for_timeout(200)
        bad = pg.evaluate(CHECK)
        total += len(bad)
        print(i, "問題:", bad)
        png = pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        Image.open(io.BytesIO(png)).convert("RGB").save(OUT / f"{i}.jpg", quality=92)
    b.close()
print(f"重疊檢查：程式 {len(slides)} 張 {total} 筆")
