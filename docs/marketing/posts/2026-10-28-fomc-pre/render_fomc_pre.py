"""FOMC 前一天貼文（2026-10-28 發）v3：Andy 10-28 第二次意見（左上只留文字「哩股哩股」不放 LOGO 圖案、
長條小圓角 5px、圖表與資訊合成單一大卡、每張視覺元素不同：甜甜圈／階梯帶狀圖／時間軸＋圖示格／樹狀圖）。
用法：CHROMIUM=... python render_fomc_pre.py <輸出資料夾>；輸出 1.jpg～5.jpg＋sheet.jpg，印「重疊檢查：程式 N 張 M 筆」。
文字（法遵 2fcab0de）：第 2 張「12 月的定價則偏向升息」、第 5 張「常被討論的 3 個管道」一律保留。"""
import sys, io, base64
from pathlib import Path
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p/"docs/marketing/posts/samples_1028/event_v2_lib").exists())/"docs/marketing/posts/samples_1028/event_v2_lib"))
import lib
from lib import *
EXTRA = """
.hd .hname{font-size:40px;font-weight:800;color:#0F2233}
body.cv{background:#EAF2FC;color:#0F2233}
.shade{background:linear-gradient(180deg,rgba(255,255,255,.35) 0%,rgba(255,255,255,0) 14%,rgba(244,248,255,.0) 40%,rgba(244,248,255,.90) 56%,rgba(244,248,255,.98) 70%,#F4F8FF 100%) !important}
.cvtop .brand{color:#0F2233;font-size:44px;text-shadow:0 1px 6px rgba(255,255,255,.7)}
.cvtop .cvdate{color:#0F2233;text-shadow:0 1px 6px rgba(255,255,255,.7)}
.cvt{color:#0F2233 !important;text-shadow:none !important}
.cvt .yy{background:#FFD23F;color:#0F2233;padding:0 14px;border-radius:10px}
.hook{color:#3F35A8 !important}
.cvsub{color:#33485B !important;border-top:2px solid rgba(15,34,51,.18) !important}
.chips{display:flex;gap:14px}
.chips span{font-size:32px;font-weight:800;padding:8px 22px;border-radius:10px;background:#fff;color:#0F2233;box-shadow:0 2px 0 rgba(15,34,51,.08)}
.chips span.a{background:#FFD23F}
.card{background:#fff;border-radius:28px;padding:30px 34px;display:flex;flex-direction:column;gap:20px;flex:1;min-height:0;box-shadow:0 2px 0 rgba(15,34,51,.06)}
.sec{font-size:32px;font-weight:800;color:#3F35A8}
.hr{height:2px;background:rgba(15,34,51,.10);flex:none}
.bar5{height:56px;background:rgba(15,34,51,.10);border-radius:5px;position:relative}
.bar5 i{position:absolute;left:0;top:0;height:100%;border-radius:5px}
.tick{display:flex;justify-content:space-between;font-size:26px;font-weight:600;color:#566B7D}
.lg2{display:flex;align-items:center;gap:18px}
.sw{width:30px;height:30px;border-radius:5px;flex:none}
.tl{display:flex;flex-direction:column;gap:0}
.cell{display:flex;gap:20px;padding:26px 8px}
.ico{width:96px;height:96px;border-radius:20px;display:flex;align-items:center;justify-content:center;flex:none}
.ct{font-size:44px;font-weight:800;line-height:1.3}
.cs{font-size:32px;font-weight:600;color:#33485B;line-height:1.45}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:0;flex:1}
.grid .cell:nth-child(odd){border-right:2px solid rgba(15,34,51,.10)}
.grid .cell:nth-child(-n+2){border-bottom:2px solid rgba(15,34,51,.10)}
.grid .cell{flex-direction:column;justify-content:flex-start;padding:30px 28px;gap:14px}.grid .cs{font-size:29px}
.tree{display:flex;align-items:stretch;flex:1;min-height:0}
.hub{width:210px;align-self:center;background:#5145C8;color:#fff;border-radius:28px;padding:30px 18px;text-align:center;font-size:44px;font-weight:800;line-height:1.35;flex:none}
.hl{width:40px;height:4px;background:#9A93E0;align-self:center;flex:none}
.rows{flex:1;display:flex;flex-direction:column;gap:20px;padding-left:40px;position:relative;min-width:0}
.chan{flex:1;border-radius:20px;padding:20px 26px;display:flex;align-items:center;gap:22px;position:relative}
.chan:before{content:"";position:absolute;left:-40px;top:calc(50% - 2px);width:40px;height:4px;background:#9A93E0}
.chan:after{content:"";position:absolute;left:-40px;width:4px;background:#9A93E0}
.chan.f:after{top:50%;bottom:-20px}.chan.m:after{top:-20px;bottom:-20px}.chan.l:after{top:-20px;bottom:50%}
.chan .ct{font-size:44px}.chan .cs{font-size:31px}
"""
lib.CSS += EXTRA
ASOF = "資料日 10/27・CME FedWatch"; TOT = 5
bgd = "data:image/jpeg;base64," + base64.b64encode((Path(lib.HERE)/"bg"/"fomc_day.jpg").read_bytes()).decode()
def crop(y0, h):
    im = Image.open(Path(lib.HERE)/"bg"/"fomc_day.jpg").convert("RGB").crop((0, y0, 1080, y0+h)); b = io.BytesIO(); im.save(b, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def pin(headline, body, idx, bib=None, bh=100, asof=ASOF):
    f = f'<div class="ft"><span class="d">{asof}</span><span class="pg num">{idx} / {TOT}</span>{bibi(bib, bh) if bib else ""}</div>'
    return (f'<body class="in" style="background:#F0EEFA"><div class="hd"><span class="hname">哩股哩股</span><span class="hdate num">10/28 事件前</span></div>'
            f'<div class="head">{headline}</div><div class="main">{body}</div>{f}</body>')
def cover():
    return (f'<body class="cv"><img class="bgimg" data-bg="1" style="top:-380px" src="{bgd}"><div class="shade"></div>'
            f'<div class="cvtop"><span class="brand">哩股哩股</span><span class="cvdate num">10/28 事件前</span></div>'
            f'<div class="cvbody"><div class="cvt">聯準會利率<br>明天凌晨<span class="yy num">2 點</span>公布</div><div class="hook">利率會變嗎？</div>'
            f'<div class="chips"><span class="num">02:00 公布</span><span class="num">02:30 記者會</span><span class="num a">目前 3.75～4.00%</span></div>'
            f'<div class="cvsub">台灣 10/29（四）02:00 公布・02:30 記者會</div></div></body>')
# ---- 第 2 張：甜甜圈＋條 合併單卡 ----
def donut():
    import math
    r = 112; c = 2*math.pi*r; v = 0.906
    return (f'<svg width="330" height="330" viewBox="0 0 330 330"><g transform="rotate(-90 165 165)" fill="none" stroke-width="58">'
            f'<circle cx="165" cy="165" r="{r}" stroke="#0F2233" stroke-dasharray="{c*v:.1f} {c:.1f}"/>'
            f'<circle cx="165" cy="165" r="{r}" stroke="#B26A00" stroke-dasharray="{c*(1-v)-4:.1f} {c:.1f}" stroke-dashoffset="{-c*v-2:.1f}"/></g>'
            f'<text x="165" y="186" text-anchor="middle" font-family="Inter,DejaVu Sans,sans-serif" font-size="66" font-weight="800" fill="#0F2233">91%</text></svg>')
p2 = (f'<div class="card" style="justify-content:space-between"><div class="sec">10/28 本次會議：持平 vs 升息</div>'
      f'<div class="row" style="gap:36px">{donut()}<div style="flex:1;display:flex;flex-direction:column;gap:26px">'
      f'<div class="lg2"><div class="sw" style="background:#0F2233"></div><div class="lb" style="width:auto;flex:1">持平</div><div class="val num" style="width:auto;color:#0F2233">91%</div></div>'
      f'<div class="lg2"><div class="sw" style="background:#B26A00"></div><div class="lb" style="width:auto;flex:1">升息</div><div class="val num" style="width:auto;color:#8F5600">9%</div></div>'
      f'<div class="note" style="font-size:32px">約 9 成預期持平</div></div></div><div class="hr"></div>'
      f'<div class="row" style="justify-content:space-between"><div class="sec">12 月會議：升息機率</div><div class="val num" style="color:#3F35A8;width:auto">73%起</div></div>'
      f'<div class="bar5" style="height:72px"><i style="width:73%;background:#3F35A8"></i></div>'
      '<div class="tick num" style="position:relative;height:36px;display:block">' + ''.join(f'<span style="position:absolute;left:{v}%;transform:translateX(-{v}%)">{v}%</span>' for v in (0, 25, 50, 75, 100)) + '</div></div>'
      '<div class="unit">CME FedWatch 約 10/27 資料。12 月升息機率各媒體引述 73%～80% 以上，圖取 73%。這是期貨市場定價，不是本帳號的預測</div>')
# ---- 第 3 張：階梯帶狀圖 ----
def stepchart():
    def y(v): return 390 - (v-3.5)*480
    g = ''.join(f'<line x1="120" x2="880" y1="{y(v):.0f}" y2="{y(v):.0f}" stroke="rgba(15,34,51,.14)" stroke-width="2"/><text x="100" y="{y(v)+9:.0f}" text-anchor="end" font-family="Inter,DejaVu Sans,sans-serif" font-size="28" font-weight="600" fill="#566B7D">{v:.2f}</text>' for v in (3.5, 3.75, 4.0, 4.25))
    def band(x, lo, hi, col, txt): return (f'<rect x="{x}" y="{y(hi):.0f}" width="220" height="{(hi-lo)*480:.0f}" rx="5" fill="{col}"/>'
        f'<text x="{x+110}" y="{(y(hi)+y(lo))/2+11:.0f}" text-anchor="middle" font-family="Inter,DejaVu Sans,sans-serif" font-size="32" font-weight="800" fill="#fff">{txt}</text>')
    return (f'<svg width="900" height="450" viewBox="0 0 900 450">{g}'
            + band(120, 3.5, 3.75, "#B26A00", "3.50–3.75%") + band(390, 3.75, 4.0, "#0A7F77", "3.75–4.00%")
            + f'<rect x="660" y="{y(4.25):.0f}" width="220" height="{(4.25-3.5)*480:.0f}" rx="5" fill="rgba(81,69,200,.08)" stroke="#5145C8" stroke-width="3" stroke-dasharray="12 9"/>'
            + f'<text x="770" y="{(y(4.25)+y(3.5))/2+30:.0f}" text-anchor="middle" font-family="Inter,DejaVu Sans,sans-serif" font-size="96" font-weight="800" fill="#5145C8">？</text>'
            + ''.join(f'<text x="{x}" y="438" text-anchor="middle" font-family="Inter,DejaVu Sans,sans-serif" font-size="30" font-weight="700" fill="#33485B">{t}</text>' for x, t in ((230, "2025/12"), (500, "2026/09"), (770, "10/29 凌晨")))
            + '</svg>')
p3 = (f'<div class="card" style="gap:16px"><img style="width:100%;height:290px;object-fit:cover;border-radius:20px;flex:none" src="{crop(500, 290)}">'
      f'<div class="sec">聯邦基金利率目標區間（%）</div>{stepchart()}'
      f'<div class="chips" style="justify-content:space-between"><span style="background:#FFF0D1">降息 1 碼</span><span style="background:#DDF1EE">升息 1 碼（12 比 0）</span><span style="background:#ECE8FA">02:00 公布</span></div></div>')
# ---- 第 4 張：時間軸＋2×2 圖示格 ----
def tline():
    return ('<svg width="900" height="175" viewBox="0 0 900 175"><line x1="80" x2="820" y1="44" y2="44" stroke="#9A93E0" stroke-width="6" stroke-linecap="round"/>'
            '<circle cx="80" cy="44" r="22" fill="#5145C8"/><circle cx="450" cy="44" r="22" fill="#B26A00"/><circle cx="820" cy="44" r="22" fill="none" stroke="#5145C8" stroke-width="5" stroke-dasharray="6 6"/>'
            '<g font-family="Inter,DejaVu Sans,sans-serif" font-size="34" font-weight="800" fill="#0F2233" text-anchor="middle">'
            '<text x="80" y="112">02:00</text><text x="450" y="112">02:30</text><text x="820" y="112">之後</text></g>'
            '<g font-size="28" font-weight="600" fill="#566B7D" text-anchor="middle" font-family="Noto Sans CJK TC,sans-serif">'
            '<text x="80" y="162" >公布聲明</text><text x="450" y="162">記者會</text><text x="820" y="162" >看反應</text></g></svg>')
def cell(ic, col, bg, t, s): return f'<div class="cell"><div class="ico" style="background:{bg}">{icon(ic, col, 60)}</div><div class="ct">{t}</div><div class="cs">{s}</div></div>'
p4 = (f'<div class="card" style="gap:6px"><div class="sec">凌晨的時間軸</div>{tline()}<div class="hr" style="margin-top:6px"></div><div class="grid">'
      + cell("quote", "#5145C8", "#E2ECFA", "1　聲明措辭", "對通膨與就業的描述有沒有改")
      + cell("flag", "#0A7F77", "#DDF1EE", "2　投票結果", "有沒有人投反對票")
      + cell("clock", "#B26A00", "#FFF0D1", "3　02:30 記者會", "對 12 月的說法")
      + cell("chart", "#3F35A8", "#ECE8FA", "4　本次沒有點陣圖", "不是經濟預測（SEP）會議")
      + '</div></div>')
# ---- 第 5 張：樹狀圖 ----
def chan(k, ic, col, bg, t, s, pos): return f'<div class="chan {pos}" style="background:{bg}"><div class="ico" style="background:#fff">{icon(ic, col, 60)}</div><div><div class="ct">{k}　{t}</div><div class="cs">{s}</div></div></div>'
p5 = ('<div class="card" style="gap:22px"><div class="sec">利率預期 → 市場的三條路</div><div class="tree"><div class="hub">利率<br>預期<br>變動</div><div class="hl"></div><div class="rows">'
      + chan("1", "coin", "#5145C8", "#E2ECFA", "美元", "反映利差預期，升降方向都可能", "f")
      + chan("2", "pct", "#0A7F77", "#DDF1EE", "美債殖利率", "常隨利率預期調整", "m")
      + chan("3", "chart", "#B26A00", "#FFF0D1", "股票估值", "折現率隨利率預期改變", "l")
      + f'</div></div><div class="hr"></div><div class="note"><b>收藏這張</b>，明天凌晨公布後回來對照<br><span style="font-size:30px;color:{INK3}">只說明傳導管道，不預測方向、非投資建議</span></div></div>')
P = [cover(),
 pin('明天約 <span class="y num">9 成</span>預期持平；<br>12 月的定價則偏向升息', p2, 2, "face_think", 100),
 pin('利率現在在 <span class="y num">3.75～4.00%</span>', p3, 3, "calendar", 100),
 pin('明天凌晨看這 <span class="y num">4</span> 件事', p4, 4, "magnifier", 100),
 pin('利率預期變動時，<br>常被討論的 <span class="y num">3</span> 個管道', p5, 5, "coins", 100),
]
if __name__ == "__main__":
    out = Path(sys.argv[1]); render(P, out)
    sheet(out, [f"{i}.jpg" for i in range(1, 6)], out/"sheet.jpg", 5, 360)
