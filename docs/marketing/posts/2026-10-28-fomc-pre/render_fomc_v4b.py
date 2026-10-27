"""FOMC 前一天貼文 v4 風格比稿 D～G（Andy 10-28：「三套都做出來我再選，並且再做出更多不同風格我看看」）。
D 雜誌編輯風、E 扁平插畫資訊圖表風、F 日系手帳便利貼風、G 新聞快報卡片風；A～C 見 render_fomc_v4.py。
用法：CHROMIUM=... python render_fomc_v4b.py <輸出根目錄> [D|E|F|G ...]；各套輸出 <根>/v4_X/1.jpg～5.jpg＋sheet.jpg，
印「重疊檢查：程式 N 張 M 筆」與該套用到的字級。文字（法遵 2fcab0de）：第 2 張「12 月的定價則偏向升息」「這是期貨市場定價，不是本帳號的預測」、
第 5 張「常被討論的 3 個管道」「只說明傳導管道，不預測方向、非投資建議」一律保留；不呼叫 OpenAI，只用既有背景 fomc_day.jpg＋比比素材。"""
import sys, io, os, base64, math
from pathlib import Path
ROOT_DIR = next(p for p in Path(__file__).resolve().parents if (p/"docs/marketing/posts/samples_1028/event_v2_lib").exists())
sys.path.insert(0, str(ROOT_DIR/"docs/marketing/posts/samples_1028/event_v2_lib"))
import lib
from lib import Image, icon, bibi, sync_playwright

FONT = "'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
TOT = 5; ASOF = "資料日 10/27・CME FedWatch"
FOOT2 = "12 月升息機率各媒體引述 73%～80% 以上，圖取 73%。這是期貨市場定價，不是本帳號的預測"
BG_PATH = Path(lib.HERE)/"bg"/"fomc_day.jpg"
def crop(y0, h, w=1080):
    im = Image.open(BG_PATH).convert("RGB").crop((0, y0, 1080, y0+h))
    if w != 1080: im = im.resize((w, int(h*w/1080)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=88); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def pos(v): return (v-3.5)/0.25   # 利率換成「第幾格 0～3」

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
.bgimg{position:absolute;left:0;width:1080px}
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

# 4 級字級的共同寫法：T1 大數字／T2 標題／T3 內文／T4 註腳
def H(tag, style, cls="", inner="", g=False):
    return f'<{tag} class="{cls}" style="{style}"{" data-g=1" if g else ""}>{inner}</{tag}>'
def icobox(name, col, size=48): return icon(name, col, size)
SVGF = "font-family=\"Inter,'Noto Sans CJK TC',sans-serif\""
CH3 = [("coin", "美元", "反映利差預期，升降方向都可能"), ("pct", "美債殖利率", "常隨利率預期調整"), ("chart", "股票估值", "折現率隨利率預期改變")]
ITEMS4 = [("quote", "聲明措辭", "對通膨與就業的描述有沒有改"), ("flag", "投票結果", "有沒有人投反對票"),
          ("clock", "02:30 記者會", "對 12 月的說法"), ("chart", "本次沒有點陣圖", "不是經濟預測（SEP）會議")]
BIB = ["face_think", "calendar", "magnifier", "coins"]

# =====================================================================  D 雜誌編輯風
def build_D():
    V = "--bg:#F7F3EA;--ink:#17241E;--gr:#1E4D3B;--gd:#B88A2E;--mu:#5F6B63;--ln:#D6CFBD;--s1:112px;--l1:120px"
    css = """
.hr{position:absolute;left:64px;width:952px;height:2px;background:var(--ln)}
.hr.k{height:4px;background:var(--ink)}
.brand{position:absolute;left:64px;top:56px;color:var(--ink)}
.hdate{position:absolute;right:64px;top:60px;color:var(--mu)}
.kick{position:absolute;left:64px;top:144px;color:var(--gr);display:flex;align-items:center;gap:12px;letter-spacing:.08em}
.kick i{width:24px;height:4px;background:var(--gd);display:block}
.head{position:absolute;left:64px;top:184px;width:952px;height:144px}
.u{color:var(--gr);border-bottom:6px solid var(--gd)}
.zone{position:absolute;left:64px;top:368px;width:952px;height:808px;display:flex;flex-direction:column;justify-content:space-between}
.ft{position:absolute;left:64px;top:1216px;width:952px;height:96px;display:flex;align-items:center;gap:16px;color:var(--mu)}
.ft img{height:88px;object-fit:contain;flex:none}.ft .pg{margin-left:auto;color:var(--ink)}
.lab{color:var(--gr);font-weight:800;font-size:28px;line-height:40px;letter-spacing:.06em;display:flex;align-items:center;gap:16px}
.lab:after{content:"";flex:1;height:2px;background:var(--ln)}
.sbar{display:flex;gap:4px}.sbar i{display:block;height:100%;border-radius:4px}
.gl{position:absolute;top:0;bottom:0;width:2px;background:var(--ln)}
.fb{position:absolute;height:56px;border-radius:5px;display:flex;align-items:center;justify-content:center}
.cell{padding:0 32px 0 0}
"""
    def page(kick, headline, content, idx, bib):
        return (f'<body style="{V}"><div class="hr k" style="top:40px"></div><div class="brand T3b">哩股哩股</div><div class="hdate T4b num">10/28 事件前</div>'
                f'<div class="hr" style="top:112px"></div><div class="kick T4b"><i></i>{kick}</div>'
                f'<div class="head T2" data-g=1>{headline}</div><div class="hr" style="top:344px"></div>'
                f'<div class="zone" data-g=1>{content}</div><div class="hr" style="top:1200px"></div>'
                f'<div class="ft T4"><span>{ASOF}</span><span class="pg num T4b">{idx} / {TOT}</span>{bibi(bib, 88)}</div></body>')
    cover = (f'<body style="{V}"><div class="hr k" style="top:40px"></div><div class="brand T3b">哩股哩股</div><div class="hdate T4b num">10/28 事件前</div>'
             f'<div class="hr" style="top:112px"></div>'
             f'<img class="a" data-g=1 style="left:64px;top:144px;width:952px;height:560px;object-fit:cover;border-radius:4px" src="{crop(330, 560, 1904)}">'
             f'<div class="kick T4b" style="top:736px"><i></i>FOMC 前夕</div>'
             f'<div class="a T1" style="left:64px;top:784px;width:952px;height:240px">聯準會利率<br>明天凌晨<span class="u num ser" style="font-size:112px;font-weight:700"> 2 </span>點公布</div>'
             f'<div class="a T2" style="left:64px;top:1040px;color:var(--gr)">利率會變嗎？</div>'
             f'<div class="hr" style="top:1152px"></div>'
             f'<div class="a T3b num" style="left:64px;top:1176px;display:flex;gap:24px;align-items:center"><span>02:00 公布</span><span style="color:var(--gd)">／</span><span>02:30 記者會</span><span style="color:var(--gd)">／</span><span>目前 3.75～4.00%</span></div>'
             f'<div class="a T4" style="left:64px;top:1240px;color:var(--mu)">台灣時間 10/29（四）凌晨 02:00 公布</div></body>')
    # --- 2
    tk = ''.join(f'<span class="a T4 num" style="left:{t}%;top:8px;transform:translateX(-{t}%);color:var(--mu)">{t}%</span><i class="a" style="left:{t}%;top:0;width:2px;height:8px;background:var(--mu);transform:translateX(-{min(t,100)//100}px)"></i>' for t in (0, 25, 50, 75, 100))
    p2 = (f'<div class="col" style="gap:16px"><div class="lab">本次會議（10/28）</div>'
          f'<div class="row" style="height:128px"><div class="row" style="flex:1;gap:16px;align-items:baseline"><span class="ser T1" style="color:var(--gr);font-weight:700">91%</span><span class="T3b">持平</span></div>'
          f'<div style="width:2px;height:112px;background:var(--ln)"></div><div class="row" style="flex:1;gap:16px;padding-left:32px;align-items:baseline"><span class="ser T1" style="color:var(--gd);font-weight:700">9%</span><span class="T3b">升息</span></div></div>'
          f'<div class="sbar" style="height:48px"><i style="width:91%;background:var(--gr)"></i><i style="flex:1;background:var(--gd)"></i></div></div>'
          f'<div class="col" style="gap:16px"><div class="lab">12 月會議：升息機率</div>'
          f'<div class="row" style="height:128px;gap:16px;align-items:baseline"><span class="ser T1" style="color:var(--gd);font-weight:700">73%</span><span class="T3b">起</span></div>'
          f'<div style="position:relative;height:48px;background:#EBE5D6;border-radius:4px"><i style="position:absolute;left:0;top:0;height:100%;width:73%;background:var(--gd);border-radius:4px"></i></div>'
          f'<div style="position:relative;height:48px">{tk}</div></div>'
          f'<div class="T4" style="color:var(--mu);border-top:2px solid var(--ln);padding-top:16px">{FOOT2}</div>')
    # --- 3 區間列（浮動長條）
    PW = 624; Q = PW/3.0   # 3.50→4.25 共 3 格
    def rowbar(date, cap, lo, hi, col, tc, txt, dashed=False):
        x = (lo-3.5)/0.25*(PW/3); w = (hi-lo)/0.25*(PW/3)
        bar = (f'<div class="fb" style="left:{x:.0f}px;top:44px;width:{w:.0f}px;background:{"transparent" if dashed else col};'
               f'{"border:3px dashed var(--gr);" if dashed else ""}color:{tc}"><span class="T4b num">{txt}</span></div>')
        return (f'<div class="row" style="height:144px;position:relative"><div style="width:288px" class="col"><span class="T3b ser" style="font-weight:700">{date}</span><span class="T4" style="color:var(--mu)">{cap}</span></div>'
                f'<div style="position:relative;width:{PW}px;height:144px">{bar}</div></div>')
    gl = ''.join(f'<i class="gl" style="left:{288+k*PW/3:.0f}px"></i>' for k in range(4))
    ax = ''.join(f'<span class="a T4 num" style="left:{288+k*PW/3:.0f}px;top:0;transform:translateX(-50%);color:var(--mu)">{3.5+k*.25:.2f}</span>' for k in range(4))
    p3 = (f'<img style="width:952px;height:208px;object-fit:cover;border-radius:4px;flex:none" src="{crop(540, 208, 1904)}">'
          f'<div class="col" style="gap:8px"><div class="lab">聯邦基金利率目標區間（%）</div>'
          f'<div style="position:relative;height:432px">{gl}'
          + rowbar("2025/12", "降息 1 碼", 3.5, 3.75, "var(--gd)", "var(--ink)", "3.50–3.75%")
          + rowbar("2026/09", "升息 1 碼<br>（12 比 0）", 3.75, 4.0, "var(--gr)", "#fff", "3.75–4.00%")
          + rowbar("10/29 凌晨", "02:00 公布", 3.5, 4.25, "", "var(--gr)", "？", True).replace('<span class="T4b num">？</span>', '<span class="T2 ser">？</span>')
          + f'</div><div style="position:relative;height:40px">{ax}</div></div>')
    # --- 4 時間軸＋2×2
    tl = ('<svg width="952" height="136" viewBox="0 0 952 136"><line x1="64" x2="888" y1="20" y2="20" stroke="#D6CFBD" stroke-width="4"/>'
          '<circle cx="64" cy="20" r="14" fill="#1E4D3B"/><circle cx="476" cy="20" r="14" fill="#1E4D3B"/><circle cx="888" cy="20" r="12" fill="#F7F3EA" stroke="#B88A2E" stroke-width="4" stroke-dasharray="5 5"/>'
          + ''.join(f'<text x="{x}" y="84" text-anchor="{an}" class="num" {SVGF} font-size="36" font-weight="800" fill="#17241E">{a}</text><text x="{x}" y="124" text-anchor="{an}" {SVGF} font-size="28" font-weight="500" fill="#5F6B63">{b}</text>'
                    for x, an, a, b in ((64, "start", "02:00", "公布聲明"), (476, "middle", "02:30", "記者會"), (888, "end", "之後", "看反應"))) + '</svg>')
    def c4(n, t, s, br, bb): return (f'<div class="col" style="width:476px;height:288px;padding:{"32px 32px 0 0" if br else "32px 0 0 32px"};{"border-right:2px solid var(--ln);" if br else ""}{"border-bottom:2px solid var(--ln);" if bb else ""}">'
                                     f'<span class="ser T1" style="color:var(--gd);font-weight:700">0{n}</span><span class="T3b" style="margin-top:8px">{t}</span><span class="T4" style="color:var(--mu)">{s}</span></div>')
    p4 = (f'<div class="col" style="gap:16px"><div class="lab">時間軸</div>{tl}</div>'
          f'<div class="col" style="flex-wrap:wrap;height:592px;border-top:2px solid var(--ln)"><div class="row" style="flex-wrap:wrap;width:952px;height:592px;align-content:flex-start">'
          + c4(1, "聲明措辭", "對通膨與就業的描述有沒有改", True, True) + c4(2, "投票結果", "有沒有人投反對票", False, True)
          + c4(3, "02:30 記者會", "對 12 月的說法", True, False) + c4(4, "本次沒有點陣圖", "不是經濟預測（SEP）會議", False, False) + '</div></div>')
    # --- 5 三欄
    def col3(i, ic, t, s): return (f'<div class="col" style="width:296px;gap:8px;border-top:4px solid var(--ink);padding-top:24px"><span class="ser T2" style="color:var(--gd);font-weight:700">0{i}</span>'
                                   f'<div style="height:112px;margin-top:16px">{icon(ic, "#1E4D3B", 96)}</div><span class="T3b">{t}</span><span class="T3" style="color:var(--mu)">{s}</span></div>')
    p5 = (f'<div class="col" style="gap:8px"><div class="row" style="height:96px;background:var(--gr);border-radius:4px;justify-content:center"><span class="T2" style="color:#fff">利率預期變動</span></div>'
          f'<div class="row" style="justify-content:space-between;height:48px;padding:0 140px"><i style="border:16px solid transparent;border-top:24px solid var(--gd);border-bottom:0"></i><i style="border:16px solid transparent;border-top:24px solid var(--gd);border-bottom:0"></i><i style="border:16px solid transparent;border-top:24px solid var(--gd);border-bottom:0"></i></div>'
          f'<div class="row" style="justify-content:space-between;align-items:flex-start;height:408px">' + ''.join(col3(i+1, *CH3[i]) for i in range(3)) + '</div></div>'
          f'<div class="col" style="gap:8px;border-top:2px solid var(--ln);padding-top:24px"><span class="T3b">收藏這張，明天凌晨公布後回來對照</span><span class="T4" style="color:var(--mu)">只說明傳導管道，不預測方向、非投資建議</span></div>')
    return css, [cover,
        page("FOMC 前夕 No.2", '明天約<span class="u num ser" style="font-weight:700"> 9 成 </span>預期持平；<br>12 月的定價則偏向升息', p2, 2, BIB[0]),
        page("FOMC 前夕 No.3", '利率現在在<br><span class="u num ser" style="font-weight:700">3.75～4.00%</span>', p3, 3, BIB[1]),
        page("FOMC 前夕 No.4", '明天凌晨<br>看這<span class="u num ser" style="font-weight:700"> 4 </span>件事', p4, 4, BIB[2]),
        page("FOMC 前夕 No.5", '利率預期變動時，<br>常被討論的<span class="u num ser" style="font-weight:700"> 3 </span>個管道', p5, 5, BIB[3])]

# =====================================================================  E 扁平插畫資訊圖表風
def build_E():
    V = "--bg:#FFF6E5;--ink:#24305E;--bl:#3A7BFF;--or:#FF7A3D;--ye:#FFC83D;--mi:#28C7A0;--s1:96px;--l1:112px"
    css = """
.blob{position:absolute;border-radius:50%}
.brand{position:absolute;left:64px;top:56px}
.hdate{position:absolute;right:64px;top:56px;height:48px;padding:4px 24px;border-radius:999px;background:var(--ye)}
.head{position:absolute;left:64px;top:144px;width:952px;height:144px}
.hl{background:var(--ye);border-radius:16px;padding:0 12px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.card{position:absolute;left:64px;top:320px;width:952px;height:864px;background:#fff;border-radius:32px;padding:32px;box-shadow:0 8px 0 rgba(36,48,94,.12);display:flex;flex-direction:column}
.zone{flex:1;display:flex;flex-direction:column;justify-content:space-between;min-height:0}
.ft{position:absolute;left:64px;top:1224px;width:952px;height:48px;display:flex;align-items:center;color:var(--ink)}
.ft .pg{margin-left:auto}
.dot{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none}
.pbar{height:64px;background:rgba(36,48,94,.09);border-radius:5px;position:relative}
.pbar i{position:absolute;left:0;top:0;height:100%;border-radius:5px}
.tile{border-radius:24px;display:flex;align-items:center;gap:24px;padding:0 24px}
.wh{width:80px;height:80px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.cb{position:absolute;border-radius:5px;display:flex;align-items:center;justify-content:center}
"""
    blobs = ('<div class="blob" style="left:-120px;top:-120px;width:360px;height:360px;background:rgba(255,200,61,.30)"></div>'
             '<div class="blob" style="right:-140px;top:880px;width:400px;height:400px;background:rgba(40,199,160,.22)"></div>')
    def page(headline, content, idx):
        return (f'<body style="{V}">{blobs}<div class="brand T3b">哩股哩股</div><div class="hdate T4b num">10/28 事件前</div>'
                f'<div class="head T2" data-g=1>{headline}</div><div class="card" data-g=1><div class="zone">{content}</div></div>'
                f'<div class="ft T4"><span>{ASOF}</span><span class="pg num T4b">{idx} / {TOT}</span></div></body>')
    ch = lambda: ''
    cover = (f'<body style="{V}"><img class="bgimg" data-bg=1 style="top:-340px;height:1620px" src="data:image/jpeg;base64,{base64.b64encode(BG_PATH.read_bytes()).decode()}">'
             f'<div class="a" data-bg=1 style="inset:0;background:linear-gradient(180deg,rgba(255,246,229,0) 30%,rgba(255,246,229,.92) 52%,#FFF6E5 62%)"></div>'
             f'<div class="brand T3b" style="text-shadow:0 1px 6px rgba(255,255,255,.8)">哩股哩股</div><div class="hdate T4b num">10/28 事件前</div>'
             f'<div class="a T1" style="left:64px;top:720px;width:952px;height:224px">聯準會利率<br>明天凌晨<span class="hl num"> 2 點 </span>公布</div>'
             f'<div class="a T2" style="left:64px;top:968px;color:var(--bl)">利率會變嗎？</div>'
             f'<div class="a row" style="left:64px;top:1056px;gap:16px"><span class="T3b num" style="height:64px;padding:8px 24px;background:var(--ye);border-radius:32px">目前 3.75～4.00%</span></div>'
             f'<div class="a row" style="left:64px;top:1136px;gap:16px"><span class="T3b num" style="height:64px;padding:8px 24px;background:#fff;border-radius:32px">02:30 記者會</span></div>'
             f'<div class="a T4" style="left:64px;top:1224px">台灣時間 10/29（四）凌晨 02:00 公布</div>'
             f'<div class="a" style="right:64px;top:960px;width:288px;height:256px;display:flex;align-items:flex-end;justify-content:center">{bibi("tilt", 248)}</div></body>')
    # --- 2 甜甜圈（比比在圈中）
    r = 124; c = 2*math.pi*r; v = .91
    donut = (f'<div style="position:relative;width:304px;height:304px;flex:none"><svg width="304" height="304" viewBox="0 0 304 304"><g transform="rotate(-90 152 152)" fill="none" stroke-width="56">'
             f'<circle cx="152" cy="152" r="{r}" stroke="#3A7BFF" stroke-dasharray="{c*v-4:.1f} {c:.1f}"/><circle cx="152" cy="152" r="{r}" stroke="#FF7A3D" stroke-dasharray="{c*(1-v)-4:.1f} {c:.1f}" stroke-dashoffset="{-c*v:.1f}"/></g></svg>'
             f'<div class="a" style="left:60px;top:60px;width:184px;height:184px;display:flex;align-items:center;justify-content:center">{bibi("face_think", 168)}</div></div>')
    leg = lambda col, t, val, ic: (f'<div class="row" style="gap:16px"><div class="dot" style="background:{col}">{icon(ic, "#fff" if col == "var(--bl)" else "#24305E", 40)}</div><span class="T3b" style="flex:1">{t}</span><span class="T1 num">{val}</span></div>')
    tk = ''.join(f'<span class="a T4 num" style="left:{t}%;top:0;transform:translateX(-{t}%)">{t}%</span>' for t in (0, 25, 50, 75, 100))
    p2 = (f'<div class="row" style="gap:32px"><div class="col" style="gap:8px"><span class="T3b">本次會議</span>{donut}</div><div class="col" style="flex:1;gap:48px;padding-top:40px">{leg("var(--bl)", "持平", "91%", "target")}{leg("var(--or)", "升息", "9%", "chart")}</div></div>'
          f'<div class="col" style="gap:16px"><div class="row" style="gap:16px"><div class="dot" style="background:var(--ye)">{icon("cal", "#24305E", 40)}</div><span class="T3b" style="flex:1">12 月會議：升息機率</span><span class="T1 num" style="color:var(--or)">73%起</span></div>'
          f'<div class="pbar"><i style="width:73%;background:var(--or)"></i></div><div style="position:relative;height:40px">{tk}</div></div>'
          f'<div class="T4" style="border-top:2px solid rgba(36,48,94,.14);padding-top:16px">{FOOT2}</div>')
    # --- 3 階梯＋比比站在階梯上
    PH = 570; sc = PH/0.75
    def y(val): return (4.25-val)*sc
    grid = ''.join(f'<i class="a" style="left:112px;width:776px;top:{y(g):.0f}px;height:2px;background:rgba(36,48,94,.14)"></i><span class="a T4 num" style="left:0;width:96px;text-align:right;top:{y(g)-20:.0f}px">{g:.2f}</span>' for g in (3.5, 3.75, 4.0, 4.25))
    def col(x, lo, hi, bgc, tc, txt):
        return (f'<div class="cb" style="left:{x}px;top:{y(hi):.0f}px;width:232px;height:{(hi-lo)*sc:.0f}px;background:{bgc};color:{tc}"><span class="T4b num">{txt}</span></div>')
    xl = lambda x, d, s: (f'<div class="a col" style="left:{x-16}px;top:{PH+16}px;width:264px;align-items:center;text-align:center"><span class="T3b num">{d}</span><span class="T4">{s}</span></div>')
    chart = (f'<div style="position:relative;height:{PH+144}px">{grid}'
             + col(112, 3.5, 3.75, "var(--ye)", "var(--ink)", "3.50–3.75%") + col(384, 3.75, 4.0, "var(--or)", "var(--ink)", "3.75–4.00%")
             + f'<div class="cb" style="left:656px;top:0;width:232px;height:{PH}px;border:4px dashed var(--bl);color:var(--bl)"><span class="T1">？</span></div>'
             + f'<div class="a" style="left:384px;top:{y(4.0)-176:.0f}px;width:232px;height:176px;display:flex;align-items:flex-end;justify-content:center">{bibi("point_r", 168)}</div>'
             + xl(112, "2025/12", "降息 1 碼") + xl(384, "2026/09", "升息 1 碼<br>（12 比 0）") + xl(656, "10/29 凌晨", "02:00 公布") + '</div>')
    p3 = f'<span class="T3b">聯邦基金利率目標區間（%）</span>{chart}'
    # --- 4 路線＋2×2
    lane = ('<div style="position:relative;height:312px"><i class="a" style="left:80px;width:736px;top:196px;height:8px;border-radius:4px;background:rgba(36,48,94,.18)"></i>'
            + ''.join(f'<div class="a dot" style="left:{x-28}px;top:176px;width:56px;height:56px;background:{bg};{b}"></div>' for x, bg, b in ((148, "var(--bl)", ""), (444, "var(--or)", ""), (740, "#fff", "border:6px dashed var(--mi)")))
            + f'<div class="a" style="left:344px;top:8px;width:200px;height:160px;display:flex;align-items:flex-end;justify-content:center">{bibi("magnifier", 152)}</div>'
            + ''.join(f'<div class="a col" style="left:{x-100}px;top:240px;width:200px;align-items:center"><span class="T3b num">{a}</span><span class="T4">{b}</span></div>' for x, a, b in ((148, "02:00", "公布聲明"), (444, "02:30", "記者會"), (740, "之後", "看反應")))
            + '</div>')
    def t4(i, ic, bg, tc, t, s): return (f'<div class="tile" style="width:436px;height:200px;background:{bg};color:{tc};position:relative;gap:16px"><div class="wh" style="width:64px;height:64px">{icon(ic, "#24305E", 40)}</div><div class="col" style="width:268px"><span class="T3b">{t}</span><span class="T4">{s}</span></div>'
                                         f'<span class="a T4b num" style="right:16px;top:16px;width:40px;height:40px;border-radius:50%;background:#fff;color:#24305E;display:flex;align-items:center;justify-content:center">{i}</span></div>')
    p4 = (lane + '<div class="row" style="flex-wrap:wrap;gap:16px;width:888px">'
          + t4(1, "quote", "var(--ye)", "var(--ink)", "聲明措辭", "對通膨與就業的描述有沒有改") + t4(2, "flag", "var(--mi)", "var(--ink)", "投票結果", "有沒有人投反對票")
          + t4(3, "clock", "var(--bl)", "#fff", "02:30 記者會", "對 12 月的說法") + t4(4, "chart", "var(--or)", "var(--ink)", "本次沒有點陣圖", "不是經濟預測<br>（SEP）會議") + '</div>')
    # --- 5 中心輻射（比比＝中心）
    def chan(ic, bg, t, s, pos_): return (f'<div class="tile chan {pos_}" style="flex:1;background:{bg};position:relative"><div class="wh">{icon(ic, "#24305E", 44)}</div><div class="col"><span class="T2">{t}</span><span class="T4">{s}</span></div></div>')
    p5 = ('<div class="row" style="height:632px;align-items:stretch"><div class="col" style="width:264px;align-items:center;justify-content:center;gap:16px;flex:none">'
          f'<div style="width:264px;height:264px;border-radius:50%;background:var(--bl);display:flex;align-items:center;justify-content:center">{bibi("coins", 176)}</div>'
          '<span class="T3b" style="background:var(--ye);border-radius:24px;padding:0 20px;white-space:nowrap">利率預期變動</span></div>'
          '<div class="col rows" style="flex:1;gap:24px;padding-left:56px;position:relative">'
          + chan("coin", "var(--mi)", CH3[0][1], CH3[0][2], "f") + chan("pct", "var(--ye)", CH3[1][1], CH3[1][2], "m") + chan("chart", "var(--or)", CH3[2][1], CH3[2][2], "l") + '</div></div>'
          '<div class="col" style="gap:8px;border-top:2px solid rgba(36,48,94,.14);padding-top:24px"><span class="T3b">收藏這張，明天凌晨公布後回來對照</span><span class="T4">只說明傳導管道，不預測方向、非投資建議</span></div>')
    css += """
.chan:before{content:"";position:absolute;left:-56px;top:calc(50% - 3px);width:56px;height:6px;background:rgba(36,48,94,.25);border-radius:3px}
.chan:after{content:"";position:absolute;left:-56px;width:6px;background:rgba(36,48,94,.25);border-radius:3px}
.chan.f:after{top:50%;bottom:-24px}.chan.m:after{top:-24px;bottom:-24px}.chan.l:after{top:-24px;bottom:50%}
"""
    return css, [cover,
        page('明天約<span class="hl num"> 9 成 </span>預期持平；<br>12 月的定價則偏向升息', p2, 2),
        page('利率現在在<br><span class="hl num"> 3.75～4.00% </span>', p3, 3),
        page('明天凌晨<br>看這<span class="hl num"> 4 </span>件事', p4, 4),
        page('利率預期變動時，<br>常被討論的<span class="hl num"> 3 </span>個管道', p5, 5)]

# =====================================================================  F 日系手帳便利貼風
def build_F():
    V = "--bg:#F4ECDD;--ink:#3E3A4F;--pk:#F6C3CD;--bt:#FBE48F;--mt:#BDE3D1;--sk:#BCD8F0;--s1:96px;--l1:112px"
    grain = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/>"
             "<feColorMatrix values='0 0 0 0 .24  0 0 0 0 .22  0 0 0 0 .3  0 0 0 .16 0'/></filter><rect width='240' height='240' filter='url(%23n)'/></svg>\")")
    css = """
body{background-image:radial-gradient(rgba(62,58,79,.18) 2.5px,transparent 3px);background-size:32px 32px;background-position:16px 16px}
body:after{content:"";position:absolute;inset:0;background-image:GRAIN;pointer-events:none}
.brand{position:absolute;left:64px;top:56px}
.hdate{position:absolute;right:72px;top:48px;height:64px;padding:8px 24px;border:3px dashed var(--ink);border-radius:8px;transform:rotate(-1deg)}
.head{position:absolute;left:72px;top:144px;width:920px;height:144px;transform:skewX(-3deg);transform-origin:left bottom}
.mk{background:linear-gradient(transparent 52%,var(--bt) 52%,var(--bt) 92%,transparent 92%);padding:0 8px}
.sheet{position:absolute;left:64px;top:320px;width:952px;height:864px;background:#FFFDF8;border-radius:8px;padding:32px;box-shadow:0 6px 0 rgba(62,58,79,.12),0 0 0 2px rgba(62,58,79,.10);display:flex;flex-direction:column}
.zone{flex:1;display:flex;flex-direction:column;justify-content:space-between;min-height:0}
.tape{position:absolute;width:176px;height:48px;opacity:.88;background:repeating-linear-gradient(135deg,var(--pk) 0 14px,#FFFDF8 14px 20px)}
.tape.b{background:repeating-linear-gradient(135deg,var(--sk) 0 14px,#FFFDF8 14px 20px)}
.tape.y{background:repeating-linear-gradient(135deg,var(--bt) 0 14px,#FFFDF8 14px 20px)}
.ft{position:absolute;left:64px;top:1208px;width:952px;height:96px;display:flex;align-items:center;gap:16px}
.ft img{height:88px;object-fit:contain;flex:none}.ft .pg{margin-left:auto}
.note{position:relative;padding:24px 32px;isolation:isolate}
.note:before{content:"";position:absolute;inset:4px;background:var(--c);transform:rotate(var(--r,-1deg));box-shadow:0 6px 0 rgba(62,58,79,.14);border-radius:4px;z-index:-1}
.note>*{position:relative;z-index:1}
.it{font-family:'Liberation Serif','DejaVu Serif',serif;font-style:italic;font-weight:700}
.pb{height:64px;border:3px solid var(--ink);border-radius:5px;position:relative;overflow:hidden;background:#fff}
.pb i{position:absolute;left:0;top:0;height:100%;background:repeating-linear-gradient(45deg,var(--pk) 0 12px,#FADCE2 12px 24px)}
.cb{position:absolute;border:3px solid var(--ink);border-radius:5px;display:flex;align-items:center;justify-content:center}
.ln{border-bottom:3px dashed rgba(62,58,79,.30)}
.chk{width:56px;height:56px;border:3px solid var(--ink);border-radius:5px;display:flex;align-items:center;justify-content:center;flex:none;background:#fff}
.tg{display:flex;flex-direction:column;align-items:center;justify-content:center;border:3px solid var(--ink);border-radius:5px;width:248px;height:144px}
""".replace("GRAIN", grain)
    def page(headline, content, idx, bib, tapes=""):
        return (f'<body style="{V}"><div class="brand T3b">哩股哩股</div><div class="hdate T4b num">10/28 事件前</div>'
                f'<div class="head T2">{headline}</div><div class="sheet" data-g=1><div class="zone">{content}</div></div>{tapes}'
                f'<div class="ft T4"><span>{ASOF}</span><span class="pg num T4b">{idx} / {TOT}</span>{bibi(bib, 88)}</div></body>')
    T = lambda x, y, k="", r=-5: f'<div class="tape {k}" style="left:{x}px;top:{y}px;transform:rotate({r}deg)"></div>'
    tapes = T(112, 296) + T(792, 296, "b", 4)
    cover = (f'<body style="{V}"><div class="brand T3b">哩股哩股</div><div class="hdate T4b num">10/28 事件前</div>'
             f'<div class="a" style="left:80px;top:152px;width:920px;height:632px;background:#FFFDF8;box-shadow:0 8px 0 rgba(62,58,79,.14),0 0 0 2px rgba(62,58,79,.10);transform:rotate(-1deg)">'
             f'<img style="position:absolute;left:24px;top:24px;width:872px;height:480px;object-fit:cover" src="{crop(330, 480, 1744)}">'
             f'<div class="T3b" style="position:absolute;left:24px;top:520px;width:872px;height:88px;display:flex;align-items:center;justify-content:center;transform:skewX(-3deg)">台灣時間 10/29（四）凌晨 02:00 公布</div></div>'
             + T(104, 128, "", -8) + T(824, 128, "b", 8) +
             f'<div class="a T1" style="left:72px;top:824px;width:920px;height:224px;transform:skewX(-3deg);transform-origin:left bottom">聯準會利率<br>明天凌晨<span class="mk num"> 2 點 </span>公布</div>'
             f'<div class="a T2" style="left:72px;top:1064px;transform:skewX(-3deg);transform-origin:left bottom">利率會變嗎？</div>'
             f'<div class="a row" style="left:64px;top:1168px;gap:24px">'
             f'<div class="note T3b num" style="--c:var(--bt);--r:-1.5deg;height:72px;padding:12px 28px">目前 3.75～4.00%</div><div class="note T3b num" style="--c:var(--sk);--r:1.5deg;height:72px;padding:12px 28px">02:30 記者會</div></div></body>')
    # --- 2 便利貼
    tk = ''.join(f'<span class="a T4 num" style="left:{t}%;top:8px;transform:translateX(-{t}%)">{t}%</span>' for t in (0, 25, 50, 75, 100))
    def n2(c, r, lab, val, cc): return (f'<div class="note col" style="--c:var({c});--r:{r}deg;width:424px;height:248px;gap:8px;justify-content:center"><span class="T3b">{lab}</span><span class="it T1">{val}</span><span class="T4">{cc}</span></div>')
    p2 = ('<div class="row" style="justify-content:space-between;padding:0 8px">' + n2("--sk", -1.2, "本次會議・持平", "91%", "約 9 成預期持平") + n2("--pk", 1.2, "本次會議・升息", "9%", "只有約 1 成") + '</div>'
          f'<div class="col" style="gap:8px"><div class="row" style="justify-content:space-between"><span class="T3b">12 月會議：升息機率</span><span class="it T1">73%起</span></div>'
          f'<div class="pb"><i style="width:73%"></i></div><div style="position:relative;height:40px">{tk}</div></div>'
          f'<div class="note T4" style="--c:var(--bt);--r:-.6deg;height:104px;padding:16px 24px">{FOOT2}</div>')
    # --- 3 方格紙上的階梯
    PH = 496; sc = PH/0.75
    def y(val): return (4.25-val)*sc
    grid = ''.join(f'<span class="a T4 num" style="left:0;width:88px;text-align:right;top:{y(g)-20:.0f}px">{g:.2f}</span>' for g in (3.5, 3.75, 4.0, 4.25))
    gp = ('<div class="a" style="left:104px;top:0;width:784px;height:%dpx;background-image:linear-gradient(rgba(62,58,79,.16) 2px,transparent 2px),linear-gradient(90deg,rgba(62,58,79,.16) 2px,transparent 2px);background-size:32px 32px;border:2px solid rgba(62,58,79,.30)"></div>' % PH)
    def col(x, lo, hi, c, txt): return f'<div class="cb" style="left:{x}px;top:{y(hi):.0f}px;width:232px;height:{(hi-lo)*sc:.0f}px;background:{c}"><span class="T4b num">{txt}</span></div>'
    xl = lambda x, d, s: (f'<div class="a col" style="left:{x-16}px;top:{PH+16}px;width:264px;align-items:center;text-align:center"><span class="T3b num">{d}</span><span class="T4">{s}</span></div>')
    chart = (f'<div style="position:relative;height:{PH+144}px">{gp}{grid}' + col(128, 3.5, 3.75, "var(--bt)", "3.50–3.75%") + col(392, 3.75, 4.0, "var(--pk)", "3.75–4.00%")
             + f'<div class="cb" style="left:656px;top:0;width:232px;height:{PH}px;border-style:dashed;background:rgba(188,216,240,.55)"><span class="it T1" style="font-size:96px">？</span></div>'
             + xl(128, "2025/12", "降息 1 碼") + xl(392, "2026/09", "升息 1 碼<br>（12 比 0）") + xl(656, "10/29 凌晨", "02:00 公布") + '</div>')
    p3 = f'<span class="T3b">聯邦基金利率目標區間（%）</span>{chart}'
    # --- 4 時間貼紙＋待辦清單
    arrow = '<svg width="72" height="32" viewBox="0 0 72 32"><path d="M4 16h56" stroke="#3E3A4F" stroke-width="4" stroke-dasharray="8 8" stroke-linecap="round"/><path d="M52 6l12 10-12 10" fill="none" stroke="#3E3A4F" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    tg = lambda c, a, b, d="": f'<div class="tg" style="background:{c};{d}"><span class="T3b num">{a}</span><span class="T4">{b}</span></div>'
    tgs = (f'<div class="row" style="justify-content:space-between">{tg("var(--sk)", "02:00", "公布聲明")}{arrow}{tg("var(--bt)", "02:30", "記者會")}{arrow}{tg("#fff", "之後", "看反應", "border-style:dashed")}</div>')
    def li(i, t, s): return (f'<div class="row ln" style="gap:24px;height:152px"><div class="chk T3b num">{i}</div><div class="col"><span class="T3b">{t}</span><span class="T4">{s}</span></div></div>')
    p4 = tgs + '<div class="col">' + ''.join(li(i+1, ITEMS4[i][1], ITEMS4[i][2]) for i in range(4)) + '</div>'
    # --- 5 便利貼樹
    def chan(ic, c, t, s, pos_, r): return (f'<div class="note chan {pos_}" style="--c:var({c});--r:{r}deg;flex:1;display:flex;align-items:center;gap:24px;padding:0 32px"><div class="wh2">{icon(ic, "#3E3A4F", 44)}</div><div class="col"><span class="T2">{t}</span><span class="T4">{s}</span></div></div>')
    css += """
.wh2{width:72px;height:72px;border-radius:50%;background:#FFFDF8;display:flex;align-items:center;justify-content:center;flex:none}
.chan:after{content:"";position:absolute;left:-56px;top:calc(50% - 2px);width:56px;height:0;border-top:4px dashed var(--ink);z-index:0}
.rows{position:relative}
.vl{position:absolute;left:0;width:0;border-left:4px dashed var(--ink)}
"""
    p5 = ('<div class="row" style="height:624px;align-items:stretch"><div class="col" style="width:232px;justify-content:center;flex:none;position:relative">'
          '<div class="note T2" style="--c:var(--pk);--r:-2deg;text-align:center;padding:32px 0;width:232px">利率<br>預期<br>變動</div></div>'
          '<div class="col rows" style="flex:1;gap:24px;margin-left:56px;position:relative"><i class="vl" style="left:-56px;top:84px;bottom:84px"></i>'
          + chan("coin", "--sk", *CH3[0][1:], "f", -.8) + chan("pct", "--bt", *CH3[1][1:], "m", .8) + chan("chart", "--mt", *CH3[2][1:], "l", -.8) + '</div></div>'
          '<div class="col" style="gap:8px;border-top:3px dashed rgba(62,58,79,.30);padding-top:24px"><span class="T3b"><span class="mk">收藏這張</span>，明天凌晨公布後回來對照</span><span class="T4">只說明傳導管道，不預測方向、非投資建議</span></div>')
    return css, [cover,
        page('明天約<span class="mk num">9 成</span>預期持平；<br>12 月的定價則偏向升息', p2, 2, BIB[0], tapes),
        page('利率現在在<br><span class="mk num">3.75～4.00%</span>', p3, 3, BIB[1], T(112, 296) + T(792, 296, "y", 4)),
        page('明天凌晨<br>看這<span class="mk num">4</span>件事', p4, 4, BIB[2], tapes),
        page('利率預期變動時，<br>常被討論的<span class="mk num">3</span>個管道', p5, 5, BIB[3], T(112, 296, "b") + T(792, 296, "", 4))]

# =====================================================================  G 新聞快報卡片風
def build_G():
    V = "--bg:#FFFFFF;--ink:#111827;--rd:#D71920;--gy:#6B7280;--lg:#EDEEF0;--ye:#FFD21F;--s1:96px;--l1:112px"
    css = """
.tick{position:absolute;left:0;top:0;width:1080px;height:80px;background:var(--ink);color:#fff}
.tick .b{position:absolute;left:64px;top:16px}
.tick .t{position:absolute;left:336px;top:20px;color:#D1D5DB;white-space:nowrap}
.tick .t b{color:var(--ye)}
.band{position:absolute;left:0;top:80px;width:1080px;height:8px;background:var(--rd)}
.tags{position:absolute;left:64px;top:112px;width:952px;height:48px;display:flex;align-items:center;gap:16px}
.flash{background:var(--rd);color:#fff;padding:4px 16px;border-radius:4px}
.tg2{background:var(--lg);padding:4px 16px;border-radius:4px}
.head{position:absolute;left:64px;top:176px;width:952px;height:144px}
.hl{background:var(--ye);padding:0 8px;border-radius:4px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.hr4{position:absolute;left:64px;top:336px;width:952px;height:4px;background:var(--ink)}
.zone{position:absolute;left:64px;top:360px;width:952px;height:816px;display:flex;flex-direction:column;justify-content:space-between}
.ft{position:absolute;left:64px;top:1216px;width:952px;height:96px;display:flex;align-items:center;gap:16px;color:var(--gy);border-top:2px solid var(--lg)}
.ft img{height:88px;object-fit:contain;flex:none}.ft .pg{margin-left:auto;color:var(--ink)}
.pn{background:var(--lg);border-radius:4px;padding:24px;display:flex;flex-direction:column}
.ph{display:flex;align-items:center;gap:16px;height:56px}
.ph i{width:16px;height:40px;background:var(--rd);border-radius:2px;display:block}
.trk{height:64px;background:#fff;border-radius:5px;position:relative;flex:1}
.trk i{position:absolute;left:0;top:0;height:100%;border-radius:5px}
.cb{position:absolute;border-radius:5px;display:flex;align-items:center;justify-content:center}
.sq{width:64px;height:64px;border-radius:4px;background:var(--rd);color:#fff;display:flex;align-items:center;justify-content:center;flex:none}
"""
    def tick(txt): return f'<div class="tick"><span class="b T3b">哩股哩股</span><span class="t T4b num">{txt}</span></div><div class="band"></div>'
    TK = '<b>▶▶</b> FOMC 10/29 02:00 公布・02:30 記者會'
    def page(headline, content, idx, bib):
        return (f'<body style="{V}">{tick(TK)}<div class="tags"><span class="flash T4b">快訊</span><span class="tg2 T4b">FOMC 前夕</span><span class="T4b num" style="margin-left:auto;color:var(--gy)">10/28 事件前</span></div>'
                f'<div class="head T2" data-g=1>{headline}</div><div class="hr4"></div><div class="zone" data-g=1>{content}</div>'
                f'<div class="ft T4"><span>{ASOF}</span><span class="pg num T4b">{idx} / {TOT}</span>{bibi(bib, 88)}</div></body>')
    cover = (f'<body style="{V}">{tick(TK)}<img class="bgimg" data-bg=1 style="top:88px;height:560px;width:1080px;object-fit:cover" src="{crop(300, 560)}">'
             f'<div class="a" style="left:64px;top:672px"><span class="flash T4b">快訊</span></div><div class="a T4b num" style="right:64px;top:676px;color:var(--gy)">10/28 事件前</div>'
             f'<div class="a T1" style="left:64px;top:744px;width:952px;height:224px">聯準會利率<br>明天凌晨<span class="hl num"> 2 點 </span>公布</div>'
             f'<div class="a T2" style="left:64px;top:984px;color:var(--rd)">利率會變嗎？</div>'
             f'<div class="a row" style="left:64px;top:1088px;gap:16px"><span class="T3b num" style="height:64px;padding:8px 24px;background:var(--ink);color:#fff;border-radius:4px">02:30 記者會</span><span class="T3b num" style="height:64px;padding:8px 24px;background:var(--ye);border-radius:4px">目前 3.75～4.00%</span></div>'
             f'<div class="a T4" style="left:64px;top:1184px;width:952px;border-top:2px solid var(--lg);padding-top:16px;color:var(--gy)">台灣時間 10/29（四）凌晨 02:00 公布</div></body>')
    # --- 2 民調式橫條
    def bar(lab, val, pct, col): return (f'<div class="row" style="gap:16px;height:112px"><span class="T3b" style="width:96px">{lab}</span><div class="trk"><i style="width:{pct}%;background:{col}"></i></div><span class="T1 num" style="width:232px;text-align:right;color:{col}">{val}</span></div>')
    tk = ''.join(f'<span class="a T4 num" style="left:{t}%;top:0;transform:translateX(-{t}%);color:var(--gy)">{t}%</span>' for t in (0, 25, 50, 75, 100))
    p2 = (f'<div class="pn" style="height:336px;justify-content:space-between"><div class="ph"><i></i><span class="T3b">本次會議（10/28）：持平 vs 升息</span></div>{bar("持平", "91%", 91, "var(--ink)")}{bar("升息", "9%", 9, "var(--rd)")}</div>'
          f'<div class="pn" style="height:288px;justify-content:space-between"><div class="ph"><i></i><span class="T3b">12 月會議：升息機率</span></div>'
          f'<div class="row" style="gap:16px;height:64px"><div class="trk"><i style="width:73%;background:var(--rd)"></i></div><span class="T1 num" style="width:360px;text-align:right;color:var(--rd);white-space:nowrap">73%起</span></div>'
          f'<div class="row"><div style="position:relative;height:40px;flex:1;margin-right:376px">{tk}</div></div></div>'
          f'<div class="T4" style="color:var(--gy);border-left:4px solid var(--rd);padding-left:16px">{FOOT2}</div>')
    # --- 3 行情板式階梯
    PH = 480; sc = PH/0.75
    def y(val): return (4.25-val)*sc
    grid = ''.join(f'<i class="a" style="left:112px;width:728px;top:{y(g):.0f}px;height:2px;background:#D1D5DB"></i><span class="a T4 num" style="left:0;width:96px;text-align:right;top:{y(g)-20:.0f}px;color:var(--gy)">{g:.2f}</span>' for g in (3.5, 3.75, 4.0, 4.25))
    def col(x, lo, hi, c, tc, txt): return f'<div class="cb" style="left:{x}px;top:{y(hi):.0f}px;width:216px;height:{(hi-lo)*sc:.0f}px;background:{c};color:{tc}"><span class="T4b num">{txt}</span></div>'
    xl = lambda x, d, s: (f'<div class="a col" style="left:{x-24}px;top:{PH+16}px;width:264px;align-items:center;text-align:center"><span class="T3b num">{d}</span><span class="T4" style="color:var(--gy)">{s}</span></div>')
    chart = (f'<div style="position:relative;height:{PH+120}px">{grid}' + col(120, 3.5, 3.75, "var(--ye)", "var(--ink)", "3.50–3.75%") + col(384, 3.75, 4.0, "var(--ink)", "#fff", "3.75–4.00%")
             + f'<div class="cb" style="left:648px;top:0;width:192px;height:{PH}px;border:4px dashed var(--rd);color:var(--rd)"><span class="T1">？</span></div>'
             + xl(120, "2025/12", "降息 1 碼") + xl(384, "2026/09", "升息 1 碼<br>（12 比 0）") + xl(624, "10/29 凌晨", "02:00 公布") + '</div>')
    p3 = f'<div class="pn" style="height:816px;justify-content:space-between"><div class="ph"><i></i><span class="T3b">聯邦基金利率目標區間（%）</span></div>{chart}</div>'
    # --- 4 記分板＋清單
    def sc3(a, b, red): return (f'<div class="col" style="flex:1;align-items:center;justify-content:center;height:160px;background:{"var(--ink)" if red else "var(--lg)"};color:{"#fff" if red else "var(--ink)"};border-radius:4px"><span class="T1 num" style="{"color:var(--ye)" if red else ""}">{a}</span><span class="T4">{b}</span></div>')
    p4 = (f'<div class="row" style="gap:16px">{sc3("02:00", "公布聲明", False)}{sc3("02:30", "記者會", True)}{sc3("之後", "看反應", False)}</div>'
          + '<div class="col">' + ''.join(f'<div class="row" style="gap:24px;height:152px;border-top:2px solid var(--lg)"><div class="sq T3b num">{i+1}</div><div class="col"><span class="T2">{ITEMS4[i][1]}</span><span class="T4" style="color:var(--gy)">{ITEMS4[i][2]}</span></div></div>' for i in range(4)) + '</div>')
    # --- 5 傳導欄
    def ch(i, t, s): return (f'<div class="pn" style="flex-direction:row;align-items:center;gap:24px;height:176px;padding:0 24px"><div class="sq T3b num">{i}</div><div class="col"><span class="T2">{t}</span><span class="T4" style="color:var(--gy)">{s}</span></div></div>')
    p5 = (f'<div class="col" style="gap:16px"><div class="row" style="height:96px;background:var(--ink);border-radius:4px;justify-content:center;gap:24px"><span class="T2" style="color:#fff">利率預期變動</span><span class="T2" style="color:var(--ye)">▼</span></div>'
          + ''.join(ch(i+1, CH3[i][1], CH3[i][2]) for i in range(3)) + '</div>'
          f'<div class="col" style="gap:8px;border-left:4px solid var(--rd);padding-left:16px"><span class="T3b">收藏這張，明天凌晨公布後回來對照</span><span class="T4" style="color:var(--gy)">只說明傳導管道，不預測方向、非投資建議</span></div>')
    return css, [cover,
        page('明天約<span class="hl num">9 成</span>預期持平；<br>12 月的定價則偏向升息', p2, 2, BIB[0]),
        page('利率現在在<br><span class="hl num">3.75～4.00%</span>', p3, 3, BIB[1]),
        page('明天凌晨<br>看這<span class="hl num">4</span>件事', p4, 4, BIB[2]),
        page('利率預期變動時，<br>常被討論的<span class="hl num">3</span>個管道', p5, 5, BIB[3])]

BUILD = {"D": build_D, "E": build_E, "F": build_F, "G": build_G}
def render(css, pages, out):
    out.mkdir(parents=True, exist_ok=True); tot = 0; sizes = set()
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, html in enumerate(pages, 1):
            pg.set_content(f"<html><head><meta charset=utf-8><style>{BASE}{css}</style></head>{html}</html>")
            pg.wait_for_timeout(300); res = pg.evaluate(CHECK); tot += len(res["bad"]); sizes |= set(res["sizes"]); print(i, res["bad"])
            Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}))).convert("RGB").save(out/f"{i}.jpg", quality=93)
        b.close()
    print(f"重疊檢查：程式 {len(pages)} 張 {tot} 筆；字級 {sorted(sizes)}"); return tot
if __name__ == "__main__":
    root = Path(sys.argv[1]); which = sys.argv[2:] or list(BUILD)
    for k in which:
        print("== 套", k); out = root/f"v4_{k}"; css, pages = BUILD[k]()
        render(css, pages, out); lib.sheet(out, [f"{i}.jpg" for i in range(1, 6)], out/"sheet.jpg", 5, 400)
