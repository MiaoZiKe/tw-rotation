"""D+ 共用元件（Andy 10-28 選定 D 雜誌編輯風後要「色彩更豐富協調」）。事件貼文／新聞圖卡共用。
規範：docs/marketing/social_unit/post_design_system.md「事件貼文 v5（D+）」。
用法：from lib_dplus import *（需設 CHROMIUM 環境變數）；page()/cover_head() 組版，render() 渲染並做重疊檢查。"""
import sys, io, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/"samples_1028/event_v2_lib"))
import lib as _l
from lib import Image, icon, bibi, sync_playwright
sheet = _l.sheet
FONT = "'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"

# ---- 色票：7 色（底、字深、主綠、珊瑚、霧藍、芥黃、灰字）；淡色底與細線是這 7 色的淡化，不另計 ----
P = dict(bg="#F7F3EA", ink="#17241E", green="#1E4D3B", coral="#D2583C", blue="#3F6F94", mustard="#E0A526", mu="#5F6B63",
         ln="#D6CFBD", t_green="#E1EDE4", t_coral="#FAE5DD", t_blue="#E0EBF3", t_mustard="#FBF0CC")
V = (f"--bg:{P['bg']};--ink:{P['ink']};--gr:{P['green']};--co:{P['coral']};--bl:{P['blue']};--my:{P['mustard']};--mu:{P['mu']};--ln:{P['ln']};"
     f"--tg:{P['t_green']};--tc:{P['t_coral']};--tb:{P['t_blue']};--tm:{P['t_mustard']};--s1:112px;--l1:120px")
# 語意：持平／主軸＝綠，升／負面事件＝珊瑚，降／中性資訊＝藍，重點數字底線／提示＝芥黃（對比低，只當底線、色塊，字用字深）
TXT_ON = dict(green="#fff", blue="#fff", coral=P["ink"], mustard=P["ink"])

BASE = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:FONTPLACE;color:var(--ink);background:var(--bg)}
.num{font-family:Inter,'DejaVu Sans',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.ser{font-family:'Liberation Serif','DejaVu Serif',serif;font-variant-numeric:lining-nums}
.row{display:flex;align-items:center}.col{display:flex;flex-direction:column}
.a{position:absolute}
.T1{font-size:var(--s1);line-height:var(--l1);font-weight:800}
.T2{font-size:56px;line-height:72px;font-weight:800}
.T3{font-size:36px;line-height:48px;font-weight:500}.T3b{font-size:36px;line-height:48px;font-weight:800}
.T4{font-size:28px;line-height:40px;font-weight:500}.T4b{font-size:28px;line-height:40px;font-weight:800}
.hr{position:absolute;left:64px;width:952px;height:2px;background:var(--ln)}
.hr.k{height:4px;background:var(--ink)}
.brand{position:absolute;left:64px;top:56px;color:var(--ink)}
.hdate{position:absolute;right:64px;top:60px;color:var(--mu)}
.kick{position:absolute;left:64px;top:144px;color:var(--gr);display:flex;align-items:center;gap:12px;letter-spacing:.08em}
.kick i{width:24px;height:4px;background:var(--my);display:block}
.head{position:absolute;left:64px;top:184px;width:952px;height:144px}
.u{color:var(--gr);border-bottom:6px solid var(--my)}
.zone{position:absolute;left:64px;top:368px;width:952px;height:808px;display:flex;flex-direction:column;justify-content:space-between}
.ft{position:absolute;left:64px;top:1216px;width:952px;height:96px;display:flex;align-items:center;gap:16px;color:var(--mu)}
.ft img{height:88px;object-fit:contain;flex:none}.ft .pg{margin-left:auto;color:var(--ink)}
.lab{color:var(--gr);font-weight:800;font-size:28px;line-height:40px;letter-spacing:.06em;display:flex;align-items:center;gap:16px}
.lab:after{content:"";flex:1;height:2px;background:var(--ln)}
.blk{border-radius:4px;padding:24px 32px}
.sbar{display:flex;gap:4px}.sbar i{display:block;height:100%;border-radius:4px}
.gl{position:absolute;top:0;bottom:0;width:2px;background:var(--ln)}
.fb{position:absolute;height:56px;border-radius:5px;display:flex;align-items:center;justify-content:center}
.dot{display:inline-block;width:20px;height:20px;border-radius:50%;flex:none}
""".replace("FONTPLACE", FONT)

CHECK = """() => {
 const els=[...document.body.querySelectorAll('*')].filter(e=>{
   if(e.dataset.bg)return false;
   const t=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
   return t||e.tagName==='IMG';});
 const R=els.map(e=>({e,r:e.getBoundingClientRect()}));let bad=[];const sizes={};
 const nm=e=>((e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)||'')+e.tagName+':'+(e.textContent||'').trim().slice(0,8);
 for(let i=0;i<R.length;i++){const a=R[i];
  if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+nm(a.e));
  if((a.r.left<63.5||a.r.right>1016.5)&&!a.e.closest('[data-free]'))bad.push('超出安全邊距64:'+nm(a.e));
  if(a.e.tagName!=='IMG'&&a.e.scrollWidth>a.e.clientWidth+1&&a.e.clientWidth>0&&!['svg','text','tspan'].includes(a.e.tagName))bad.push('溢出:'+nm(a.e));
  if(a.e.tagName!=='IMG'){const fs=parseFloat(getComputedStyle(a.e).fontSize);sizes[fs]=1;if(fs<28)bad.push('字太小:'+nm(a.e)+fs);}
  for(let j=i+1;j<R.length;j++){const b=R[j];
   if(a.e.contains(b.e)||b.e.contains(a.e))continue;
   const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
   if(w>1&&h>1)bad.push('重疊:'+nm(a.e)+'/'+nm(b.e));}}
 // 內容區（.zone）不可溢出，且其下所有文字／圖要在區內
 const z=document.querySelector('.zone');
 if(z){const zr=z.getBoundingClientRect();
  if(z.scrollHeight>z.clientHeight+1)bad.push('內容區溢出 '+z.scrollHeight+'>'+z.clientHeight);
  for(const {e,r} of R){if(!z.contains(e))continue;if(r.left<zr.left-1||r.right>zr.right+1||r.top<zr.top-1||r.bottom>zr.bottom+1)bad.push('跑出內容區:'+nm(e));}}
 // 格線：標 data-g 的區塊 left／top／width 必須是 8 的倍數
 for(const e of document.querySelectorAll('[data-g]')){const r=e.getBoundingClientRect();
  for(const [k,v] of [['left',r.left],['top',r.top],['width',r.width]]) if(Math.abs(v/8-Math.round(v/8))>.01)bad.push('格線:'+nm(e)+' '+k+'='+v);}
 return {bad,sizes:Object.keys(sizes).map(Number)};}"""

def cover_head(label, extra=""):
    """頁首：粗線＋哩股哩股＋右上標籤＋細線（封面與內頁共用，左上只留文字）"""
    return (f'<div class="hr k" style="top:40px"></div><div class="brand T3b">哩股哩股</div><div class="hdate T4b num">{label}</div>'
            f'<div class="hr" style="top:112px"></div>')

def page(label, kick, headline, content, idx, tot, asof, bib):
    """內頁：頁首／眉標（芥黃短線）／2 行標題／細線／內容區 808／頁尾（資料日、頁碼、比比）"""
    return (f'<body style="{V}">{cover_head(label)}<div class="kick T4b"><i></i>{kick}</div>'
            f'<div class="head T2" data-g=1>{headline}</div><div class="hr" style="top:344px"></div>'
            f'<div class="zone" data-g=1>{content}</div><div class="hr" style="top:1200px"></div>'
            f'<div class="ft T4"><span>{asof}</span><span class="pg num T4b">{idx} / {tot}</span>{bibi(bib, 88)}</div></body>')

def u(txt): return f'<span class="u num ser" style="font-weight:700"> {txt} </span>'   # 標題重點數字（深綠＋芥黃底線）
def chip(txt, col, cls="T4b"):   # 小色標：實心色塊＋對比字色
    return f'<span class="{cls} num" style="background:var(--{ {"green":"gr","coral":"co","blue":"bl","mustard":"my"}[col] });color:{TXT_ON[col]};padding:0 16px;border-radius:4px;display:inline-block">{txt}</span>'

def render(css, pages, out, tail=""):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); tot = 0; sizes = set(); names = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, html in enumerate(pages, 1):
            pg.set_content(f"<html><head><meta charset=utf-8><style>{BASE}{css}</style></head>{html}</html>")
            pg.wait_for_timeout(300); res = pg.evaluate(CHECK); tot += len(res["bad"]); sizes |= set(res["sizes"]); print(i, res["bad"])
            Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}))).convert("RGB").save(out/f"{i}.jpg", quality=93)
        b.close()
    print(f"重疊檢查：程式 {len(pages)} 張 {tot} 筆；字級 {sorted(sizes)}"); return tot
