"""FOMC 前一天貼文 v4（三套配色比稿）。Andy 10-28：「文字、配色、圖表色調再調整，v3 感覺不整齊、配色奇怪不親人」。
版面、字級、格線三套完全相同，只換 THEMES 的 6 個顏色。規格見 docs/marketing/social_unit/post_design_system.md「事件貼文 v4（比稿中）」。
用法：CHROMIUM=... python render_fomc_v4.py <輸出根目錄> [A|B|C ...]；各套輸出 <根>/v4_A/1.jpg～5.jpg＋sheet.jpg，
印「重疊檢查：程式 N 張 M 筆」。文字（法遵 2fcab0de）：第 2 張「12 月的定價則偏向升息」「這是期貨市場定價，不是本帳號的預測」、
第 5 張「常被討論的 3 個管道」「只說明傳導管道，不預測方向、非投資建議」一律保留。"""
import sys, io, os, base64, math
from pathlib import Path
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p/"docs/marketing/posts/samples_1028/event_v2_lib").exists())/"docs/marketing/posts/samples_1028/event_v2_lib"))
import lib
from lib import Image, icon, bibi, sync_playwright

# ---- 三套配色：每套 6 色（底、主、輔1、輔2、字深、字淺），卡片白為底色族 ----
THEMES = {
 "A": dict(name="溫暖米白", bg="#FBF5EA", pri="#1F4FB4", a1="#E5603F", a2="#FFC93C", ink="#1B2433", ink2="#5A6272", warm=True),
 "B": dict(name="清新青綠藍", bg="#F2F9FA", pri="#0B7A8C", a1="#6E62DC", a2="#FFD54F", ink="#12303A", ink2="#4F6A73", warm=False),
 "C": dict(name="網站品牌", bg="#F4F3EF", pri="#5643D1", a1="#0A6B8A", a2="#F5C842", ink="#1F1D19", ink2="#5F5A51", warm=False),
}
FONT = "'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
TOT = 5; ASOF = "資料日 10/27・CME FedWatch"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:FONTPLACE;color:var(--ink);background:var(--bg)}
.num{font-family:Inter,'DejaVu Sans',sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
/* 字級階梯 4 級：L1 96/112、L2 56/72、L3 36/48、L4 28/40；字重只有 粗(800)／常規(500) */
.L1{font-size:96px;line-height:112px;font-weight:800}
.L2{font-size:56px;line-height:72px;font-weight:800}
.L3{font-size:36px;line-height:48px;font-weight:500}
.L3b{font-size:36px;line-height:48px;font-weight:800}
.L4{font-size:28px;line-height:40px;font-weight:500}
.L4b{font-size:28px;line-height:40px;font-weight:800}
.bg{background:radial-gradient(760px 420px at 100% 0,var(--glow),transparent 70%),var(--bg)}
.hd{position:absolute;left:64px;right:64px;top:48px;height:72px;display:flex;align-items:center;justify-content:space-between}
.hd .brand{font-size:36px;line-height:48px;font-weight:800}
.hd .hdate{font-size:36px;line-height:48px;font-weight:800;color:var(--ink2)}
.head{position:absolute;left:64px;right:64px;top:144px;height:144px}
.hl{background:var(--a2);color:var(--ink);padding:0 12px;border-radius:8px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.card{position:absolute;left:64px;top:320px;width:952px;height:864px;background:#fff;border-radius:24px;padding:32px;box-shadow:inset 0 0 0 2px var(--line);display:flex;flex-direction:column}
.ft{position:absolute;left:64px;right:64px;top:1208px;height:96px;display:flex;align-items:center;gap:16px}
.ft .d{color:var(--ink2)} .ft .pg{margin-left:auto;color:var(--ink2)}
.ft img{height:88px;object-fit:contain;flex:none}
.lab{color:var(--pri);font-size:36px;line-height:48px;font-weight:800}
.hr{height:2px;background:var(--line);flex:none}
.sw{width:32px;height:32px;border-radius:5px;flex:none}
.track{height:64px;background:var(--tint);border-radius:5px;position:relative}
.track i{position:absolute;left:0;top:0;height:100%;border-radius:5px}
.tile{width:80px;height:80px;border-radius:16px;background:var(--tint);display:flex;align-items:center;justify-content:center;flex:none}
.row{display:flex;align-items:center}
.sec2{display:flex;flex-direction:column}
.irow{flex:1;display:flex;align-items:center;gap:24px;border-top:2px solid var(--line)}
.irow:first-child{border-top:0}
.tree{flex:1;display:flex;align-items:stretch;min-height:0}
.hub{width:176px;align-self:center;background:var(--pri);color:#fff;border-radius:16px;padding:32px 8px;text-align:center;flex:none}
.rows{flex:1;display:flex;flex-direction:column;gap:24px;padding-left:48px;position:relative;min-width:0}
.chan{flex:1;border-radius:16px;padding:0 24px;display:flex;align-items:center;gap:24px;position:relative;background:var(--tint)}
.chan .tile{background:#fff}
.chan:before{content:"";position:absolute;left:-48px;top:calc(50% - 2px);width:48px;height:4px;background:var(--conn)}
.chan:after{content:"";position:absolute;left:-48px;width:4px;background:var(--conn)}
.chan.f:after{top:50%;bottom:-24px}.chan.m:after{top:-24px;bottom:-24px}.chan.l:after{top:-24px;bottom:50%}
/* 封面 */
.bgimg{position:absolute;left:0;top:-380px;width:1080px;height:1620px}
.tone{position:absolute;inset:0}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.28) 0%,transparent 14%,transparent 38%,color-mix(in srgb,var(--bg) 88%,transparent) 54%,var(--bg) 66%)}
.cvbody{position:absolute;left:64px;right:64px;bottom:46px;display:flex;flex-direction:column}
.chip{height:64px;padding:0 24px;border-radius:8px;background:#fff;display:flex;align-items:center;font-size:36px;font-weight:800;box-shadow:inset 0 0 0 2px var(--line)}
.chip.a{background:var(--a2);box-shadow:none}
.cvsub{border-top:2px solid var(--line);padding-top:16px;color:var(--ink2)}
""".replace("FONTPLACE", FONT)

CHECK = """() => {
 const els=[...document.body.querySelectorAll('*')].filter(e=>{
   if(e.dataset.bg||e.classList.contains('shade')||e.classList.contains('tone'))return false;
   const t=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
   return t||e.tagName==='IMG';});
 const R=els.map(e=>({e,r:e.getBoundingClientRect()}));let bad=[];
 const nm=e=>((e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)||'')+e.tagName+':'+(e.textContent||'').trim().slice(0,8);
 for(let i=0;i<R.length;i++){const a=R[i];
  if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+nm(a.e));
  if(a.r.left<63.5&&a.e.tagName!=='IMG'||a.r.right>1016.5&&a.e.tagName!=='IMG')bad.push('超出安全邊距64:'+nm(a.e));
  if(a.e.scrollWidth>a.e.clientWidth+1&&a.e.clientWidth>0&&a.e.tagName!=='svg'&&a.e.tagName!=='text')bad.push('溢出:'+nm(a.e));
  const fs=parseFloat(getComputedStyle(a.e).fontSize);
  if([...a.e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&fs<28)bad.push('字太小:'+nm(a.e)+fs);
  for(let j=i+1;j<R.length;j++){const b=R[j];
   if(a.e.contains(b.e)||b.e.contains(a.e))continue;
   const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
   if(w>1&&h>1)bad.push('重疊:'+nm(a.e)+'/'+nm(b.e));}}
 // 卡片內：所有文字／圖示必須落在卡片內距 32 之內
 const c=document.querySelector('.card');
 if(c){const cr=c.getBoundingClientRect();
  if(c.scrollHeight>c.clientHeight+1)bad.push('卡片內容溢出 '+c.scrollHeight+'>'+c.clientHeight);
  for(const {e,r} of R){ if(!c.contains(e))continue;
   if(r.left<cr.left+31||r.right>cr.right-31||r.top<cr.top+31||r.bottom>cr.bottom-31)bad.push('壓到卡片內距:'+nm(e));}}
 // 格線：主要區塊的 left/top/width/height 必須是 8 的倍數（卡片、標題區、頁首、頁尾）
 for(const s of ['.hd','.head','.card','.ft','.cvbody']){const e=document.querySelector(s);if(!e)continue;const r=e.getBoundingClientRect();
  for(const [k,v] of [['left',r.left],['top',r.top],['width',r.width]]) if(k!=='top'||s!=='.cvbody') if(Math.abs(v/8-Math.round(v/8))>.01)bad.push('格線:'+s+' '+k+'='+v);}
 const hd=document.querySelector('.head'); if(hd){const hh=[...hd.querySelectorAll('div')].map(x=>x.getBoundingClientRect().height)[0]; if(hh>144.5)bad.push('標題超過 2 行 '+hh);}
 return bad;}"""

def theme_vars(T):
    return (f"--bg:{T['bg']};--pri:{T['pri']};--a1:{T['a1']};--a2:{T['a2']};--ink:{T['ink']};--ink2:{T['ink2']};"
            f"--tint:color-mix(in srgb,{T['pri']} 10%,#fff);--line:color-mix(in srgb,{T['ink']} 13%,#fff);"
            f"--conn:color-mix(in srgb,{T['pri']} 45%,#fff);--glow:color-mix(in srgb,{T['a2']} 30%,{T['bg']})")

def crop(y0, h):
    im = Image.open(Path(lib.HERE)/"bg"/"fomc_day.jpg").convert("RGB").crop((0, y0, 1080, y0+h)); b = io.BytesIO(); im.save(b, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
BGD = "data:image/jpeg;base64," + base64.b64encode((Path(lib.HERE)/"bg"/"fomc_day.jpg").read_bytes()).decode()

def build(T):
    P, A1, A2, INK, INK2 = T["pri"], T["a1"], T["a2"], T["ink"], T["ink2"]
    SVGF = "font-family=\"Inter,'Noto Sans CJK TC',sans-serif\""
    def page(headline, card, idx, bib, bh=88):
        return (f'<body class="bg" style="{theme_vars(T)}"><div class="hd"><span class="brand">哩股哩股</span><span class="hdate num">10/28 事件前</span></div>'
                f'<div class="head L2">{headline}</div><div class="card">{card}</div>'
                f'<div class="ft L4"><span class="d">{ASOF}</span><span class="pg num L4b">{idx} / {TOT}</span>{bibi(bib, bh)}</div></body>')
    # ---- 封面 ----
    tone = (f'<div class="tone" style="background:linear-gradient(180deg,{A2}38 0%,transparent 40%)"></div>' if T["warm"] else
            f'<div class="tone" style="background:linear-gradient(180deg,{P}1A 0%,transparent 40%)"></div>')
    cover = (f'<body style="{theme_vars(T)};background:var(--bg)"><img class="bgimg" data-bg="1" src="{BGD}">{tone}<div class="shade"></div>'
             f'<div class="hd"><span class="brand">哩股哩股</span><span class="hdate num">10/28 事件前</span></div>'
             f'<div class="cvbody"><div class="L1">聯準會利率<br>明天凌晨<span class="hl num">2 點</span>公布</div>'
             f'<div class="L2" style="color:var(--pri);margin-top:24px">利率會變嗎？</div>'
             f'<div class="row" style="gap:16px;margin-top:32px"><span class="chip a num">目前 3.75～4.00%</span><span class="chip num">02:30 記者會</span></div>'
             f'<div class="cvsub L4" style="margin-top:32px">台灣時間 10/29（四）凌晨 02:00 公布</div></div></body>')
    # ---- 第 2 張：甜甜圈＋進度條 ----
    r = 124; c = 2*math.pi*r; v = 0.906
    donut = (f'<svg width="304" height="304" viewBox="0 0 304 304"><g transform="rotate(-90 152 152)" fill="none" stroke-width="56">'
             f'<circle cx="152" cy="152" r="{r}" stroke="{P}" stroke-dasharray="{c*v-3:.1f} {c:.1f}"/>'
             f'<circle cx="152" cy="152" r="{r}" stroke="{A1}" stroke-dasharray="{c*(1-v)-3:.1f} {c:.1f}" stroke-dashoffset="{-c*v-0:.1f}"/></g>'
             f'<text x="152" y="148" text-anchor="middle" class="num" {SVGF} font-size="56" font-weight="800" fill="{INK}">10/28</text>'
             f'<text x="152" y="190" text-anchor="middle" {SVGF} font-size="28" font-weight="500" fill="{INK2}">會議</text></svg>')
    leg = lambda col, t, val: (f'<div class="row" style="gap:16px;height:112px"><div class="sw" style="background:{col}"></div><div class="L3b" style="flex:1">{t}</div>'
                               f'<div class="L1 num" style="color:{INK}">{val}</div></div>')
    ticks = ''.join(f'<span class="L4 num" style="position:absolute;left:{t}%;transform:translateX(-{t}%);color:{INK2}">{t}%</span>' for t in (0, 25, 50, 75, 100))
    p2 = (f'<div class="lab" style="margin-bottom:24px">本次會議：持平 vs 升息</div>'
          f'<div class="row" style="gap:48px">{donut}<div style="flex:1;display:flex;flex-direction:column;gap:48px">{leg(P, "持平", "91%")}{leg(A1, "升息", "9%")}</div></div>'
          f'<div class="hr" style="margin:32px 0"></div>'
          f'<div class="row" style="justify-content:space-between;height:112px"><div class="lab">12 月會議：升息機率</div><div class="L1 num" style="color:{A1}">73%起</div></div>'
          f'<div class="track" style="margin-top:16px"><i style="width:73%;background:{A1}"></i></div>'
          f'<div style="position:relative;height:40px;margin-top:8px">{ticks}</div>'
          f'<div class="L4" style="margin-top:auto;color:{INK2}">12 月升息機率各媒體引述 73%～80% 以上，圖取 73%。這是期貨市場定價，不是本帳號的預測</div>')
    # ---- 第 3 張：階梯帶狀圖 ----
    def y(val): return 20 + (4.25-val)/0.75*450
    grid = ''.join(f'<line x1="112" x2="888" y1="{y(g):.0f}" y2="{y(g):.0f}" stroke="{T["ink"]}22" stroke-width="2"/>'
                   f'<text x="96" y="{y(g)+10:.0f}" text-anchor="end" class="num" {SVGF} font-size="28" font-weight="500" fill="{INK2}">{g:.2f}</text>' for g in (3.5, 3.75, 4.0, 4.25))
    def band(x, lo, hi, col, tcol, txt):
        return (f'<rect x="{x}" y="{y(hi):.0f}" width="232" height="{y(lo)-y(hi):.0f}" rx="5" fill="{col}"/>'
                f'<text x="{x+116}" y="{(y(hi)+y(lo))/2+10:.0f}" text-anchor="middle" class="num" {SVGF} font-size="28" font-weight="800" fill="{tcol}">{txt}</text>')
    def xl(x, d, s): return (f'<text x="{x+116}" y="518" text-anchor="middle" class="num" {SVGF} font-size="36" font-weight="800" fill="{INK}">{d}</text>'
                             f'<text x="{x+116}" y="560" text-anchor="middle" {SVGF} font-size="28" font-weight="500" fill="{INK2}">{s}</text>')
    chart = (f'<svg width="888" height="572" viewBox="0 0 888 572">{grid}'
             + band(112, 3.5, 3.75, A2, INK, "3.50–3.75%") + band(384, 3.75, 4.0, A1, "#fff", "3.75–4.00%")
             + f'<rect x="656" y="{y(4.25):.0f}" width="232" height="{y(3.5)-y(4.25):.0f}" rx="5" fill="{P}14" stroke="{P}" stroke-width="3" stroke-dasharray="12 9"/>'
             + f'<text x="772" y="{(y(4.25)+y(3.5))/2+34:.0f}" text-anchor="middle" {SVGF} font-size="96" font-weight="800" fill="{P}">？</text>'
             + xl(112, "2025/12", "降息 1 碼") + xl(384, "2026/09", "升息 1 碼（12 比 0）") + xl(656, "10/29 凌晨", "02:00 公布") + '</svg>')
    p3 = (f'<img style="width:888px;height:128px;object-fit:cover;border-radius:16px;flex:none" src="{crop(540, 220)}">'
          f'<div class="lab" style="margin:24px 0 16px">聯邦基金利率目標區間（%）</div>{chart}')
    # ---- 第 4 張：時間軸＋四列 ----
    tl = (f'<svg width="888" height="160" viewBox="0 0 888 160"><line x1="148" x2="740" y1="28" y2="28" stroke="{P}55" stroke-width="6" stroke-linecap="round"/>'
          f'<circle cx="148" cy="28" r="20" fill="{P}"/><circle cx="444" cy="28" r="20" fill="{P}"/><circle cx="740" cy="28" r="18" fill="#fff" stroke="{P}" stroke-width="5" stroke-dasharray="6 6"/>'
          + ''.join(f'<text x="{x}" y="98" text-anchor="middle" class="num" {SVGF} font-size="36" font-weight="800" fill="{INK}">{a}</text>'
                    f'<text x="{x}" y="140" text-anchor="middle" {SVGF} font-size="28" font-weight="500" fill="{INK2}">{b}</text>' for x, a, b in ((148, "02:00", "公布聲明"), (444, "02:30", "記者會"), (740, "之後", "看反應")))
          + '</svg>')
    def irow(ic, n, t, s): return (f'<div class="irow"><div class="tile">{icon(ic, P, 48)}</div><div><div class="L2"><span class="num" style="color:{A1}">{n}</span>　{t}</div>'
                                   f'<div class="L3" style="color:{INK2}">{s}</div></div></div>')
    p4 = (f'{tl}<div class="hr" style="margin:16px 0 0"></div><div class="sec2" style="flex:1">'
          + irow("quote", 1, "聲明措辭", "對通膨與就業的描述有沒有改") + irow("flag", 2, "投票結果", "有沒有人投反對票")
          + irow("clock", 3, "02:30 記者會", "對 12 月的說法") + irow("chart", 4, "本次沒有點陣圖", "不是經濟預測（SEP）會議") + '</div>')
    p4 = p4.replace('<div class="sec2" style="flex:1">', '<div class="sec2" style="flex:1;justify-content:stretch">')
    # ---- 第 5 張：樹狀圖 ----
    def chan(ic, t, s, pos): return (f'<div class="chan {pos}"><div class="tile">{icon(ic, P, 48)}</div><div><div class="L2">{t}</div><div class="L3" style="color:{INK2}">{s}</div></div></div>')
    p5 = (f'<div class="tree"><div class="hub L2">利率<br>預期<br>變動</div><div class="rows">'
          + chan("coin", "美元", "反映利差預期，升降方向都可能", "f") + chan("pct", "美債殖利率", "常隨利率預期調整", "m") + chan("chart", "股票估值", "折現率隨利率預期改變", "l")
          + f'</div></div><div class="hr" style="margin:32px 0 24px"></div>'
          f'<div class="L3b">收藏這張，明天凌晨公布後回來對照</div><div class="L4" style="color:{INK2}">只說明傳導管道，不預測方向、非投資建議</div>')
    H = lambda a, b: a + '<br>' + b
    return [cover,
        page(f'明天約<span class="hl num">9 成</span>預期持平；<br>12 月的定價則偏向升息', p2, 2, "face_think"),
        page(f'利率現在在<br><span class="hl num">3.75～4.00%</span>', p3, 3, "calendar"),
        page(f'明天凌晨<br>看這<span class="hl num">4</span>件事', p4, 4, "magnifier"),
        page(f'利率預期變動時，<br>常被討論的<span class="hl num">3</span>個管道', p5, 5, "coins")]

def render(pages, out):
    out.mkdir(parents=True, exist_ok=True); tot = 0
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, html in enumerate(pages, 1):
            pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head>{html}</html>")
            pg.wait_for_timeout(250); bad = pg.evaluate(CHECK); tot += len(bad); print(i, bad)
            Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}))).convert("RGB").save(out/f"{i}.jpg", quality=93)
        b.close()
    print(f"重疊檢查：程式 {len(pages)} 張 {tot} 筆"); return tot

if __name__ == "__main__":
    root = Path(sys.argv[1]); which = sys.argv[2:] or list(THEMES)
    for k in which:
        print("== 套", k, THEMES[k]["name"]); out = root/f"v4_{k}"
        render(build(THEMES[k]), out); lib.sheet(out, [f"{i}.jpg" for i in range(1, 6)], out/"sheet.jpg", 5, 400)
