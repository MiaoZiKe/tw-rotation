"""ETF 每週介紹樣張（0050 最壞情境回測）IG 輪播 8 張 1080×1350。
用法：python render_carousel.py <輸出資料夾>   （資料：同資料夾 etf_0050_snapshot.json，取自 site/data/etf.json）
數字全部由 site/data/etf.json 的 series['0050']（週資料；p＝還原後價格、t＝含息再投入總報酬指數）即時計算。
輸出 JPEG 並逐張重疊檢查，最後印「重疊檢查：程式 N 張 0 筆」。"""
import sys, io, json, base64, datetime as D
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "scripts" / "social_theme.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
from social_theme import logo_uri, TOKENS as T  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
E = json.load(open(HERE / "etf_0050_snapshot.json")); X = E["series"]["0050"]
dd, P, TR = X["d"], X["p"], X["t"]; N = len(dd)
Y = lambda a, b: (D.date.fromisoformat(dd[b]) - D.date.fromisoformat(dd[a])).days / 365.25
def peak(lo, hi): return max((k for k in range(N) if lo <= dd[k] <= hi), key=lambda k: P[k])
def stats(i):
    rp = next(j for j in range(i+1, N) if P[j] > P[i]); rt = next(j for j in range(i+1, N) if TR[j] > TR[i])
    lo = min(range(i, N), key=lambda j: TR[j])
    hz = {}
    for h in (1, 3, 5, 10):
        j = next((j for j in range(i, N) if Y(i, j) >= h), None)
        if j: hz[h] = (round((TR[j]/TR[i]-1)*100, 1), round((P[j]/P[i]-1)*100, 1))
    return dict(i=i, rp=rp, rt=rt, lo=lo, dd=round((TR[lo]/TR[i]-1)*100, 1), yp=round(Y(i, rp), 1), yt=round(Y(i, rt), 1),
                hz=hz, now_tr=TR[-1]/TR[i], now_p=P[-1]/P[i], yrs=Y(i, N-1), ann=((TR[-1]/TR[i])**(1/Y(i, N-1))-1)*100)
A = stats(peak("2007-01-01", "2008-03-01")); B = stats(peak("2021-01-01", "2022-03-01"))
asof = E["asof"]; it = {i["code"]: i for i in E["items"]}["0050"]
print("A", {k: v for k, v in A.items()}, "\nB", B)

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;font-family:'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{T['ink']};
background:{T['bg']};background-image:linear-gradient(rgba(10,106,134,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(10,106,134,.05) 1px,transparent 1px);background-size:32px 32px;padding:36px 40px 40px;display:flex;flex-direction:column;gap:16px}}
.num{{font-family:Inter,sans-serif;font-variant-numeric:tabular-nums}}
.hd{{height:88px;display:flex;align-items:center;gap:18px;border-bottom:2px solid {T['accent']};flex:none}}
.hd img{{width:72px;height:72px;border-radius:17px}}
.pill{{background:#F5B73B;color:{T['ink']};font-weight:800;font-size:28px;padding:6px 18px;border-radius:12px}}
.ht{{font-size:46px;font-weight:800}}
.hdate{{margin-left:auto;font-size:30px;font-weight:600;color:{T['ink2']}}}
.card{{flex:1;background:{T['panel']};border:1.5px solid {T['line']};border-radius:10px;padding:44px 44px;display:flex;flex-direction:column;justify-content:space-between;gap:20px;position:relative;overflow:hidden}}
.blk{{display:flex;flex-direction:column;gap:30px;flex:1;justify-content:center}} .cv{{flex:none!important}}
.bibi{{align-self:center;object-fit:contain}}
.big{{font-size:100px;font-weight:800;line-height:1.25}}
.title{{font-size:84px;font-weight:800;line-height:1.28}}
.mid{{font-size:64px;font-weight:800;line-height:1.3}}
.sub{{font-size:42px;font-weight:600;color:{T['ink2']};line-height:1.5}}
.hl{{color:{T['rise']}}} .hy{{background:#F5B73B;padding:0 14px;border-radius:10px}}
.dn{{color:{T['fall']}}} .up{{color:{T['rise']}}}
.row{{display:flex;align-items:center;gap:20px;height:128px}}
.lb{{font-size:46px;font-weight:800;width:190px}}
.track{{flex:1;height:56px;background:{T['panel2']};border:1.5px solid {T['line']};border-radius:6px;position:relative}}
.bar{{position:absolute;top:0;height:100%;border-radius:5px}}
.val{{font-size:54px;font-weight:800;width:200px;text-align:right}}
.unit{{font-size:30px;font-weight:600;color:{T['ink3']};line-height:1.5}}
.tag{{font-size:32px;font-weight:800;background:{T['accent']};color:#fff;padding:6px 20px;border-radius:12px;align-self:flex-start}}
.kpi{{background:{T['panel2']};border:1.5px solid {T['line']};border-radius:12px;padding:20px 28px;display:flex;flex-direction:column;gap:6px}}
.kpi .k{{font-size:34px;font-weight:700;color:{T['ink2']}}} .kpi .v{{font-size:84px;font-weight:800;line-height:1.1}}
.two{{display:flex;gap:20px}} .two .kpi{{flex:1}}
"""
def bibi(name, h, src=None):
    f = src or ROOT/'docs'/'anim'/'bibi_library'/name/'key.png'
    im = Image.open(f).convert('RGBA'); im = im.crop(im.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox())
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return f'<img class="bibi" style="height:{h}px" src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'
def cover_img():
    im = Image.open(HERE/'cover_raw.png').convert('RGB').crop((0, 60, 1024, 700))   # 取山頂＋比比
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=92)
    return f'<img class="bibi" style="width:960px;height:600px;border-radius:12px;object-fit:cover" src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">'
def hd(): return f'<div class="hd"><img src="{logo_uri()}"><div class="pill">ETF</div><div class="ht">每週一檔</div><div class="hdate num">資料 {asof[5:].replace("-","/")}</div></div>'
def pct(v): return f'<span class="{"up" if v>=0 else "dn"} num">{v:+.1f}%</span>'
def d(i): return dd[i].replace("-", "/")

# ---- 圖 2：買點之後 19 年（對數座標，以買點＝100 萬）----
def chart():
    i0 = A["i"]; xs = range(i0, N); W, H, L, R, Tp, Bt = 960, 700, 96, 20, 20, 44
    lo, hi = 30, 1200; import math
    fx = lambda k: L + (k-i0)/(N-1-i0)*(W-L-R)
    fy = lambda v: Tp + (math.log(hi)-math.log(v))/(math.log(hi)-math.log(lo))*(H-Tp-Bt)
    pl = lambda arr, col, w: f'<polyline fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" points="' + " ".join(f"{fx(k):.1f},{fy(100*arr[k]/arr[i0]):.1f}" for k in xs) + '"/>'
    g = "".join(f'<line x1="{L}" x2="{W-R}" y1="{fy(v):.1f}" y2="{fy(v):.1f}" stroke="{T["line"]}" stroke-width="1.5"/><text x="{L-12}" y="{fy(v)+9:.1f}" text-anchor="end" font-size="26" font-weight="700" fill="{T["ink3"]}" class="num">{v}</text>' for v in (50, 100, 300, 1000))
    xl = "".join(f'<text x="{fx(next(k for k in range(N) if dd[k]>=f"{y}-01-01")):.1f}" y="{H-10}" text-anchor="middle" font-size="26" font-weight="700" fill="{T["ink3"]}" class="num">{y}</text>' for y in (2010, 2015, 2020, 2025))
    lo_k = A["lo"]; rt = A["rt"]
    mk = (f'<circle cx="{fx(i0):.1f}" cy="{fy(100):.1f}" r="11" fill="#F5B73B" stroke="{T["ink"]}" stroke-width="3"/>'
          f'<circle cx="{fx(lo_k):.1f}" cy="{fy(100*TR[lo_k]/TR[i0]):.1f}" r="11" fill="{T["fall"]}" stroke="#fff" stroke-width="3"/>'
          f'<circle cx="{fx(rt):.1f}" cy="{fy(100):.1f}" r="11" fill="{T["rise"]}" stroke="#fff" stroke-width="3"/>')
    lab = (f'<text x="{fx(i0)+22:.1f}" y="{fy(100)-30:.1f}" font-size="30" font-weight="800" fill="{T["ink"]}">買在高點</text>'
           f'<text x="{fx(lo_k)+22:.1f}" y="{fy(100*TR[lo_k]/TR[i0])-24:.1f}" font-size="30" font-weight="800" fill="{T["fall"]}">最低 {A["dd"]:+.1f}%</text>'
           f'<text x="{fx(rt)+30:.1f}" y="{fy(100)+58:.1f}" font-size="30" font-weight="800" fill="{T["rise"]}">含息回本</text>')
    return (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{g}{xl}{pl(P,"#8AA3B5",5)}{pl(TR,T["rise"],7)}{mk}{lab}</svg>')

def bars(rows, mx, signed=False):
    out = ""
    for lb, v, col in rows:
        w = abs(v)/mx*100
        out += (f'<div class="row"><div class="lb">{lb}</div><div class="track"><div class="bar" style="left:0;width:{w:.1f}%;background:{col}"></div></div>'
                f'<div class="val num">{pct(v) if signed else v}</div></div>')
    return out

hz = A["hz"]
s = []
s.append(cover_img() + f'<div class="blk cv"><div class="title" style="font-size:78px">2007 年買在 <span class="hy">0050</span><br>最高點，要等<span class="hl">幾年</span><br>才回本？</div><div class="sub">用 19 年真實價格回測，一次講清楚</div></div>')
s.append(f'<div class="blk"><div class="mid">假設 {d(A["i"])}<br>一次投入 <span class="hl">100 萬</span></div>{chart()}<div class="unit">紅線＝含息再投入　灰線＝只看價格　縱軸對數，買點＝100</div></div>')
s.append(f'<div class="blk"><div class="mid">最痛的時候：</div><div class="big dn num">{A["dd"]:+.1f}%</div><div class="sub">{d(A["lo"])}，100 萬剩約 <b>{round(100*(1+A["dd"]/100))} 萬</b><br>買進後第 1 年就 {hz[1][0]:+.1f}%</div></div>' + bibi("face_shock", 380))
mx = 60
s.append(f'<div class="blk"><div class="mid">含息報酬，隨持有年數怎麼走</div>' + bars([("1 年", hz[1][0], T["fall"]), ("3 年", hz[3][0], T["fall"]), ("5 年", hz[5][0], T["fall"]), ("10 年", hz[10][0], T["rise"])], mx, True) + '<div class="unit">買進後第 N 年的累計報酬（含息再投入）</div></div>')
s.append(f'<div class="blk"><div class="mid">回到買點，用了多久？</div>' + bars([("含息", A["yt"], T["rise"]), ("只看價", A["yp"], "#8AA3B5")], 8) .replace('class="val num"', 'class="val num" ').replace(f'{A["yt"]}</div>', f'{A["yt"]} 年</div>').replace(f'{A["yp"]}</div>', f'{A["yp"]} 年</div>') + f'<div class="sub">含息：{d(A["rt"])}　只看價：{d(A["rp"])}</div></div>' + bibi("calendar", 340))
s.append(f'<div class="blk"><div class="mid">撐到今天（{asof[:4]}/{asof[5:7]}）</div><div class="two"><div class="kpi"><div class="k">含息</div><div class="v hl num">{A["now_tr"]*100:,.0f} 萬</div></div><div class="kpi"><div class="k">只看價</div><div class="v num">{A["now_p"]*100:,.0f} 萬</div></div></div><div class="sub">投入 100 萬、持有 {A["yrs"]:.0f} 年，年化約 {A["ann"]:.1f}%（含息）</div><div class="unit">未扣交易費與稅；配息假設全數再投入</div></div>' + bibi("growth", 330))
s.append(f'<div class="blk"><div class="mid">換成 2022 年高點呢？</div><div class="two"><div class="kpi"><div class="k">最深回檔</div><div class="v dn num">{B["dd"]:+.1f}%</div></div><div class="kpi"><div class="k">含息回本</div><div class="v hl num">{B["yt"]} 年</div></div></div><div class="sub">{d(B["i"])} 買在當時高點<br>對照：2007 年 {A["dd"]:+.1f}%、{A["yt"]} 年</div></div>' + bibi("face_relief", 330))
s.append(f'<div class="blk"><div class="big">跌<span class="dn num">{abs(A["dd"]):.0f}%</span>，<br>你撐得住嗎？</div><div class="sub">回測只是在說「過去發生過什麼」</div><div class="unit">過去績效不代表未來。本內容為歷史資料情境說明，不構成投資建議。</div></div>' + bibi("tilt", 460))
BIB = s
CHECK = """() => {
 const els=[...document.body.querySelectorAll('*')].filter(e=>{
   const t=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
   return t||e.classList.contains('bar')||e.tagName==='IMG'||e.tagName==='circle'||e.classList.contains('track')||e.tagName==='polyline';});
 const R=els.map(e=>({e,r:e.getBoundingClientRect()}));
 let bad=[];
 for(let i=0;i<R.length;i++){const a=R[i];
  if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+a.e.className);
  for(let j=i+1;j<R.length;j++){const b=R[j];
   if(a.e.contains(b.e)||b.e.contains(a.e))continue;
   if(a.e.tagName==='polyline'||b.e.tagName==='polyline'||a.e.tagName==='circle'&&b.e.tagName==='circle'&&false)continue;
   const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
   if(w>1&&h>1){
     const tt=x=>x.e.tagName==='text'||x.e.tagName==='TEXT';
     if((a.e.tagName==='circle'&&!tt(b))||(b.e.tagName==='circle'&&!tt(a)))continue;
     bad.push('重疊:'+(a.e.className.baseVal??a.e.className)+a.e.tagName+'/'+(b.e.className.baseVal??b.e.className)+b.e.tagName+':'+(a.e.textContent||'').slice(0,8)+'|'+(b.e.textContent||'').slice(0,8));}}}
 return bad;}"""
total = 0
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=__import__("os").environ.get("CHROMIUM") or None)
    pg = b.new_page(viewport={"width": 1080, "height": 1350})
    for i, body in enumerate(s, 1):
        pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{hd()}<div class='card'>{body}</div></body></html>")
        pg.wait_for_timeout(250)
        bad = pg.evaluate(CHECK)
        # 內容不得被卡片裁掉
        clip = pg.evaluate("()=>{const c=document.querySelector('.card');return c.scrollHeight>c.clientHeight+1}")
        if clip: bad.append("內容超出卡片")
        total += len(bad); print(i, "問題:", bad)
        png = pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        Image.open(io.BytesIO(png)).convert("RGB").save(OUT / f"{i}.jpg", quality=92)
    b.close()
print(f"重疊檢查：程式 {len(s)} 張 {total} 筆")
